"""
Stream 1000 Genomes Phase 3 VCFs for 12 chromosomes, extracting only the
41 HIrisPlex-S SNP lines. No chromosome VCFs are ever written to disk.

Bandwidth: ~8 GB streamed. Disk written: ~50 KB output.
Time: 30-90 minutes depending on connection speed.

Resume-safe: already-found SNPs are loaded from partial output on restart.
Run with: python download_hirisplex_1kg.py
"""
from __future__ import annotations

import gzip
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests
import urllib3
urllib3.disable_warnings()

sys.path.insert(0, "src")
from phenotype_predictor.markers.hirisplex import HIRISPLEX_S_MARKERS

# ── Config ────────────────────────────────────────────────────────────────────

OUT_DIR = Path("data/raw/igsr/hirisplex_genotypes")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_VCF = OUT_DIR / "hirisplex_1kg_phase3.vcf"

BASE_URL = (
    "https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/"
    "ALL.chr{chrom}.phase3_shapeit2_mvncall_integrated_v5b."
    "20130502.genotypes.vcf.gz"
)

# rsID → chromosome map for all 41 HIrisPlex-S SNPs
RSID_TO_CHROM: dict[str, str] = {
    "rs312262906": "16", "rs11547464":  "16", "rs885479":    "16",
    "rs1805008":   "16", "rs1805005":   "16", "rs1805006":   "16",
    "rs1805007":   "16", "rs1805009":   "16", "rs201326893": "16",
    "rs2228479":   "16", "rs1110400":   "16", "rs3212355":   "16",
    "rs28777":     "5",  "rs16891982":  "5",
    "rs12821256":  "12",
    "rs4959270":   "4",
    "rs12203592":  "6",
    "rs1042602":   "11", "rs1393350":   "11", "rs1126809":   "11",
    "rs1800407":   "15", "rs12913832":  "15", "rs2238289":   "15",
    "rs6497292":   "15", "rs1129038":   "15", "rs1667394":   "15",
    "rs1470608":   "15", "rs1426654":   "15", "rs1545397":   "15",
    "rs12441727":  "15", "rs1800414":   "15",
    "rs2402130":   "14", "rs12896399":  "14", "rs17128291":  "14",
    "rs2378249":   "20", "rs6119471":   "20", "rs6059655":   "20",
    "rs3114908":   "17",
    "rs683":       "9",  "rs10756819":  "9",
    "rs8051733":   "8",
}

TARGET_RSIDS: set[str] = set(RSID_TO_CHROM.keys())

chrom_to_rsids: dict[str, set[str]] = defaultdict(set)
for rsid, chrom in RSID_TO_CHROM.items():
    chrom_to_rsids[chrom].add(rsid)

CHROMS_NEEDED = sorted(chrom_to_rsids.keys(), key=int)

# ── Resume: load already-found SNPs from partial output ───────────────────────
already_found: set[str] = set()
existing_lines: list[str] = []
header_line: str | None = None

if OUT_VCF.exists():
    with open(OUT_VCF, encoding="utf-8") as f:
        for line in f:
            if line.startswith("##"):
                continue
            if line.startswith("#CHROM"):
                header_line = line
                continue
            parts = line.split("\t", 4)
            if len(parts) >= 3 and parts[2] in TARGET_RSIDS:
                already_found.add(parts[2])
                existing_lines.append(line)
    print(f"Resume: {len(already_found)} SNPs already in {OUT_VCF}")

# ── Print plan ────────────────────────────────────────────────────────────────
remaining = TARGET_RSIDS - already_found
chroms_todo = [c for c in CHROMS_NEEDED if chrom_to_rsids[c] - already_found]

print("=" * 60)
print("HIrisPlex-S 1000 Genomes Streaming Extractor")
print("=" * 60)
print(f"Target rsIDs  : {len(TARGET_RSIDS)}  ({len(already_found)} already done, {len(remaining)} remaining)")
print(f"Chromosomes   : {chroms_todo}")
print(f"Bandwidth     : ~{len(chroms_todo)} chromosome VCFs (up to 8 GB total)")
print(f"Disk written  : ~50 KB  (SNP lines only, no chromosome VCFs saved)")
print(f"Output file   : {OUT_VCF}")
print()

