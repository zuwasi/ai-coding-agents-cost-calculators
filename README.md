# AI Coding Agents Cost Calculators

Customer-ready desktop calculators for estimating and comparing real-world usage
cost for three AI coding agents on a real code repository:

| Option | Folder | Uses | Best for |
| --- | --- | --- | --- |
| Claude Code | `qt_dashboard/` | `claude -p --output-format json` | Measuring Claude Code when the CLI reports `total_cost_usd` directly. |
| Amp Code | `amp_dashboard/` | `amp -x --stream-json` | Estimating Amp usage by mode (`smart`, `deep`, `large`, `rush`). |
| Droid / Factory.ai | `droid_dashboard/` | `droid exec -o json` | Estimating Factory.ai Droid usage by selected model. |

The calculators analyze a repository, propose representative engineering tasks,
run selected task prompts through the chosen CLI, capture token usage/cost data,
and roll the result up into per-developer, per-team, monthly, and yearly
forecasts.

> These tools are forecasting aids, not vendor quotes. They help customers size
> budgets, compare usage patterns, and choose which AI coding agent or workflow
> to test first.

## What a customer can test

1. **Claude Code calculator** - if the customer already has Claude Code
   installed and authenticated.
2. **Amp Code calculator** - if the customer wants to evaluate Amp and has the
   Amp CLI installed/authenticated.
3. **Droid calculator** - if the customer wants to evaluate Factory.ai Droid and
   has Droid installed/authenticated.
4. **Forecast script** - `claude_cost_forecast.py` is a non-GUI Claude Code
   command-line baseline for customers who prefer CSV output.

Each calculator is independent. A customer can test only the tool they care
about without installing the other CLIs.

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

4. Choose the calculator to test from the menu.

The launcher checks for PyQt6 and installs it from the selected calculator's
`requirements.txt` if needed. It also warns when the selected CLI is not on
`PATH`, while still opening the UI so customers can see what the calculator
does.

## Manual run

From a terminal:

```powershell
cd C:\path\to\ai-coding-agents-cost-calculators

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

```text
Customer repository
        |
        v
Analyze repo and propose 5-7 tasks
        |
        v
Customer selects tasks and daily frequency
        |
        v
Run selected CLI and capture usage
        |
        v
Forecast per developer, team, month, and year
```

The prompts ask the agent to produce realistic, shippable work with docs and
tests in its response. They are designed to estimate real task cost rather than
the cost of a short sketch.

## Repository layout

```text
.
|-- run_dashboards.bat              # Customer menu to launch any calculator
|-- claude_cost_forecast.py         # Non-GUI Claude Code forecast script
|-- requirements.txt                # Shared GUI dependency
|-- LICENSE                         # MIT license
|-- NOTICE                          # Attribution/source notes
|-- qt_dashboard/
|   |-- claude_cost_dashboard.py
|   |-- run_dashboard.bat
|   |-- requirements.txt
|   `-- README.md
|-- amp_dashboard/
|   |-- amp_cost_dashboard.py
|   |-- run_dashboard.bat
|   |-- requirements.txt
|   `-- README.md
`-- droid_dashboard/
    |-- droid_cost_dashboard.py
    |-- run_dashboard.bat
    |-- requirements.txt
    `-- README.md
```

## Cost calculation notes

- **Claude Code**: uses `total_cost_usd` reported by Claude Code's JSON output.
- **Amp**: Amp currently reports usage tokens but not `total_cost_usd`, so the
  calculator estimates cost using `AMP_MODE_PRICING` in
  `amp_dashboard/amp_cost_dashboard.py`.
- **Droid**: Droid reports usage tokens but not `total_cost_usd`, so the
  calculator estimates cost using `DROID_MODEL_PRICING` in
  `droid_dashboard/droid_cost_dashboard.py`.

Customers with contracted pricing should update the pricing tables and seat
price fields before treating forecasts as budget inputs.

## Safety and privacy

- The calculators run the selected CLI against a repository path chosen by the
  customer.
- Prompts are written to be read-only: the agent is asked to return proposed
  implementation, documentation, and tests in its response rather than modifying
  files.
- Some CLI modes use permissive flags to avoid interactive permission prompts
  during measurement. Use a clean working tree, a disposable copy, or a test
  repository for customer demos.
- Repository content is sent only to the selected vendor CLI in the same way it
  would be sent during normal use of that agent.

## License

MIT. See [LICENSE](LICENSE).

## Original source

The Claude Code calculator is based on
[`zuwasi/claude-code-cost-dashboard`](https://github.com/zuwasi/claude-code-cost-dashboard)
and has been extended here with Amp and Droid variants plus a shared customer
launcher.

## Maintainer verification

Before sharing a new release with customers, verify:

```powershell
py -3 -m py_compile claude_cost_forecast.py `
  qt_dashboard\claude_cost_dashboard.py `
  amp_dashboard\amp_cost_dashboard.py `
  droid_dashboard\droid_cost_dashboard.py
```

For visual verification, launch `run_dashboards.bat` and open each calculator.
