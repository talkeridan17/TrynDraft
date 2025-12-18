# backend/app/services/llm_fine_tuning.py
import os
import json
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
import httpx
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class LLMFineTuningService:
    """Service for fine-tuning LLMs with League of Legends data."""
    
    def __init__(self, db: Session):
        self.db = db
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_base_url = "https://api.openai.com/v1"
        
        # HuggingFace for open-source models
        self.huggingface_token = os.getenv("HUGGINGFACE_TOKEN")
        self.huggingface_api_url = "https://api-inference.huggingface.co"
        
        # Supported models
        self.supported_models = {
            'openai': ['gpt-3.5-turbo', 'gpt-4-turbo-preview'],
            'huggingface': ['mistral-7b', 'llama-2-7b', 'codellama-7b']
        }
    
    async def prepare_training_data(self, content: List[Dict]) -> List[Dict]:
        """Prepare scraped content for LLM training."""
        training_examples = []
        
        for item in content:
            # Create prompt-completion pairs
            prompt = f"Analyze this League of Legends content: {item['content'][:500]}"
            
            # Generate completion based on content type
            completion = self.generate_completion(item)
            
            if completion:
                training_examples.append({
                    "prompt": prompt,
                    "completion": completion,
                    "metadata": {
                        "source": item['source'],
                        "url": item['url'],
                        "champion": item.get('champion'),
                        "role": item.get('role'),
                        "tags": item.get('tags', []),
                        "created_at": item['created_at']
                    }
                })
        
        return training_examples
    
    def generate_completion(self, item: Dict) -> Optional[str]:
        """Generate completion text for training data."""
        source = item['source']
        content = item['content']
        
        if source == 'mobafire':
            return f"This is a League of Legends guide. Key points: {content[:300]}"
        elif source == 'lolalytics':
            return f"Statistical analysis of League of Legends meta. Data shows: {content[:300]}"
        elif source == 'reddit':
            return f"Community discussion about League of Legends. Main topic: {content[:300]}"
        elif source == 'opgg':
            return f"Champion statistics from OP.GG. Current meta data: {content[:300]}"
        else:
            return f"League of Legends content: {content[:300]}"
    
    async def create_fine_tuning_job(
        self,
        model_provider: str,
        model_name: str,
        training_data: List[Dict],
        hyperparameters: Dict = None
    ) -> Optional[str]:
        """Create a fine-tuning job with the specified provider."""
        
        if hyperparameters is None:
            hyperparameters = {
                "n_epochs": 3,
                "batch_size": 4,
                "learning_rate_multiplier": 0.1
            }
        
        if model_provider == 'openai':
            return await self.create_openai_fine_tuning_job(
                model_name, training_data, hyperparameters
            )
        elif model_provider == 'huggingface':
            return await self.create_huggingface_fine_tuning_job(
                model_name, training_data, hyperparameters
            )
        else:
            logger.error(f"Unsupported model provider: {model_provider}")
            return None
    
    async def create_openai_fine_tuning_job(
        self,
        model_name: str,
        training_data: List[Dict],
        hyperparameters: Dict
    ) -> Optional[str]:
        """Create fine-tuning job with OpenAI."""
        if not self.openai_api_key:
            logger.error("OpenAI API key not configured")
            return None
        
        # Prepare data in OpenAI format
        formatted_data = []
        for example in training_data:
            formatted_data.append({
                "messages": [
                    {"role": "user", "content": example["prompt"]},
                    {"role": "assistant", "content": example["completion"]}
                ]
            })
        
        # Save training data to file
        training_file = f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        with open(training_file, 'w') as f:
            for item in formatted_data:
                f.write(json.dumps(item) + '\n')
        
        try:
            # Upload file to OpenAI
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.openai_api_key}"
                }
                
                # Upload file
                with open(training_file, 'rb') as f:
                    files = {'file': (training_file, f, 'application/jsonl')}
                    data = {'purpose': 'fine-tune'}
                    
                    upload_response = await client.post(
                        f"{self.openai_base_url}/files",
                        headers=headers,
                        files=files,
                        data=data
                    )
                    
                    if upload_response.status_code != 200:
                        logger.error(f"Failed to upload file: {upload_response.text}")
                        return None
                    
                    file_id = upload_response.json()['id']
                
                # Create fine-tuning job
                job_data = {
                    "training_file": file_id,
                    "model": model_name,
                    **hyperparameters
                }
                
                job_response = await client.post(
                    f"{self.openai_base_url}/fine_tuning/jobs",
                    headers=headers,
                    json=job_data
                )
                
                if job_response.status_code != 200:
                    logger.error(f"Failed to create job: {job_response.text}")
                    return None
                
                job_id = job_response.json()['id']
                logger.info(f"Created OpenAI fine-tuning job: {job_id}")
                return job_id
                
        except Exception as e:
            logger.error(f"Error creating OpenAI fine-tuning job: {str(e)}")
            return None
        
        finally:
            # Clean up training file
            if os.path.exists(training_file):
                os.remove(training_file)
    
    async def create_huggingface_fine_tuning_job(
        self,
        model_name: str,
        training_data: List[Dict],
        hyperparameters: Dict
    ) -> Optional[str]:
        """Create fine-tuning job with HuggingFace."""
        if not self.huggingface_token:
            logger.error("HuggingFace token not configured")
            return None
        
        # Prepare data in HuggingFace format
        formatted_data = []
        for example in training_data:
            formatted_data.append({
                "text": f"{example['prompt']} {example['completion']}"
            })
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.huggingface_token}",
                    "Content-Type": "application/json"
                }
                
                # Create dataset
                dataset_data = {
                    "name": f"tryndraft_training_{datetime.now().strftime('%Y%m%d')}",
                    "data": formatted_data,
                    "description": "League of Legends training data for TrynDraft"
                }
                
                dataset_response = await client.post(
                    f"{self.huggingface_api_url}/datasets",
                    headers=headers,
                    json=dataset_data
                )
                
                if dataset_response.status_code != 200:
                    logger.error(f"Failed to create dataset: {dataset_response.text}")
                    return None
                
                dataset_id = dataset_response.json()['id']
                
                # Create fine-tuning job
                job_data = {
                    "model": model_name,
                    "dataset": dataset_id,
                    "config": {
                        "training_args": {
                            "num_train_epochs": hyperparameters.get("n_epochs", 3),
                            "per_device_train_batch_size": hyperparameters.get("batch_size", 4),
                            "learning_rate": hyperparameters.get("learning_rate_multiplier", 0.1) * 5e-5,
                            "warmup_steps": 100,
                            "weight_decay": 0.01,
                            "logging_steps": 10,
                            "save_steps": 100
                        }
                    }
                }
                
                job_response = await client.post(
                    f"{self.huggingface_api_url}/training",
                    headers=headers,
                    json=job_data
                )
                
                if job_response.status_code != 200:
                    logger.error(f"Failed to create job: {job_response.text}")
                    return None
                
                job_id = job_response.json()['id']
                logger.info(f"Created HuggingFace fine-tuning job: {job_id}")
                return job_id
                
        except Exception as e:
            logger.error(f"Error creating HuggingFace fine-tuning job: {str(e)}")
            return None
    
    async def check_job_status(self, provider: str, job_id: str) -> Dict:
        """Check the status of a fine-tuning job."""
        if provider == 'openai':
            return await self.check_openai_job_status(job_id)
        elif provider == 'huggingface':
            return await self.check_huggingface_job_status(job_id)
        else:
            return {"status": "UNKNOWN", "error": "Unsupported provider"}
    
    async def check_openai_job_status(self, job_id: str) -> Dict:
        """Check OpenAI fine-tuning job status."""
        if not self.openai_api_key:
            return {"status": "ERROR", "error": "API key not configured"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.openai_api_key}"
                }
                
                response = await client.get(
                    f"{self.openai_base_url}/fine_tuning/jobs/{job_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": data.get("status", "UNKNOWN"),
                        "model": data.get("fine_tuned_model"),
                        "created_at": data.get("created_at"),
                        "finished_at": data.get("finished_at"),
                        "error": data.get("error")
                    }
                else:
                    return {"status": "ERROR", "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
    
    async def check_huggingface_job_status(self, job_id: str) -> Dict:
        """Check HuggingFace fine-tuning job status."""
        if not self.huggingface_token:
            return {"status": "ERROR", "error": "Token not configured"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.huggingface_token}"
                }
                
                response = await client.get(
                    f"{self.huggingface_api_url}/training/{job_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": data.get("status", "UNKNOWN"),
                        "metrics": data.get("metrics"),
                        "created_at": data.get("created_at"),
                        "finished_at": data.get("finished_at"),
                        "error": data.get("error")
                    }
                else:
                    return {"status": "ERROR", "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
    
    async def generate_with_fine_tuned_model(
        self,
        provider: str,
        model_name: str,
        prompt: str
    ) -> str:
        """Generate text using a fine-tuned model."""
        if provider == 'openai':
            return await self.generate_with_openai(model_name, prompt)
        elif provider == 'huggingface':
            return await self.generate_with_huggingface(model_name, prompt)
        else:
            return "Unsupported model provider"
    
    async def generate_with_openai(self, model_name: str, prompt: str) -> str:
        """Generate text using OpenAI fine-tuned model."""
        if not self.openai_api_key:
            return "OpenAI API key not configured"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": model_name,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                }
                
                response = await client.post(
                    f"{self.openai_base_url}/chat/completions",
                    headers=headers,
                    json=data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content']
                else:
                    return f"Error: {response.status_code}"
                    
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def generate_with_huggingface(self, model_name: str, prompt: str) -> str:
        """Generate text using HuggingFace fine-tuned model."""
        if not self.huggingface_token:
            return "HuggingFace token not configured"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.huggingface_token}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 500,
                        "temperature": 0.7,
                        "do_sample": True
                    }
                }
                
                response = await client.post(
                    f"{self.huggingface_api_url}/models/{model_name}",
                    headers=headers,
                    json=data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result[0]['generated_text']
                else:
                    return f"Error: {response.status_code}"
                    
        except Exception as e:
            return f"Error: {str(e)}"