# Interactive Features Implementation Plan

Plan for adding interactive selection, preview mode, and dry-run capabilities to the CLI plotting commands.

---

## Overview

Add three major enhancements to make the CLI more interactive and user-friendly:

1. **Interactive Selection Mode** - TUI for selecting experiments with checkboxes
2. **Preview Mode** - Show what will be plotted without generating files
3. **Dry Run Mode** - Show what files would be created without plotting

---

## 1. Interactive Selection Mode

### Goal
Replace manual `--seq` entry with a visual checkbox interface using Textual TUI.

### Design

**Invocation:**
```bash
python process_and_analyze.py plot-its 67 --interactive
python process_and_analyze.py plot-ivg 67 --interactive
python process_and_analyze.py plot-transconductance 67 --interactive
```

**Behavior:**
1. Load chip history for the specified chip
2. Filter by procedure type (ITS for plot-its, IVg for plot-ivg/transconductance)
3. Display scrollable list with checkboxes
4. Allow user to select/deselect experiments
5. Show summary of selected experiments
6. Proceed to plotting when user clicks "Plot Selected"

**UI Layout:**
```
┌─ Select ITS Experiments for Alisson67 ─────────────────────┐
│                                                             │
│  Filter by: [VG: -0.4    ] [λ: 365     ] [Date:          ] │
│                                                             │
│  ┌─ Experiments ─────────────────────────────────────────┐ │
│  │ [x] 52  2025-10-15 10:47  ITS  VG=-0.4V  λ=365nm     │ │
│  │ [ ] 53  2025-10-15 10:52  ITS  VG=-0.5V  λ=365nm     │ │
│  │ [x] 57  2025-10-16 12:03  ITS  VG=-0.4V  λ=365nm     │ │
│  │ [x] 58  2025-10-16 12:07  ITS  VG=-0.4V  λ=365nm     │ │
│  │ [ ] 61  2025-10-16 14:21  ITS  VG=-0.4V  λ=455nm     │ │
│  │ [x] 63  2025-10-16 15:03  ITS  VG=-0.4V  λ=365nm     │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  Selected: 4 experiment(s)    [Select All] [Deselect All]  │
│                                                             │
│  [Plot Selected]  [Preview]  [Cancel]                       │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Details

**New Module: `src/interactive_selector.py`**

```python
from textual.app import App, ComposeResult
from textual.containers import Container, Scrollable
from textual.widgets import Header, Footer, Checkbox, Button, Static, Input
from textual.binding import Binding

class ExperimentSelector(App):
    """Interactive experiment selector using Textual."""

    CSS = """
    # CSS styling for the TUI
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("a", "select_all", "Select All"),
        Binding("d", "deselect_all", "Deselect All"),
        Binding("enter", "plot", "Plot"),
    ]

    def __init__(self, chip_number: int, chip_group: str,
                 history: pl.DataFrame, proc_type: str):
        super().__init__()
        self.chip_number = chip_number
        self.chip_group = chip_group
        self.history = history
        self.proc_type = proc_type
        self.selected_seqs = []
        self.action = None  # "plot", "preview", or "cancel"

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Container(
            # Filter inputs
            # Scrollable list of checkboxes
            # Summary line
            # Action buttons
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "plot":
            self.action = "plot"
            self.exit(self.selected_seqs)
        elif event.button.id == "preview":
            self.action = "preview"
            self.exit(self.selected_seqs)
        elif event.button.id == "cancel":
            self.action = "cancel"
            self.exit([])

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Update selected_seqs when checkbox changes."""
        # Update selection
        # Update summary
