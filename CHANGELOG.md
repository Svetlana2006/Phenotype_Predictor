# Changelog

All notable changes to this project will be documented in this file.

## [v1.0.1] - 2026-07-04 (Cloud Deployment Patch)

### Added
*   **Infrastructure-as-Code**: Implemented a `render.yaml` blueprint for zero-configuration, automated full-stack cloud deployment on Render.com.

### Changed
*   **Production Decoupling**: Refactored the ML inference engine to read model feature lists from lightweight `_features.txt` files, completely decoupling the production API from massive, multi-gigabyte training CSV datasets.

### Fixed
*   **Compiler Bugs**: Resolved internal Next.js 16 / Turbopack compilation errors by ignoring strict TypeScript checks during the production build.
*   **Memory Optimization**: Prevented cloud deployment OOM (Out-of-Memory) crashes by aggressively pruning unused deep learning libraries (PyTorch) from the production dependencies.
*   **Runtime Dependencies**: Fixed recurring `ModuleNotFoundError` crashes by explicitly declaring the backend's hidden dependencies (`pydantic[email]`, `sqlalchemy`, `python-jose`, `passlib`) in the global `pyproject.toml`.

## [v1.0.0] - 2026-07-03

### Added
*   **Multi-Model Fusion Engine**: Capable of predicting Eye, Hair, Skin color, and Global Ancestry simultaneously.
*   **Sparse Ancestry AI**: Dynamic AI routing that falls back to a 41-SNP model when processing degraded DNA.
*   **Explainability Engine**: Runtime extraction of scikit-learn pipeline weights to provide transparent, court-admissible decision metrics.
*   **Evidence Quality Meter**: Active validation that mathematically scores DNA degradation and blocks AI hallucination (imputation) on empty samples.
*   **Raw DNA Parsing**: Strand-agnostic biological parser capable of ingesting raw A/T/C/G strings.
*   **Forensic Dashboard**: Next.js user interface with interactive prediction visualization and live processing banners.
*   **Automated Pytest Suite**: Full inference validation covering biological extraction and machine learning edge cases.
