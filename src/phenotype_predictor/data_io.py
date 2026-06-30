from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() in {".tsv", ".txt"}:
        return pd.read_csv(path, sep="\t")
    return pd.read_csv(path)


def write_table(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in {".tsv", ".txt"}:
        df.to_csv(path, sep="\t", index=False)
    else:
        df.to_csv(path, index=False)


def split_features_target(df: pd.DataFrame, target: str, id_col: str = "sample_id"):
    drop_cols = [target]
    if id_col in df.columns:
        drop_cols.append(id_col)
    x = df.drop(columns=drop_cols)
    y = df[target]
    return x, y
