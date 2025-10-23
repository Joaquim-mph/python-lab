# Documentation Index

**Complete guide to all documentation in this repository.**

Last Updated: October 22, 2025

---

## Quick Navigation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[README.md](README.md)** | Project overview and quick start | All users |
| **[CLAUDE.md](CLAUDE.md)** | Technical reference for AI assistants | Developers, AI |
| **[TUI_GUIDE.md](TUI_GUIDE.md)** | Complete TUI user manual | Lab members (interactive users) |
| **[CLI_GUIDE.md](CLI_GUIDE.md)** | Command-line reference | Power users, scripters |
| **[CHIP_HISTORY_GUIDE.md](CHIP_HISTORY_GUIDE.md)** | Chip timeline functions | Advanced users |
| **[CROSS_DAY_ITS_GUIDE.md](CROSS_DAY_ITS_GUIDE.md)** | Cross-day analysis workflow | Advanced users |
| **[PLOT_OUTPUT_SYSTEM.md](PLOT_OUTPUT_SYSTEM.md)** | Output directory structure | Developers |
| **[structure.md](structure.md)** | Codebase reorganization plan | Developers |

---

## Documentation by Use Case

### I want to generate plots

**Interactive (Recommended for lab members):**
1. Read: [README.md](README.md) - Quick Start → TUI section
2. Launch: `python tui_app.py`
3. Reference: [TUI_GUIDE.md](TUI_GUIDE.md) - Complete wizard walkthrough

**Command-line (For automation):**
1. Read: [CLI_GUIDE.md](CLI_GUIDE.md) - Plotting commands section
2. Run: `python process_and_analyze.py plot-its 67 --seq 52,57,58`
3. Reference: [CLI_GUIDE.md](CLI_GUIDE.md) - All options and examples

### I want to process new raw data

**Option 1: TUI**
1. Launch: `python tui_app.py`
2. Select: "Process New Data" from main menu
3. Follow on-screen instructions

**Option 2: CLI**
```bash
python process_and_analyze.py full-pipeline
# Parses all raw CSVs + generates chip histories
```

### I want to analyze chip history over time

**View history:**
```bash
python process_and_analyze.py show-history 67 --meta metadata --group Alisson
```

**Generate all chip histories:**
```bash
python process_and_analyze.py chip-histories --meta metadata --min 5
```

**Reference:** [CHIP_HISTORY_GUIDE.md](CHIP_HISTORY_GUIDE.md)

### I want to combine experiments from multiple days

**Python/Jupyter:**
```python
from src.core.timeline import print_chip_history
from src.plotting.its import plot_its_overlay, combine_metadata_by_seq

# 1. View history to get seq numbers
print_chip_history(Path("metadata"), Path("."), 67, "Alisson", proc_filter="ITS")

# 2. Combine by seq (not file_idx!)
meta = combine_metadata_by_seq(Path("metadata"), Path("."), 67, [52, 57, 58], "Alisson")

# 3. Plot
plot_its_overlay(meta, Path("."), "cross_day_analysis")
```

**Reference:** [CROSS_DAY_ITS_GUIDE.md](CROSS_DAY_ITS_GUIDE.md)

### I'm developing/modifying the code

**Architecture overview:**
- [CLAUDE.md](CLAUDE.md) - Complete technical reference
- [structure.md](structure.md) - Codebase organization

**Key sections in CLAUDE.md:**
- TUI Architecture - Textual framework patterns
- Core Data Pipeline - Metadata extraction, plotting
- Code Conventions - Session model, path handling
- Common Issues - Troubleshooting guide

---

## Feature-Specific Documentation

### Terminal User Interface (TUI)

**Main Guide:** [TUI_GUIDE.md](TUI_GUIDE.md)

**Contents:**
- 8-step wizard workflow
- Keyboard navigation reference
- Configuration persistence (NEW!)
- Quick vs Custom modes (NEW!)
- Recent configurations (NEW!)
- Export/import configs (NEW!)
- Troubleshooting

