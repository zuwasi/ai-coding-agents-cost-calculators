# Amp Code Cost Dashboard

A desktop forecasting tool that estimates the cost of using
[Amp Code](https://ampcode.com/) on a real repository. It is a customer-ready
Amp variant of the original Claude Code cost dashboard.

## What it does

1. You point it at a repo on disk.
2. It calls `amp -x --stream-json` to skim the repo and propose 5-7 typical
   engineering tasks tailored to that codebase.
3. You pick which suggested tasks to estimate and adjust how many times per day
   each one happens.
4. For each chosen task it runs `amp -x --stream-json` again with a prompt that
   asks for realistic, shippable work with documentation and tests in the
   response.
5. It rolls those per-task numbers up into a per-dev / per-team / per-year
   forecast and compares the result to the cost of Amp seats.

## How cost is computed

Unlike Claude Code, the Amp CLI does **not** emit a `total_cost_usd` field in
its JSON output. This dashboard estimates cost as:

```text
cost_usd = (input_tokens          * input_rate
         +  output_tokens         * output_rate
         +  cache_read_tokens     * cache_read_rate
         +  cache_creation_tokens * cache_creation_rate) / 1_000_000
```

using a price table keyed off the selected Amp **mode** (`smart`, `deep`,
`large`, `rush`). The table, `AMP_MODE_PRICING` near the top of
[`amp_cost_dashboard.py`](amp_cost_dashboard.py), uses best-effort
USD-per-million-token estimates of the underlying frontier model that each mode
dispatches to. Edit it to match your contract.

The "Seat $/mo" spinner controls the assumed Amp seat list price. The default
is $40/seat/month.

## Requirements

- Python 3.9+
- `PyQt6 >= 6.5` (`pip install -r requirements.txt`)
- The Amp CLI installed and authenticated:
  - install the Amp CLI using the current Amp instructions
  - run `amp login` or set `AMP_API_KEY`

## Run

```cmd
pip install -r requirements.txt
python amp_cost_dashboard.py
```

or double-click `run_dashboard.bat` on Windows. From the repository root,
customers can also double-click `run_dashboards.bat` and choose option 2.

## Caveats

- This is a forecasting / planning aid, not a quote.
- Amp bills via credits, not per-token, so the USD figures should be read as
  comparable underlying-model cost for benchmarking and sizing.
- Real bills can still run 1.5-3x higher than this forecast due to iteration,
  long autonomous sessions, and MCP context bloat.
