import pickle
import json
import numpy as np
import faiss
from pathlib import Path
from tqdm import tqdm

import torch
from torch.utils.data import DataLoader

from train import (
    DraftDataset,
    collate_fn,
    DOMAIN_PRO,
    DOMAIN_SOLOQ,
)
from inference import load_model

def extract_cls_vectors(
    model,
    df,
    device,
    batch_size
):
    pass

