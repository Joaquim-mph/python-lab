
  Current State Analysis

  Current file counts:
  - process_and_analyze.py: 1,650 lines (main CLI - getting large!)
  - src/plots.py: 1,348 lines (plotting functions)
  - src/plots_legacy.py: 2,250 lines (legacy code)
  - src/timeline.py: 542 lines (chip history)
  - src/cli_plots.py: 450 lines (CLI helpers)
  - Total: ~6,700 lines in src/ + 1,650 in CLI = 8,350+ lines

  Issues with current structure:
  1. All modules are flat in src/ - hard to navigate
  2. process_and_analyze.py is getting very large (1,650 lines)
  3. Mix of legacy and active code
  4. No clear separation of concerns
  5. CLI helpers separated from CLI commands

  Recommended Structure

  I recommend this modular, scalable structure:

  python-lab/
  ├── src/
  │   ├── __init__.py
  │   │
  │   ├── cli/                          # CLI-specific code
  │   │   ├── __init__.py
  │   │   ├── main.py                   # Main Typer app (moved from process_and_analyze.py)
  │   │   ├── commands/                 # Command implementations
  │   │   │   ├── __init__.py
  │   │   │   ├── data_pipeline.py      # parse-all, chip-histories, full-pipeline
  │   │   │   ├── history.py            # show-history, quick-stats
  │   │   │   ├── plot_its.py          # plot-its command
  │   │   │   ├── plot_ivg.py          # plot-ivg command
  │   │   │   └── plot_transconductance.py  # plot-transconductance command
  │   │   └── helpers.py                # CLI helpers (moved from cli_plots.py)
  │   │
  │   ├── core/                         # Core data processing
  │   │   ├── __init__.py
  │   │   ├── parser.py                 # CSV metadata parsing
  │   │   ├── utils.py                  # Data utilities
  │   │   └── timeline.py               # Chip history tracking
  │   │
  │   ├── plotting/                     # All plotting functionality
  │   │   ├── __init__.py
  │   │   ├── its.py                    # ITS plotting functions
  │   │   ├── ivg.py                    # IVg plotting functions
  │   │   ├── transconductance.py       # Transconductance plots
  │   │   ├── overlays.py               # Multi-experiment overlays
  │   │   ├── styles.py                 # Matplotlib styles
  │   │   └── utils.py                  # Plotting utilities
  │   │
  │   └── legacy/                       # Legacy code (archived)
  │       ├── __init__.py
  │       ├── plots_legacy.py
  │       ├── old_parser.py
  │       ├── process_day.py
  │       ├── process_day_updated.py
  │       └── helpers_plots_day.py
  │
  ├── process_and_analyze.py            # Simple entry point (5-10 lines)
  ├── requirements.txt
  ├── README.md
  ├── CLAUDE.md
  ├── CLI_GUIDE.md
  ├── CHIP_HISTORY_GUIDE.md
  └── CROSS_DAY_ITS_GUIDE.md

  Benefits of This Structure

  1. Clear Separation of Concerns

  - cli/: All CLI-specific code (commands, helpers, UI)
  - core/: Core data processing (parsing, utilities, timelines)
  - plotting/: All plotting functions organized by type
  - legacy/: Archived code that's not actively maintained

  2. Scalability

  - Easy to add new commands: just create new file in cli/commands/
  - Easy to add new plot types: just create new file in plotting/
  - Each module is focused and manageable (~200-400 lines)

  3. Better Imports

  Instead of:
  from src.cli_plots import parse_seq_list, generate_plot_tag
  from src.plots import plot_its_overlay
  from src.timeline import build_chip_history

  You'll have:
  from src.cli.helpers import parse_seq_list, generate_plot_tag
  from src.plotting.its import plot_its_overlay
  from src.core.timeline import build_chip_history

  4. Cleaner Entry Point

  process_and_analyze.py becomes ultra-simple:
  #!/usr/bin/env python3
  from src.cli.main import app

  if __name__ == "__main__":
      app()

  5. Easier Testing

  - Test CLI commands independently
  - Test plotting functions without CLI overhead
  - Mock dependencies more easily

  Migration Strategy

  I can help you migrate in small, safe steps:

  Phase 1: Create Structure (No Breaking Changes)

  1. Create new directories
  2. Add __init__.py files
  3. Keep old files as-is

  Phase 2: Move CLI Code

  1. Create src/cli/main.py (move Typer app from process_and_analyze.py)
  2. Split commands into src/cli/commands/
  3. Move cli_plots.py → src/cli/helpers.py
  4. Update process_and_analyze.py to import from new location

  Phase 3: Reorganize Plotting

  1. Split plots.py into focused modules:
    - plotting/its.py - ITS functions
    - plotting/ivg.py - IVg functions
    - plotting/transconductance.py - Transconductance
    - plotting/overlays.py - Multi-experiment overlays
  2. Move styles.py → plotting/styles.py

  Phase 4: Organize Core

  1. Move core files to core/:
    - parser.py → core/parser.py
    - utils.py → core/utils.py
    - timeline.py → core/timeline.py

  Phase 5: Archive Legacy

  1. Move legacy code to legacy/
  2. Update imports if anything still depends on it

  Alternative: Lighter Reorganization

  If you want something less aggressive, here's a minimal approach:

  src/
  ├── cli/
  │   ├── commands.py      # All CLI commands (from process_and_analyze.py)
  │   └── helpers.py       # CLI helpers (from cli_plots.py)
  ├── core/
  │   ├── parser.py
  │   ├── utils.py
  │   └── timeline.py
  ├── plots/
  │   ├── its.py
  │   ├── ivg.py
  │   ├── styles.py
  │   └── utils.py
  └── legacy/              # Archive old code

  This is simpler but still gives you good organization.

  My Recommendation

  I recommend the full modular structure because:
  1. Your project is already at 8,000+ lines - it will only grow
  2. The CLI has distinct commands that deserve separate files
  3. Plot types are distinct enough to warrant separate modules
  4. Future contributors will appreciate the clear structure
  5. It sets you up well for potential packaging/distribution

  Would you like me to:
  1. Start the migration with Phase 1 (create structure)?
  2. Show you a detailed plan for one specific module (e.g., how to split plots.py)?
  3. Create a migration script to automate the reorganization?

  Let me know your preference and I'll help you reorganize in a safe, non-breaking
  way!



  python-lab/
  ├── src/
  │   ├── __init__.py
  │   │
  │   ├── plotting/                     # All plotting functionality
  │   │   ├── __init__.py
  │   │   ├── its.py                    # ITS plotting functions
  │   │   ├── ivg.py                    # IVg plotting functions
  │   │   ├── transconductance.py       # Transconductance plots
  │   │   ├── overlays.py               # Multi-experiment overlays
  │   │   ├── styles.py                 # Matplotlib styles
  │   │   └── utils.py                  # Plotting utilities


