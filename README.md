# AI Coding Agent Cost Dashboards

Customer-ready desktop tools for estimating and comparing real-world usage cost
for three AI coding agents on a real code repository:

| Option | Folder | Uses | Best for |
| --- | --- | --- | --- |
| Claude Code | `qt_dashboard/` | `claude -p --output-format json` | Measuring Claude Code when the CLI reports `total_cost_usd` directly. |
| Amp Code | `amp_dashboard/` | `amp -x --stream-json` | Estimating Amp usage by mode (`smart`, `deep`, `large`, `rush`). |
| Droid / Factory.ai | `droid_dashboard/` | `droid exec -o json` | Estimating Factory.ai Droid usage by selected model. |

The dashboards analyze a repository, propose representative engineering tasks,
run selected task prompts through the chosen CLI, capture token usage/cost data,
and roll the result up into per-developer, per-team, monthly, and yearly
forecasts.

> These tools are forecasting aids, not vendor quotes. They are intended to help
> customers size budgets, compare usage patterns, and choose which agent or
> workflow to test first.

## What a customer can test

1. **Claude Code dashboard** - if the customer already has Claude Code installed
   and authenticated.
2. **Amp Code dashboard** - if the customer wants to evaluate Amp and has the Amp
   CLI installed/authenticated.
3. **Droid dashboard** - if the customer wants to evaluate Factory.ai Droid and
   has Droid installed/authenticated.
4. **Forecast script** - `claude_cost_forecast.py` is a non-GUI Claude Code
   command-line baseline for customers who prefer CSV output.

Each dashboard is independent. A customer can test only the tool they care about
without installing the other CLIs.

## Quick start on Windows

1. Install **Python 3.9+**.
2. Install and authenticate at least one supported coding-agent CLI:
   - Claude Code: install from Anthropic's Claude Code documentation, then ensure
     `claude` is on `PATH`.
   - Amp: install the Amp CLI and authenticate with `amp login` or `AMP_API_KEY`.
   - Droid: install the Droid CLI from Factory.ai and set `FACTORY_API_KEY` if
     required by your environment.
3. Double-click:

   ```text
   run_dashboards.bat
   ```

4. Choose the dashboard to test from the menu.

The launcher checks for PyQt6 and installs it from the selected dashboard's
`requirements.txt` if needed. It also warns when the selected CLI is not on
`PATH`, while still opening the UI so customers can see what the dashboard does.

## Manual run

From a terminal:

```powershell
cd C:\path\to\ai-coding-agent-cost-dashboards

# Claude Code GUI
cd qt_dashboard
pip install -r requirements.txt
python claude_cost_dashboard.py

# Amp GUI
cd ..\amp_dashboard
pip install -r requirements.txt
python amp_cost_dashboard.py

# Droid GUI
cd ..\droid_dashboard
pip install -r requirements.txt
python droid_cost_dashboard.py
```

## How the workflow works

```diagram
╭────────────────────╮
│ Customer repository │
╰─────────┬──────────╯
          │
          ▼
╭────────────────────╮
│ Analyze repo        │
│ propose 5-7 tasks   │
╰─────────┬──────────╯
          │
          ▼
╭────────────────────╮
│ Customer selects    │
│ tasks + frequency   │
╰─────────┬──────────╯
          │
          ▼
╭────────────────────╮
│ Run selected CLI    │
│ capture usage       │
╰─────────┬──────────╯
          │
          ▼
╭────────────────────╮
│ Forecast per dev,   │
│ team, month, year   │
╰────────────────────╯
```

The prompts ask the agent to produce realistic, shippable work with docs and
tests in its response. They are designed to estimate real task cost rather than
the cost of a short sketch.

## Repository layout

```text
.
├── run_dashboards.bat              # Customer menu to launch any dashboard
├── claude_cost_forecast.py         # Non-GUI Claude Code forecast script
├── qt_dashboard/
│   ├── claude_cost_dashboard.py
│   ├── run_dashboard.bat
│   ├── requirements.txt
│   └── README.md
├── amp_dashboard/
│   ├── amp_cost_dashboard.py
│   ├── run_dashboard.bat
│   ├── requirements.txt
│   └── README.md
└── droid_dashboard/
    ├── droid_cost_dashboard.py
    ├── run_dashboard.bat
    ├── requirements.txt
    └── README.md
```

## Cost calculation notes

- **Claude Code**: uses `total_cost_usd` reported by Claude Code's JSON output.
- **Amp**: Amp currently reports usage tokens but not `total_cost_usd`, so the
  dashboard estimates cost using `AMP_MODE_PRICING` in
  `amp_dashboard/amp_cost_dashboard.py`.
- **Droid**: Droid reports usage tokens but not `total_cost_usd`, so the
  dashboard estimates cost using `DROID_MODEL_PRICING` in
  `droid_dashboard/droid_cost_dashboard.py`.

Customers with contracted pricing should update the pricing tables and seat
price fields before treating forecasts as budget inputs.

## Safety and privacy

- The dashboards run the selected CLI against a repository path chosen by the
  customer.
- Prompts are written to be read-only: the agent is asked to return proposed
  implementation, documentation, and tests in its response rather than modifying
  files.
- Some CLI modes use permissive flags to avoid interactive permission prompts
  during measurement. Use a clean working tree, a disposable copy, or a test
  repository for customer demos.
- Repository content is sent only to the selected vendor CLI in the same way it
  would be sent during a normal use of that agent.

## Preparing/pushing upstream

This folder is intended to be the upstream repository root. A clean push should
include the dashboard source, READMEs, requirements, launcher scripts, license,
and screenshot assets, but not generated Python caches or local reports.

Suggested first push:

```powershell
git init
git add .
git commit -m "Customer-ready AI coding agent cost dashboards"
git branch -M main
git remote add origin <customer-facing-repo-url>
git push -u origin main
```

Before sharing with customers, verify:

```powershell
py -3 -m py_compile claude_cost_forecast.py `
  qt_dashboard\claude_cost_dashboard.py `
  amp_dashboard\amp_cost_dashboard.py `
  droid_dashboard\droid_cost_dashboard.py
```

For visual verification, launch `run_dashboards.bat` and open each dashboard.

## Original source

The Claude Code dashboard is based on
[`zuwasi/claude-code-cost-dashboard`](https://github.com/zuwasi/claude-code-cost-dashboard)
and has been extended here with Amp and Droid variants plus a shared customer
launcher.
