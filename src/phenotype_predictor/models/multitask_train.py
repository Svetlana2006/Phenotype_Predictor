from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import LabelEncoder, StandardScaler
from torch.utils.data import DataLoader, TensorDataset

from phenotype_predictor.models.multitask import MultiTaskHead, MultiTaskPhenotypeNet, masked_multitask_loss


def train_multitask_table(
    df: pd.DataFrame,
    targets: dict[str, str],
    output_dir: str | Path,
    epochs: int = 40,
    batch_size: int = 32,
    hidden_dim: int = 128,
    random_state: int = 42,
) -> dict:
    """Train a masked multi-task neural network from one aligned table.

    `targets` maps column name -> kind, where kind is regression or classification.
    Rows may have missing target values; each task loss is computed only for rows
    where that target is present.
    """
    torch.manual_seed(random_state)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    target_cols = list(targets)
    feature_cols = [c for c in df.columns if c not in target_cols and c != "sample_id"]
    x_df = df[feature_cols]
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    x = scaler.fit_transform(imputer.fit_transform(x_df)).astype("float32")

    encoded_targets = {}
    masks = {}
    heads = []
    encoders = {}
    for col, kind in targets.items():
        mask = df[col].notna().to_numpy()
        masks[col] = mask.astype("float32")
        if kind == "regression":
            values = pd.to_numeric(df[col], errors="coerce").fillna(0).to_numpy(dtype="float32")
            heads.append(MultiTaskHead(col, kind, 1))
        else:
            encoder = LabelEncoder()
            non_missing = df.loc[mask, col].astype(str)
            encoder.fit(non_missing)
            values = np.zeros(len(df), dtype="int64")
            values[mask] = encoder.transform(non_missing)
            encoders[col] = encoder
            heads.append(MultiTaskHead(col, kind, len(encoder.classes_)))
        encoded_targets[col] = values

    tensors = [torch.tensor(x)]
    for col in target_cols:
        dtype = torch.float32 if targets[col] == "regression" else torch.long
        tensors.append(torch.tensor(encoded_targets[col], dtype=dtype))
        tensors.append(torch.tensor(masks[col], dtype=torch.float32))

    dataset = TensorDataset(*tensors)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    model = MultiTaskPhenotypeNet(input_dim=x.shape[1], heads=heads, hidden_dim=hidden_dim)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    history = []
    for epoch in range(epochs):
        model.train()
        epoch_losses = []
        for batch in loader:
            xb = batch[0]
            target_batch = {}
            mask_batch = {}
            offset = 1
            for col in target_cols:
                target_batch[col] = batch[offset]
                mask_batch[col] = batch[offset + 1]
                offset += 2
            optimizer.zero_grad()
            outputs = model(xb)
            loss = masked_multitask_loss(outputs, target_batch, mask_batch, heads)
            loss.backward()
            optimizer.step()
            epoch_losses.append(float(loss.detach()))
        history.append({"epoch": epoch + 1, "loss": float(np.mean(epoch_losses))})

    torch.save(model.state_dict(), output_dir / "multitask_model.pt")
    metadata = {
        "feature_cols": feature_cols,
        "targets": targets,
        "heads": [asdict(head) for head in heads],
        "history": history,
        "class_labels": {name: encoder.classes_.tolist() for name, encoder in encoders.items()},
    }
    joblib.dump({"imputer": imputer, "scaler": scaler, "metadata": metadata}, output_dir / "multitask_preprocess.joblib")
    pd.DataFrame(history).to_csv(output_dir / "training_history.csv", index=False)
    return metadata
