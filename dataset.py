import torch
import torch.nn as nn
import torch.nn.functional as F
import pandas as pd
import numpy as np
from torch.utils.data import Dataset, DataLoader
import urllib.request
import io


# ==========================================
# 3. Dataset and Data Loading
# ==========================================
class ETTForecastDataset(Dataset):
    def __init__(self, data, lookback=256, horizon=96):
        self.data = torch.tensor(data, dtype=torch.float32)
        self.lookback = lookback
        self.horizon = horizon

    def __len__(self):
        return len(self.data) - self.lookback - self.horizon + 1

    def __getitem__(self, idx):
        # Frozen task (plan/gates/gate1/gate1_task.md §1-3): input window + disjoint next-H
        # window. Windows are stride-1 (they overlap heavily by design) and never span
        # a split boundary.
        x = self.data[idx : idx + self.lookback]                              # [L, F]
        y = self.data[idx + self.lookback : idx + self.lookback + self.horizon]  # [H, F]
        return x, y

def _standardize(x, mean, std):
    """Per-feature z-score using PRE-FITTED stats (train-fitted for all splits)."""
    return (x - mean) / std


def download_and_preprocess_etth1(return_stats=False):
    print("Downloading ETTh1 dataset...")
    url = "https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh1.csv"
    response = urllib.request.urlopen(url)
    df = pd.read_csv(io.BytesIO(response.read()))
    
    # Use the 7 main features (HUFL, HULL, MUFL, MULL, LUFL, LULL, OT)
    cols = ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]
    data = df[cols].values
    
    # Chronological 60/20/20 split on the RAW row axis (before normalization).
    # This is the split contract (plan/gates/gate1/gate1_task.md §4) — no future stats leak.
    n = len(data)
    train_rows = data[:int(n*0.6)]
    val_rows = data[int(n*0.6):int(n*0.8)]
    test_rows = data[int(n*0.8):]
    
    # Per-feature z-score: mean/std fit on the TRAIN split ONLY (plan/gates/gate1/gate1_task.md §5);
    # the same train-fitted stats are applied to val and test — they are never
    # re-centered/re-scaled by their own statistics.
    mean = train_rows.mean(axis=0)
    std = train_rows.std(axis=0)
    
    train_data = _standardize(train_rows, mean, std)
    val_data = _standardize(val_rows, mean, std)
    test_data = _standardize(test_rows, mean, std)
    
    if return_stats:
        return train_data, val_data, test_data, {"mean": mean, "std": std}
    return train_data, val_data, test_data