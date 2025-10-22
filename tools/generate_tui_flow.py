#!/usr/bin/env python3
"""
generate_tui_flow.py — Produce presentation-ready Graphviz diagrams of a TUI user flow.

Outputs:
  - Slide PNG/SVGs (high-level, selection phase, generation/outcomes, poster)
  - Optional simple HTML deck to present the SVGs in a browser

Requirements:
  1) Python 3.8+
  2) Graphviz installed with the `dot` command available in PATH
     - Linux:   sudo apt-get install graphviz
     - macOS:   brew install graphviz
     - Windows: choco install graphviz  (or download from graphviz.org)
  3) (Optional) A web browser to open the HTML deck.

Usage examples:
  # Generate SVG+PNG for all slides in ./build
  python generate_tui_flow.py --out build --formats svg png --all

  # Only the one-page poster (SVG only), dark theme
  python generate_tui_flow.py --out build --formats svg --slides poster --theme dark

  # Build slides + HTML deck
  python generate_tui_flow.py --out build --formats svg png --all --html

  # Windows-friendly fonts and sharper PNGs
  python tools/generate_tui_flow.py --out build --formats png svg --all --dpi 300 --width-in 18 --height-in 10 
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import os
from pathlib import Path
from typing import Iterable, Dict, List, Optional

# -------------------------------
# Font helpers (Windows-friendly default)
# -------------------------------
def _default_font() -> str:
    # Prefer a native Windows font on Windows to avoid Pango warnings
    return "Segoe UI" if sys.platform.startswith("win") else "Inter"

# -------------------------------
# Themes
# -------------------------------
THEMES = {
    "light": {
        "graph": dict(fontsize=18, pad="0.1", nodesep="0.35", ranksep="0.45",
                      labelloc="t", labeljust="l", fontname=_default_font()),
        "node": dict(shape="rect", style="rounded,filled",
                     fillcolor="#ffffff", color="#98a2b3",
                     penwidth="1.2", fontname=_default_font(), fontsize="16"),
        "edge": dict(color="#667085", penwidth="1.2", arrowsize="0.7",
                     fontname=_default_font(), fontsize="14"),
        "ok_fill": "#eaf7ef", "ok_edge": "#12b76a",
        "fail_fill": "#fdecec", "fail_edge": "#f04438",
        "note_fill": "#ffffff", "placeholder_edge": "#98a2b3",
        "bg": "#ffffff",
    },
    "dark": {
        "graph": dict(fontsize=18, pad="0.1", nodesep="0.35", ranksep="0.45",
                      labelloc="t", labeljust="l", fontname=_default_font()),
        "node": dict(shape="rect", style="rounded,filled",
                     fillcolor="#0f172a", color="#64748b",
                     penwidth="1.2", fontname=_default_font(), fontsize="16"),
        "edge": dict(color="#94a3b8", penwidth="1.2", arrowsize="0.7",
                     fontname=_default_font(), fontsize="14"),
        "ok_fill": "#064e3b", "ok_edge": "#34d399",
        "fail_fill": "#7f1d1d", "fail_edge": "#fca5a5",
        "note_fill": "#111827", "placeholder_edge": "#64748b",
        "bg": "#0b1020",
    },
}

# -------------------------------
# Default labels (can be overridden by --config JSON)
# -------------------------------
DEFAULT_LABELS = {
    "main_menu": "Main Menu",
    "chip": "Chip Selection",
    "type": "Plot Type",
    "exps": "Experiment Selection",
    "preview": "Preview & Configure",
    "generate": "Generate Plot",
    "success": "Success",
    "error": "Error",
    "process": "Process New Data",
    "plot_another": "Plot another",
    "adjust_config": "Adjust config",
    "edit_retry": "Edit & retry",
    "global_note": "Esc: Back/Cancel • Ctrl+Q: Quit",
    "slide1_title": "TUI User Flow — High-Level Overview",
    "slide2_title": "Selection Phase — From Main Menu to Experiments",
    "slide3_title": "Generation & Outcomes — Preview to Success/Error",
    "slide4_title": "TUI User Flow — One-Page Poster",
    "menu_new_plot_hint": "N/Enter: New Plot",
    "chip_hint": "↑↓ to navigate • Enter select • Esc back",
    "type_hint": "↑↓ • Enter • Esc back",
    "exps_hint": "Space toggle • A=all • C=clear • Enter continue",
    "success_hint": "Open output • Copy path • Plot another",
    "error_hint": "Traceback shown • Edit & retry",
    "preview_hint": "Enter: Generate • ← Edit back",
    "gen_hint": "Progress 0→100% • Esc cancels",
}

# -------------------------------
# DOT building utilities
# -------------------------------
def _attrs(d: Dict[str, str]) -> str:
    return ", ".join(f'{k}="{v}"' for k, v in d.items())

def dot_header(theme: str, title: str, font_override: Optional[str] = None) -> str:
    T = THEMES[theme]
    g = _attrs(T["graph"])
    n = _attrs(T["node"])
    e = _attrs(T["edge"])
    if font_override:
        g = g.replace(f'fontname="{T["graph"]["fontname"]}"', f'fontname="{font_override}"')
        n = n.replace(f'fontname="{T["node"]["fontname"]}"', f'fontname="{font_override}"')
        e = e.replace(f'fontname="{T["edge"]["fontname"]}"', f'fontname="{font_override}"')
    return f'digraph {{\n  graph [{g}, label="{title}"];\n  node  [{n}];\n  edge  [{e}];\n'

def write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")

def _resolve_dot(dot_cli: Optional[str]) -> str:
    if dot_cli:
        return dot_cli
    env_dot = os.environ.get("DOT_EXE")
    if env_dot:
        return env_dot
    which = shutil.which("dot")
    if which:
        return which
    raise FileNotFoundError(
        "Graphviz 'dot' not found. Install Graphviz and ensure 'dot' is on PATH, "
        'or pass --dot-path "C:\\Program Files\\Graphviz\\bin\\dot.exe"'
    )

def render_dot(dot_path: Path, outputs: Iterable[str], *, dot_cli: Optional[str] = None,
               dpi: Optional[int] = None, width_in: Optional[float] = None,
               height_in: Optional[float] = None, transparent: bool = False) -> List[Path]:
    dot_exe = _resolve_dot(dot_cli)
    generated: List[Path] = []
    for fmt in outputs:
        # Prefer cairo renderer for cleaner antialiasing on PNG
        fmt_string = "png:cairo" if fmt == "png" else fmt
        out_path = dot_path.with_suffix(f".{fmt if fmt!='png' else 'png'}")
        cmd = [dot_exe, f"-T{fmt_string}", str(dot_path), "-o", str(out_path)]
        if fmt == "png":
            if dpi:
                cmd.insert(1, f"-Gdpi={dpi}")
            if width_in and height_in:
                cmd.insert(1, f"-Gsize={width_in},{height_in}!")
            if transparent:
                cmd.insert(1, "-Gbgcolor=transparent")
        subprocess.run(cmd, check=True)
        generated.append(out_path)
    return generated

# -------------------------------
# Slide templates
# -------------------------------
def slide_overview(theme: str, L: Dict[str, str], font_override: Optional[str] = None) -> str:
    T = THEMES[theme]
    okfill, okedge = T["ok_fill"], T["ok_edge"]
    failfill, failedge = T["fail_fill"], T["fail_edge"]
    placeholder_edge = T["placeholder_edge"]
    s = [dot_header(theme, L["slide1_title"], font_override)]
    s += [
        f'  MainMenu    [label="{L["main_menu"]}"];',
        f'  Chip        [label="{L["chip"]}"];',
        f'  Type        [label="{L["type"]}"];',
        f'  Exps        [label="{L["exps"]}"];',
        f'  Preview     [label="{L["preview"]}"];',
        f'  Gen         [label="{L["generate"]}"];',
        f'  OK          [label="{L["success"]}", fillcolor="{okfill}", color="{okedge}"];',
        f'  Fail        [label="{L["error"]}",   fillcolor="{failfill}", color="{failedge}"];',
        f'  Proc        [label="{L["process"]}", style="rounded,dashed", color="{placeholder_edge}"];',
        "",
        "  MainMenu -> Chip -> Type -> Exps -> Preview -> Gen;",
        "  Gen -> OK;",
        "  Gen -> Fail;",
        "",
        "  MainMenu -> Proc [style=dashed];",
        "",
        f'  OK   -> Exps     [label="{L["plot_another"]}", style=solid];',
        "  OK   -> MainMenu [style=dotted];",
        f'  Fail -> Preview  [label="{L["adjust_config"]}"];',
        "  Fail -> MainMenu [style=dotted];",
        "}\n"
    ]
    return "\n".join(s)

def slide_selection(theme: str, L: Dict[str, str], font_override: Optional[str] = None) -> str:
    T = THEMES[theme]
    note_fill = T["note_fill"]; placeholder_edge = T["placeholder_edge"]
    s = [dot_header(theme, L["slide2_title"], font_override)]
    s += [
        f'  MainMenu [label="{L["main_menu"]}\\n{L["menu_new_plot_hint"]}"];',
        f'  Chip     [label="{L["chip"]}\\n{L["chip_hint"]}"];',
        f'  Type     [label="{L["type"]}\\n{L["type_hint"]}"];',
        f'  Exps     [label="{L["exps"]}\\n{L["exps_hint"]}"];',
        f'  Recent   [label="Recent Configs\\n(placeholder)", style="rounded,dashed", fillcolor="#ffffff", color="{placeholder_edge}"];',
        f'  Batch    [label="Batch Mode\\n(placeholder)", style="rounded,dashed", fillcolor="#ffffff", color="{placeholder_edge}"];',
        f'  Settings [label="Settings\\n(placeholder)", style="rounded,dashed", fillcolor="#ffffff", color="{placeholder_edge}"];',
        f'  Help     [label="Help / Shortcuts\\n(placeholder)", style="rounded,dashed", fillcolor="#ffffff", color="{placeholder_edge}"];',
        "",
        "  MainMenu -> Chip;",
        "  Chip -> Type;",
        "  Type -> Exps;",
        "  MainMenu -> Recent [style=dashed];",
        "  MainMenu -> Batch  [style=dashed];",
        "  MainMenu -> Settings [style=dashed];",
        "  MainMenu -> Help   [style=dashed];",
        "",
        f'  Q [label="Ctrl+Q anywhere: Quit", shape=note, fillcolor="{note_fill}", color="{placeholder_edge}"];',
        f'  Esc [label="Esc: Back/Cancel", shape=note, fillcolor="{note_fill}", color="{placeholder_edge}"];',
        "  Q -> MainMenu   [style=dotted, arrowhead=none];",
        "  Q -> Chip       [style=dotted, arrowhead=none];",
        "  Q -> Type       [style=dotted, arrowhead=none];",
        "  Q -> Exps       [style=dotted, arrowhead=none];",
        "  Esc -> Chip     [style=dotted, arrowhead=none];",
        "  Esc -> Type     [style=dotted, arrowhead=none];",
        "  Esc -> Exps     [style=dotted, arrowhead=none];",
        "}\n"
    ]
    return "\n".join(s)

def slide_generation(theme: str, L: Dict[str, str], font_override: Optional[str] = None) -> str:
    T = THEMES[theme]
    okfill, okedge = T["ok_fill"], T["ok_edge"]
    failfill, failedge = T["fail_fill"], T["fail_edge"]
    s = [dot_header(theme, L["slide3_title"], font_override)]
    s += [
        f'  Preview [label="{L["preview"]}\\n{L["preview_hint"]}"];',
        f'  Gen     [label="{L["generate"]}\\n{L["gen_hint"]}"];',
        f'  OK      [label="{L["success"]}\\n{L["success_hint"]}", fillcolor="{okfill}", color="{okedge}"];',
        f'  Fail    [label="{L["error"]}\\n{L["error_hint"]}", fillcolor="{failfill}", color="{failedge}"];',
        f'  Exps    [label="{L["exps"]}\\n(keeps chip & type)"];',
        "",
        "  Preview -> Gen;",
        "  Gen -> OK;",
        "  Gen -> Fail;",
        f'  OK -> Exps    [label="{L["plot_another"]}"];',
        '  OK -> Preview [style=dotted, label="Tweak"];',
        f'  Fail -> Preview [label="{L["edit_retry"]}"];',
        "}\n"
    ]
    return "\n".join(s)

def slide_poster(theme: str, L: Dict[str, str], font_override: Optional[str] = None) -> str:
    T = THEMES[theme]
    okfill, okedge = T["ok_fill"], T["ok_edge"]
    failfill, failedge = T["fail_fill"], T["fail_edge"]
    note_fill = T["note_fill"]
    s = [dot_header(theme, L["slide4_title"], font_override)]
    s += [
        '  {rank=same; MainMenu; Proc;}',
        '  {rank=same; Chip; Type; Exps;}',
        '  {rank=same; Preview;}',
        '  {rank=same; Gen;}',
        '  {rank=same; OK; Fail;}',
        "",
        f'  MainMenu [label="{L["main_menu"]}"];',
        f'  Proc     [label="{L["process"]}", style="rounded,dashed"];',
        f'  Chip     [label="{L["chip"]}"];',
        f'  Type     [label="{L["type"]}"];',
        f'  Exps     [label="{L["exps"]}"];',
        f'  Preview  [label="{L["preview"]}"];',
        f'  Gen      [label="{L["generate"]}"];',
        f'  OK       [label="{L["success"]}", fillcolor="{okfill}", color="{okedge}"];',
        f'  Fail     [label="{L["error"]}",   fillcolor="{failfill}", color="{failedge}"];',
        "",
        "  MainMenu -> Chip -> Type -> Exps -> Preview -> Gen;",
        "  MainMenu -> Proc [style=dashed];",
        "  Gen -> OK;",
        "  Gen -> Fail;",
        f'  OK -> Exps [label="{L["plot_another"]}"];',
        f'  Fail -> Preview [label="{L["edit_retry"]}"];',
        "",
        f'  Note1 [label="{L["global_note"]}", shape=note, fillcolor="{note_fill}"];',
        "  Note1 -> MainMenu [style=dotted, arrowhead=none];",
        "  Note1 -> Chip     [style=dotted, arrowhead=none];",
        "  Note1 -> Type     [style=dotted, arrowhead=none];",
        "  Note1 -> Exps     [style=dotted, arrowhead=none];",
        "  Note1 -> Preview  [style=dotted, arrowhead=none];",
        "  Note1 -> Gen      [style=dotted, arrowhead=none];",
        "}\n"
    ]
    return "\n".join(s)

SLIDE_BUILDERS = {
    "overview": slide_overview,
    "selection": slide_selection,
    "generation": slide_generation,
    "poster": slide_poster,
}

# Human-friendly display names for summary output
DISPLAY_NAMES = {
    "overview": "Overview",
    "selection": "Selection phase",
    "generation": "Generation & outcomes",
    "poster": "One-page poster",
}

# -------------------------------
# HTML deck
# -------------------------------
def write_html_deck(html_path: Path, svg_files: List[Path], theme: str) -> None:
    bg = THEMES[theme]["bg"]
    html = [
        "<!doctype html><meta charset='utf-8'>",
        "<title>TUI Flow Slides</title>",
        "<style>",
        f"body{{margin:0;background:{bg};color:#eee;font-family:Inter,system-ui;}}",
        "section{display:flex;align-items:center;justify-content:center;height:100vh;}",
        "img{max-width:90vw;max-height:85vh;box-shadow:0 20px 60px rgba(0,0,0,.5);",
        "    background:#fff;border-radius:18px;padding:12px;}",
        "</style>",
    ]
    for svg in svg_files:
        html.append(f"<section><img src='{svg.name}' alt=''></section>")
    html_path.write_text("\n".join(html), encoding="utf-8")

# -------------------------------
# Main
# -------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Generate TUI user-flow slides with Graphviz.")
    parser.add_argument("--out", type=Path, default=Path("build"), help="Output directory")
    parser.add_argument("--formats", nargs="+", default=["svg", "png"],
                        choices=["svg", "png", "pdf"], help="Output formats for each slide")
    parser.add_argument("--slides", nargs="+", choices=list(SLIDE_BUILDERS.keys()),
                        help="Specific slides to build (default: poster only unless --all)")
    parser.add_argument("--all", action="store_true", help="Build all slides")
    parser.add_argument("--html", action="store_true", help="Also write a simple HTML deck of the SVGs")
    parser.add_argument("--theme", choices=list(THEMES.keys()), default="light",
                        help="Color theme")
    parser.add_argument("--config", type=Path, help="JSON file to override default labels/titles")
    parser.add_argument("--font", help="Override font family for this run (e.g., 'Segoe UI', 'Arial')")
    # Windows-friendly: allow explicit dot.exe path & higher-res PNG controls
    parser.add_argument("--dot-path", help="Full path to dot.exe (Windows), e.g. C:\\Program Files\\Graphviz\\bin\\dot.exe")
    parser.add_argument("--dpi", type=int, default=None, help="DPI for PNG outputs (e.g., 300 or 600)")
    parser.add_argument("--width-in", type=float, help="Graph width in inches (PNG only, requires --height-in)")
    parser.add_argument("--height-in", type=float, help="Graph height in inches (PNG only, requires --width-in)")
    parser.add_argument("--transparent", action="store_true", help="Transparent background for PNGs")
    args = parser.parse_args()

    labels = DEFAULT_LABELS.copy()
    if args.config and args.config.exists():
        override = json.loads(args.config.read_text(encoding='utf-8'))
        labels.update(override)

    slides = list(SLIDE_BUILDERS.keys()) if args.all else (args.slides or ["poster"])

    args.out.mkdir(parents=True, exist_ok=True)
    generated_svgs: List[Path] = []

    # Track outputs per slide for a friendly summary
    per_slide_outputs = {}

    for key in slides:
        builder = SLIDE_BUILDERS[key]
        dot_src = builder(args.theme, labels, args.font)
        dot_path = args.out / f"tui_{key}.dot"
        write_file(dot_path, dot_src)
        out_files = render_dot(
            dot_path,
            args.formats,
            dot_cli=args.dot_path,
            dpi=args.dpi,
            width_in=args.width_in,
            height_in=args.height_in,
            transparent=args.transparent,
        )
        if any(p.suffix.lower() == ".svg" for p in out_files):
            generated_svgs.append(dot_path.with_suffix(".svg"))
        print(f"[ok] Wrote {dot_path.name} → " + ", ".join(p.name for p in out_files))

        # Build a map of available artifacts for summary
        artifacts = {"DOT": dot_path}
        for p in out_files:
            ext = p.suffix.lower().lstrip(".")
            if ext == "svg":
                artifacts["SVG"] = p
            elif ext == "png":
                artifacts["PNG"] = p
            elif ext == "pdf":
                artifacts["PDF"] = p
        per_slide_outputs[key] = artifacts

    if args.html and generated_svgs:
        html_path = args.out / "tui_flow_slides.html"
        write_html_deck(html_path, generated_svgs, args.theme)
        print(f"[ok] HTML deck: {html_path}")

    # Friendly summary block: 'Overview — SVG · PNG · DOT' etc.
    print("\nSummary:")
    order = ["overview", "selection", "generation", "poster"]
    for key in order:
        if key in per_slide_outputs:
            name = DISPLAY_NAMES.get(key, key.title())
            arts = per_slide_outputs[key]
            parts = []
            for label in ("SVG", "PNG", "DOT"):
                if label in arts:
                    parts.append(f"{label}: {arts[label].name}")
            print(f"- {name} — " + " · ".join(parts))

if __name__ == "__main__":
    main()