**New Features (October 2025):**
- **Configuration Persistence** - Auto-save successful plots to `~/.lab_plotter_configs.json`
- **Recent Configurations Screen** - Load/view/export/import/delete saved configs
- **Config Mode Selector** - Choose Quick (defaults) or Custom (full control)
- **Custom Config Screens** - ITS/IVg/Transconductance with all parameters
- **Validation** - Input validation with user-friendly error messages

### Command-Line Interface (CLI)

**Main Guide:** [CLI_GUIDE.md](CLI_GUIDE.md)

**Contents:**
- Complete pipeline command
- Parsing commands
- Chip history commands
- Plotting commands (ITS, IVg, Transconductance)
- All command-line options
- Examples and use cases

**Key Commands:**
```bash
full-pipeline      # Parse all + generate histories (most common)
parse-all          # Extract metadata from raw CSVs
chip-histories     # Generate chip timeline histories
show-history       # View single chip history
plot-its           # Generate ITS plots
plot-ivg           # Generate IVg plots
plot-transconductance  # Generate transconductance plots
quick-stats        # Show metadata statistics
```

### Chip History & Timeline

**Main Guide:** [CHIP_HISTORY_GUIDE.md](CHIP_HISTORY_GUIDE.md)

**Purpose:** Track complete experimental timeline for each chip across all days

**Key Functions:**
- `print_chip_history()` - Generate complete history for one chip
- `generate_all_chip_histories()` - Auto-generate for all chips
- Saves to `chip_histories/AlissonXX_history.csv`

**Important:** Always use `seq` numbers (not `file_idx`) for cross-day analysis!

### Cross-Day Analysis

**Main Guide:** [CROSS_DAY_ITS_GUIDE.md](CROSS_DAY_ITS_GUIDE.md)

**Purpose:** Combine experiments from multiple days into single plot

**Key Function:**
```python
combine_metadata_by_seq(metadata_dir, raw_data_dir, chip, seq_numbers, chip_group_name)
```

**Critical:** Use `seq` numbers from `print_chip_history()`, NOT `file_idx`!

**Works with:**
- ITS overlay plots
- IVg sequence plots
- Transconductance plots
- Delta plots

### Plotting System

**Main Guide:** [PLOT_OUTPUT_SYSTEM.md](PLOT_OUTPUT_SYSTEM.md)

**Contents:**
- Output filename patterns
- Directory structure
- CLI vs TUI behavior
- FIG_DIR global variable system

**Plot Types:**
- **ITS:** `chip{N}_ITS_overlay_{tag}.png`, `chip{N}_ITS_dark_{tag}.png`
- **IVg:** `Encap{N}_IVg_sequence_{tag}.png`
- **Transconductance:** `Chip{N}_gm_sequence_{tag}.png`, `Chip{N}_gm_savgol_{tag}.png`

---

## Development Documentation

### For AI Assistants (Claude)

**Primary:** [CLAUDE.md](CLAUDE.md)

**Complete technical reference including:**
- Repository purpose and architecture
- TUI framework (Textual 6.3.0)
- Core data pipeline
- Session model and conventions
- Path handling (critical!)
- Dependencies and common issues
- Recent additions and changes

**Critical sections:**
- TUI Implementation Details - Thread safety, focus management
- Path Handling - Avoiding duplication bugs
- Cross-Day Analysis - seq vs file_idx
- Transconductance Analysis - Segmentation, methods

### Codebase Organization

**Document:** [structure.md](structure.md)

**Contents:**
- Current structure analysis (8,350+ lines)
- Recommended modular structure
- Migration strategy (5 phases)
- Benefits of reorganization

**Current Structure:**
```
src/
├── cli/              # CLI commands and helpers
├── core/             # Parser, utils, timeline
├── plotting/         # ITS, IVg, transconductance, overlays
├── tui/              # Terminal user interface
│   ├── app.py
│   ├── config_manager.py
│   ├── screens/
│   └── widgets/
└── legacy/           # Archived code
```

### Changelog & Progress

**TUI Development:**
- [CHANGELOG_TUI.md](CHANGELOG_TUI.md) - Detailed session-by-session changes
- [TUI_IMPLEMENTATION_PLAN.md](TUI_IMPLEMENTATION_PLAN.md) - Original implementation plan
- [TUI_PROGRESS_REPORT.md](TUI_PROGRESS_REPORT.md) - Phase completion status

