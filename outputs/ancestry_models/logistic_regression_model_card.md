# Ancestry model: logistic_regression

Generated: 2026-06-30T14:30:35.955569Z

## Training Data

data\raw\igsr\ALL.chr22.phase3.genotypes.vcf.gz

## Target

super_population

## Metrics

- balanced_accuracy: 0.6852

## Limitations

- Trained on 1000 Genomes Phase 3 chr22 SNPs (biallelic, MAF>5%).
- Labels are reference-panel super-populations (AFR/AMR/EAS/EUR/SAS).
- Population labels are proxies for reference-panel structure, not identity.
- Confidence should be reduced for samples outside the training distribution.
