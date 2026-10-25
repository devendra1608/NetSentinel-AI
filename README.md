# NetSentinel-AI

A machine-learning-powered network intrusion detection system based on
the research paper "Adaptive Network Anomaly Detection Using Machine
Learning Approaches" (2025).

## Planned capabilities

- Network traffic preprocessing and feature engineering
- Random Forest, Gradient Boosting, KNN, SVM, and Logistic Regression
- Hard voting, soft voting, and stacking ensembles
- Classification metrics and feature importance
- FastAPI backend and Next.js security dashboard
- Controlled-environment live traffic detection

## Project status

Phase 0: Repository and development environment setup.

## Research datasets

The initial experimental dataset is CICIDS2017. NFS-2023-TE may be
added for additional evaluation if its data and licensing requirements
are verified.

## Development principles

- Reproducible training and evaluation
- Separate training and inference pipelines
- No evaluation on training data
- Report per-class metrics, including minority attack classes
- Do not claim research results until independently reproduced

## Safety

Live traffic collection and security testing must be limited to
systems and networks for which we have authorization.

## License

To be determined after reviewing the dataset and dependency licenses.