---

## Dependencies

### Core Analysis
- `polars>=0.19.0` - Fast dataframe operations
- `numpy>=1.24.0` - Numerical computing
- `scipy>=1.11.0` - Signal processing (Savitzky-Golay filtering)
- `matplotlib>=3.7.0` + `scienceplots>=2.0.0` - Plotting
- `imageio>=2.28.0` + `Pillow>=10.0.0` - GIF generation

### CLI
- `typer>=0.9.0` - Command-line framework
- `rich>=13.0.0` - Terminal output (tables, progress bars)

### TUI
- `textual==6.3.0` - Terminal user interface framework
- `rich>=13.0.0` - Rich text formatting

### Optional
- `ipython>=8.0.0` - Enhanced Python shell
- `jupyter>=1.0.0` - Interactive notebooks

**Install all:**
```bash
pip install -r requirements.txt
```

---

## Quick Reference Tables

### Plot Types

| Type | Description | CLI Command | TUI Option |
|------|-------------|-------------|------------|
| **ITS** | Time series (I vs t) | `plot-its` | ITS |
| **IVg** | Gate voltage sweep (I vs Vg) | `plot-ivg` | IVg |
| **Transconductance** | Derivative (dI/dVg) | `plot-transconductance` | Transconductance |

### Configuration Storage

| Item | Location | Format | Max Count |
|------|----------|--------|-----------|
| Plot configs | `~/.lab_plotter_configs.json` | JSON | 20 (auto-trim) |
| Chip histories | `chip_histories/AlissonXX_history.csv` | CSV | Unlimited |
| Metadata | `metadata/<day>/metadata.csv` | CSV | Unlimited |
| Plots | `figs/*.png` | PNG | Unlimited |

### Important Conventions

| Term | Definition | Example |
|------|------------|---------|
| **seq** | Sequential experiment number across ALL days | 52, 57, 58 |
| **file_idx** | File number from CSV filename (repeats per day) | 1, 2, 3 (in file #1, #2, #3) |
| **proc** | Procedure type | ITS, IVg, IV, LaserCalibration |
| **session** | IVg → ITS... → IVg block | Session 1, Session 2 |
| **chip_group** | Chip name prefix | "Alisson" |

**Critical:** Always use `seq` (not `file_idx`) for cross-day analysis!

---

## Getting Help

### Documentation Not Found?

1. Check this index for the right document
2. Search within documents (all are markdown)
3. Check [CLAUDE.md](CLAUDE.md) for technical details
4. Review [CHANGELOG_TUI.md](CHANGELOG_TUI.md) for recent changes

### Common Questions

**Q: How do I get started?**
A: Read [README.md](README.md), then launch `python tui_app.py`

**Q: How do I automate plot generation?**
A: Use CLI - see [CLI_GUIDE.md](CLI_GUIDE.md)

**Q: How do I combine experiments from different days?**
A: See [CROSS_DAY_ITS_GUIDE.md](CROSS_DAY_ITS_GUIDE.md)

**Q: Where are my saved configurations?**
A: `~/.lab_plotter_configs.json` - see [TUI_GUIDE.md](TUI_GUIDE.md) "Configuration Persistence"

**Q: What's the difference between seq and file_idx?**
A: See [CHIP_HISTORY_GUIDE.md](CHIP_HISTORY_GUIDE.md) "Understanding seq vs file_idx"

**Q: How do I add new features to the TUI?**
A: See [CLAUDE.md](CLAUDE.md) "TUI Architecture" section

---

## Documentation Standards

All documentation follows these conventions:

- **Markdown format** - Compatible with GitHub and common viewers
- **Code blocks** - Use triple backticks with language specification
- **Clear headings** - Hierarchical structure with ##, ###
- **Examples** - Real, working examples with expected output
- **Cross-references** - Links to related documentation
- **Tables** - For structured reference information
- **Last updated** - Date stamps for major revisions

---

**This documentation is actively maintained. Last comprehensive review: October 22, 2025**
