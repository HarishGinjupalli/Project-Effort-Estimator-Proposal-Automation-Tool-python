# Client Effort Estimator & Proposal Automation Tool

A Python-based consulting utility that turns raw client requirements into a
costed effort estimate and a client-ready Word proposal — the kind of workflow
a delivery/consulting analyst runs before a statement of work goes out.

## Why this project exists

Consulting engagements (the type Infosys' Enterprise Package Application
Services teams run) live and die on three things:

1. **Accurate effort estimation** — translating requirements into person-days
2. **Defensible pricing** — applying a rate card + complexity + risk buffer in
   a way that's consistent and auditable
3. **Fast, professional proposal turnaround** — not re-typing the same Word
   document structure every time

This tool automates all three, driven entirely by config files (YAML), so
rate cards, complexity multipliers, and risk buffers can be updated without
touching code — a lightweight configuration-management pattern.

## Features

- **Config-driven rate card** (`config/rate_card.yaml`): role-wise daily
  rates, currency, complexity multipliers, risk contingency %
- **Works with any reasonably-shaped requirements CSV** — column names for
  requirement ID, description, role, and complexity are auto-detected from
  common aliases (`role` or `assigned_role`, `requirement_description` or
  `requirement_title`, etc.). No need to reformat exports from Jira, Azure
  DevOps, or a client's own tracker before running the tool. See
  [Working with different CSV schemas](#working-with-different-csv-schemas).
- **Graceful fallback pricing**: unrecognized roles or complexity values
  don't crash the run — they price at a configurable default rate/complexity
  and get flagged in the log, so a first pass at any dataset always
  completes. `--strict` mode is available when you want hard failures instead.
- **Visual summary charts**: every proposal includes a cost-by-role bar
  chart, an effort-by-complexity pie chart, and a top-cost-drivers chart
  (auto-skipped for very small requirement lists), rendered with
  matplotlib and embedded directly in the Word doc. Skip them with
  `--no-charts` if you just want the tables.
- **Effort estimation engine** (`src/estimator.py`): reads client
  requirements (CSV), computes person-days per requirement based on
  complexity and role mix, applies risk buffer, rolls up to a total estimate
- **Cost calculation**: person-days × rate card → line-item and total cost,
  with currency formatting
- **Proposal generation** (`src/proposal_generator.py`): builds a formatted
  Word (.docx) proposal — cover section, scope table, effort & cost
  breakdown table, assumptions, and terms — using `python-docx`
- **CLI** (`main.py`): single command from CSV input to finished `.docx`
- **Config validation**: guards against malformed rate cards / missing roles
  before any estimate is generated
- **Logging**: structured run log written to `output/run.log`
- **Unit tests** (`pytest`): covers estimator math, config validation,
  column auto-detection across schemas, fallback pricing, and edge cases

## Project structure

```
project-effort-estimator/
├── README.md
├── requirements.txt
├── .gitignore
├── main.py                        # CLI entry point
├── config/
│   ├── rate_card.yaml             # roles, daily rates, multipliers, buffer
│   └── config.yaml                # company info, currency, output paths
├── data/
│   └── sample_client_requirements.csv
├── src/
│   ├── __init__.py
│   ├── config_manager.py          # loads + validates YAML config
│   ├── column_mapper.py            # auto-detects CSV columns across schemas
│   ├── estimator.py                # effort & cost calculation engine
│   ├── chart_generator.py          # matplotlib charts embedded in the proposal
│   ├── proposal_generator.py       # builds the Word proposal
│   └── utils.py                    # logging setup, helpers
├── tests/
│   ├── __init__.py
│   ├── test_config_manager.py
│   ├── test_column_mapper.py
│   ├── test_chart_generator.py
│   └── test_estimator.py
└── output/                         # generated proposals + logs land here
```

## Setup (Windows / VS Code)

```powershell
# from the project root, in a VS Code terminal
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```powershell
python main.py --input data/sample_client_requirements.csv --client "Contoso Retail" --output output/Contoso_Proposal.docx
```

A larger, differently-shaped example is included too — `data/enterprise_requirements_dataset.csv`
(320 rows, uses `assigned_role`/`requirement_title` instead of `role`/`requirement_description`):

```powershell
python main.py --input data/enterprise_requirements_dataset.csv --client "Digital Transformation Program" --output output/DigitalTransformation_Proposal.docx
```

Both run through the exact same command shape — the tool figures out the column layout on its own.

Skip the chart section (tables only) with `--no-charts`:

```powershell
python main.py --input data/sample_client_requirements.csv --client "Contoso Retail" --output output/Contoso_Proposal.docx --no-charts
```

Run the test suite:

```powershell
pytest tests/ -v
```

## Sample workflow

1. Client shares a requirements list → saved as CSV (`data/sample_client_requirements.csv`)
2. `estimator.py` maps each requirement to a role + complexity, computes
   person-days, applies the risk buffer from `rate_card.yaml`
3. `proposal_generator.py` renders everything into a Word document with a
   scope table and a cost summary table
4. Output lands in `output/`, ready to send to the client

## Configuration example

`config/rate_card.yaml` defines roles like:

```yaml
roles:
  Python Developer: 8000
  Senior Consultant: 14000
  Business Analyst: 9500
complexity_multiplier:
  Low: 1.0
  Medium: 1.5
  High: 2.2
risk_buffer_percent: 12
currency: INR
```

Change rates, add roles, or adjust the risk buffer without touching a single
line of Python — this is the "software configuration management" pattern
referenced in enterprise consulting workflows.

## Working with different CSV schemas

Real requirement exports rarely share one column layout. The tool auto-detects
four fields it needs and leaves everything else (epic, module, sprint,
status, priority, ...) untouched — nothing needs to be stripped out of your
CSV first.

| Logical field | Auto-detected from (first match wins) |
|---|---|
| requirement id | `requirement_id`, `req_id`, `id`, `story_id`, `ticket_id`, `item_id` |
| description | `requirement_description`, `description`, `requirement_title`, `title`, `summary`, `task_description`, `story_title` |
| role | `assigned_role`, `role`, `resource_role`, `assignee_role`, `responsible_role`, `resource`, `assignee` |
| complexity | `complexity`, `story_complexity`, `effort_complexity`, `size` |

If your CSV uses a column name outside that list, override it explicitly:

```powershell
python main.py --input data/my_export.csv --client "Acme Corp" --output output/Acme_Proposal.docx --role-col "Resource Type" --desc-col "Notes"
```

**Unknown roles or complexity values** (e.g. a role not yet in
`rate_card.yaml`) don't stop the run — they're priced using
`default_role_rate` / `default_complexity` from the rate card, and flagged
in the console/log output so you know what to add to the rate card for a
more accurate estimate next time:

```
WARNING | Roles not in rate_card.yaml, priced at default_role_rate (9000): ['UI/UX Lead']
```

Run with `--strict` to fail the run instead of falling back — useful once a
rate card is finalized and you want to catch typos or genuinely new roles
rather than silently defaulting them.

## Possible extensions

- REST API wrapper (FastAPI) so estimates can be requested by a front-end
- Multi-currency support with live FX rates
- PDF export alongside Word
- Historical estimate tracking (SQLite) to compare estimated vs. actual effort
