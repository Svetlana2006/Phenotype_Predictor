# Ethical Considerations and Limitations

Forensic Phenotype Prediction intersects deeply with genetic privacy, racial profiling, and the justice system. The use of machine learning to generate physical descriptions of human beings from biological material carries immense responsibility. 

This document outlines the strict ethical boundaries, scientific limitations, and privacy considerations for using this software in a forensic or research capacity.

## 1. Predictions are Leads, Not Identifications
This software generates a **probabilistic physical description** (e.g., "75% probability of brown eyes"). It does **not** identify an individual, nor does it provide a deterministic DNA fingerprint. 
*   **Investigative Use Only:** Phenotype reports should only be used to narrow down suspect pools or generate investigative leads when traditional CODIS database searches fail. 
*   **Not for Conviction:** Predictions from this software must *never* be used as primary evidence for conviction in a court of law.

## 2. Population Bias and Ancestry
Our models are trained on global datasets (such as the 1000 Genomes Project). However, machine learning inherits the biases of its training data.
*   **Super-Population Limits:** The Ancestry model classifies individuals into five broad super-populations (AFR, AMR, EAS, EUR, SAS). It is scientifically incapable of determining specific nationalities, ethnicities, or tribal affiliations. 
*   **Underrepresented Groups:** Populations that are underrepresented in global genomic databases may experience lower prediction accuracy. The model's confidence scores attempt to reflect this uncertainty, but investigators must remain vigilant against assuming high accuracy for historically marginalized groups.

## 3. The Danger of Imputation (Hallucination)
Forensic DNA is often degraded (e.g., sun-bleached bone, washed blood). When DNA is missing, machine learning models attempt to "impute" or guess the missing data based on global medians.
*   **Our Safeguard:** This software actively blocks extreme imputation. If critical DNA is missing, the platform refuses to generate a prediction rather than hallucinate a trait.
*   **Transparency:** The UI actively displays an "Evidence Quality Meter." If the meter is Yellow or Red, the investigator is explicitly warned that the prediction relies heavily on imputed data and should be treated with extreme skepticism.

## 4. Genetic Privacy
DNA contains the most sensitive data a human possesses, including predisposition to severe medical conditions (e.g., BRCA mutations for breast cancer).
*   **Trait Isolation:** This software only ingests and processes SNPs explicitly linked to visible, non-medical traits (Eye, Hair, and Skin pigmentation). 
*   **Medical Blindness:** The platform does not scan for, store, or predict any medically relevant genetic markers. 

## 5. Potential for Misuse
If misused, phenotype prediction can contribute to racial profiling. Law enforcement agencies utilizing this software must ensure that phenotype leads are cross-referenced with other robust investigative evidence (alibis, motive, physical forensics) before acting. Relying solely on an AI-generated phenotype prediction to target individuals is a severe violation of the intended use of this platform.
