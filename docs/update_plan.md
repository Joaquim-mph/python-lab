# CLI Plotting Implementation Plan

Plan for adding terminal-based plotting commands to `process_and_analyze.py` that replicate the notebook workflow but with CLI convenience.

---

## Overview

Add new commands to generate IVg, ITS, and transconductance plots directly from the terminal, using the same workflow as notebooks but with CLI arguments for experiment selection.

**Goal:** Replace notebook workflow with simple CLI commands like:
```bash
python process_and_analyze.py plot-its 67 --seq 52,57,58 --legend led_voltage
```

---

## Core Design Principles

1. **Use existing plotting functions** - Don't rewrite plot logic, just wrap `src/plots.py` functions
2. **Leverage chip history** - Users select experiments by `seq` numbers (same as `combine_metadata_by_seq()`)
3. **Rich terminal feedback** - Show progress, confirmation of what's being plotted, output file paths
4. **Flexible filtering** - Support multiple selection methods (seq numbers, date ranges, procedure filters)
5. **Sensible defaults** - Minimize required arguments while allowing full customization

---

## Architecture

### New Module: `src/cli_plots.py`

Create a dedicated module for CLI plotting helpers:
- Parse and validate user inputs
- Call `combine_metadata_by_seq()` to get experiment metadata
- Set up output directories
- Call existing plot functions from `src/plots.py`
- Handle errors gracefully with user-friendly messages

### Integration: `process_and_analyze.py`

Add new commands:
- `plot-its` - ITS overlay plots
- `plot-ivg` - IVg sequence plots
- `plot-transconductance` - Transconductance plots
- `plot-batch` - Generate multiple plot types at once

---

## Command Specifications

### 1. `plot-its` Command

**Purpose:** Generate ITS overlay plots for selected experiments

**Signature:**
```bash
python process_and_analyze.py plot-its CHIP_NUMBER [OPTIONS]
```

**Arguments:**
- `chip_number` (positional, required): Chip number (e.g., 67)

**Options:**
- `--seq`, `-s`: Comma-separated seq numbers (e.g., `52,57,58`) [REQUIRED unless --auto]
- `--auto`: Automatically plot all ITS experiments (skip manual selection)
- `--legend`, `-l`: Legend grouping (`led_voltage`, `wavelength`, `vg`, `date`) [default: `led_voltage`]
- `--tag`, `-t`: Output filename tag [default: `cli_its_{timestamp}`]
- `--output`, `-o`: Output directory [default: `figs/`]
- `--group`, `-g`: Chip group name [default: `Alisson`]
- `--padding`: Y-axis padding [default: `0.05`]
- `--vg`: Filter by specific gate voltage (e.g., `-0.4`)
- `--wavelength`: Filter by wavelength (e.g., `365`)
- `--date`: Filter by date (e.g., `2025-10-15`)

**Examples:**
```bash
# Basic usage - select specific experiments
python process_and_analyze.py plot-its 67 --seq 52,57,58

# With custom legend grouping
python process_and_analyze.py plot-its 67 --seq 52,57,58 --legend wavelength

# Auto-plot all ITS experiments
python process_and_analyze.py plot-its 67 --auto

# Filter by gate voltage
python process_and_analyze.py plot-its 67 --auto --vg -0.4

# Custom output location
python process_and_analyze.py plot-its 67 --seq 52,57,58 --output results/ --tag my_analysis
```

**Workflow:**
1. Parse chip number and options
2. If `--seq` provided: Use those specific experiments
3. If `--auto`: Load chip history, filter by ITS (+ optional filters), select all
4. Call `combine_metadata_by_seq()` with selected seq numbers
5. Apply additional filters (VG, wavelength, date) if specified
6. Set `plots.FIG_DIR` to output directory
7. Call `plot_its_overlay()` with metadata
8. Display success message with output file path

**Output Display:**
```
╭──────────────────────────────────────────╮
│  Plotting ITS Overlay: Alisson67         │
╰──────────────────────────────────────────╯

Selected experiments:
  • seq 52: 2025-10-15 10:47 - ITS VG=-0.4V λ=365nm
  • seq 57: 2025-10-16 12:03 - ITS VG=-0.4V λ=365nm
  • seq 58: 2025-10-16 12:07 - ITS VG=-0.4V λ=365nm

Settings:
  Legend by: led_voltage
  Padding: 0.05

Generating plot... ✓

Output saved: figs/Alisson67_its_overlay_cli_its_20251020.png
```

