"""
Download eye color, hair color phenotype data + matching genotype files from OpenSNP.

OpenSNP (opensnp.org) is a public database where people upload their 23andMe /
AncestryDNA raw genotype files alongside self-reported phenotypes.

Pipeline:
  1. Download phenotype variation lists for eye color and hair color (~1 MB each)
  2. Find user IDs that have BOTH eye AND hair color reported
  3. Download their genotype files (23andMe format, ~5-15 MB each)
  4. Parse genotype files to extract HIrisPlex-S SNPs
  5. Write a merged table: user_id, eye_color, hair_color, <41 HIrisPlex dosages>

Estimated download: 100-500 MB depending on how many users have both traits.
Estimated users with both: ~500-1500 (out of ~6000 total OpenSNP users).

NOTE: Do NOT run until ready. Each genotype file is ~5-15 MB.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests
import pandas as pd

sys.path.insert(0, "src")
from phenotype_predictor.markers.hirisplex import HIRISPLEX_S_MARKERS

# ── Config ────────────────────────────────────────────────────────────────────

OUT_DIR      = Path("data/raw/opensnp")
GENO_DIR     = OUT_DIR / "genotypes"
OUT_DIR.mkdir(parents=True, exist_ok=True)
GENO_DIR.mkdir(parents=True, exist_ok=True)

BASE = "https://opensnp.org"

# OpenSNP phenotype IDs (stable IDs from the platform)
# Eye color = 1, Hair color = 2  (confirmed from opensnp.org/phenotypes)
PHENOTYPE_IDS = {
    "eye_color":  1,
    "hair_color": 2,
}

# HIrisPlex rsIDs we need
TARGET_RSIDS: set[str] = {m.rsid for m in HIRISPLEX_S_MARKERS}

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_json(url: str, retries: int = 3) -> dict | list:
    for i in range(retries):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(2)


def download_file(url: str, dest: Path, desc: str = "") -> bool:
    if dest.exists():
        return True  # already downloaded
    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"    FAIL {desc}: {e}")
        return False


def parse_23andme_for_hirisplex(path: Path) -> dict[str, int]:
    """Read a 23andMe raw genotype file, return {rsid: dosage} for HIrisPlex SNPs.

    23andMe format:
      # comment lines
      rsid  chromosome  position  genotype
    Dosage = count of the effect allele for each HIrisPlex marker.
    """
    marker_by_rsid = {m.rsid: m for m in HIRISPLEX_S_MARKERS}
    result: dict[str, int] = {}

    try:
        opener = open
        if path.suffix == ".gz":
            import gzip as gz
            opener = gz.open

        with opener(path, "rt", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("#"):
                    continue
                parts = line.strip().split("\t")
                if len(parts) < 4:
                    continue
                rsid = parts[0]
                if rsid not in marker_by_rsid:
                    continue
                genotype = parts[3].upper()
                effect_allele = marker_by_rsid[rsid].allele.upper()
                if "D" in genotype or "I" in genotype or "-" in genotype:
                    continue  # skip indels
                dosage = sum(1 for a in genotype if a == effect_allele)
                result[rsid] = dosage
    except Exception:
        pass

    return result


# ── Normalise phenotype labels ────────────────────────────────────────────────

EYE_NORM = {
    "blue": "blue", "light blue": "blue", "blue-gray": "blue",
    "green": "green", "hazel": "hazel",
    "brown": "brown", "dark brown": "brown",
    "gray": "gray", "grey": "gray",
    "amber": "amber",
}
HAIR_NORM = {
    "black": "black", "dark brown": "dark_brown", "brown": "brown",
    "light brown": "light_brown", "dirty blonde": "light_brown",
    "blonde": "blonde", "blond": "blonde", "strawberry blonde": "red",
    "red": "red", "auburn": "red",
    "gray": "gray", "grey": "gray", "white": "white",
}


def norm_eye(v: str) -> str | None:
    return EYE_NORM.get(v.lower().strip())


def norm_hair(v: str) -> str | None:
    return HAIR_NORM.get(v.lower().strip())


# ── Main ──────────────────────────────────────────────────────────────────────

print("=" * 60)
print("OpenSNP Pigmentation Phenotype Downloader")
print("=" * 60)
print()

confirm = input("Type 'yes' to start, anything else to exit: ").strip().lower()
if confirm != "yes":
    print("Aborted.")
    sys.exit(0)

print()

# ── Step 1: Download phenotype variation lists ────────────────────────────────
print("[1/5] Downloading phenotype variation lists...")
phenotype_users: dict[str, dict[int, str]] = {}   # trait -> {user_id: value}

for trait, pid in PHENOTYPE_IDS.items():
    url = f"{BASE}/phenotypes/json/variations/{pid}.json"
    print(f"  {trait} (id={pid}): {url}")
    data = get_json(url)

    # Data is a list of {"user_id": X, "variation": "..."}
    users: dict[int, str] = {}
    for entry in data:
        uid = entry.get("user_id")
        val = entry.get("variation", "")
        if uid and val:
            users[uid] = val

    phenotype_users[trait] = users
    print(f"    {len(users)} users with {trait}")

# ── Step 2: Find users with BOTH traits ──────────────────────────────────────
print("\n[2/5] Finding users with both eye color AND hair color...")
eye_users  = set(phenotype_users["eye_color"].keys())
hair_users = set(phenotype_users["hair_color"].keys())
both_users = eye_users & hair_users
print(f"  Eye color:  {len(eye_users)}")
print(f"  Hair color: {len(hair_users)}")
print(f"  Both:       {len(both_users)}")

# Normalise labels and filter to known categories
valid_users: list[dict] = []
for uid in both_users:
    eye  = norm_eye(phenotype_users["eye_color"][uid])
    hair = norm_hair(phenotype_users["hair_color"][uid])
    if eye and hair:
        valid_users.append({"user_id": uid, "eye_color": eye, "hair_color": hair})

print(f"  After normalisation: {len(valid_users)} users with clean labels")

if not valid_users:
    print("ERROR: No users found with clean labels. Check the phenotype IDs.")
    sys.exit(1)

# Save phenotype table
pheno_path = OUT_DIR / "opensnp_phenotypes.csv"
pd.DataFrame(valid_users).to_csv(pheno_path, index=False)
print(f"  Phenotype table saved: {pheno_path}")

# ── Step 3: Get genotype file URLs for each user ──────────────────────────────
print(f"\n[3/5] Fetching genotype file URLs for {len(valid_users)} users...")
user_geno_urls: dict[int, str] = {}

for i, u in enumerate(valid_users):
    uid = u["user_id"]
    url = f"{BASE}/users/{uid}/genotypes.json"
    try:
        data = get_json(url)
        # Find the first 23andMe or AncestryDNA file
        for g in data:
            furl = g.get("download_url") or g.get("url", "")
            if furl and ("23andme" in furl.lower() or "ancestry" in furl.lower() or ".txt" in furl):
                user_geno_urls[uid] = furl
                break
    except Exception:
        pass

    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{len(valid_users)} users queried...", flush=True)

print(f"  {len(user_geno_urls)} users have downloadable genotype files")

# ── Step 4: Download genotype files ──────────────────────────────────────────
print(f"\n[4/5] Downloading {len(user_geno_urls)} genotype files...")
ok = 0
for i, (uid, gurl) in enumerate(user_geno_urls.items()):
    ext = ".txt.gz" if gurl.endswith(".gz") else ".txt"
    dest = GENO_DIR / f"user_{uid}{ext}"
    success = download_file(gurl, dest, desc=f"user {uid}")
    if success:
        ok += 1
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(user_geno_urls)} downloaded ({ok} ok)...", flush=True)

print(f"  Downloaded: {ok}/{len(user_geno_urls)}")

# ── Step 5: Parse HIrisPlex SNPs from genotype files ─────────────────────────
print("\n[5/5] Parsing HIrisPlex-S SNPs from genotype files...")

uid_to_pheno = {u["user_id"]: u for u in valid_users}
rows: list[dict] = []

for f in sorted(GENO_DIR.glob("user_*")):
    uid_str = f.stem.replace("user_", "")
    try:
        uid = int(uid_str)
    except ValueError:
        continue

    if uid not in uid_to_pheno:
        continue

    dosages = parse_23andme_for_hirisplex(f)
    if len(dosages) < 10:   # skip files with too few HIrisPlex SNPs found
        continue

    row = {"user_id": uid}
    row.update(uid_to_pheno[uid])  # eye_color, hair_color
    for m in HIRISPLEX_S_MARKERS:
        row[m.feature_name] = dosages.get(m.rsid, None)  # None = missing
    rows.append(row)

result_df = pd.DataFrame(rows)
out_path = OUT_DIR / "opensnp_hirisplex_features.csv"
result_df.to_csv(out_path, index=False)

print(f"\nDone!")
print(f"  Users parsed:          {len(rows)}")
print(f"  Output feature table:  {out_path}")
print(f"  Columns:               {list(result_df.columns[:6])} ...")
print(f"  Eye color dist:\n{result_df['eye_color'].value_counts().to_string()}")
print(f"  Hair color dist:\n{result_df['hair_color'].value_counts().to_string()}")
print()
print("Next step: run train_pigmentation.py to train eye/hair color models")
