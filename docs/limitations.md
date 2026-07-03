# System and Research Limitations

While the Forensic Phenotype Predictor leverages state-of-the-art machine learning, users must understand the mathematical and biological boundaries of the system.

## 1. Population Bias
The models are trained heavily on the **1000 Genomes Project** and **HIrisPlex** datasets. These datasets have inherent geographical biases. The ancestry model is restricted to five broad super-populations (AFR, AMR, EAS, EUR, SAS). It is incapable of defining specific ethnic boundaries. Underrepresented populations will inherently yield lower confidence scores and potentially skewed predictions.

## 2. Dataset Limitations
Phenotype traits like Eye, Hair, and Skin color are polygenic. Our models look at 41 specific SNPs. While these SNPs are highly correlated with these traits, they do not account for all genetic variation. Environmental factors (e.g., sun exposure for skin, hair dye) cannot be predicted by DNA.

## 3. Confidence Uncertainty
The AI outputs a probability distribution (e.g., 75% Brown Eyes, 20% Blue Eyes, 5% Green Eyes). A high probability does **not** equal absolute certainty. It represents the statistical likelihood based on the training distribution. Investigators must interpret these as statistical clues, not definitive facts.

## 4. Missing SNP Limitations (Degradation)
Degraded DNA (common in forensics) leads to missing SNPs. If too many SNPs are missing, the system dynamically routes to a Sparse Ancestry Model. However, if critical phenotypic SNPs are missing, the confidence interval will drastically decrease. The system actively blocks imputation (hallucination) if the Evidence Quality Meter drops too low.

## 5. Research-Only Disclaimer
This software is provided for **research and investigative lead generation only**. It is not FDA-approved, nor is it a certified forensic diagnostic tool. 

## 6. Ethical Use
Predictions must never be used as primary evidence for conviction. Relying solely on phenotype prediction to profile individuals is a severe violation of the intended use of this software.
