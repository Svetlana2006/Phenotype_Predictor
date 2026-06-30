from __future__ import annotations

from pathlib import Path

import pandas as pd

from phenotype_predictor.data_io import write_table


def read_gse40279_metadata(path: str | Path) -> pd.DataFrame:
    """Read the GSE40279 sample metadata CSV parsed from the GEO SOFT brief file.

    Expects columns: gsm, sample_id, age (and optionally gender, ethnicity, tissue).
    Falls back gracefully to simpler key files that only have sample_id and age.
    """
    df = pd.read_csv(path, sep=None, engine="python", compression="infer")
    cols_lower = {c.lower().strip(): c for c in df.columns}

    sample_col = _first_existing(cols_lower, ["sample_id", "source_name", "gsm", "sample"])
    age_col = _first_existing(cols_lower, ["age", "age.y", "age_years", "characteristics_ch1"])

    keep_dest = ["sample_id", "age"]
    keep_src = [cols_lower.get(sample_col.lower(), sample_col), cols_lower.get(age_col.lower(), age_col)]
    # Use the actual column names from the dict
    keep_src = [sample_col, age_col]

    optional = {
        "gender": ["gender", "sex"],
        "ethnicity": ["ethnicity", "race", "population"],
        "tissue": ["tissue", "source"],
    }
    for dest, aliases in optional.items():
        try:
            src = _first_existing(cols_lower, aliases)
            keep_dest.append(dest)
            keep_src.append(src)
        except ValueError:
            pass

    out = df[keep_src].copy()
    out.columns = keep_dest
    out["age"] = out["age"].astype(str).str.extract(r"(\d+(?:\.\d+)?)").astype(float)
    return out.dropna(subset=["sample_id", "age"])


# Backward-compatible alias used by the CLI and older code
read_gse40279_sample_key = read_gse40279_metadata


def prepare_age_table(
    beta_matrix_path: str | Path,
    sample_key_path: str | Path,
    output_path: str | Path,
    max_cpgs: int | None = 5000,
) -> pd.DataFrame:
    """Create a model-ready age table from a methylation beta matrix.

    The beta matrix has CpGs as rows and samples as columns. This function:
    1. Reads the sample metadata (age + optional covariates).
    2. Loads up to `max_cpgs` rows from the beta matrix and transposes it.
    3. Joins by sample_id and writes a sample-row × CpG-column CSV.

    Parameters
    ----------
    beta_matrix_path:
        Path to the gzipped tab-separated beta matrix (CpGs × samples).
    sample_key_path:
        CSV/TSV with at minimum sample_id and age. The SOFT-derived metadata
        CSV (with gender/ethnicity/tissue) is fully supported.
    output_path:
        Destination for the merged, model-ready CSV.
    max_cpgs:
        Maximum number of CpG rows to load. None loads all (~450k, ~8 GB RAM).
    """
    print("  Loading sample metadata...", flush=True)
    sample_key = read_gse40279_metadata(sample_key_path)
    print(f"  {len(sample_key)} samples with age labels (range {sample_key['age'].min():.0f}–{sample_key['age'].max():.0f})", flush=True)

    print(f"  Loading beta matrix (max_cpgs={max_cpgs})...", flush=True)
    beta = pd.read_csv(beta_matrix_path, sep="\t", compression="infer", nrows=max_cpgs)
    cpg_col = beta.columns[0]
    beta = beta.set_index(cpg_col).T
    beta.index.name = "sample_id"
    features = beta.reset_index()
    print(f"  Beta: {len(features)} samples × {len(features.columns) - 1} CpGs loaded", flush=True)

    merged = sample_key.merge(features, on="sample_id", how="inner")
    print(f"  Joined: {len(merged)} samples with both methylation and age label", flush=True)
    write_table(merged, output_path)
    return merged


def _first_existing(columns: dict[str, str], aliases: list[str]) -> str:
    for alias in aliases:
        if alias in columns:
            return columns[alias]
    raise ValueError(f"Could not find any of these columns: {aliases}")
