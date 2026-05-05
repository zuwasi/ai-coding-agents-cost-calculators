# Droid (Factory.ai) Cost Dashboard

A desktop forecasting tool that estimates the cost of using
[Droid](https://docs.factory.ai/cli/getting-started/overview), Factory.ai's AI
coding agent, on a real repository. It is a customer-ready Droid variant of the
original Claude Code cost dashboard.

## What it does

1. You point it at a repo on disk.
2. It calls `droid exec -o json` to skim the repo and propose 5-7 typical
   engineering tasks tailored to that codebase.
3. You pick which suggested tasks to estimate and adjust how many times per day
   each one happens.
4. For each chosen task it runs `droid exec -o json` again with a prompt that
   asks for realistic, shippable work with documentation and tests in the
   response.
5. It rolls those per-task numbers up into a per-dev / per-team / per-year
   forecast and compares the result to the cost of Factory.ai seats.

## How cost is computed

The Droid CLI's `-o json` output reports token usage but **not** a
`total_cost_usd` field. This dashboard estimates cost as:

```text
cost_usd = (input_tokens          * input_rate
         +  output_tokens         * output_rate
         +  cache_read_tokens     * cache_read_rate
         +  cache_creation_tokens * cache_creation_rate) / 1_000_000
```

using a price table keyed off the selected **model** (`claude-opus-4-7`,
`claude-sonnet-4-6`, `gpt-5.5`, `glm-5.1`, etc.). The table,
`DROID_MODEL_PRICING` near the top of
[`droid_cost_dashboard.py`](droid_cost_dashboard.py), uses best-effort
USD-per-million-token estimates of the underlying model's API list price. Edit
it to match your contract.

The "Seat $/mo" spinner controls the assumed Factory.ai seat list price. The
default is $40/seat/month.

## Requirements

- Python 3.9+
- `PyQt6 >= 6.5` (`pip install -r requirements.txt`)
- The Droid CLI installed and authenticated:
  - install via Factory.ai's current instructions
  - set `FACTORY_API_KEY` if required by your environment

## Run

```cmd
pip install -r requirements.txt
python droid_cost_dashboard.py
```

or double-click `run_dashboard.bat` on Windows. From the repository root,
customers can also double-click `run_dashboards.bat` and choose option 3.

## Caveats

- This is a forecasting / planning aid, not a quote.
- Each estimation run is invoked with `--skip-permissions-unsafe` so the agent
  can read freely. The prompt explicitly forbids writing to disk, but you should
  still point this at a clean working tree or a disposable copy.
- Real bills can run 1.5-3x higher than this forecast due to iteration, long
  autonomous sessions, and MCP context bloat.
