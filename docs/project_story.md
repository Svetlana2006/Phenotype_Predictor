# Project Story: Forensic Phenotype Predictor

## The Problem
Forensic investigations often reach a dead end when DNA is recovered from a crime scene but yields no match in CODIS or other national databases. When this happens, investigators need to know *who* to look for. Existing commercial phenotype prediction tools are expensive, proprietary black-boxes that offer zero algorithmic transparency, making them difficult to defend in court. Furthermore, open-source solutions are highly fragmented—one script predicts age, another predicts eye color, and none of them communicate with each other or handle degraded DNA well.

## Our Solution
We built the **Forensic Phenotype Predictor**: a population-aware, multi-model AI platform. It unifies disparate genetic prediction tasks into a single, cohesive engine. By uploading a single unaligned DNA sequence, the system simultaneously extracts relevant SNPs and predicts Eye, Hair, and Skin color, alongside Global Ancestry.

## Engineering Decisions
1. **Explainability Over Accuracy:** We explicitly rejected black-box Deep Learning neural networks for the core pigmentation models. Instead, we used scikit-learn models wrapped in a custom Explainability Engine. This allows us to extract the exact decision tree weights (`feature_importances_`) and mathematical coefficients at runtime, proving exactly which genes drove the prediction.
2. **Dynamic AI Routing:** Real forensic DNA is corrupted. We built a dynamic routing system. If a sample has over 100 SNPs, it uses the Full Genome Ancestry model. If the Evidence Quality drops below that threshold, it seamlessly hot-swaps to a Sparse Ancestry Model trained exclusively on 41 SNPs, guaranteeing a result without crashing.
3. **Imputation Safeguards:** Standard imputation algorithms guess missing data using global medians. In genetics, this hallucinates traits (e.g., defaulting to brown eyes). We engineered a strict block: if the DNA is too sparse, the system refuses to guess, preserving scientific integrity.

## Biological Challenges
DNA sequencing machines output raw, unaligned A/T/C/G strings, often from the reverse-minus strand. We had to build a biological sequence parser (`sequence_extractor.py`) capable of running regex searches across the sequence, identifying the strand orientation, and mathematically calculating the `reverse_complement` to standardize the data before it ever touches the ML models.

## Impact
This platform democratizes forensic phenotyping. It provides investigators with a free, open-source, mathematically transparent, and highly robust tool to generate investigative leads from degraded DNA, all wrapped in a modern Next.js dashboard with cryptographic reproducibility tracking.
