import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from dataset import ETTForecastDataset, download_and_preprocess_etth1
from model import CSATimeSeriesModel, ModifiedCSATimeSeriesModel


# ── Shared evaluation (used for both validation and test) ────────────────────
@torch.no_grad()
def evaluate(model, loader, criterion, device):
    """Compute average loss over a DataLoader without gradient tracking."""
    model.eval()
    total_loss = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        out = model(x)  # [B, H, F]; full horizon scored against y (frozen task)
        loss = criterion(out, y)
        total_loss += loss.item()
    return total_loss / len(loader)


# ==========================================
# 4. Training, Validation, and Test Loop
# ==========================================
if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Hyperparams
    LOOKBACK = 256
    HORIZON = 96
    BATCH_SIZE = 32
    EPOCHS = 5

    # 1. Load Data
    train_data, val_data, test_data = download_and_preprocess_etth1()
    train_dataset = ETTForecastDataset(train_data, LOOKBACK, HORIZON)
    val_dataset   = ETTForecastDataset(val_data, LOOKBACK, HORIZON)
    test_dataset  = ETTForecastDataset(test_data, LOOKBACK, HORIZON)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader   = DataLoader(val_dataset,   batch_size=BATCH_SIZE, shuffle=False)
    test_loader  = DataLoader(test_dataset,  batch_size=BATCH_SIZE, shuffle=False)

    # 2. Init Model
    num_features = train_data.shape[1]
    model_type = "ModifiedCSAAttention"
    model = ModifiedCSATimeSeriesModel(
        num_features=num_features,
        hidden_size=128,
        lookback=LOOKBACK,
        horizon=HORIZON
    ).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-5)
    criterion = nn.MSELoss()

    # 3. Train with per-epoch validation
    print(f"\n=== {model_type} ===")
    print(f"Starting training for {EPOCHS} epochs...")
    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)

            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)  # out=[B,96,7], y=[B,96,7], no slicing
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        avg_train = total_loss / len(train_loader)
        avg_val   = evaluate(model, val_loader, criterion, device)
        print(f"Epoch {epoch+1}/{EPOCHS} | Train MSE: {avg_train:.4f} | Val MSE: {avg_val:.4f}")

    # 4. Final test evaluation
    avg_test = evaluate(model, test_loader, criterion, device)
    print(f"\nTest MSE: {avg_test:.4f}")

