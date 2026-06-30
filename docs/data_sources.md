# Public Data Sources

## GSE40279

Use for methylation-based chronological age prediction.

Files to download from GEO:

- `GSE40279_sample_key.txt.gz`
- one or more `GSE40279_average_beta...txt.gz` files

Prepare a table:

```powershell
$env:PYTHONPATH='src'
python -m phenotype_predictor.cli prepare-gse40279 `
  --beta data/raw/gse40279/GSE40279_average_beta_GSM989827-GSM989990.txt.gz `
  --sample-key data/raw/gse40279/GSE40279_sample_key.txt.gz `
  --output data/processed/age/gse40279_age.csv
```

## 1000 Genomes / IGSR

Use for ancestry/population prediction.

Recommended workflow:

1. Download a sample panel with population/super-population labels.
2. Extract SNP dosage features from VCF with PLINK/bcftools.
3. Join the features to labels with `prepare-igsr`.

```powershell
$env:PYTHONPATH='src'
python -m phenotype_predictor.cli prepare-igsr `
  --features data/processed/ancestry/igsr_snp_dosages.csv `
  --sample-panel data/raw/igsr/integrated_call_samples_v3.20130502.ALL.panel `
  --output data/processed/ancestry/igsr_ancestry.csv
```

## HIrisPlex-S

Use as a forensic marker panel for eye, hair, and skin color inputs. The marker manifest can be generated with:

```powershell
$env:PYTHONPATH='src'
python -m phenotype_predictor.cli markers --output data/external/hirisplex/hirisplex_s_markers.csv
```

## Personal Genome Project

Use only for exploratory multi-phenotype experiments. It is public but identifiable human data. Avoid exposing names, contact details, medical records, or raw participant-level outputs in reports.
