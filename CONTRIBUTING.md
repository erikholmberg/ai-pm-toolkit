# Contributing

Thanks for considering contributing. A few pointers so the toolkit stays easy to navigate:

## Where things go

| Content | Location | Notes |
|--------|----------|--------|
| **Python scripts** | `scripts/` | Use argparse, docstring with Usage/CSV format. Add to [scripts/README.md](scripts/README.md) in the right category; add a `sample-*.csv` in `scripts/samples/` if the script takes CSV input. |
| **Prompts** | `prompts/core-pm/`, `prompts/ai-ml/`, or `prompts/developer-community/` | Use `.prompt.md` suffix. Add a one-line entry to [prompts/README.md](prompts/README.md). |
| **Templates** | `templates/` | Markdown templates (PRD, OKR, RICE, etc.). |
| **MCP servers** | `mcps/servers/<name>/` | Document in [mcps/README.md](mcps/README.md) and in the server’s own README with env vars. |
| **Eval scripts** | `evals/scripts/` | Document in [evals/scripts/README.md](evals/scripts/README.md). |

## Script conventions

- Python 3.10+, dependencies in `scripts/requirements.txt`.
- `python script.py --help` should show usage and main options.
- If the script reads CSV, add a small `sample-<topic>.csv` in `scripts/samples/` and reference it in `scripts/README.md`.

## Submitting changes

Open a PR with your changes. For new scripts, add an entry to the right category in `scripts/README.md` (and a sample CSV if applicable).