```

**Helper Function:**
```python
def run_interactive_selector(
    chip_number: int,
    chip_group: str,
    history_dir: Path,
    proc_type: str
) -> tuple[list[int], str]:
    """
    Run interactive selector and return selected seq numbers and action.

    Returns
    -------
    tuple[list[int], str]
        (selected_seq_numbers, action)
        action is "plot", "preview", or "cancel"
    """
    # Load history
    history = load_chip_history(chip_number, chip_group, history_dir)

    # Filter by procedure
    history = history.filter(pl.col("proc") == proc_type)

    # Run TUI
    app = ExperimentSelector(chip_number, chip_group, history, proc_type)
    selected_seqs = app.run()

    return selected_seqs, app.action
```

**Integration with Commands:**

Modify each plotting command to support `--interactive`:

```python
@app.command()
def plot_its(
    chip_number: int = typer.Argument(...),
    seq: Optional[str] = typer.Option(None, "--seq", "-s"),
    auto: bool = typer.Option(False, "--auto"),
    interactive: bool = typer.Option(False, "--interactive", "-i"),
    # ... other options
):
    # Check for conflicting options
    if sum([bool(seq), auto, interactive]) > 1:
        console.print("[red]Error:[/red] Use only one: --seq, --auto, or --interactive")
        raise typer.Exit(1)

    if not seq and not auto and not interactive:
        console.print("[red]Error:[/red] Must use --seq, --auto, or --interactive")
        raise typer.Exit(1)

    # Handle interactive mode
    if interactive:
        seq_numbers, action = run_interactive_selector(
            chip_number, chip_group, history_dir, "ITS"
        )

        if action == "cancel":
            console.print("[yellow]Selection cancelled[/yellow]")
            raise typer.Exit(0)

        if not seq_numbers:
            console.print("[yellow]No experiments selected[/yellow]")
            raise typer.Exit(0)

        console.print(f"[green]✓[/green] Selected {len(seq_numbers)} experiment(s)")

        # If user clicked "Preview", set preview mode
        if action == "preview":
            preview = True

    # Rest of command logic...
```

### Features

- **Keyboard Navigation**: Arrow keys, space to toggle, Enter to confirm
- **Mouse Support**: Click checkboxes directly
- **Filtering**: Live filter by VG, wavelength, date
- **Batch Actions**: Select All, Deselect All buttons
- **Preview from Selector**: "Preview" button shows what would be plotted
- **Summary**: Shows count of selected experiments
- **Validation**: Can't proceed without selection

---

## 2. Preview Mode

### Goal
Show exactly what will be plotted without generating files. Useful for verifying selections before running.

### Design

**Invocation:**
```bash
python process_and_analyze.py plot-its 67 --seq 52,57,58 --preview
python process_and_analyze.py plot-ivg 67 --auto --preview
python process_and_analyze.py plot-transconductance 67 --seq 2,8,14 --method savgol --preview
```

**Behavior:**
1. Load metadata (same as normal plotting)
2. Validate all seq numbers
3. Apply filters
4. Display what WOULD be plotted
5. Show output filename that WOULD be created
6. Exit WITHOUT generating any files

**Output Format:**
```
╭─────────────────────────────────────╮
│ PREVIEW MODE: ITS Overlay Plot      │
│ Alisson67                           │
╰─────────────────────────────────────╯

✓ Loaded 3 experiment(s)

           Experiments to be Plotted
┌──────┬──────┬─────────┬────────┬───────┬──────────┐
│ Seq  │ Proc │  VG (V) │  λ (nm)│ LED V │   Date   │
├──────┼──────┼─────────┼────────┼───────┼──────────┤
│  52  │ ITS  │  -0.40  │  365   │  2.50 │ 10-15    │
│  57  │ ITS  │  -0.40  │  365   │  2.50 │ 10-16    │
│  58  │ ITS  │  -0.40  │  365   │  2.50 │ 10-16    │
└──────┴──────┴─────────┴────────┴───────┴──────────┘

╭─────── Plot Settings ────────╮
│ Legend by: led_voltage       │
│ Baseline time: 60.0 s        │
│ Padding: 5.00%               │
│ Output directory: figs       │
╰──────────────────────────────╯