---

### 2. `plot-ivg` Command

**Purpose:** Generate IVg sequence plots for selected experiments

**Signature:**
```bash
python process_and_analyze.py plot-ivg CHIP_NUMBER [OPTIONS]
```

**Arguments:**
- `chip_number` (positional, required): Chip number

**Options:**
- `--seq`, `-s`: Comma-separated seq numbers [REQUIRED unless --auto]
- `--auto`: Automatically plot all IVg experiments
- `--tag`, `-t`: Output filename tag [default: `cli_ivg_{timestamp}`]
- `--output`, `-o`: Output directory [default: `figs/`]
- `--group`, `-g`: Chip group name [default: `Alisson`]
- `--date`: Filter by date
- `--vds`: Filter by VDS voltage

**Examples:**
```bash
# Basic usage
python process_and_analyze.py plot-ivg 67 --seq 2,8,14

# Auto-plot all IVg
python process_and_analyze.py plot-ivg 67 --auto

# Filter by date
python process_and_analyze.py plot-ivg 67 --auto --date 2025-10-15
```

**Workflow:**
1. Parse arguments
2. Select experiments (manual or auto)
3. Call `combine_metadata_by_seq()`
4. Apply filters
5. Set output directory
6. Call `plot_ivg_sequence()`
7. Display results

---

### 3. `plot-transconductance` Command

**Purpose:** Generate transconductance plots from IVg data

**Signature:**
```bash
python process_and_analyze.py plot-transconductance CHIP_NUMBER [OPTIONS]
```

**Arguments:**
- `chip_number` (positional, required): Chip number

**Options:**
- `--seq`, `-s`: Comma-separated seq numbers of IVg experiments
- `--auto`: Auto-select all IVg experiments
- `--method`: Method to use (`gradient`, `savgol`) [default: `gradient`]
- `--tag`, `-t`: Output filename tag
- `--output`, `-o`: Output directory [default: `figs/`]
- `--group`, `-g`: Chip group name [default: `Alisson`]

**Examples:**
```bash
# Basic usage
python process_and_analyze.py plot-transconductance 67 --seq 2,8,14

# Use Savitzky-Golay method for smoother curves
python process_and_analyze.py plot-transconductance 67 --seq 2,8,14 --method savgol

# Auto with specific method
python process_and_analyze.py plot-transconductance 67 --auto --method savgol
```

**Workflow:**
1. Parse arguments
2. Validate seq numbers correspond to IVg experiments
3. Call `combine_metadata_by_seq()`
4. Set output directory
5. Call appropriate transconductance function based on `--method`
6. Display results

---

### 4. `plot-batch` Command

**Purpose:** Generate multiple plot types in one command (convenience)

**Signature:**
```bash
python process_and_analyze.py plot-batch CHIP_NUMBER [OPTIONS]
```

**Arguments:**
- `chip_number` (positional, required): Chip number

**Options:**
- `--types`, `-t`: Plot types to generate (comma-separated: `its,ivg,gm`) [default: `its,ivg,gm`]
- `--seq-its`: Seq numbers for ITS plots
- `--seq-ivg`: Seq numbers for IVg/transconductance plots
- `--auto`: Auto-select all experiments for each type
- `--output`, `-o`: Output directory [default: `figs/`]
- `--group`, `-g`: Chip group name [default: `Alisson`]
- `--prefix`: Filename prefix for all plots

**Examples:**
```bash
# Generate all plot types with auto-selection
python process_and_analyze.py plot-batch 67 --auto

# Custom selections for each type
python process_and_analyze.py plot-batch 67 \
  --seq-its 52,57,58 \
  --seq-ivg 2,8,14 \
  --types its,ivg,gm

# Only ITS and IVg (skip transconductance)
python process_and_analyze.py plot-batch 67 --auto --types its,ivg
```

