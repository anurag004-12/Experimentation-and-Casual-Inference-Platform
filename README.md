# Experimentation and Causal Inference Platform

An internal tool that helps teams design A/B tests, analyze them correctly, and
estimate cause and effect when experiments are not possible. It doesn't just
compute a p-value; it tells you whether the experiment can be trusted.

## Project structure
```
experimentation-platform/
├── backend/     FastAPI service + statistics code (app/) and tests (tests/)
├── frontend/    React UI (Phase 4)
└── docs/        Architecture notes
```

## Status
- [x] Phase 1: simulator, power calculator, SRM check, CUPED, FastAPI endpoints
- [x] Phase 2a: chi-square test, Bonferroni / Benjamini-Hochberg corrections
- [ ] Phase 2b: sequential testing (peeking simulation)
- [ ] Phase 3: Bayesian A/B (PyMC), propensity matching, DiD, synthetic control
- [ ] Phase 4: React front end, deployment, final write-up

## Run the backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --reload     # docs at http://127.0.0.1:8000/docs
```

See [docs/architecture.md](docs/architecture.md) for the design.
