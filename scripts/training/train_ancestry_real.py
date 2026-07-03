"""
Build ancestry training dataset from 1000 Genomes Phase 3 chr22 VCF.

Pipeline:
1. Parse chr22 VCF → alt-allele dosage matrix (samples × SNPs)
2. Apply MAF filter (>5%) to keep ancestry-informative SNPs
3. Join with phase3 population panel → super_population labels
4. Train Logistic Regression + Random Forest classifiers
5. Report balanced accuracy per super-population
"""
from __future__ import annotations

import gzip
import io
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")

RAW_DIR = Path("data/raw/igsr")
OUT_DIR = Path("outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

VCF_PATH = RAW_DIR / "ALL.chr22.phase3.genotypes.vcf.gz"
PANEL_PATH = RAW_DIR / "igsr_sample_panel.panel"

# How many SNPs to load (2500 is plenty for 5-class ancestry; full chr22 has ~500k)
MAX_SNPS = 3000
MAF_THRESHOLD = 0.05  # minor allele freq filter

print("=== B: 1000 Genomes Ancestry Model (chr22 VCF) ===")


# ── 1. Load population panel ──────────────────────────────────────────────────
print("\n[1/5] Loading sample panel...", flush=True)
panel = pd.read_csv(PANEL_PATH, sep="\t", usecols=["sample", "pop", "super_pop"])
panel.columns = ["sample_id", "population", "super_population"]
print(f"      {len(panel)} samples, {panel['super_population'].nunique()} super-pops")
for sp, cnt in panel["super_population"].value_counts().items():
    print(f"        {sp}: {cnt}")


# ── 2. Parse VCF ──────────────────────────────────────────────────────────────
print(f"\n[2/5] Parsing chr22 VCF (first {MAX_SNPS} biallelic SNPs)...", flush=True)
t0 = time.time()

sample_ids: list[str] = []
snp_ids: list[str] = []
dosage_rows: list[np.ndarray] = []

with gzip.open(VCF_PATH, "rt", errors="replace") as gz:
    for raw_line in gz:
        line = raw_line.rstrip("\n")
        if line.startswith("##"):
            continue
        if line.startswith("#CHROM"):
            parts = line.split("\t")
            sample_ids = parts[9:]
            print(f"      VCF samples: {len(sample_ids)}", flush=True)
            continue

        if len(snp_ids) >= MAX_SNPS:
            break

        parts = line.split("\t")
        if len(parts) < 10:
            continue

        # Skip indels and multi-allelic sites
        ref, alt = parts[3], parts[4]
        if "," in alt or len(ref) > 1 or len(alt) > 1:
            continue

        snp_id = parts[2] if parts[2] not in (".", "") else f"22:{parts[1]}"

        # Fast GT dosage extraction: GT is always first field in FORMAT
        dosages = np.empty(len(sample_ids), dtype=np.float32)
        for i, gt_field in enumerate(parts[9:]):
            gt = gt_field[:3]  # first 3 chars cover "0/0", "0/1", "1/1", "./."
            if gt[1] == "/" or gt[1] == "|":
                a0, a2 = gt[0], gt[2]
                if a0 == "." or a2 == ".":
                    dosages[i] = np.nan
                else:
                    dosages[i] = float(a0) + float(a2)
            else:
                dosages[i] = np.nan

        snp_ids.append(snp_id)
        dosage_rows.append(dosages)

        if len(snp_ids) % 500 == 0:
            print(f"      {len(snp_ids)} SNPs parsed  ({time.time()-t0:.0f}s)", flush=True)

print(f"      Parsed {len(snp_ids)} SNPs in {time.time()-t0:.1f}s", flush=True)


# ── 3. Build & filter feature matrix ─────────────────────────────────────────
print("\n[3/5] Building dosage matrix and applying MAF filter...", flush=True)

X = np.stack(dosage_rows, axis=1).astype(np.float32)  # samples × SNPs
print(f"      Raw shape: {X.shape}")

# MAF filter
col_mean = np.nanmean(X, axis=0)  # mean dosage per SNP
maf = np.minimum(col_mean / 2, 1 - col_mean / 2)
keep_mask = maf > MAF_THRESHOLD
X = X[:, keep_mask]
snp_ids_filtered = [s for s, k in zip(snp_ids, keep_mask) if k]
print(f"      After MAF>{MAF_THRESHOLD}: {X.shape[1]} SNPs kept from {len(snp_ids)}", flush=True)

features_df = pd.DataFrame(X, columns=snp_ids_filtered)
features_df.insert(0, "sample_id", sample_ids)


# ── 4. Join with population labels ────────────────────────────────────────────
print("\n[4/5] Joining with population labels...", flush=True)

# Use phase3 panel (2504 unrelated samples)
merged = panel.merge(features_df, on="sample_id", how="inner")
print(f"      Matched: {len(merged)} samples", flush=True)
print("      Super-pop distribution:")
for sp, cnt in merged["super_population"].value_counts().items():
    print(f"        {sp}: {cnt}")

ancestry_path = OUT_DIR / "igsr_ancestry_table.csv"
merged.to_csv(ancestry_path, index=False)
print(f"      Saved to {ancestry_path}", flush=True)


# ── 5. Train classifiers ──────────────────────────────────────────────────────
print("\n[5/5] Training ancestry classifiers...", flush=True)

from phenotype_predictor.models.baselines import train_classifiers
from phenotype_predictor.reporting import write_model_card

X_feat = merged.drop(columns=["sample_id", "population", "super_population"])
y = merged["super_population"]

t1 = time.time()
results = train_classifiers(X_feat, y, OUT_DIR / "ancestry_models")
print(f"      Training done in {time.time()-t1:.1f}s", flush=True)

# Write model cards
for r in results:
    write_model_card(
        Path("outputs/ancestry_models") / f"{r.model_name}_model_card.md",
        f"Ancestry model: {r.model_name}",
        str(VCF_PATH),
        "super_population",
        r.metrics,
        [
            "Trained on 1000 Genomes Phase 3 chr22 SNPs (biallelic, MAF>5%).",
            "Labels are reference-panel super-populations (AFR/AMR/EAS/EUR/SAS).",
            "Population labels are proxies for reference-panel structure, not identity.",
            "Confidence should be reduced for samples outside the training distribution.",
        ],
    )

print()
print("=" * 60)
print("ANCESTRY RESULTS  (5-class super-population, 20% test set)")
print("=" * 60)
best = max(results, key=lambda r: r.metrics["balanced_accuracy"])
for r in results:
    tag = " <-- BEST" if r.model_name == best.model_name else ""
    print(f"  {r.model_name:<28}  Balanced Acc = {r.metrics['balanced_accuracy']:.4f}{tag}")
print()
print("  Balanced accuracy: 1.0 = perfect, 0.20 = random (5 classes)")
print(f"\nTotal elapsed: {time.time()-t0:.1f}s")