╭─────── Output File ──────────╮
│ figs/chip67_ITS_overlay_     │
│ seq_52_57_58.png             │
╰──────────────────────────────╯

✓ Preview complete - no files generated
  Run without --preview to generate plot
```

### Implementation

**Add `--preview` flag to all plotting commands:**

```python
preview: bool = typer.Option(
    False,
    "--preview",
    "-p",
    help="Preview mode: show what will be plotted without generating files"
)
```

**Modify plotting workflow:**

```python
# After loading and validating metadata...

# Display what will be plotted
display_experiment_list(meta, title="Experiments to be Plotted")
display_plot_settings(settings)

# Show output filename
output_file = output_dir / f"{chip_label}_ITS_overlay_{plot_tag}.png"
console.print()
console.print(Panel(
    f"[cyan]Output file:[/cyan]\n{output_file}",
    title="Output File",
    border_style="cyan"
))

# Exit in preview mode
if preview:
    console.print()
    console.print("[green]✓ Preview complete - no files generated[/green]")
    console.print("[dim]  Run without --preview to generate plot[/dim]")
    raise typer.Exit(0)

# Otherwise, proceed with plotting...
console.print("\n[cyan]Generating plot...[/cyan]")
```

### Features

- **Complete Validation**: All validations run (seq numbers, experiment types, etc.)
- **Metadata Loading**: Actually loads and combines metadata
- **Filter Application**: Shows results after filtering
- **Filename Preview**: Shows exact filename that would be created
- **No File Generation**: Exits before calling plot functions
- **Quick Check**: Fast way to verify selections are correct

---

## 3. Dry Run Mode

### Goal
Show what files would be created for batch operations without actually plotting.

### Design

**Primary Use Case:** Batch plotting command (future implementation)

```bash
python process_and_analyze.py plot-batch 67 --auto --dry-run
python process_and_analyze.py plot-batch 67 --types its,ivg,gm --auto --dry-run
```

**Also Applicable to Single Commands:**
```bash
python process_and_analyze.py plot-its 67 --auto --dry-run
python process_and_analyze.py plot-ivg 67 --seq 1,2,3,4,5 --dry-run
```

**Behavior:**
1. Select experiments (auto or manual)
2. Determine what plots would be generated
3. Show list of output files
4. Show total file count and estimated size
5. Exit WITHOUT loading data or plotting

**Output Format:**
```
╭─────────────────────────────────────╮
│ DRY RUN: Batch Plotting             │
│ Alisson67                           │
╰─────────────────────────────────────╯

Auto-selecting experiments...
✓ Found 15 ITS experiment(s)
✓ Found 8 IVg experiment(s)

╭─────── Files to be Created ──────────╮
│                                      │
│ ITS Plots:                           │
│   • chip67_ITS_overlay_seq_52_...   │
│                                      │
│ IVg Plots:                           │
│   • Encap67_IVg_sequence_seq_2_...  │
│                                      │
│ Transconductance Plots:              │
│   • Chip67_gm_sequence_seq_2_...    │
│                                      │
│ Total: 3 file(s)                     │
│ Output directory: figs/              │
│                                      │
╰──────────────────────────────────────╯

✓ Dry run complete - no files generated
  Run without --dry-run to generate plots
```

### Implementation

**Add `--dry-run` flag:**

```python
dry_run: bool = typer.Option(
    False,
    "--dry-run",
    help="Dry run: show what files would be created without plotting"
)
```

**Modify workflow:**

```python
# After selecting seq numbers but BEFORE loading metadata...

