# Agentic Chargeback Dispute Resolution Assistant

This project implements a local-first chargeback investigation demo with a FastAPI API, a single Streamlit analyst screen, a bounded LangGraph planner/tool cycle, deterministic decisions, PII masking, prompt-injection checks, SQLite case/audit/feedback persistence, and a synthetic evaluation harness.

The bundled demo records are India-localized: amounts use INR, case deadlines use India Standard Time offsets, and synthetic merchants, customers, addresses, and delivery services use Indian locations. These are fictional assessment fixtures, not real financial or personal records.

## Prerequisites

- Python 3.11+
- Git
- Ollama

## Setup

```bash
git clone <repository>
cd chargeback-agent

python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Pull the local model (Qwen generates grounded explanations; Python rules control final decisions):

```bash
ollama --version
ollama pull qwen3:8b
ollama serve
```

Health check:

```bash
curl http://localhost:11434/api/tags
```

Copy environment defaults:

```bash
cp .env.example .env
```

On Windows, use `Copy-Item .env.example .env` in PowerShell.

## Run the backend

```bash
uvicorn app.main:app --reload
```

## Run the analyst UI

```bash
streamlit run app/ui/streamlit_app.py
```

The form accepts PDF, `.eml`, `.txt`, PNG, and JPEG evidence. Select the evidence types that are actually present. PDF/email text is extracted; images are previewed but are not OCR-read by the configured Qwen text model, so summarize image facts in Case details. Missing or conflicting fields are surfaced for analyst review.

The UI shows the deterministic recommendation, Qwen-generated rationale when available, evidence citations/status, investigation steps, and approve/reject/edit controls. Analyst choices are stored in SQLite.

## Run the tests

```bash
pytest
```

For step-by-step UI, API, upload, guardrail, and evaluation checks, see [docs/testing-guide.md](docs/testing-guide.md).

## Run the evaluation harness

```bash
python -m evaluation.run_evaluation
```

The harness uses deterministic rules and versioned synthetic evidence fixtures; it does not call Ollama. It reports decision/reason-code accuracy, deadline correctness, escalation accuracy, citation validity/relevance, latency, tool counts, token counts, and writes `evaluation/results.json` plus `evaluation/error_analysis.json`. The synthetic score is not a claim of production accuracy.

## Key architecture points

- FastAPI serves the API and health endpoints
- LangGraph runs a bounded planner/investigator cycle driven by missing required evidence
- deterministic rule checks govern evidence completeness, reason-specific outcomes, deadlines, and escalation
- PII masking, injection detection, citation allowlisting, and schema validation guard model output
- the model explains the decision; it cannot replace the deterministic final decision
- synthetic cases and evaluation output are used for repeatability and testability

## Presentation

See [Chargeback_Architecture_and_Testing.pptx](Chargeback_Architecture_and_Testing.pptx) for the application use case, current architecture flow, safety boundaries, and step-by-step manual tests with expected results for every documented case ID.

## Important notes

- The API startup check verifies that Ollama and the configured model are available.
- The Streamlit UI falls back to deterministic reasoning when Ollama is unavailable and labels that fallback.
- Investigation APIs use explicit synthetic records; unknown identifiers return `not_found`.
- Synthetic rules are not official Visa/Mastercard policy. Replace them with versioned network rules and reviewed policy before production use.
- Images are accepted, validated, and previewed, but the current Qwen3 configuration does not perform OCR/vision extraction.
