# Claude Code Cost Dashboard (Qt6)

Desktop dashboard built on top of Claude Code's JSON cost reporting. It uses
Claude Code's own per-call `total_cost_usd` values to forecast spend in an
interactive customer demo flow.

## What it does

1. You point it at a repo on disk.
2. It calls `claude -p` to analyze the repo and suggest 5-7 typical tasks
   tailored to that codebase.
3. You pick which suggested tasks to estimate and adjust how often per day each
   one is done.
4. For each chosen task it runs `claude -p` with a prompt that asks for
   realistic, shippable work with documentation and tests in the response.
5. It rolls those per-task numbers up into a per-dev / per-team / per-year
   forecast and compares the result to Premium seat pricing.

## Requirements

- Python 3.9+
- [PyQt6](https://pypi.org/project/PyQt6/) (`pip install -r requirements.txt`)
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and
  authenticated, with `claude` on your `PATH`

## Run

```powershell
pip install -r requirements.txt
python claude_cost_dashboard.py
```

or double-click `run_dashboard.bat` on Windows. From the repository root,
customers can also double-click `run_dashboards.bat` and choose option 1.

The dashboard will warn in the status bar if `claude` is not on PATH.

## Notes

- The estimate prompt explicitly asks Claude to write the change, write the
  docs, and write the tests in its response without modifying files. That makes
  the captured `total_cost_usd` a realistic per-task figure rather than a
  quick-sketch lower bound.
- The repo analysis itself costs a small amount; that one-off cost is reported
  separately in the Forecast panel.
- `--permission-mode bypassPermissions` is set internally so Claude does not
  pause for confirmation prompts mid-run.
- All tasks are read-only by design; nothing is written to disk.
- Real bills can still run 1.5-3x the forecast because of long autonomous
  sessions, agent teams, MCP context bloat, and iteration churn.