if not remaining:
    print("All SNPs already extracted! Nothing to do.")
    sys.exit(0)

# ── Stream each chromosome ────────────────────────────────────────────────────
all_snp_lines: list[str] = list(existing_lines)
total_found = len(already_found)
t_total = time.time()

CHROM_SIZES_GB = {
    "4": 1.07, "5": 0.95, "6": 0.96, "8": 0.82, "9": 0.64,
    "11": 0.73, "12": 0.71, "14": 0.49, "15": 0.44,
    "16": 0.47, "17": 0.42, "20": 0.33,
}

for chrom in chroms_todo:
    want = chrom_to_rsids[chrom] - already_found
    if not want:
        print(f"[chr{chrom}] All SNPs already found, skipping.")
        continue

    url = BASE_URL.format(chrom=chrom)
    size_gb = CHROM_SIZES_GB.get(chrom, "?")
    print(f"\n[chr{chrom}]  {len(want)} SNPs to find  ({size_gb} GB to stream)  ", flush=True)
    found_here: set[str] = set()
    t0 = time.time()
    lines_scanned = 0

    try:
        with requests.get(url, stream=True, timeout=120, verify=False) as resp:
            resp.raise_for_status()
            gz = gzip.GzipFile(fileobj=resp.raw)

            for raw_line in gz:
                line = raw_line.decode("utf-8", errors="replace")

                if line.startswith("##"):
                    continue
                if line.startswith("#CHROM"):
                    if header_line is None:
                        header_line = line
                    continue

                lines_scanned += 1
                if lines_scanned % 500_000 == 0:
                    elapsed = time.time() - t0
                    print(
                        f"  {lines_scanned//1_000_000}M lines scanned  "
                        f"{elapsed:.0f}s  {len(found_here)}/{len(want)} found",
                        flush=True,
                    )

                parts = line.split("\t", 4)
                if len(parts) < 3:
                    continue

                rsid = parts[2]
                if rsid in want and rsid not in found_here:
                    all_snp_lines.append(line)
                    found_here.add(rsid)
                    total_found += 1
                    print(f"  -> Found {rsid}  ({len(found_here)}/{len(want)})", flush=True)

                if found_here == want:
                    print(f"  All {len(want)} found — stopping chr{chrom} early.", flush=True)
                    break

    except Exception as e:
        print(f"  ERROR on chr{chrom}: {type(e).__name__}: {e}", flush=True)

    missing = want - found_here
    elapsed = time.time() - t0
    already_found |= found_here

    status = "OK" if not missing else f"MISSING: {missing}"
    print(f"  chr{chrom} done in {elapsed:.0f}s  [{status}]", flush=True)

    # ── Write partial output after each chromosome (crash-safe) ──────────────
    with open(OUT_VCF, "w", encoding="utf-8") as f:
        f.write("##fileformat=VCFv4.1\n")
        f.write("##source=1000GenomesPhase3_HIrisPlex-S_extract\n")
        if header_line:
            f.write(header_line)
        for snp_line in all_snp_lines:
            f.write(snp_line)
    print(f"  Partial save: {OUT_VCF}  ({len(all_snp_lines)} SNPs written)", flush=True)

# ── Final summary ─────────────────────────────────────────────────────────────
print()
print("=" * 60)
print("DONE")
print("=" * 60)
total_elapsed = time.time() - t_total
missing_all = TARGET_RSIDS - already_found
print(f"SNPs found    : {len(already_found)}/{len(TARGET_RSIDS)}")
if missing_all:
    print(f"SNPs missing  : {missing_all}")
print(f"Output file   : {OUT_VCF}  ({OUT_VCF.stat().st_size / 1024:.1f} KB)")
print(f"Total time    : {total_elapsed/60:.1f} min")
print()
print("Next: run format_hirisplex_webtool.py to prepare submission for erasmusmc.nl")
