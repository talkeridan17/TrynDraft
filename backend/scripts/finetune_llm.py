#!/usr/bin/env python3
"""
Fine-tuning script for TrynDraft LLM.

Options:
1. Local fine-tuning with Unsloth (recommended for fast, efficient training)
2. HuggingFace fine-tuning with LoRA
3. Export to GGUF for llama.cpp inference

Prerequisites:
    pip install unsloth transformers datasets peft accelerate bitsandbytes

Usage:
    python scripts/finetune_llm.py --method unsloth --model mistral-7b
    python scripts/finetune_llm.py --method lora --model llama-3.2-1b
    python scripts/finetune_llm.py --export-gguf  # Export to GGUF after training
"""
import sys
import os
import json
import logging
import argparse
from pathlib import Path
from typing import List, Dict
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Model configurations
MODELS = {
    "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.3",
    "llama-3.2-1b": "meta-llama/Llama-3.2-1B-Instruct",
    "llama-3.2-3b": "meta-llama/Llama-3.2-3B-Instruct",
    "qwen-1.5b": "Qwen/Qwen2.5-1.5B-Instruct",
    "phi-3-mini": "microsoft/Phi-3-mini-4k-instruct",
}


def load_training_data(data_path: str) -> List[Dict]:
    """Load training data from JSONL file."""
    data = []
    with open(data_path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            # Filter to chat format (messages key)
            if 'messages' in item:
                data.append(item)
    logger.info(f"Loaded {len(data)} training examples")
    return data


def format_for_training(examples: List[Dict]) -> List[str]:
    """Format examples for instruction tuning."""
    formatted = []
    for ex in examples:
        messages = ex.get('messages', [])
        if len(messages) >= 2:
            user_msg = messages[0]['content']
            assistant_msg = messages[1]['content']
            # Format as instruction-response
            text = f"### Instruction:\n{user_msg}\n\n### Response:\n{assistant_msg}"
            formatted.append(text)
    return formatted


def finetune_with_unsloth(
    model_name: str,
    training_data: List[Dict],
    output_dir: str,
    epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 2e-4,
    max_seq_length: int = 2048
):
    """Fine-tune using Unsloth for 2-5x faster training."""
    try:
        from unsloth import FastLanguageModel
        from unsloth import is_bfloat16_supported
        from transformers import TrainingArguments
        from trl import SFTTrainer
        from datasets import Dataset
    except ImportError:
        logger.error("Unsloth not installed. Run: pip install unsloth")
        logger.info("Alternative: pip install 'unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git'")
        return None

    logger.info(f"Loading model: {model_name}")

    # Load model with 4-bit quantization
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODELS.get(model_name, model_name),
        max_seq_length=max_seq_length,
        dtype=None,  # Auto-detect
        load_in_4bit=True,
    )

    # Add LoRA adapters
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,  # LoRA rank
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                       "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    # Prepare dataset
    texts = format_for_training(training_data)
    dataset = Dataset.from_dict({"text": texts})

    logger.info(f"Training on {len(texts)} examples")

    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=learning_rate,
        weight_decay=0.01,
        warmup_steps=50,
        logging_steps=10,
        save_strategy="epoch",
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        optim="adamw_8bit",
    )

    # Trainer
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        args=training_args,
    )

    # Train
    logger.info("Starting training...")
    trainer.train()

    # Save
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info(f"Model saved to {output_dir}")

    return model, tokenizer


def finetune_with_lora(
    model_name: str,
    training_data: List[Dict],
    output_dir: str,
    epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 2e-4
):
    """Fine-tune using standard HuggingFace with LoRA."""
    try:
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            TrainingArguments,
            BitsAndBytesConfig
        )
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from trl import SFTTrainer
        from datasets import Dataset
        import torch
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.info("Install with: pip install transformers peft trl datasets bitsandbytes")
        return None

    logger.info(f"Loading model: {model_name}")

    # 4-bit quantization config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        MODELS.get(model_name, model_name),
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(
        MODELS.get(model_name, model_name),
        trust_remote_code=True
    )
    tokenizer.pad_token = tokenizer.eos_token

    # Prepare for k-bit training
    model = prepare_model_for_kbit_training(model)

    # LoRA config
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
    )

    model = get_peft_model(model, lora_config)

    # Prepare dataset
    texts = format_for_training(training_data)
    dataset = Dataset.from_dict({"text": texts})

    logger.info(f"Training on {len(texts)} examples")

    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=learning_rate,
        weight_decay=0.01,
        warmup_steps=50,
        logging_steps=10,
        save_strategy="epoch",
        fp16=True,
    )

    # Trainer
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        args=training_args,
    )

    # Train
    logger.info("Starting training...")
    trainer.train()

    # Save
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info(f"Model saved to {output_dir}")

    return model, tokenizer


