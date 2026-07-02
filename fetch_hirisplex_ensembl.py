"""
Fetch HIrisPlex-S genotypes for all 1000 Genomes Phase 3 samples
using the Ensembl REST API.

Much faster than streaming 8 GB of VCF files:
  - One API call per rsID (~41 calls total)
  - Each call returns genotypes for all 1000G samples directly
  - Total download: ~10-20 MB, Time: ~5-10 minutes

Output: data/raw/igsr/hirisplex_genotypes/hirisplex_1kg_phase3.vcf
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, "src")
from phenotype_predictor.markers.hirisplex import HIRISPLEX_S_MARKERS

# ── Config ────────────────────────────────────────────────────────────────────

OUT_DIR  = Path("data/raw/igsr/hirisplex_genotypes")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "hirisplex_1kg_genotypes.csv"

ENSEMBL_URL = "https://rest.ensembl.org/variation/human/{rsid}?genotypes=1"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}
DELAY   = 0.35   # seconds between requests (Ensembl rate limit: ~15/sec)

# ── Fetch genotypes for each rsID ─────────────────────────────────────────────

print("=" * 60)
print("Fetching HIrisPlex-S genotypes via Ensembl REST API")
print("=" * 60)
print(f"RSIDs     : {len(HIRISPLEX_S_MARKERS)}")
print(f"API calls : 1 per rsID (~{len(HIRISPLEX_S_MARKERS)} total)")
print(f"Est. time : 5-10 minutes")
print()

# sample_id -> {rsid: "A|G"}
sample_genos: dict[str, dict[str, str]] = {}
rsid_to_marker = {m.rsid: m for m in HIRISPLEX_S_MARKERS}
missing_rsids: list[str] = []

t_start = time.time()

for i, marker in enumerate(HIRISPLEX_S_MARKERS, 1):
    rsid = marker.rsid
    url  = ENSEMBL_URL.format(rsid=rsid)

    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                print(f"  [{i}/{len(HIRISPLEX_S_MARKERS)}] {rsid} rate-limited, waiting 5s...")
                time.sleep(5)
                continue
            r.raise_for_status()
            data = r.json()
            break
        except Exception as e:
            if attempt == 2:
                print(f"  [{i}/{len(HIRISPLEX_S_MARKERS)}] {rsid} FAILED after 3 attempts: {e}")
                missing_rsids.append(rsid)
                data = None
            else:
                time.sleep(2)

    if data is None:
        continue

    genotypes = data.get("genotypes", [])
    found_1kg = 0
    for g in genotypes:
        sample = g.get("sample", "")
        # Only keep 1000 Genomes Phase 3 samples
        if "1000GENOMES:phase_3:" not in sample:
            continue
        sample_id = sample.replace("1000GENOMES:phase_3:", "")
        gt = g.get("genotype", "./.")
        if sample_id not in sample_genos:
            sample_genos[sample_id] = {}
        sample_genos[sample_id][rsid] = gt
        found_1kg += 1

    print(f"  [{i:2d}/{len(HIRISPLEX_S_MARKERS)}] {rsid:<15}  {found_1kg} samples  (gene: {marker.gene})", flush=True)
    time.sleep(DELAY)

elapsed = time.time() - t_start
print(f"\nFetched {len(HIRISPLEX_S_MARKERS) - len(missing_rsids)}/{len(HIRISPLEX_S_MARKERS)} rsIDs in {elapsed:.0f}s")
print(f"Samples with at least 1 genotype: {len(sample_genos)}")
if missing_rsids:
    print(f"Missing rsIDs (will be NaN): {missing_rsids}")

# ── Build dosage matrix ───────────────────────────────────────────────────────
print("\nBuilding dosage matrix...")

rows = []
for sample_id, geno_dict in sample_genos.items():
    row = {"sample_id": sample_id}
    for marker in HIRISPLEX_S_MARKERS:
        gt = geno_dict.get(marker.rsid, "./.")
        alleles = gt.replace("|", "/").split("/")
        effect  = marker.allele
        try:
            dosage = sum(1 for a in alleles if a == effect)
        except Exception:
            dosage = float("nan")
        row[marker.feature_name] = dosage
    rows.append(row)

df = pd.DataFrame(rows)
df.to_csv(OUT_PATH, index=False)

print(f"Saved: {OUT_PATH}")
print(f"Shape: {df.shape[0]} samples x {df.shape[1]} columns")
print(f"Missing data rate: {df.iloc[:,1:].isna().mean().mean():.1%}")
print()
print("Next: run format_hirisplex_webtool.py to prepare for erasmusmc.nl submission")
