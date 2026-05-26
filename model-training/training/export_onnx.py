#!/usr/bin/env python3
"""
Export DraftTransformer model to ONNX format for cross-platform deployment.
"""

import argparse
import json
import pickle
from pathlib import Path

import torch
import torch.nn as nn

from train import (
    DraftTransformer,
    CHAMPION_VOCAB,
    build_damage_matrix,
    build_tag_matrix,
)


class ONNXExportWrapper(nn.Module):
    """
    Wrapper to convert dict-style forward to tensor inputs for ONNX compatibility.
    ONNX doesn't support dict inputs, so we flatten them to individual tensors.
    """
    def __init__(self, base_model: DraftTransformer, tag_matrix: torch.Tensor, damage_matrix: torch.Tensor):
        super().__init__()
        self.model = base_model
        # Register static matrices as buffers for ONNX export
        self.register_buffer("tag_matrix", tag_matrix)
        self.register_buffer("damage_matrix", damage_matrix)
        # Register on the base model too
        self.model.register_static_features(tag_matrix, damage_matrix)

    def forward(
        self,
        champion_ids: torch.Tensor,
        sides: torch.Tensor,
        phases: torch.Tensor,
        lanes: torch.Tensor,
        event_types: torch.Tensor,
        domain: torch.Tensor,
        target_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:

        B, S = champion_ids.shape
        # Domain is [B], expand to [B, S] for broadcasting
        domain_expanded = domain.unsqueeze(1).expand(B, S)

        # is_pick is derived from event_types (EVENT_PICK = 1)
        is_pick = event_types == 1

        batch = {
            "champion_ids": champion_ids,
            "sides": sides,
            "phases": phases,
            "lanes": lanes,
            "event_types": event_types,
            "domain": domain_expanded,
            "is_pick": is_pick,
        }

        # Call the full forward pass with optional target_mask
        return self.model(batch, target_mask=target_mask)


def export_to_onnx(
    checkpoint_path: Path,
    tag_df_path: Path,
    damage_df_path: Path,
    output_path: Path,
    opset_version: int = 17,
    validate: bool = True,
) -> None:
    """
    Export a trained DraftTransformer checkpoint to ONNX format.

    Args:
        checkpoint_path: Path to the .pt checkpoint file
        tag_df_path: Path to the tag dataframe pickle
        damage_df_path: Path to the damage dataframe pickle
        output_path: Output path for the .onnx file
        opset_version: ONNX opset version (default 17 for better transformer support)
        validate: Whether to validate the exported model
    """
    device = torch.device("cpu")  # Export on CPU for compatibility

    print(f"Loading checkpoint from {checkpoint_path}")
    ckpt = torch.load(checkpoint_path, map_location=device)

    args = ckpt["args"]
    num_tags = ckpt["num_tags"]

    print(f"Loading tag matrix from {tag_df_path}")
    with open(tag_df_path, "rb") as f:
        tag_df = pickle.load(f)

    print(f"Loading damage matrix from {damage_df_path}")
    with open(damage_df_path, "rb") as f:
        damage_df = pickle.load(f)

    damage_matrix = build_damage_matrix(damage_df)
    tag_matrix, valid_tags = build_tag_matrix(tag_df, damage_df)

    print(f"Initializing model (d_model={args.get('d_model', 256)}, layers={args.get('n_layers', 4)})")
    model = DraftTransformer(
        num_tags=num_tags,
        d_model=args.get("d_model", 256),
        n_heads=args.get("n_heads", 8),
        num_layers=args.get("n_layers", 4),
        ffn_dim=args.get("ffn_dim", 1024),
        dropout=0.0,  # Disable dropout for inference
    ).to(device)

    model.register_static_features(tag_matrix.to(device), damage_matrix.to(device))
    model.load_state_dict(ckpt["model"])
    model.eval()

    # Wrap for ONNX export (pass static matrices to register as buffers)
    wrapped = ONNXExportWrapper(model, tag_matrix.to(device), damage_matrix.to(device)).to(device)
    wrapped.eval()

    # Get static matrix numpy versions for validation
    tag_matrix_np = tag_matrix.cpu().numpy()
    damage_matrix_np = damage_matrix.cpu().numpy()

    # Create dummy inputs for tracing
    # Shape: [batch_size, sequence_length=20]
    batch_size = 1
    seq_len = 20

    dummy_inputs = (
        torch.randint(0, CHAMPION_VOCAB, (batch_size, seq_len), dtype=torch.long, device=device),  # champion_ids
        torch.randint(0, 2, (batch_size, seq_len), dtype=torch.long, device=device),            # sides
        torch.randint(0, 3, (batch_size, seq_len), dtype=torch.long, device=device),            # phases
        torch.randint(0, 6, (batch_size, seq_len), dtype=torch.long, device=device),             # lanes
        torch.randint(0, 2, (batch_size, seq_len), dtype=torch.long, device=device),              # event_types
        torch.randint(0, 2, (batch_size,), dtype=torch.long, device=device),                      # domain
        torch.zeros(batch_size, seq_len, dtype=torch.bool, device=device),                        # target_mask (optional)
    )

    input_names = [
        "champion_ids",
        "sides",
        "phases",
        "lanes",
        "event_types",
        "domain",
        "target_mask",
    ]

    output_names = ["pick_ban_logits", "win_probability_logit"]

    dynamic_axes = {
        "champion_ids": {0: "batch_size"},
        "sides": {0: "batch_size"},
        "phases": {0: "batch_size"},
        "lanes": {0: "batch_size"},
        "event_types": {0: "batch_size"},
        "domain": {0: "batch_size"},
        "target_mask": {0: "batch_size"},
        "pick_ban_logits": {0: "batch_size"},
        "win_probability_logit": {0: "batch_size"},
    }

    print(f"Exporting to ONNX format (opset {opset_version})...")
    print(f"Output: {output_path}")

    torch.onnx.export(
        wrapped,
        dummy_inputs,
        output_path,
        input_names=input_names,
        output_names=output_names,
        dynamic_axes=dynamic_axes,
        opset_version=opset_version,
        do_constant_folding=True,
        export_params=True,
    )

    print("Export complete!")

    # Export metadata alongside the model
    metadata_path = output_path.with_suffix(".json")
    metadata = {
        "model_type": "DraftTransformer",
        "champion_vocab": CHAMPION_VOCAB,
        "num_tags": num_tags,
        "d_model": args.get("d_model", 256),
        "n_heads": args.get("n_heads", 8),
        "num_layers": args.get("n_layers", 4),
        "ffn_dim": args.get("ffn_dim", 1024),
        "valid_tags": valid_tags,
        "opset_version": opset_version,
        "static_matrices": {
            "tag_matrix": {"shape": [CHAMPION_VOCAB, num_tags], "dtype": "float32"},
            "damage_matrix": {"shape": [CHAMPION_VOCAB, 3], "dtype": "float32"},
        },
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata exported to {metadata_path}")

    if validate:
        print("Validating ONNX model...")
        try:
            import onnx
            import onnxruntime as ort

            # Load and check model
            onnx_model = onnx.load(output_path)
            onnx.checker.check_model(onnx_model)
            print("ONNX model validation passed!")

            # Test inference
            session = ort.InferenceSession(output_path)

            test_inputs = {
                "champion_ids": dummy_inputs[0].numpy(),
                "sides": dummy_inputs[1].numpy(),
                "phases": dummy_inputs[2].numpy(),
                "lanes": dummy_inputs[3].numpy(),
                "event_types": dummy_inputs[4].numpy(),
                "domain": dummy_inputs[5].numpy(),
                "target_mask": dummy_inputs[6].numpy(),
            }

            outputs = session.run(None, test_inputs)
            print(f"ONNX Runtime test passed!")
            print(f"  Pick/ban logits shape: {outputs[0].shape}")
            print(f"  Win probability logit shape: {outputs[1].shape}")

        except ImportError:
            print("Skipping validation (onnx/onnxruntime not installed)")
        except Exception as e:
            print(f"Validation warning: {e}")


def main():
    parser = argparse.ArgumentParser(description="Export DraftTransformer to ONNX")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        required=True,
        help="Path to the .pt checkpoint file",
    )
    parser.add_argument(
        "--tags",
        type=Path,
        default=Path("data/annotated_abilities_df.pkl"),
        help="Path to tag dataframe pickle",
    )
    parser.add_argument(
        "--damage",
        type=Path,
        default=Path("data/champion_damage_breakdown.pkl"),
        help="Path to damage dataframe pickle",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output ONNX file path (default: checkpoint directory)",
    )
    parser.add_argument(
        "--opset",
        type=int,
        default=17,
        help="ONNX opset version (default: 17)",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip validation after export",
    )

    args = parser.parse_args()

    if args.output is None:
        args.output = args.checkpoint.parent / "model.onnx"

    export_to_onnx(
        checkpoint_path=args.checkpoint,
        tag_df_path=args.tags,
        damage_df_path=args.damage,
        output_path=args.output,
        opset_version=args.opset,
        validate=not args.no_validate,
    )


if __name__ == "__main__":
    main()