def export_to_gguf(model_dir: str, output_path: str = None):
    """Export fine-tuned model to GGUF format for llama.cpp."""
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        logger.error("Unsloth required for GGUF export. Run: pip install unsloth")
        return None

    if output_path is None:
        output_path = os.path.join(model_dir, "model.gguf")

    logger.info(f"Loading model from {model_dir}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_dir,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )

    logger.info(f"Exporting to GGUF: {output_path}")
    # Save as GGUF (requires llama.cpp conversion)
    model.save_pretrained_gguf(output_path, tokenizer, quantization_method="q4_k_m")
    logger.info(f"GGUF model saved to {output_path}")

    return output_path


def upload_to_huggingface(model_dir: str, repo_name: str, token: str = None):
    """Upload fine-tuned model to HuggingFace Hub."""
    try:
        from huggingface_hub import HfApi, login
    except ImportError:
        logger.error("huggingface_hub not installed. Run: pip install huggingface_hub")
        return None

    if token:
        login(token=token)

    api = HfApi()

    logger.info(f"Uploading model to {repo_name}")
    api.upload_folder(
        folder_path=model_dir,
        repo_id=repo_name,
        repo_type="model"
    )

    logger.info(f"Model uploaded to https://huggingface.co/{repo_name}")
    return f"https://huggingface.co/{repo_name}"


def main():
    parser = argparse.ArgumentParser(description="Fine-tune LLM for TrynDraft")
    parser.add_argument("--method", choices=["unsloth", "lora"], default="lora",
                       help="Fine-tuning method")
    parser.add_argument("--model", default="qwen-1.5b",
                       help=f"Model to fine-tune. Options: {list(MODELS.keys())}")
    parser.add_argument("--data", default="training_data/training_data.jsonl",
                       help="Path to training data")
    parser.add_argument("--output", default="models/finetuned_lol_advisor",
                       help="Output directory for fine-tuned model")
    parser.add_argument("--epochs", type=int, default=3,
                       help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4,
                       help="Training batch size")
    parser.add_argument("--export-gguf", action="store_true",
                       help="Export to GGUF format after training")
    parser.add_argument("--upload", type=str, default=None,
                       help="HuggingFace repo name to upload to (e.g., username/model-name)")

    args = parser.parse_args()

    # Check if training data exists
    if not os.path.exists(args.data):
        logger.error(f"Training data not found: {args.data}")
        logger.info("Run: python scripts/scrape_llm_training.py first")
        return

    # Load training data
    training_data = load_training_data(args.data)

    if len(training_data) < 10:
        logger.warning(f"Only {len(training_data)} examples. Recommend at least 100 for good results.")

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Fine-tune
    if args.method == "unsloth":
        result = finetune_with_unsloth(
            args.model,
            training_data,
            args.output,
            epochs=args.epochs,
            batch_size=args.batch_size
        )
    else:
        result = finetune_with_lora(
            args.model,
            training_data,
            args.output,
            epochs=args.epochs,
            batch_size=args.batch_size
        )

    if result is None:
        logger.error("Fine-tuning failed")
        return

    # Export to GGUF if requested
    if args.export_gguf:
        export_to_gguf(args.output)

    # Upload if requested
    if args.upload:
        token = os.getenv("HF_TOKEN")
        upload_to_huggingface(args.output, args.upload, token)

    logger.info("Fine-tuning complete!")
    logger.info(f"Model saved to: {args.output}")
    logger.info("To use this model, update FINE_TUNED_MODEL_ID in your .env file")


if __name__ == "__main__":
    main()