if dry_run:
    console.print("\n[cyan]DRY RUN MODE[/cyan]")
    console.print(f"[dim]Selected {len(seq_numbers)} experiment(s)[/dim]")

    # Generate output filename without loading data
    plot_tag = generate_plot_tag(seq_numbers, custom_tag=tag)
    output_file = output_dir / f"{chip_label}_ITS_overlay_{plot_tag}.png"

    console.print()
    console.print(Panel(
        f"[cyan]File to be created:[/cyan]\n{output_file}\n\n"
        f"[cyan]Output directory:[/cyan] {output_dir}",
        title="Dry Run Results",
        border_style="yellow"
    ))

    console.print()
    console.print("[green]✓ Dry run complete - no files generated[/green]")
    console.print("[dim]  Run without --dry-run to generate plot[/dim]")
    raise typer.Exit(0)

# Otherwise, proceed with loading metadata and plotting...
```

### Features

- **Fast**: Doesn't load metadata or plot data
- **File Prediction**: Shows exact filenames that would be created
- **Batch Support**: Perfect for plot-batch command
- **Conflict Detection**: Can detect if files already exist
- **Size Estimation**: Could estimate total file size

---

## 4. Batch Plotting Command (New)

### Goal
Generate multiple plot types (ITS, IVg, transconductance) in one command.

### Design

**Invocation:**
```bash
python process_and_analyze.py plot-batch 67 --auto
python process_and_analyze.py plot-batch 67 --types its,ivg,gm --auto
python process_and_analyze.py plot-batch 67 --seq-its 52,57 --seq-ivg 2,8 --seq-gm 2,8
```

**Options:**
```python
@app.command()
def plot_batch(
    chip_number: int = typer.Argument(...),
    types: str = typer.Option(
        "its,ivg,gm",
        "--types",
        "-t",
        help="Plot types to generate (comma-separated: its,ivg,gm)"
    ),
    seq_its: Optional[str] = typer.Option(None, "--seq-its"),
    seq_ivg: Optional[str] = typer.Option(None, "--seq-ivg"),
    seq_gm: Optional[str] = typer.Option(None, "--seq-gm"),
    auto: bool = typer.Option(False, "--auto"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    # ... other common options
):
    """Generate multiple plot types in one command."""
```

**Workflow:**
1. Parse requested plot types
2. For each type:
   - Select experiments (auto or from --seq-{type})
   - Validate
   - Generate plot (or show dry-run info)
3. Display consolidated summary

**Output:**
```
╭─────────────────────────────────────╮
│ Batch Plotting: Alisson67           │
│ Types: ITS, IVg, Transconductance   │
╰─────────────────────────────────────╯

[1/3] Generating ITS overlay...
✓ ITS plot complete: chip67_ITS_overlay_seq_52_57_58.png

[2/3] Generating IVg sequence...
✓ IVg plot complete: Encap67_IVg_sequence_seq_2_8_14.png

[3/3] Generating transconductance...
✓ Transconductance plot complete: Chip67_gm_sequence_seq_2_8_14.png

╭─────── Batch Complete ───────────╮
│ Generated 3 plot(s)              │
│ Output directory: figs/          │
│ Total time: 12.3s                │
╰──────────────────────────────────╯

Files created:
  • chip67_ITS_overlay_seq_52_57_58.png
  • Encap67_IVg_sequence_seq_2_8_14.png
  • Chip67_gm_sequence_seq_2_8_14.png
```

---

## Implementation Phases

### Phase 1: Preview Mode (Easiest - 1-2 hours)
**Why First:** Simple flag addition, no new UI, tests the concept

1. Add `--preview` flag to all three plotting commands
2. Implement preview display logic
3. Test with existing commands
4. Update documentation

### Phase 2: Dry Run Mode (Easy - 1-2 hours)
**Why Second:** Similar to preview but lighter weight

1. Add `--dry-run` flag to all three plotting commands
2. Implement dry-run logic (exit before metadata loading)
3. Add file existence checking
4. Test with existing commands

### Phase 3: Batch Command (Medium - 3-4 hours)
**Why Third:** Builds on dry-run, good testing ground

1. Create `plot-batch` command
2. Implement type selection and routing
3. Add consolidated summary
4. Integrate dry-run mode
5. Test all combinations

### Phase 4: Interactive Selection (Complex - 6-8 hours)
**Why Last:** Most complex, requires Textual TUI

1. Create `src/interactive_selector.py` module
2. Design and implement Textual app
3. Add filtering capabilities
4. Integrate with all plotting commands
5. Add keyboard bindings
6. Extensive testing

**Total Estimated Time: 11-16 hours**

---

## Testing Strategy

### Preview Mode Tests
- [ ] Plot with --preview shows correct experiments
- [ ] Plot with --preview shows correct filename
- [ ] Plot with --preview does not create files
- [ ] Preview works with --auto
- [ ] Preview works with --seq
- [ ] Preview works with filters

### Dry Run Tests
- [ ] Dry-run shows correct filenames
- [ ] Dry-run does not load metadata
- [ ] Dry-run is fast (< 1 second)
- [ ] Dry-run works with batch command
- [ ] Dry-run detects existing files

### Interactive Mode Tests
- [ ] Interactive mode displays all experiments
- [ ] Checkboxes work (keyboard and mouse)
- [ ] Filters work correctly
- [ ] Select All / Deselect All work
- [ ] Cancel exits without plotting
- [ ] Preview button triggers preview mode
- [ ] Plot button proceeds to plotting
- [ ] Empty selection is handled

### Batch Command Tests
- [ ] All three types generate correctly
- [ ] Type filtering works
- [ ] Per-type seq selection works
- [ ] Dry-run shows all files
- [ ] Summary is accurate
- [ ] Errors in one type don't stop others

---

## User Experience Enhancements

### Error Prevention
- **Preview Mode**: Catch mistakes before spending time plotting
- **Interactive Selection**: Visual confirmation of selections
- **Dry Run**: Know exactly what will be created

### Efficiency
- **Batch Command**: Generate all plots in one command
- **Interactive Filtering**: Quick selection of relevant experiments
- **Auto-selection**: Sensible defaults for common workflows

### Discoverability
- **Help Text**: Clear descriptions of each mode
- **Examples**: Show common usage patterns
- **Hints**: Suggest alternatives when errors occur

---

## Documentation Requirements

### CLI_GUIDE.md Updates

Add new sections:

1. **Interactive Mode**
   - How to use --interactive
   - Keyboard shortcuts
   - Filter syntax
   - Examples

2. **Preview Mode**
   - When to use --preview
   - What it shows
   - Examples with all commands

3. **Dry Run Mode**
   - Difference from preview
   - Use cases
   - Batch planning examples

4. **Batch Command**
   - Complete command reference
   - Type selection
   - Per-type options
   - Dry-run integration

### New Files

1. **INTERACTIVE_MODE.md**
   - Detailed guide to interactive selection
   - Screenshots/ASCII art of TUI
   - Keyboard reference
   - Tips and tricks

2. **BATCH_PLOTTING.md**
   - Batch plotting workflows
   - Examples for common scenarios
   - Integration with automation

---

## Success Criteria

### Preview Mode
✅ Shows all experiments that will be plotted
✅ Shows exact output filename
✅ Runs all validations
✅ Does not create any files
✅ Fast (< 2 seconds)

### Dry Run Mode
✅ Shows all files that would be created
✅ Does not load metadata (very fast < 1 second)
✅ Works with batch command
✅ Detects file conflicts

### Interactive Mode
✅ Visual, intuitive interface
✅ Keyboard and mouse navigation
✅ Live filtering
✅ Integrates with preview mode
✅ Works with all three plot types

### Batch Command
✅ Generates multiple plot types in one run
✅ Per-type configuration
✅ Consolidated summary
✅ Error isolation (one failure doesn't stop others)
✅ Dry-run support

---

## Dependencies

### Additional Packages
- `textual` >= 0.60.0 (already in requirements.txt)

### No New Dependencies
- Preview mode: uses existing Rich
- Dry-run mode: uses existing Rich
- Batch command: uses existing infrastructure

---

## Future Enhancements (Beyond This Plan)

1. **Configuration Files**: Save favorite selections
2. **Watch Mode**: Auto-regenerate when data changes
3. **Comparison Mode**: Side-by-side diff of two selections
4. **Export Mode**: Save selections to file for later
5. **History Mode**: Remember recent selections
6. **Template Mode**: Apply selection patterns to multiple chips

---

## Notes

- Keep commands simple for scripting (non-interactive default)
- Interactive mode optional (require explicit flag)
- Preview/dry-run are progressive checks (dry-run < preview < plot)
- Batch command should support all features of individual commands
- Error messages should guide users between modes


## TUI Update

  1. Navigation Flow

  Should it be:
  - Option A: Main menu → Select plot type → Select chip → Configure options → Launch
  selector → Generate plot
  - Option B: Main menu with tabs (ITS, IVg, Transconductance) where each tab has its
  own chip/option inputs?
  - Option C: Wizard-style (step-by-step screens)?

  2. Chip Selection

  - Should the TUI auto-discover available chips from the metadata/chip_histories
  directories?
  - Or show a manual input field for chip number?
  - Should it show a list of chips with experiment counts (e.g., "Alisson67 (82
  experiments)")?

  3. Plot Options

  For each plot type, should the TUI provide:
  - All CLI options (filters, baselines, methods, etc.)?
  - Most common options only (simplified)?
  - Preset configurations (e.g., "Quick plot", "Custom plot")?

  4. Advanced Features

  Do you want:
  - Batch plotting: Select multiple chips/plot types and queue them?
  - Preview mode: Show what will be plotted before generating?
  - Recent/favorites: Quick access to recently used configurations?
  - Export configuration: Save settings for later reuse?

  5. Output Display

  After generating a plot, should it:
  - Show success message and return to main menu?
  - Show the plot file path with option to open it?
  - Stay on the same screen for easy re-plotting?

  6. User Level

  Are your target users:
  - Complete beginners: Need tooltips, help screens, safe defaults?
  - Lab members: Familiar with the experiments but not CLI?
  - Mix of both?

  7. Launch Method

  Should users run:
  - python process_and_analyze.py (opens TUI by default)
  - python process_and_analyze.py tui (explicit TUI command)
  - Separate script like python tui_app.py?

  ---
  My recommendation based on typical scientific workflow:

  Main Menu with options:
  ┌─────────────────────────────────────────┐
  │     Experiment Plotting Assistant       │
  ├─────────────────────────────────────────┤
  │  1. Plot ITS (Current vs Time)          │
  │  2. Plot IVg (Transfer Curves)          │
  │  3. Plot Transconductance               │
  │  4. Settings (directories, chip group)  │
  │  5. Quit                                │
  └─────────────────────────────────────────┘

  Then for each plot type, a configuration screen with:
  - Chip selection (dropdown of available chips)
  - Selection mode (Auto / Interactive / Manual seq input)
  - Common filters (VG, wavelength, date)
  - Plot-specific options (collapsible/optional)
  - Preview/Generate buttons

  Does this match your vision? What would you change?


  I want:
  Navigation Flow: Wizard-style (step-by-step screens)
  Chip Selection: The TUI hould auto-discover available chips from the metadata/chip_histories directories
  Plot Options: Preset configurations (e.g., "Quick plot", "Custom plot") 
  Advanced Features:
  - Batch plotting: Select multiple chips/plot types and queue them?
  - Preview mode: Show what will be plotted before generating?
  - Recent/favorites: Quick access to recently used configurations?
  - Export configuration: Save settings for later reuse?
  After generating a plot, it should: Stay on the same screen for easy re-plotting
  target users are lab members familiar with the experiments but not all familiar with CLI
  I would like a separate script like python tui_app.py
  Your suggestion are good, what do you think about this vision?