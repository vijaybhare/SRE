# prr-readiness

A CLI and web app that assesses a change/release document against SRE
Production Readiness Review (PRR) criteria and returns a Ready / Conditional
/ Not Ready gate decision.

The default rubric is grounded in Google's *The Site Reliability Workbook*
(O'Reilly, 2018) — Ch.18 SRE Engagement Model (which defines the PRR itself),
plus Ch.2 Implementing SLOs, Ch.4 Monitoring, Ch.5 Alerting on SLOs,
Ch.6 Eliminating Toil, Ch.8 On-Call, Ch.9 Incident Response, Ch.11 Managing
Load, and Ch.16 Canarying Releases. It's organization-agnostic — bring your
own SRE checklist instead via `normalize-criteria` if you want.

It's built on `arch-compliance`, a small generic engine (also included here)
that extracts text/images from a document, grades it against a rubric with
an LLM, and deterministically aggregates the score.

## Install

```bash
pip install -e .           # CLI only
pip install -e ".[web]"    # CLI + web app
```

Point at an OpenAI-compatible endpoint:

```bash
export OPENAI_API_KEY=sk-...
# or, for Core42/G42 Compass or another compatible gateway:
export COMPASS_API_KEY=...
export COMPASS_BASE_URL=https://<your-endpoint>/v1
export ARCH_COMPLIANCE_MODEL=<model name>   # must support image input
```

## CLI usage

```bash
# Assess a change against the built-in SRE Workbook PRR rubric
prr-readiness assess --change release-notes/payments-v2.docx --format md --output prr-report.md

# Or bring your own SRE readiness checklist instead of the default rubric
prr-readiness normalize-criteria --input standards/sre-readiness-checklist.pdf --output criteria.json
prr-readiness assess --change release-notes/payments-v2.docx --rubric criteria.json
```

`assess` exits non-zero when the gate decision is `NOT READY`, so it can be
wired into a CI/CD gate ahead of a staged/canary go-live step.

## Web app

```bash
pip install -e ".[web]"
prr-readiness-web
# open http://localhost:8000
```

- `POST /api/assess` — upload a change document (+ optional custom rubric JSON), returns a `job_id`.
- `POST /api/normalize-criteria` — upload standards document(s), returns a `job_id`.
- `GET /api/jobs/{job_id}` — poll for `pending` → `running` → `done`/`error`.

Both run as background jobs since grading a document is an LLM call that can
take 10-30+ seconds. The frontend (`prr_readiness/static/`) is plain
HTML/CSS/JS with no build step.

Configure host/port via `PRR_WEB_HOST` / `PRR_WEB_PORT` (default
`0.0.0.0:8000`). This is a single-process demo server (in-memory job store,
no auth) — put it behind your org's auth/reverse proxy before exposing it
beyond local use.

## Notes / limitations

- `ARCH_COMPLIANCE_MODEL` env var selects the model (must support image input to grade diagrams).
- Document text is truncated to ~60k characters and diagrams to the first 20 PDF pages per call.
- Review any generated `rubric.json` before relying on it — spot-check that
  requirements were split atomically and weighted sensibly.
