# Contributing Guidelines

Thank you for your interest in contributing to the Forensic Phenotype Predictor!

## Folder Structure
- `/backend`: FastAPI Python server and REST API logic.
- `/frontend`: Next.js React user interface.
- `/src/phenotype_predictor`: The core machine learning algorithms and inference engine.
- `/tests`: Pytest automated testing suite.
- `/scripts`: Data preparation, benchmarking, and training scripts.

## Coding Style
- **Python**: We adhere strictly to `PEP-8`. Please use Type Hints (`typing`) for all function signatures to maintain robust architecture.
- **TypeScript**: Use strict typing. Any new UI components should follow Tailwind CSS standard practices.

## Pull Request Process
1. Fork the repository and create your branch from `main`.
2. Ensure your code passes the test suite (`python -m pytest`). If you add new ML features, write corresponding tests.
3. Update the `CHANGELOG.md` with your changes.
4. Ensure any new API endpoints are documented in `docs/api.md`.
5. Issue a Pull Request with a detailed description of the architectural changes.