##################

  Implementation Plan: True Raw Data Plotting Feature

  Based on my analysis of the codebase, here's the detailed implementation plan to fix
   the raw data plotting issue:

  ---
  Problem Analysis

  Currently, the system has three baseline modes, but there's confusion between
  "baseline=0s" and "raw data":

  1. Current behavior when checkbox unchecked: Sets baseline_mode="none" →
  apply_baseline=False → plots yy_corr = yy (line 732 in its.py)
    - Expected: This SHOULD plot raw data
    - Actual: This already plots raw data correctly! The code at line 732 sets yy_corr
   = yy (no modification)
  2. The ACTUAL issue: The user wants to distinguish between:
    - Raw data mode: Plot CSV data as-is (no correction) - checkbox OFF
    - Baseline=0s mode: Subtract value at t=0 from all points - checkbox ON + enter 
  "0"
    - These are DIFFERENT operations, but currently treated similarly
  3. Additional requirements:
    - Add _raw suffix to filenames when plotting raw data
    - Allow duplicate plots (both corrected and raw versions)

  ---
  Root Cause

  The confusion stems from:
  1. The code at plot_generation.py:181 only passes baseline_t value, NOT
  baseline_mode and other preset parameters
  2. When baseline_mode="none", the plotting code correctly skips correction, but user
   perception is that it's still applying "0s baseline"
  3. No filename suffix differentiation between raw and corrected plots
  4. No mechanism to generate both versions

  ---
  Files to Modify

  1. src/tui/screens/plot_generation.py (Lines 175-227)

  What needs to change: Pass all baseline parameters from config to plotting functions

  Current code:
  # Get ITS-specific config
  legend_by = self.config.get("legend_by", "vg")
  baseline_t = self.config.get("baseline", 60.0)
  padding = self.config.get("padding", 0.05)

  # Later...
  its.plot_its_overlay(
      meta, raw_dir, plot_tag,
      baseline_t=baseline_t,
      legend_by=legend_by,
      padding=padding
  )

  Needs to become:
  # Get ITS-specific config
  legend_by = self.config.get("legend_by", "vg")
  baseline_t = self.config.get("baseline", 60.0)
  padding = self.config.get("padding", 0.05)
  baseline_mode = self.config.get("baseline_mode", "fixed")  # NEW
  baseline_auto_divisor = self.config.get("baseline_auto_divisor", 2.0)  # NEW
  plot_start_time = self.config.get("plot_start_time", 20.0)  # NEW
  check_duration_mismatch = self.config.get("check_duration_mismatch", False)  # NEW
  duration_tolerance = self.config.get("duration_tolerance", 0.10)  # NEW

  # Later...
  its.plot_its_overlay(
      meta, raw_dir, plot_tag,
      baseline_t=baseline_t,
      baseline_mode=baseline_mode,  # NEW
      baseline_auto_divisor=baseline_auto_divisor,  # NEW
      plot_start_time=plot_start_time,  # NEW
      legend_by=legend_by,
      padding=padding,
      check_duration_mismatch=check_duration_mismatch,  # NEW
      duration_tolerance=duration_tolerance  # NEW
  )

  Same changes needed for plot_its_dark() call at lines 211-218

  ---
  2. src/tui/screens/plot_generation.py (Lines 262-298)

  What needs to change: Add _raw suffix to filename when baseline_mode="none"

  Current code:
  if all_dark:
      filename = f"encap{self.chip_number}_ITS_dark_{plot_tag}.png"
  else:
      filename = f"encap{self.chip_number}_ITS_{plot_tag}.png"

  Needs to become:
  # Check if raw data mode
  baseline_mode = self.config.get("baseline_mode", "fixed")
  raw_suffix = "_raw" if baseline_mode == "none" else ""

  if all_dark:
      filename = f"encap{self.chip_number}_ITS_dark_{plot_tag}{raw_suffix}.png"
  else:
      filename = f"encap{self.chip_number}_ITS_{plot_tag}{raw_suffix}.png"

  ---
  3. src/tui/screens/preview_screen.py (Lines 388-424)

  What needs to change: Update _generate_filename() to match the generation screen
  logic

  Current code (line 411):
  filename = f"encap{self.chip_number}_ITS_{plot_tag}.png"

  Needs to become:
  # Check if raw data mode
  baseline_mode = self.config.get("baseline_mode", "fixed")
  raw_suffix = "_raw" if baseline_mode == "none" else ""
  filename = f"encap{self.chip_number}_ITS_{plot_tag}{raw_suffix}.png"

  ---
  4. src/tui/screens/preview_screen.py (Lines 315-385)

  What needs to change: Update _build_config_summary() to clarify raw data mode

  Current code (lines 346-354):
  # Show baseline mode
  baseline_mode = self.config.get("baseline_mode", "fixed")
  if baseline_mode == "none":
      lines.append("• Baseline: None (no correction)")
  elif baseline_mode == "auto":
      divisor = self.config.get("baseline_auto_divisor", 2.0)
      lines.append(f"• Baseline: Auto (LED period / {divisor})")
  else:  # fixed
      baseline = self.config.get("baseline", 60.0)
      lines.append(f"• Baseline time: {baseline} s")

  Needs to become:
  # Show baseline mode
  baseline_mode = self.config.get("baseline_mode", "fixed")
  if baseline_mode == "none":
      lines.append("• Baseline: None (RAW DATA - no correction)")  # CLARIFIED
  elif baseline_mode == "auto":
      divisor = self.config.get("baseline_auto_divisor", 2.0)
      lines.append(f"• Baseline: Auto (LED period / {divisor})")
  else:  # fixed
      baseline = self.config.get("baseline", 60.0)
      if baseline == 0.0:
          lines.append("• Baseline: 0.0 s (subtract value at t=0)")  # NEW CASE
      else:
          lines.append(f"• Baseline time: {baseline} s")

  ---
  5. src/plotting/its.py (NEW FUNCTION - add after line 100)

  What needs to add: New function to implement baseline=0s correction

  New code to insert:
  def _apply_baseline_zero(tt: np.ndarray, yy: np.ndarray) -> np.ndarray:
      """
      Apply t=0 baseline correction (subtract first point).
      
      Parameters
      ----------
      tt : np.ndarray
          Time array
      yy : np.ndarray
          Current array
          
      Returns
      -------
      np.ndarray
          Baseline-corrected current (yy - yy[0])
      """
      if len(yy) == 0:
          return yy

      I0 = yy[0]  # Value at first time point
      return yy - I0

  ---
  6. src/plotting/its.py (Lines 209-224)

  What needs to change: Handle baseline=0.0 as special case in plot_its_overlay()

  Current code:
  # --- Handle baseline mode ---
  if baseline_mode == "auto":
      baseline_t = _calculate_auto_baseline(df, baseline_auto_divisor)
      apply_baseline = True
  elif baseline_mode == "none":
      baseline_t = None
      apply_baseline = False
      print("[info] Baseline correction disabled (dark experiment mode)")
  else:  # baseline_mode == "fixed"
      if baseline_t is None:
          baseline_t = 60.0
          print("[warn] baseline_mode='fixed' but baseline_t=None, using 60.0")
      apply_baseline = True

  Needs to become:
  # --- Handle baseline mode ---
  if baseline_mode == "auto":
      baseline_t = _calculate_auto_baseline(df, baseline_auto_divisor)
      apply_baseline = "interpolate"  # CHANGED from True
  elif baseline_mode == "none":
      baseline_t = None
      apply_baseline = False
      print("[info] Baseline correction disabled (RAW DATA mode)")
  else:  # baseline_mode == "fixed"
      if baseline_t is None:
          baseline_t = 60.0
          print("[warn] baseline_mode='fixed' but baseline_t=None, using 60.0")
      # Check if baseline is exactly 0.0 (special case)
      if baseline_t == 0.0:
          apply_baseline = "zero"  # NEW: Subtract first point
          print("[info] Baseline at t=0: subtracting first point from each trace")
      else:
          apply_baseline = "interpolate"  # CHANGED from True

  ---
  7. src/plotting/its.py (Lines ~400-420 in plot_its_overlay)

  What needs to change: Update baseline application logic to handle three cases

  Current code (estimated around line 400, in the loop):
  # baseline correction (if enabled)
  if apply_baseline:
      I0 = interpolate_baseline(tt, yy, baseline_t, warn_extrapolation=True)
      yy_corr = yy - I0
  else:
      # No baseline correction
      yy_corr = yy

  Needs to become:
  # baseline correction (three modes)
  if apply_baseline == "interpolate":
      # Standard interpolation at baseline_t
      I0 = interpolate_baseline(tt, yy, baseline_t, warn_extrapolation=True)
      yy_corr = yy - I0
  elif apply_baseline == "zero":
      # Subtract first point (t=0 baseline)
      yy_corr = _apply_baseline_zero(tt, yy)
  else:  # apply_baseline == False
      # No baseline correction (raw data)
      yy_corr = yy

  ---
  8. src/plotting/its.py (plot_its_dark function, lines ~581-603)

  What needs to change: Same changes as #6 and #7 for dark plots

  Apply the same baseline mode handling logic to plot_its_dark() function.

  ---
  Testing Plan

  After implementation, test these scenarios:

  1. Raw data mode (checkbox OFF):
    - Filename should have _raw suffix
    - Plot should show CSV data exactly as recorded
    - Preview should say "RAW DATA - no correction"
  2. Baseline=0s mode (checkbox ON + enter "0"):
    - Filename should NOT have _raw suffix
    - Each trace should be shifted so first point is at y=0
    - Preview should say "Baseline: 0.0 s (subtract value at t=0)"
  3. Normal baseline mode (checkbox ON + enter "60"):
    - Filename should NOT have _raw suffix
    - Standard interpolation baseline correction
    - Preview should say "Baseline time: 60.0 s"
  4. Auto baseline mode (checkbox ON + leave empty):
    - Filename should NOT have _raw suffix
    - Auto-calculate from LED period
    - Preview should say "Baseline: Auto (LED period / 2.0)"

  ---
  Optional Enhancement: Duplicate Plots Feature

  To allow generating both corrected and raw versions in one pass:

  Add to src/tui/screens/its_config.py (after baseline checkbox):
  with Horizontal(classes="form-row"):
      yield Checkbox("Also generate raw version", id="generate-raw-duplicate",
  value=False)

  Add to preview screen logic:
  If generate-raw-duplicate is checked, show warning that TWO files will be created.

  Add to plot_generation.py:
  If generate-raw-duplicate is enabled and baseline_mode != "none":
  1. Generate corrected plot first
  2. Create modified config with baseline_mode="none"
  3. Generate raw plot second

  ---
  Summary of Changes

  | File               | Lines     | Change Type | Purpose
              |
  |--------------------|-----------|-------------|------------------------------------
  ------------|
  | plot_generation.py | 175-227   | Modify      | Pass all baseline params to
  plotting functions |
  | plot_generation.py | 262-298   | Modify      | Add _raw suffix for raw mode
  filenames         |
  | preview_screen.py  | 388-424   | Modify      | Match filename generation logic
              |
  | preview_screen.py  | 315-385   | Modify      | Clarify baseline mode descriptions
              |
  | its.py             | After 100 | Add         | New _apply_baseline_zero() function
              |
  | its.py             | 209-224   | Modify      | Handle baseline=0.0 as special case
              |
  | its.py             | ~400-420  | Modify      | Three-way baseline application
  logic           |
  | its.py             | 581-603   | Modify      | Same changes for plot_its_dark()
              |

  ---
  Estimated complexity: Medium (8 file modifications, ~50 lines changed, 1 new
  function)

  Risk level: Low - Changes are localized to baseline handling, existing tests should
  catch regressions

  User impact: HIGH - Fixes fundamental gap in raw data plotting capability