#!/usr/bin/env python3
# Copyright 2026 zuwasi
#
# SPDX-License-Identifier: MIT
"""
Droid (Factory.ai) Cost Dashboard (Qt6).

A desktop dashboard that:
  1. Lets you point at a repo on disk.
  2. Calls `droid exec -o json` to analyze the repo and SUGGEST a set of
     typical tasks tailored to that codebase.
  3. Lets you pick which suggested tasks to estimate.
  4. For each chosen task, runs `droid exec -o json` with a prompt that
     demands the task be done CORRECTLY, with DOCUMENTATION and TESTING,
     and captures per-task tokens / duration / estimated cost.
  5. Displays per-task results and a rolled-up cost estimate.

NOTE: The Droid CLI's `-o json` output reports token usage but not a
`total_cost_usd` field. This dashboard ESTIMATES cost from the reported
token usage using a built-in price table keyed off the selected model.
Adjust the table below to match Factory.ai's billing if it changes.

Requires:
    - Python 3.9+
    - PyQt6
    - Droid CLI (`droid` on PATH), authenticated (FACTORY_API_KEY set)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


# ---------------------------------------------------------------------------
# Theme: Droid — emerald/cyan brand
# ---------------------------------------------------------------------------

ACCENT_1 = "#10B981"   # emerald
ACCENT_2 = "#06B6D4"   # cyan
ACCENT_GLOW = "#34D399"
TOOL_TITLE = "Droid Cost Dashboard"
TOOL_TAGLINE = "Forecast real spend on Factory.ai's Droid CLI"
TOOL_EMOJI = "🤖"


def _apply_theme(app: QApplication) -> None:
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor("#0B1020"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#E2E8F0"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#101729"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#1E293B"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#F1F5F9"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#1E293B"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#F8FAFC"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT_1))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#0B1020"))
    app.setPalette(pal)
    app.setStyleSheet(f"""
        QMainWindow, QWidget {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #0B1020, stop:0.55 #111827, stop:1 #1E293B);
            color: #E2E8F0;
            font-family: "Inter", "Segoe UI", system-ui, sans-serif;
            font-size: 10pt;
        }}
        #HeroHeader {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {ACCENT_2}, stop:0.5 {ACCENT_1}, stop:1 {ACCENT_GLOW});
            border-radius: 14px;
            padding: 8px;
        }}
        #HeroTitle {{
            color: #FFFFFF;
            font-size: 22pt;
            font-weight: 800;
            letter-spacing: 0.5px;
        }}
        #HeroTagline {{
            color: rgba(255,255,255,200);
            font-size: 10pt;
            font-weight: 500;
        }}
        QGroupBox {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(30, 41, 59, 230),
                stop:1 rgba(15, 23, 42, 230));
            border: 1px solid rgba(148, 163, 184, 60);
            border-radius: 12px;
            margin-top: 22px;
            padding: 14px 10px 10px 10px;
            font-weight: 600;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 4px 14px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {ACCENT_2}, stop:1 {ACCENT_1});
            color: white;
            border-radius: 8px;
            font-size: 10pt;
            font-weight: 700;
        }}
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {ACCENT_1}, stop:1 {ACCENT_2});
            color: white;
            border: 0;
            border-radius: 9px;
            padding: 9px 18px;
            font-weight: 700;
            font-size: 10pt;
            min-height: 18px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {ACCENT_GLOW}, stop:1 {ACCENT_1});
        }}
        QPushButton:pressed {{
            background: {ACCENT_2};
            padding-top: 11px; padding-bottom: 7px;
        }}
        QPushButton:disabled {{
            background: #334155; color: #64748B;
        }}
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            background: rgba(15, 23, 42, 220);
            border: 1px solid #334155;
            border-radius: 7px;
            padding: 6px 10px;
            color: #F1F5F9;
            selection-background-color: {ACCENT_1};
            min-height: 18px;
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 2px solid {ACCENT_1};
        }}
        QComboBox::drop-down {{ border: 0; width: 18px; }}
        QComboBox QAbstractItemView {{
            background: #1E293B; color: #F1F5F9;
            selection-background-color: {ACCENT_1};
            selection-color: #0B1020;
            border: 1px solid #334155; border-radius: 6px;
        }}
        QTableWidget {{
            background: rgba(15, 23, 42, 200);
            alternate-background-color: rgba(30, 41, 59, 120);
            gridline-color: #334155;
            color: #E2E8F0;
            border: 1px solid #334155;
            border-radius: 8px;
        }}
        QHeaderView::section {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {ACCENT_1}, stop:1 #064E3B);
            color: white; padding: 8px; border: 0; font-weight: 700;
        }}
        QPlainTextEdit {{
            background: #050912; color: #94A3B8;
            border: 1px solid #334155; border-radius: 7px; padding: 6px;
        }}
        QCheckBox {{ spacing: 8px; }}
        QCheckBox::indicator {{
            width: 18px; height: 18px; border-radius: 5px;
            border: 2px solid #475569; background: #1E293B;
        }}
        QCheckBox::indicator:checked {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {ACCENT_1}, stop:1 {ACCENT_2});
            border: 2px solid {ACCENT_1};
        }}
        QProgressBar {{
            background: #0F172A; border: 1px solid #334155;
            border-radius: 9px; height: 16px; text-align: center; color: white;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {ACCENT_1}, stop:0.5 {ACCENT_GLOW}, stop:1 {ACCENT_2});
            border-radius: 8px;
        }}
        QScrollBar:vertical {{
            background: #0F172A; width: 12px; border-radius: 6px; margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: #475569; border-radius: 5px; min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {ACCENT_1};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar:horizontal {{
            background: #0F172A; height: 12px; border-radius: 6px; margin: 2px;
        }}
        QScrollBar::handle:horizontal {{
            background: #475569; border-radius: 5px; min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{ background: {ACCENT_1}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
        QStatusBar {{
            background: rgba(11, 16, 32, 230); color: #94A3B8;
            border-top: 1px solid #334155;
        }}
        QSplitter::handle {{ background: #334155; }}
        QSplitter::handle:horizontal {{ width: 3px; }}
        QSplitter::handle:vertical {{ height: 3px; }}
        QLabel {{ background: transparent; }}
        QScrollArea {{ background: transparent; border: 0; }}
    """)


def _drop_shadow(widget: QWidget, color_hex: str = "#000000", blur: int = 28,
                 offset: int = 4) -> None:
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, offset)
    c = QColor(color_hex)
    c.setAlpha(180)
    eff.setColor(c)
    widget.setGraphicsEffect(eff)


def _build_header(parent: QWidget) -> QFrame:
    frame = QFrame(parent)
    frame.setObjectName("HeroHeader")
    frame.setMinimumHeight(80)
    lay = QHBoxLayout(frame)
    lay.setContentsMargins(20, 12, 20, 12)
    emoji = QLabel(TOOL_EMOJI)
    emoji.setStyleSheet("font-size: 36pt; background: transparent;")
    lay.addWidget(emoji)
    text_lay = QVBoxLayout()
    text_lay.setSpacing(2)
    title = QLabel(TOOL_TITLE)
    title.setObjectName("HeroTitle")
    title.setStyleSheet("background: transparent;")
    tagline = QLabel(TOOL_TAGLINE)
    tagline.setObjectName("HeroTagline")
    tagline.setStyleSheet("background: transparent;")
    text_lay.addWidget(title)
    text_lay.addWidget(tagline)
    lay.addLayout(text_lay, stretch=1)
    badge = QLabel("v2 • Qt6")
    badge.setStyleSheet(
        "background: rgba(0,0,0,80); color: white; "
        "padding: 6px 12px; border-radius: 12px; font-weight: 700;"
    )
    lay.addWidget(badge, alignment=Qt.AlignmentFlag.AlignTop)
    _drop_shadow(frame, ACCENT_1, blur=40, offset=6)
    return frame


# ---------------------------------------------------------------------------
# Pricing table (USD per 1,000,000 tokens) — best-effort estimates of the
# underlying model's API list price. Adjust freely. Fields:
#   input, output, cache_read, cache_creation
# ---------------------------------------------------------------------------

DROID_MODEL_PRICING: dict[str, dict[str, float]] = {
    # Anthropic Claude class
    "claude-opus-4-7":     {"input": 15.00, "output": 75.00,
                            "cache_read": 1.50, "cache_creation": 18.75},
    "claude-opus-4-6":     {"input": 15.00, "output": 75.00,
                            "cache_read": 1.50, "cache_creation": 18.75},
    "claude-sonnet-4-6":   {"input": 3.00,  "output": 15.00,
                            "cache_read": 0.30, "cache_creation": 3.75},
    "claude-sonnet-4-5-20250929": {
                            "input": 3.00,  "output": 15.00,
                            "cache_read": 0.30, "cache_creation": 3.75},
    "claude-haiku-4-5-20251001": {
                            "input": 0.80,  "output": 4.00,
                            "cache_read": 0.08, "cache_creation": 1.00},
    # OpenAI GPT-5 class
    "gpt-5.5":             {"input": 1.25,  "output": 10.00,
                            "cache_read": 0.125, "cache_creation": 1.5625},
    "gpt-5.4":             {"input": 1.25,  "output": 10.00,
                            "cache_read": 0.125, "cache_creation": 1.5625},
    "gpt-5.2":             {"input": 1.25,  "output": 10.00,
                            "cache_read": 0.125, "cache_creation": 1.5625},
    # Google
    "gemini-3.1-pro-preview": {
                            "input": 1.25,  "output": 10.00,
                            "cache_read": 0.125, "cache_creation": 1.5625},
    # Droid Core OSS / cheap class
    "glm-5.1":             {"input": 0.10,  "output": 0.50,
                            "cache_read": 0.01, "cache_creation": 0.125},
    "kimi-k2.6":           {"input": 0.15,  "output": 2.50,
                            "cache_read": 0.015, "cache_creation": 0.1875},
    "minimax-m2.7":        {"input": 0.20,  "output": 1.10,
                            "cache_read": 0.02, "cache_creation": 0.25},
}

# Model order for the dropdown
DROID_MODEL_LIST = [
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
    "gpt-5.5",
    "gpt-5.4",
    "gemini-3.1-pro-preview",
    "glm-5.1",
    "kimi-k2.6",
    "minimax-m2.7",
]

# Factory.ai paid-plan list price (USD / seat / month). Editable in the UI.
DEFAULT_DROID_SEAT_PRICE_USD_PER_MONTH = 40.0


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SuggestedTask:
    name: str
    description: str
    rationale: str = ""
    weight_per_day: float = 1.0


@dataclass
class TaskCost:
    name: str
    cost_usd: float = 0.0
    duration_sec: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    total_tokens: int = 0
    num_turns: int = 0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Droid CLI helpers
# ---------------------------------------------------------------------------


def droid_on_path() -> Optional[str]:
    """Return absolute path to `droid` if found, else None."""
    return shutil.which("droid")


def _price_tokens(usage: dict, model: str) -> float:
    """Compute estimated USD cost for a single result's token usage."""
    rates = DROID_MODEL_PRICING.get(model)
    if rates is None:
        # Default to sonnet-class pricing if model is unknown.
        rates = {"input": 3.00, "output": 15.00,
                 "cache_read": 0.30, "cache_creation": 3.75}
    return (
        usage.get("input_tokens", 0) * rates["input"]
        + usage.get("output_tokens", 0) * rates["output"]
        + usage.get("cache_read_input_tokens", 0) * rates["cache_read"]
        + usage.get("cache_creation_input_tokens", 0) * rates["cache_creation"]
    ) / 1_000_000.0


def run_droid(
    repo_path: Path,
    prompt: str,
    model: str,
    timeout: int,
) -> tuple[Optional[dict], Optional[str], float]:
    """
    Run `droid exec -o json` once. Returns (parsed_dict, error, duration_sec).

    The returned dict mimics Claude Code's envelope:
      {
        "result": "<final assistant text>",
        "usage": {input_tokens, output_tokens,
                  cache_read_input_tokens, cache_creation_input_tokens},
        "num_turns": int,
        "total_cost_usd": float,        # estimated from token rates
      }
    """
    exe = droid_on_path()
    if not exe:
        return None, "`droid` not found on PATH — install Droid CLI first", 0.0

    cmd = [
        exe, "exec",
        "-o", "json",
        "--skip-permissions-unsafe",
        "--cwd", str(repo_path),
        "-m", model,
        "-",   # read prompt from stdin
    ]
    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, f"timeout after {timeout}s", time.time() - start
    except FileNotFoundError:
        return None, "`droid` not found on PATH — install Droid CLI first", 0.0

    duration = time.time() - start
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip().replace("\n", " ")[:300]
        return None, f"exit {proc.returncode}: {stderr}", duration

    # Droid -o json may emit a single JSON object OR JSONL (depending on
    # version). Handle both.
    out = (proc.stdout or "").strip()
    if not out:
        return None, "empty stdout from droid", duration

    obj: Optional[dict] = None
    try:
        obj = json.loads(out)
    except json.JSONDecodeError:
        # Try JSONL: take the last `result` line, sum any per-event usage.
        agg = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        }
        result_text = ""
        num_turns = 0
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            usage = ev.get("usage") or {}
            for k in agg:
                if usage.get(k):
                    agg[k] += int(usage[k])
            if ev.get("type") == "result":
                num_turns = int(ev.get("num_turns") or num_turns)
                if ev.get("result"):
                    result_text = ev.get("result")
        obj = {
            "result": result_text,
            "usage": agg,
            "num_turns": num_turns,
        }

    if not isinstance(obj, dict):
        return None, "unexpected JSON shape from droid", duration

    usage = obj.get("usage") or {}
    cost = _price_tokens(usage, model)
    return (
        {
            "result": obj.get("result", ""),
            "usage": usage,
            "num_turns": int(obj.get("num_turns") or 0),
            "total_cost_usd": cost,
        },
        None,
        duration,
    )


def extract_cost(data: dict) -> TaskCost:
    usage = data.get("usage") or {}
    tc = TaskCost(name="")
    tc.input_tokens = int(usage.get("input_tokens") or 0)
    tc.output_tokens = int(usage.get("output_tokens") or 0)
    tc.cache_read_tokens = int(usage.get("cache_read_input_tokens") or 0)
    tc.cache_creation_tokens = int(usage.get("cache_creation_input_tokens") or 0)
    tc.total_tokens = (
        tc.input_tokens
        + tc.output_tokens
        + tc.cache_read_tokens
        + tc.cache_creation_tokens
    )
    tc.cost_usd = float(data.get("total_cost_usd") or 0.0)
    tc.num_turns = int(data.get("num_turns") or 0)
    return tc


# ---------------------------------------------------------------------------
# Worker threads
# ---------------------------------------------------------------------------


SUGGEST_PROMPT_TEMPLATE = """\
You are analyzing the repository in the current working directory in order
to suggest typical software-engineering tasks that a developer would
realistically be asked to do on this codebase in the next few weeks.

Step 1: briefly skim the repo (top-level layout, README, a few key source
files) — DO NOT modify any files.

Step 2: return EXACTLY a JSON array (and nothing else, no markdown fences)
of 5 to 7 task suggestions. Each element MUST be an object with these
fields:

  - "name":        a short snake_case identifier (max ~30 chars)
  - "description": one sentence describing the concrete task, specific to
                   THIS repo (mention real file/module names where useful)
  - "rationale":   one sentence on why this task matters for this repo
  - "weight_per_day": a number between 0.1 and 5 estimating how often a
                     typical dev would do this kind of task per active
                     workday on this codebase

Tasks should reflect the actual character of this codebase: the languages
used, the apparent maturity, missing tests, obvious refactor targets, etc.
Prefer concrete tasks ("add pagination to /api/users endpoint") over
generic ones ("improve code quality").

Output ONLY the JSON array. No prose, no code fences.
"""


ESTIMATE_PROMPT_TEMPLATE = """\
You are being asked to perform the following task on the repository in the
current working directory:

TASK: {description}

Do this task PROPERLY and COMPLETELY, as if you were going to ship it:

  1. Read whatever source files you need to understand the change.
  2. Plan the implementation.
  3. Write the actual code change (in your response only — DO NOT write
     to disk, DO NOT modify files).
  4. Write accompanying DOCUMENTATION (docstrings, README updates,
     usage notes) for the change.
  5. Write accompanying TESTS (unit tests, and integration tests where
     appropriate) that would give real confidence the change works.
  6. Briefly note any follow-up work or risks.

Be thorough. The point of this exercise is to measure the realistic cost
of doing this task correctly, including docs and tests — not the cost of
a quick sketch.

Do not modify any files on disk. Put everything in your response.
"""


class SuggestWorker(QThread):
    finished_ok = pyqtSignal(list, dict)
    failed = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, repo: Path, model: str, timeout: int):
        super().__init__()
        self.repo = repo
        self.model = model
        self.timeout = timeout

    def run(self) -> None:
        self.log.emit(f"Asking Droid ({self.model}) to analyze {self.repo} ...")
        data, err, dur = run_droid(
            self.repo, SUGGEST_PROMPT_TEMPLATE, self.model, self.timeout
        )
        if err:
            self.failed.emit(err)
            return

        text = data.get("result") or ""
        if isinstance(text, list):
            text = "".join(
                c.get("text", "") for c in text if isinstance(c, dict)
            )
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        lb, rb = text.find("["), text.rfind("]")
        if lb == -1 or rb == -1 or rb < lb:
            self.failed.emit(
                "Could not locate a JSON array in Droid's reply. "
                "Raw reply:\n" + text[:500]
            )
            return
        try:
            arr = json.loads(text[lb : rb + 1])
        except json.JSONDecodeError as e:
            self.failed.emit(f"JSON parse error: {e}\nRaw:\n{text[:500]}")
            return

        suggestions: List[SuggestedTask] = []
        for item in arr:
            if not isinstance(item, dict):
                continue
            try:
                suggestions.append(
                    SuggestedTask(
                        name=str(item.get("name", "task"))[:60],
                        description=str(item.get("description", "")).strip(),
                        rationale=str(item.get("rationale", "")).strip(),
                        weight_per_day=float(item.get("weight_per_day", 1) or 1),
                    )
                )
            except (TypeError, ValueError):
                continue

        if not suggestions:
            self.failed.emit("Droid returned no usable task suggestions.")
            return

        analyze_cost = extract_cost(data)
        analyze_cost.name = "(repo analysis)"
        analyze_cost.duration_sec = dur
        self.log.emit(
            f"Got {len(suggestions)} suggestions "
            f"(analysis est. ${analyze_cost.cost_usd:.4f}, "
            f"{analyze_cost.total_tokens:,} tok, {dur:.1f}s)."
        )
        self.finished_ok.emit(
            suggestions,
            {
                "cost_usd": analyze_cost.cost_usd,
                "duration_sec": dur,
                "total_tokens": analyze_cost.total_tokens,
            },
        )


class EstimateWorker(QThread):
    one_done = pyqtSignal(int, object)
    all_done = pyqtSignal()
    log = pyqtSignal(str)

    def __init__(
        self,
        repo: Path,
        tasks: List[SuggestedTask],
        model: str,
        timeout: int,
    ):
        super().__init__()
        self.repo = repo
        self.tasks = tasks
        self.model = model
        self.timeout = timeout
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        for i, t in enumerate(self.tasks):
            if self._cancel:
                self.log.emit("Cancelled.")
                break
            self.log.emit(f"[{i+1}/{len(self.tasks)}] estimating: {t.name}")
            prompt = ESTIMATE_PROMPT_TEMPLATE.format(description=t.description)
            data, err, dur = run_droid(self.repo, prompt, self.model, self.timeout)
            if err:
                tc = TaskCost(name=t.name, error=err, duration_sec=dur)
            else:
                tc = extract_cost(data)
                tc.name = t.name
                tc.duration_sec = dur
            self.one_done.emit(i, tc)
        self.all_done.emit()


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------


class TaskRow(QWidget):
    def __init__(self, task: SuggestedTask):
        super().__init__()
        self.task = task
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        self.check = QCheckBox()
        self.check.setChecked(True)
        layout.addWidget(self.check)

        text_box = QVBoxLayout()
        name_lbl = QLabel(f"<b>{task.name}</b>")
        name_lbl.setTextFormat(Qt.TextFormat.RichText)
        text_box.addWidget(name_lbl)
        desc_lbl = QLabel(task.description)
        desc_lbl.setWordWrap(True)
        text_box.addWidget(desc_lbl)
        if task.rationale:
            rat = QLabel(f"<i>why: {task.rationale}</i>")
            rat.setTextFormat(Qt.TextFormat.RichText)
            rat.setWordWrap(True)
            rat.setStyleSheet("color: #94A3B8; background: transparent;")
            text_box.addWidget(rat)
        layout.addLayout(text_box, stretch=1)

        weight_box = QVBoxLayout()
        weight_box.addWidget(QLabel("times/day"))
        self.weight = QSpinBox()
        self.weight.setRange(0, 50)
        self.weight.setValue(int(round(task.weight_per_day)))
        weight_box.addWidget(self.weight)
        layout.addLayout(weight_box)

    def is_selected(self) -> bool:
        return self.check.isChecked()

    def updated_task(self) -> SuggestedTask:
        self.task.weight_per_day = float(self.weight.value())
        return self.task


class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Droid (Factory.ai) Cost Dashboard")
        self.resize(1100, 800)

        self.repo_path: Optional[Path] = None
        self.task_rows: List[TaskRow] = []
        self.results: List[TaskCost] = []
        self.analysis_cost: float = 0.0
        self.suggest_worker: Optional[SuggestWorker] = None
        self.estimate_worker: Optional[EstimateWorker] = None

        self._build_ui()
        self._check_droid()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setSpacing(10)

        outer.addWidget(_build_header(self))

        top = QGroupBox("Project")
        top_layout = QHBoxLayout(top)

        top_layout.addWidget(QLabel("Repo:"))
        self.repo_edit = QLineEdit()
        self.repo_edit.setPlaceholderText("Path to a git repository on disk")
        top_layout.addWidget(self.repo_edit, stretch=1)

        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._on_browse)
        top_layout.addWidget(browse_btn)

        top_layout.addSpacing(12)
        top_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(DROID_MODEL_LIST)
        top_layout.addWidget(self.model_combo)

        top_layout.addSpacing(12)
        top_layout.addWidget(QLabel("Devs:"))
        self.devs_spin = QSpinBox()
        self.devs_spin.setRange(1, 500)
        self.devs_spin.setValue(5)
        top_layout.addWidget(self.devs_spin)

        top_layout.addWidget(QLabel("Active days/mo:"))
        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 31)
        self.days_spin.setValue(20)
        top_layout.addWidget(self.days_spin)

        top_layout.addWidget(QLabel("Seat $/mo:"))
        self.seat_spin = QDoubleSpinBox()
        self.seat_spin.setRange(0.0, 1000.0)
        self.seat_spin.setDecimals(2)
        self.seat_spin.setValue(DEFAULT_DROID_SEAT_PRICE_USD_PER_MONTH)
        top_layout.addWidget(self.seat_spin)

        outer.addWidget(top)

        action = QHBoxLayout()
        self.analyze_btn = QPushButton("1. Analyze repo & suggest tasks")
        self.analyze_btn.clicked.connect(self._on_analyze)
        action.addWidget(self.analyze_btn)

        self.estimate_btn = QPushButton("2. Estimate real cost (with docs + tests)")
        self.estimate_btn.setEnabled(False)
        self.estimate_btn.clicked.connect(self._on_estimate)
        action.addWidget(self.estimate_btn)

        self.export_test_btn = QPushButton("Export test")
        self.export_test_btn.setEnabled(False)
        self.export_test_btn.clicked.connect(self._on_export_test)
        action.addWidget(self.export_test_btn)

        self.import_test_btn = QPushButton("Import test")
        self.import_test_btn.clicked.connect(self._on_import_test)
        action.addWidget(self.import_test_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        action.addWidget(self.cancel_btn)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        action.addWidget(self.progress, stretch=1)

        outer.addLayout(action)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        tasks_box = QGroupBox("Suggested tasks (uncheck any you don't want)")
        tasks_layout = QVBoxLayout(tasks_box)
        self.tasks_scroll = QScrollArea()
        self.tasks_scroll.setWidgetResizable(True)
        self.tasks_inner = QWidget()
        self.tasks_inner_layout = QVBoxLayout(self.tasks_inner)
        self.tasks_inner_layout.addStretch(1)
        self.tasks_scroll.setWidget(self.tasks_inner)
        tasks_layout.addWidget(self.tasks_scroll)
        splitter.addWidget(tasks_box)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        results_box = QGroupBox("Per-task cost (estimated from token usage)")
        rb = QVBoxLayout(results_box)
        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(
            ["Task", "Est. cost (USD)", "Tokens", "Turns", "Time (s)"]
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.results_table.verticalHeader().setVisible(False)
        rb.addWidget(self.results_table)
        right_layout.addWidget(results_box, stretch=2)

        summary_box = QGroupBox("Forecast")
        sb = QVBoxLayout(summary_box)
        self.summary_label = QLabel("Run an analysis to begin.")
        f = self.summary_label.font()
        f.setPointSize(f.pointSize() + 1)
        self.summary_label.setFont(f)
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)
        sb.addWidget(self.summary_label)
        right_layout.addWidget(summary_box)

        log_box = QGroupBox("Log")
        lb = QVBoxLayout(log_box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.log_view.setFont(mono)
        lb.addWidget(self.log_view)
        right_layout.addWidget(log_box, stretch=1)

        splitter.addWidget(right)
        splitter.setSizes([450, 650])
        outer.addWidget(splitter, stretch=1)

        self.setStatusBar(QStatusBar())

        for w in (top, tasks_box, results_box, summary_box, log_box):
            _drop_shadow(w, "#000000", blur=24, offset=4)
        _drop_shadow(self.analyze_btn, ACCENT_1, blur=22, offset=3)
        _drop_shadow(self.estimate_btn, ACCENT_1, blur=22, offset=3)

    def _check_droid(self) -> None:
        path = droid_on_path()
        if path:
            self.statusBar().showMessage(f"droid CLI: {path}")
        else:
            self.statusBar().showMessage(
                "WARNING: `droid` not found on PATH — install Droid CLI first."
            )

    def _log(self, msg: str) -> None:
        self.log_view.appendPlainText(msg)

    def _clear_tasks(self) -> None:
        for row in self.task_rows:
            row.setParent(None)
            row.deleteLater()
        self.task_rows = []

    def _clear_results(self) -> None:
        self.results = []
        self.results_table.setRowCount(0)
        self.summary_label.setText("Run estimation to begin.")

    def _set_busy(self, busy: bool) -> None:
        self.analyze_btn.setEnabled(not busy)
        self.estimate_btn.setEnabled(not busy and bool(self.task_rows))
        self.export_test_btn.setEnabled(not busy and bool(self.task_rows))
        self.import_test_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy and self.estimate_worker is not None)
        self.progress.setVisible(busy)
        self.progress.setRange(0, 0 if busy else 1)

    def _on_browse(self) -> None:
        start = self.repo_edit.text().strip() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, "Choose a repository", start)
        if path:
            self.repo_edit.setText(path)

    def _on_export_test(self) -> None:
        if not self.task_rows:
            QMessageBox.information(
                self, "No test to export", "Analyze or import tasks before exporting."
            )
            return

        default_path = str(Path.cwd() / "ai-agent-cost-test.json")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export test",
            default_path,
            "AI agent cost test (*.ai-agent-test.json);;JSON files (*.json);;All files (*)",
        )
        if not path:
            return

        tasks = []
        for row in self.task_rows:
            task = row.updated_task()
            tasks.append(
                {
                    "name": task.name,
                    "description": task.description,
                    "rationale": task.rationale,
                    "weight_per_day": task.weight_per_day,
                    "selected": row.is_selected(),
                }
            )
        payload = {
            "schema": "ai-coding-agents-cost-calculators.test.v1",
            "source_tool": TOOL_TITLE,
            "repo_path": self.repo_edit.text().strip(),
            "settings": {
                "devs": self.devs_spin.value(),
                "active_days_per_month": self.days_spin.value(),
                "seat_usd_per_month": self.seat_spin.value(),
            },
            "tasks": tasks,
        }

        try:
            Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as e:
            QMessageBox.critical(self, "Export failed", str(e))
            return

        self._log(f"Exported reusable test to {path}")
        self.statusBar().showMessage(f"Exported test: {path}")

    def _on_import_test(self) -> None:
        start = self.repo_edit.text().strip() or os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import test",
            start,
            "AI agent cost test (*.ai-agent-test.json);;JSON files (*.json);;All files (*)",
        )
        if not path:
            return

        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Import failed", str(e))
            return

        tasks_payload = payload.get("tasks")
        if not isinstance(tasks_payload, list) or not tasks_payload:
            QMessageBox.critical(self, "Import failed", "No tasks found in test file.")
            return

        repo_text = str(payload.get("repo_path") or "").strip()
        if repo_text:
            self.repo_edit.setText(repo_text)
            self.repo_path = Path(repo_text).expanduser()
        else:
            self.repo_path = None

        settings = payload.get("settings") or {}
        if isinstance(settings, dict):
            self.devs_spin.setValue(int(settings.get("devs") or self.devs_spin.value()))
            self.days_spin.setValue(
                int(settings.get("active_days_per_month") or self.days_spin.value())
            )
            self.seat_spin.setValue(
                float(settings.get("seat_usd_per_month") or self.seat_spin.value())
            )

        self._clear_tasks()
        self._clear_results()
        self.analysis_cost = 0.0

        for item in tasks_payload:
            if not isinstance(item, dict):
                continue
            task = SuggestedTask(
                name=str(item.get("name") or "task")[:60],
                description=str(item.get("description") or "").strip(),
                rationale=str(item.get("rationale") or "").strip(),
                weight_per_day=float(item.get("weight_per_day") or 1.0),
            )
            row = TaskRow(task)
            row.check.setChecked(bool(item.get("selected", True)))
            self.task_rows.append(row)
            self.tasks_inner_layout.insertWidget(
                self.tasks_inner_layout.count() - 1, row
            )

        if not self.task_rows:
            QMessageBox.critical(self, "Import failed", "No valid tasks found in test file.")
            return

        self.estimate_btn.setEnabled(True)
        self.export_test_btn.setEnabled(True)
        self._log(
            f"Imported {len(self.task_rows)} reusable task(s) from {path}; "
            "choose this dashboard's model and click Estimate."
        )
        self.statusBar().showMessage(
            f"Imported {len(self.task_rows)} task(s). Click Estimate to run the same test."
        )

    def _on_analyze(self) -> None:
        if not droid_on_path():
            QMessageBox.critical(
                self,
                "Droid not found",
                "The `droid` CLI was not found on PATH.\n\n"
                "Install Droid CLI from Factory.ai and authenticate it "
                "(set FACTORY_API_KEY) before using this dashboard.",
            )
            return

        repo = Path(self.repo_edit.text().strip()).expanduser()
        if not repo.is_dir():
            QMessageBox.warning(self, "Invalid repo", f"Not a directory:\n{repo}")
            return
        self.repo_path = repo
        self._clear_tasks()
        self._clear_results()
        self.analysis_cost = 0.0

        self._set_busy(True)
        self._log(
            f"--- Analyzing {repo} (model={self.model_combo.currentText()}) ---"
        )

        self.suggest_worker = SuggestWorker(
            repo, self.model_combo.currentText(), timeout=600
        )
        self.suggest_worker.log.connect(self._log)
        self.suggest_worker.finished_ok.connect(self._on_suggest_ok)
        self.suggest_worker.failed.connect(self._on_suggest_fail)
        self.suggest_worker.start()

    def _on_suggest_ok(self, suggestions: list, analysis: dict) -> None:
        self._set_busy(False)
        self.analysis_cost = float(analysis.get("cost_usd", 0.0))
        self._log(
            f"Repo analysis est. cost: ${self.analysis_cost:.4f} "
            f"({analysis.get('total_tokens', 0):,} tokens)"
        )
        for s in suggestions:
            row = TaskRow(s)
            self.task_rows.append(row)
            self.tasks_inner_layout.insertWidget(
                self.tasks_inner_layout.count() - 1, row
            )
        self.estimate_btn.setEnabled(True)
        self.export_test_btn.setEnabled(True)
        self.statusBar().showMessage(
            f"{len(suggestions)} task(s) suggested. Tweak weights and click Estimate."
        )

    def _on_suggest_fail(self, msg: str) -> None:
        self._set_busy(False)
        self._log("ANALYSIS FAILED: " + msg)
        QMessageBox.critical(self, "Analysis failed", msg)

    def _on_estimate(self) -> None:
        chosen = [r.updated_task() for r in self.task_rows if r.is_selected()]
        if not chosen:
            QMessageBox.information(
                self, "No tasks", "Select at least one task to estimate."
            )
            return
        repo = Path(self.repo_edit.text().strip()).expanduser()
        if not repo.is_dir():
            QMessageBox.warning(self, "Invalid repo", f"Not a directory:\n{repo}")
            return
        self.repo_path = repo

        self._clear_results()
        self.results_table.setRowCount(len(chosen))
        for i, t in enumerate(chosen):
            self.results_table.setItem(i, 0, QTableWidgetItem(t.name))
            for col in range(1, 5):
                self.results_table.setItem(i, col, QTableWidgetItem("…"))

        self._chosen_for_run = chosen
        self.estimate_worker = EstimateWorker(
            repo,
            chosen,
            self.model_combo.currentText(),
            timeout=900,
        )
        self.estimate_worker.log.connect(self._log)
        self.estimate_worker.one_done.connect(self._on_one_done)
        self.estimate_worker.all_done.connect(self._on_all_done)
        self._set_busy(True)
        self.cancel_btn.setEnabled(True)
        self._log("--- Estimating chosen tasks (real cost: code + docs + tests) ---")
        self.estimate_worker.start()

    def _on_cancel(self) -> None:
        if self.estimate_worker:
            self.estimate_worker.cancel()
            self.cancel_btn.setEnabled(False)

    def _on_one_done(self, idx: int, tc: TaskCost) -> None:
        self.results.append(tc)
        if tc.error:
            self.results_table.setItem(idx, 1, QTableWidgetItem("ERROR"))
            self.results_table.setItem(idx, 2, QTableWidgetItem("-"))
            self.results_table.setItem(idx, 3, QTableWidgetItem("-"))
            self.results_table.setItem(
                idx, 4, QTableWidgetItem(f"{tc.duration_sec:.1f}")
            )
            self._log(f"  {tc.name}: ERROR — {tc.error}")
        else:
            self.results_table.setItem(
                idx, 1, QTableWidgetItem(f"${tc.cost_usd:.4f}")
            )
            self.results_table.setItem(
                idx, 2, QTableWidgetItem(f"{tc.total_tokens:,}")
            )
            self.results_table.setItem(idx, 3, QTableWidgetItem(str(tc.num_turns)))
            self.results_table.setItem(
                idx, 4, QTableWidgetItem(f"{tc.duration_sec:.1f}")
            )
            self._log(
                f"  {tc.name}: ~${tc.cost_usd:.4f}  "
                f"{tc.total_tokens:,} tok  "
                f"{tc.num_turns} turns  {tc.duration_sec:.1f}s"
            )

    def _on_all_done(self) -> None:
        self._set_busy(False)
        self.cancel_btn.setEnabled(False)
        self._render_summary()
        self._log("--- Done ---")

    def _render_summary(self) -> None:
        valid = [r for r in self.results if r.error is None and r.cost_usd > 0]
        if not valid:
            self.summary_label.setText(
                "<b>No valid results.</b> Check the log for errors."
            )
            return

        weight_by_name = {
            t.name: t.weight_per_day for t in getattr(self, "_chosen_for_run", [])
        }
        per_task_total = sum(r.cost_usd for r in valid)
        per_dev_per_day = sum(
            r.cost_usd * weight_by_name.get(r.name, 1.0) for r in valid
        )
        devs = self.devs_spin.value()
        days = self.days_spin.value()
        seat = self.seat_spin.value()
        model = self.model_combo.currentText()

        per_dev_per_month = per_dev_per_day * days
        team_per_month = per_dev_per_month * devs
        team_per_year = team_per_month * 12

        seats_yr = seat * devs * 12
        overage = max(0.0, team_per_year - seats_yr)
        expected = seats_yr + overage

        html = f"""
        <table cellpadding="4">
        <tr><td><b>Model:</b></td>
            <td align="right"><code>{model}</code></td></tr>
        <tr><td><b>Repo analysis (one-off):</b></td>
            <td align="right">~${self.analysis_cost:,.4f}</td></tr>
        <tr><td><b>Sum of one run of selected tasks:</b></td>
            <td align="right">~${per_task_total:,.4f}</td></tr>
        <tr><td><b>Per dev / active day (weighted):</b></td>
            <td align="right">~${per_dev_per_day:,.2f}</td></tr>
        <tr><td><b>Per dev / month ({days} days):</b></td>
            <td align="right">~${per_dev_per_month:,.2f}</td></tr>
        <tr><td><b>Team ({devs} devs) / month:</b></td>
            <td align="right">~${team_per_month:,.2f}</td></tr>
        <tr><td><b>Team ({devs} devs) / year:</b></td>
            <td align="right">~${team_per_year:,.2f}</td></tr>
        <tr><td colspan="2"><hr></td></tr>
        <tr><td>Factory seats list price (${seat:.0f}/seat/mo):</td>
            <td align="right">${seats_yr:,.2f}/yr</td></tr>
        <tr><td>Estimated overage above seats:</td>
            <td align="right">${overage:,.2f}/yr</td></tr>
        <tr><td><b>Expected total cost:</b></td>
            <td align="right"><b>${expected:,.2f}/yr</b></td></tr>
        </table>
        <p style="color:#94A3B8;">Droid does not emit
        <code style="color:{ACCENT_1};">total_cost_usd</code> directly. Costs
        above are <i>estimates</i> derived from reported token usage × the
        price table for the selected model (see
        <code style="color:{ACCENT_1};">DROID_MODEL_PRICING</code> in this
        file). Real bills can run 1.5–3× higher due to iteration, long
        autonomous sessions, and MCP context bloat.</p>
        """.replace("{ACCENT_1}", ACCENT_1)
        self.summary_label.setText(html)


def main() -> int:
    app = QApplication(sys.argv)
    _apply_theme(app)
    win = Dashboard()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
