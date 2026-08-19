"""Side-by-side comparison of CSAAttention vs ModifiedCSAAttention with fixed seed."""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from dataset import ETTForecastDataset, download_and_preprocess_etth1
from model import (CSATimeSeriesModel, ModifiedCSATimeSeriesModel, NormalTimeSeriesModel,
                   FlatPlusTimeSeriesModel, ExpertFlatTimeSeriesModel,
                   ExpertPlusPlusTimeSeriesModel)

SEED = 42
torch.manual_seed(SEED)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}\n")

LOOKBACK = 256
HORIZON = 96
BATCH_SIZE = 32
EPOCHS = 10

train_data, val_data, test_data = download_and_preprocess_etth1()
train_dataset = ETTForecastDataset(train_data, LOOKBACK, HORIZON)
val_dataset   = ETTForecastDataset(val_data, LOOKBACK, HORIZON)
test_dataset  = ETTForecastDataset(test_data, LOOKBACK, HORIZON)

val_loader   = DataLoader(val_dataset,   batch_size=BATCH_SIZE, shuffle=False)
test_loader  = DataLoader(test_dataset,  batch_size=BATCH_SIZE, shuffle=False)

num_features = train_data.shape[1]
criterion = nn.MSELoss()

@torch.no_grad()
def evaluate(model, loader):
    model.eval()
    total = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        loss = criterion(model(x), y)  # out=[B,96,7], full horizon scored
        total += loss.item()
    return total / len(loader)

def train_model(ModelClass, name):
    torch.manual_seed(SEED)
    # Create fresh DataLoader to avoid shared iterator state
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    model = ModelClass(num_features=num_features, hidden_size=128,
                       lookback=LOOKBACK, horizon=HORIZON).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-5)

    print(f"\n  {'Epoch':>6} | {'Train MSE':>10} | {'Val MSE':>8} | {'Test MSE':>8}")
    print(f"  {'-'*6}-+-{'-'*10}-+-{'-'*8}-+-{'-'*8}")
    for epoch in range(EPOCHS):
        model.train()
        total = 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            loss = criterion(model(x), y)  # out=[B,96,7], full horizon scored
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0)
            opt.step()
            total += loss.item()
        train_loss = total / len(train_loader)
        val_loss = evaluate(model, val_loader)
        test_loss = evaluate(model, test_loader)
        print(f"  {epoch+1:>5}  | {train_loss:>10.4f} | {val_loss:>8.4f} | {test_loss:>8.4f}")
    final_val = evaluate(model, val_loader)
    final_test = evaluate(model, test_loader)
    return final_val, final_test

print("─── Flat CSAAttention ─────────────────────────────")
flat_val, flat_test = train_model(CSATimeSeriesModel, "Flat")

print("\n─── ModifiedCSAAttention ───────────────────────────")
mod_val, mod_test = train_model(ModifiedCSATimeSeriesModel, "Modified")

print("\n─── Normal Attention ─────────────────────────────────")
norm_val, norm_test = train_model(NormalTimeSeriesModel, "Normal")

print("\n─── FlatPlus Attention ──────────────────────────────")
fp_val, fp_test = train_model(FlatPlusTimeSeriesModel, "FlatPlus")

print("\n─── ExpertFlat Attention ────────────────────────────")
exf_val, exf_test = train_model(ExpertFlatTimeSeriesModel, "ExpertFlat")

print("\n─── ExpertPlusPlus Attention ─────────────────────────")
epp_val, epp_test = train_model(ExpertPlusPlusTimeSeriesModel, "ExpertPlusPlus")

print(f"\n{'='*60}")
print(f"  {'Model':>24}  | {'Val MSE':>8} | {'Test MSE':>8}")
print(f"  {'-'*24}-+-{'-'*8}-+-{'-'*8}")
print(f"  {'Flat CSAAttention':>24}  | {flat_val:>8.4f} | {flat_test:>8.4f}")
print(f"  {'FlatPlus':>24}  | {fp_val:>8.4f} | {fp_test:>8.4f}")
print(f"  {'ModifiedCSAAttention':>24}  | {mod_val:>8.4f} | {mod_test:>8.4f}")
print(f"  {'Normal Attention':>24}  | {norm_val:>8.4f} | {norm_test:>8.4f}")
print(f"  {'ExpertFlat':>24}  | {exf_val:>8.4f} | {exf_test:>8.4f}")
print(f"  {'ExpertPlusPlus':>24}  | {epp_val:>8.4f} | {epp_test:>8.4f}")
results = [('Flat', flat_val), ('FlatPlus', fp_val), ('Modified', mod_val), ('Normal', norm_val), ('ExpertFlat', exf_val), ('ExpertPlusPlus', epp_val)]
best_name = min(results, key=lambda x: x[1])[0]
print(f"\n  Best validation ({EPOCHS} epochs, seed={SEED}): {best_name}")
# Print gaps relative to best
best_val = min(v for _, v in results)
for name, val in results:
    if val != best_val:
        print(f"  {name} vs best: +{val - best_val:+.4f}")