**Workflow:**
1. Parse requested plot types
2. For each type, follow individual command workflow
3. Show consolidated progress and results
4. Display summary table of all generated files

---

## Helper Functions Needed

### In `src/cli_plots.py`:

```python
def parse_seq_list(seq_str: str) -> list[int]:
    """Parse comma-separated seq numbers from string."""

def auto_select_experiments(
    chip: int,
    proc: str,
    history_dir: Path,
    chip_group: str,
    filters: dict
) -> list[int]:
    """Auto-select experiments based on filters."""

def validate_experiments_exist(
    seq_numbers: list[int],
    chip: int,
    history_dir: Path,
    chip_group: str
) -> tuple[bool, list[str]]:
    """Check that seq numbers exist and return details."""

def setup_output_dir(output_dir: Path, chip: int, chip_group: str) -> Path:
    """Create and return appropriate output directory."""

def generate_timestamp_tag() -> str:
    """Generate timestamp for default tags."""

def apply_metadata_filters(
    meta: pl.DataFrame,
    vg: Optional[float],
    vds: Optional[float],
    wavelength: Optional[float],
    date: Optional[str]
) -> pl.DataFrame:
    """Apply user-specified filters to metadata."""

def display_experiment_list(experiments: pl.DataFrame):
    """Pretty-print selected experiments using Rich."""

def display_plot_settings(settings: dict):
    """Pretty-print plot settings using Rich."""

def display_plot_success(output_file: Path):
    """Show success message with output file path."""
```

---

## Implementation Steps

### Phase 1: Foundation (1-2 hours)
1. Create `src/cli_plots.py` module
2. Implement helper functions:
   - `parse_seq_list()`
   - `generate_timestamp_tag()`
   - `setup_output_dir()`
3. Add basic imports and structure to `process_and_analyze.py`

### Phase 2: ITS Plotting (2-3 hours)
1. Implement `plot-its` command
2. Add `auto_select_experiments()` helper
3. Add `validate_experiments_exist()` helper
4. Implement filter application
5. Test with various argument combinations

### Phase 3: IVg Plotting (1-2 hours)
1. Implement `plot-ivg` command (simpler than ITS)
2. Reuse helper functions from Phase 2
3. Test with auto-selection and manual selection

### Phase 4: Transconductance (1-2 hours)
1. Implement `plot-transconductance` command
2. Add method selection logic
3. Validate that selected experiments are IVg type
4. Test both gradient and savgol methods

### Phase 5: Batch Plotting (2-3 hours)
1. Implement `plot-batch` command
2. Add logic to call individual plot functions
3. Implement consolidated progress display
4. Generate summary report

### Phase 6: Documentation & Polish (1-2 hours)
1. Update `CLI_GUIDE.md` with new commands
2. Add examples to docstrings
3. Add error handling and helpful messages
4. Test edge cases

**Total Estimated Time: 8-14 hours**

---

## Error Handling

### Common Errors to Handle:

1. **No history file found**
   - Message: "Run `chip-histories` first to generate history"
   - Show available chips

2. **Invalid seq numbers**
   - Message: "Seq numbers X, Y, Z not found in history"
   - Show valid range or suggest `show-history` command

3. **Wrong procedure type**
   - Message: "Seq numbers X, Y are IVg but expected ITS"
   - List correct procedure for each seq

4. **No experiments match filters**
   - Message: "No experiments found matching filters"
   - Show what filters were applied

5. **Missing metadata**
   - Message: "Metadata not found for day X"
   - Suggest running `parse-all` first

6. **Empty result after filtering**
   - Message: "Selection resulted in 0 experiments"
   - Show available options

---

## User Experience Enhancements

### Interactive Selection (Future Enhancement)
Add optional interactive mode using Textual TUI:
```bash
python process_and_analyze.py plot-its 67 --interactive
```

Shows a scrollable list of experiments with checkboxes:
```
┌─ Select ITS Experiments (Alisson67) ────────┐
│                                              │
│ [x] 52  2025-10-15  10:47  ITS  VG=-0.4V   │
│ [ ] 53  2025-10-15  10:52  ITS  VG=-0.5V   │
│ [x] 57  2025-10-16  12:03  ITS  VG=-0.4V   │
│ [x] 58  2025-10-16  12:07  ITS  VG=-0.4V   │
│                                              │
│ [Plot Selected] [Cancel]                     │
└──────────────────────────────────────────────┘
```

