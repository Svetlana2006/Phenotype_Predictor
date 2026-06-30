from __future__ import annotations

from pathlib import Path

import pandas as pd

from phenotype_predictor.data_io import write_table


def read_sample_panel(path: str | Path) -> pd.DataFrame:
    """Read a 1000 Genomes / IGSR sample panel.

    Common columns are sample, pop, super_pop, gender. This normalizes them to
    sample_id, population, super_population.
    """
    df = pd.read_csv(path, sep=None, engine="python")
    lower = {c.lower().strip(): c for c in df.columns}
    sample_col = lower.get("sample") or lower.get("sample_id")
    pop_col = lower.get("pop") or lower.get("population")
    super_col = lower.get("super_pop") or lower.get("super_population")
    if not sample_col or not pop_col:
        raise ValueError("Sample panel must include sample/pop or sample_id/population columns")
    out = df[[sample_col, pop_col] + ([super_col] if super_col else [])].copy()
    out.columns = ["sample_id", "population"] + (["super_population"] if super_col else [])
    return out


def prepare_ancestry_table(
    genotype_features_path: str | Path,
    sample_panel_path: str | Path,
    output_path: str | Path,
    target: str = "super_population",
) -> pd.DataFrame:
    """Join extracted genotype features with IGSR population labels.

    `genotype_features_path` should be a table with sample_id plus numeric SNP
    dosage columns. VCF-to-table extraction can be done with PLINK/bcftools
    outside this helper.
    """
    features = pd.read_csv(genotype_features_path, sep=None, engine="python")
    panel = read_sample_panel(sample_panel_path)
    if target not in panel.columns:
        raise ValueError(f"Target {target!r} is not present in sample panel columns {list(panel.columns)}")
    merged = panel[["sample_id", target]].merge(features, on="sample_id", how="inner")
    if target != "ancestry":
        merged = merged.rename(columns={target: "ancestry"})
    write_table(merged, output_path)
    return merged