### Preview Mode
```bash
python process_and_analyze.py plot-its 67 --seq 52,57,58 --preview
```
Shows what would be plotted without generating files.

### Dry Run
```bash
python process_and_analyze.py plot-batch 67 --auto --dry-run
```
Shows what files would be created without actually plotting.

---

## Configuration File Support (Optional)

Allow users to save plot configurations:

**File: `plot_config.yaml`**
```yaml
defaults:
  chip_group: Alisson
  output_dir: figs/

its_defaults:
  legend_by: led_voltage
  padding: 0.05

ivg_defaults:
  # IVg specific defaults

transconductance_defaults:
  method: gradient
```

Load with: `--config plot_config.yaml`

---

## Integration with Existing Workflow

### Current Notebook Workflow:
```python
# 1. View history
print_chip_history(Path("metadata"), Path("."), 67, "Alisson", proc_filter="ITS")

# 2. Note seq numbers
selected = [52, 57, 58]

# 3. Combine metadata
meta = combine_metadata_by_seq(
    Path("metadata"), Path("."), 67.0, selected, "Alisson"
)

# 4. Plot
plot_its_overlay(meta, Path("."), "analysis", legend_by="led_voltage")
```

### New CLI Workflow:
```bash
# 1. View history (optional - can use show-history)
python process_and_analyze.py show-history 67 --proc ITS

# 2. Plot with selected seq numbers
python process_and_analyze.py plot-its 67 --seq 52,57,58 --legend led_voltage
```

**Advantages:**
- ✅ Single command instead of multi-step notebook
- ✅ Reproducible (same command always gives same result)
- ✅ Scriptable (can include in automation pipelines)
- ✅ Faster for routine analyses

---

## Testing Strategy

### Unit Tests
- Test each helper function independently
- Mock file I/O and plotting calls
- Verify error handling

### Integration Tests
- Test full command workflows
- Verify files are created correctly
- Test filter combinations

### Manual Testing Checklist
- [ ] Plot ITS with manual seq selection
- [ ] Plot ITS with auto-selection
- [ ] Plot ITS with VG filter
- [ ] Plot ITS with wavelength filter
- [ ] Plot IVg with manual selection
- [ ] Plot IVg with auto-selection
- [ ] Plot transconductance with gradient method
- [ ] Plot transconductance with savgol method
- [ ] Plot batch with all types
- [ ] Test error cases (missing history, invalid seq, etc.)
- [ ] Test with different chip groups
- [ ] Test custom output directories

---

## Documentation Requirements

### Update `CLI_GUIDE.md`:
- Add new commands section
- Include examples for each command
- Show common workflows
- Add troubleshooting section

### Update `CLAUDE.md`:
- Document new CLI plotting capabilities
- Explain when to use CLI vs notebooks
- Add examples of CLI integration

### Create `CLI_PLOTTING_GUIDE.md`:
- Dedicated guide for plotting commands
- Detailed examples
- Best practices
- Common patterns

---

## Success Criteria

✅ Commands work with minimal arguments (good defaults)
✅ Clear, helpful error messages
✅ Output paths clearly displayed
✅ Progress feedback for long operations
✅ Matches notebook plot quality exactly
✅ Documentation complete and clear
✅ All edge cases handled gracefully

---

## Future Enhancements (Post-MVP)

1. **Interactive TUI mode** - Textual-based experiment selector
2. **Plot comparison** - Side-by-side comparison of different experiments
3. **Animated GIFs from CLI** - Generate IVg sequence GIFs
4. **Export formats** - Support PDF, SVG output
5. **Batch processing scripts** - Generate plots for all chips
6. **Watch mode** - Auto-regenerate plots when data changes
7. **Web viewer** - Launch local web server to view plots
8. **Plot customization** - CLI flags for colors, styles, etc.

---

## Notes

- Keep commands simple and intuitive
- Prioritize common use cases over edge cases
- Make error messages actionable
- Provide examples in help text
- Use consistent naming across commands
- Follow existing CLI patterns from other commands
