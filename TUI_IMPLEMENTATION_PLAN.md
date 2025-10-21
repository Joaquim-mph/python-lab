# TUI Implementation Plan
**Experiment Plotting Assistant - Textual User Interface**

---

## Overview

Create a wizard-style TUI that allows lab members unfamiliar with CLI to easily generate plots from experimental data. The interface will guide users step-by-step through plot configuration and generation.

---

## Design Principles

1. **Wizard-style navigation**: Step-by-step screens, not overwhelming
2. **Consistent Tokyo Night theme**: Professional dark theme throughout
3. **User-friendly errors**: Return to config screen on failure with clear messages
4. **Smart defaults**: Quick plot mode for common use cases
5. **Lab-member focused**: Assumes knowledge of experiments, not CLI

---

## File Structure

```
src/tui/
├── __init__.py
├── app.py                       # Main PlotterApp class
├── config_manager.py            # Configuration save/load
├── utils.py                     # Chip discovery, validation
│
├── screens/
│   ├── __init__.py
│   ├── main_menu.py            # Step 1: Main menu
│   ├── plot_type_selector.py   # Step 2: ITS/IVg/Transconductance
│   ├── chip_selector.py        # Step 3: Auto-discovered chips
│   ├── config_mode_selector.py # Step 4: Quick/Custom
│   ├── its_config.py           # Step 5b: ITS custom config
│   ├── ivg_config.py           # Step 5b: IVg custom config
│   ├── transconductance_config.py  # Step 5b: Transconductance config
│   ├── preview_screen.py       # Step 6: Preview before plotting
│   ├── progress_screen.py      # Step 7: Plotting progress
│   ├── success_screen.py       # Step 7: Success with options
│   ├── recent_configs.py       # Recent configurations loader
│   ├── batch_mode.py           # Batch plotting queue
│   └── settings.py             # Settings/preferences
│
└── widgets/
    ├── __init__.py
    ├── config_form.py          # Reusable form fields
    └── chip_list.py            # Custom chip list widget

tui_app.py                       # Entry point: python tui_app.py
```

---

## Keyboard Shortcuts

### Global
- **Ctrl+Q**: Quit application (with confirmation)
- **Ctrl+H**: Help screen
- **Ctrl+P**: Access Textual command palette (theme switching)
- **Esc**: Cancel/Go back

### Navigation
- **Tab / Shift+Tab**: Navigate between fields
- **Enter**: Confirm/Next
- **Arrow keys**: Navigate lists/options
- **Space**: Toggle checkboxes/radio buttons

### Shortcuts per screen
- **Ctrl+N**: Next step (in wizard)
- **Ctrl+B**: Back to previous step
- **Ctrl+S**: Save configuration
- **Ctrl+R**: Refresh (chip discovery)

---

## Wizard Flow

### **Step 1: Main Menu**

```
┌──────────────────────────────────────────────────┐
│    🔬 Experiment Plotting Assistant              │
│    Alisson Lab - Device Characterization         │
├──────────────────────────────────────────────────┤
│                                                  │
│  → New Plot                        [Ctrl+N]     │
│    Recent Configurations (3)       [Ctrl+R]     │
│    Batch Mode                      [Ctrl+B]     │
│    Settings                        [Ctrl+,]     │
│    Help                            [Ctrl+H]     │
│    Quit                            [Ctrl+Q]     │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Class**: `MainMenuScreen`
**File**: `src/tui/screens/main_menu.py`

**Actions**:
- New Plot → Step 2 (Plot Type Selector)
- Recent → Load saved config → Step 6 (Preview)
- Batch → Batch Mode screen
- Settings → Settings screen
- Help → Help screen
- Quit → Exit with confirmation

---

### **Step 2: Plot Type Selection**

```
┌──────────────────────────────────────────────────┐
│  Select Plot Type                    [Step 1/6] │
├──────────────────────────────────────────────────┤
│                                                  │
│  ○ ITS (Current vs Time)                        │
│    Plot photocurrent time series with           │
│    light/dark cycles. Best for photoresponse.   │
│                                                  │
│  ○ IVg (Transfer Curves)                        │
│    Plot gate voltage sweep characteristics.     │
│    Shows device transfer behavior.              │
│                                                  │
│  ○ Transconductance                             │
│    Plot gm = dI/dVg from IVg data.              │
│    Derivative analysis of transfer curves.      │
│                                                  │
│  [Back] [Next]                                   │
└──────────────────────────────────────────────────┘
```

**Class**: `PlotTypeSelectorScreen`
**File**: `src/tui/screens/plot_type_selector.py`

**State saved**: `plot_type` (ITS/IVg/Transconductance)

**Actions**:
- Back → Step 1 (Main Menu)
- Next → Step 3 (Chip Selector)

---

### **Step 3: Chip Selection**

```
┌──────────────────────────────────────────────────┐
│  Select Chip                         [Step 2/6] │
├──────────────────────────────────────────────────┤
│  Auto-discovered chips:                          │
│                                                  │
│  ✓ Alisson67  (82 experiments)                  │
│    • 36 IVg, 46 ITS                             │
│    • Last: 2025-10-21                           │
│                                                  │
│    Alisson72  (156 experiments)                  │
│    • 64 IVg, 92 ITS                             │
│    • Last: 2025-10-20                           │
│                                                  │
│    Alisson81  (94 experiments)                   │
│    • 40 IVg, 54 ITS                             │
│    • Last: 2025-10-19                           │
│                                                  │
│  [Refresh] [Back] [Next]                         │
└──────────────────────────────────────────────────┘
```

**Class**: `ChipSelectorScreen`
**File**: `src/tui/screens/chip_selector.py`

**Auto-discovery logic** (`src/tui/utils.py`):
```python
def discover_chips(metadata_dir, raw_dir, history_dir):
    """
    Scan chip_histories/*.parquet and metadata/ directories.
    Returns list of ChipInfo objects with:
    - chip_number
    - chip_group
    - total_experiments
    - ivg_count, its_count
    - last_experiment_date
    """
```

**State saved**: `chip_number`, `chip_group`

**Actions**:
- Refresh → Re-scan directories
- Back → Step 2 (Plot Type)
- Next → Step 4 (Config Mode)

---

### **Step 4: Configuration Mode**

```
┌──────────────────────────────────────────────────┐
│  Configuration Mode - ITS Plot       [Step 3/6] │
├──────────────────────────────────────────────────┤
│                                                  │
│  ○ Quick Plot                                    │
│    Use smart defaults, just select experiments   │
│    interactively. Best for routine plotting.     │
│                                                  │
│  ○ Custom Plot                                   │
│    Configure all parameters: filters, baseline,  │
│    legend style, etc. For specialized analysis.  │
│                                                  │
│  [Back] [Next]                                   │
└──────────────────────────────────────────────────┘
```

**Class**: `ConfigModeSelectorScreen`
**File**: `src/tui/screens/config_mode_selector.py`

**State saved**: `mode` (quick/custom)

**Actions**:
- Back → Step 3 (Chip Selector)
- Next (Quick) → Experiment Selector (interactive_selector.py)
- Next (Custom) → Step 5 (Config Screen for plot type)

---

### **Step 5a: Quick Plot → Experiment Selection**

**Reuse existing**: `src/interactive_selector.py`

Launched with:
```python
seq_numbers = select_experiments_interactive(
    chip_number,
    chip_group,
    metadata_dir,
    raw_dir,
    proc_filter=plot_type,  # "ITS", "IVg", etc.
    title=f"Select {plot_type} Experiments - {chip_group}{chip_number}"
)
```

**State saved**: `seq_numbers`

**Actions**:
- Cancel → Step 4 (Config Mode)
- Confirm → Step 6 (Preview)

---

### **Step 5b: Custom Plot → Parameter Configuration**

**ITS Config Example**:

```
┌──────────────────────────────────────────────────┐
│  Custom Configuration - ITS          [Step 4/6] │
├──────────────────────────────────────────────────┤
│  Selection Mode:                                 │
│  ● Interactive  ○ Auto  ○ Manual                │
│                                                  │
│  ─── Filters (Optional) ───────────────────────  │
│  VG (V):         [_____]  Gate voltage filter    │
│  Wavelength (nm):[_____]  Laser wavelength       │
│  Date:           [_____]  YYYY-MM-DD format      │
│                                                  │
│  ─── Plot Options ──────────────────────────────  │
│  Legend by:      [led_voltage ▼]                │
│                  (led_voltage, wavelength, vg)   │
│  Baseline (s):   [60.0     ]  Baseline time      │
│  Padding:        [0.05     ]  Y-axis padding     │
│                                                  │
│  Output dir:     [figs/Alisson67/           ]    │
│                                                  │
│  [Save Config] [Back] [Next]                     │
└──────────────────────────────────────────────────┘
```

**Class**: `ITSConfigScreen`, `IVgConfigScreen`, `TransconductanceConfigScreen`
**Files**: `src/tui/screens/{its,ivg,transconductance}_config.py`

**Reusable widget**: `ConfigForm` in `src/tui/widgets/config_form.py`

**Configuration per plot type**:

#### ITS Parameters:
- Selection mode: interactive/auto/manual
- Filters: VG, wavelength, date
- Legend by: led_voltage, wavelength, vg
- Baseline (s): default 60.0
- Padding: default 0.05
- Output dir: default figs/{chip_group}{chip_number}/

#### IVg Parameters:
- Selection mode: interactive/auto/manual
- Filters: VDS, date
- Output dir: default figs/{chip_group}{chip_number}/

#### Transconductance Parameters:
- Selection mode: interactive/auto/manual
- Method: gradient, savgol
- Window length: default 9 (for savgol)
- Polyorder: default 3 (for savgol)
- Filters: VDS, date
- Output dir: default figs/{chip_group}{chip_number}/

**State saved**: All form values as dict

**Actions**:
- Back → Step 4 (Config Mode)
- Next → If Interactive: Launch selector → Step 6 (Preview)
- Next → If Auto/Manual: Step 6 (Preview)
- Save Config → Export to JSON

---

### **Step 6: Preview**

```
┌──────────────────────────────────────────────────┐
│  Preview - ITS Plot                  [Step 5/6] │
├──────────────────────────────────────────────────┤
│  Chip: Alisson67                                 │
│  Plot Type: ITS Overlay                          │
│                                                  │
│  ─── Experiments ────────────────────────────────│
│  Selected: 5 experiments                         │
│  Seq numbers: 4, 10, 15, 20, 25                 │
│                                                  │
│  ─── Configuration ──────────────────────────────│
│  • Selection mode: Interactive                   │
│  • Legend by: LED Voltage                        │
│  • Baseline time: 60.0 s                         │
│  • Y-axis padding: 5.0%                          │
│  • Filters: VG = -0.4 V                          │
│                                                  │
│  ─── Output ─────────────────────────────────────│
│  File: figs/Alisson67/                           │
│        chip67_ITS_overlay_4_10_15_20_25.png      │
│  Status: Ready to generate (file does not exist) │
│                                                  │
│  [Edit Config] [Generate Plot] [Save & Exit]     │
└──────────────────────────────────────────────────┘
```

**Class**: `PreviewScreen`
**File**: `src/tui/screens/preview_screen.py`

**Display**:
- All configuration parameters
- Expected output filename
- File existence check (warn if overwriting)
- Experiment count validation

**Actions**:
- Edit Config → Back to Step 5 (Config)
- Generate Plot → Step 7 (Progress/Results)
- Save & Exit → Save config and return to main menu

---

### **Step 7: Plot Generation & Results**

**During plotting**:

```
┌──────────────────────────────────────────────────┐
│  Generating Plot...                  [Step 6/6] │
├──────────────────────────────────────────────────┤
│                                                  │
│  ⣾ Loading experiment metadata...                │
│                                                  │
│  Progress: 40%                                   │
│  ████████████░░░░░░░░░░░░░░                      │
│                                                  │
│  Current: Reading measurement data (seq 15)      │
│                                                  │
└──────────────────────────────────────────────────┘
```

**On success**:

```
┌──────────────────────────────────────────────────┐
│  Plot Generated Successfully! ✓                  │
├──────────────────────────────────────────────────┤
│                                                  │
│  Output file:                                    │
│  figs/Alisson67/chip67_ITS_overlay_4_10_15...png│
│                                                  │
│  File size: 2.3 MB                               │
│  Experiments plotted: 5                          │
│  Generation time: 3.2s                           │
│                                                  │
│  Configuration saved to recent history.          │
│                                                  │
│  [Open File] [Plot Another] [Main Menu]          │
└──────────────────────────────────────────────────┘
```

**On error**:

```
┌──────────────────────────────────────────────────┐
│  Plot Generation Failed ✗                        │
├──────────────────────────────────────────────────┤
│                                                  │
│  Error Type: ValueError                          │
│                                                  │
│  Message:                                        │
│  No experiments remain after filtering.          │
│  VG=-0.4 V filter removed all 5 experiments.     │
│                                                  │
│  Suggestion:                                     │
│  Try adjusting or removing the VG filter.        │
│                                                  │
│  [View Details] [Edit Config] [Main Menu]        │
└──────────────────────────────────────────────────┘
```

**Class**: `ProgressScreen`, `SuccessScreen`, `ErrorScreen`
**File**: `src/tui/screens/progress_screen.py`

**Error handling**:
- Catch all exceptions from plotting functions
- Parse error type and message
- Provide user-friendly explanations
- Return to config screen for retry
- Log full traceback for debugging

**Actions**:
- Open File → Call system open command (varies by OS)
- Plot Another → Return to Step 2 (Plot Type) with same chip
- Edit Config → Return to Step 5 (Config)
- Main Menu → Return to Step 1

---

## Configuration Persistence

### Recent Configurations

**Storage**: `~/.lab_plotter_config.json`

```json
{
  "version": "1.0",
  "recent": [
    {
      "timestamp": "2025-10-21T14:30:00",
      "chip_number": 67,
      "chip_group": "Alisson",
      "plot_type": "ITS",
      "mode": "quick",
      "seq_numbers": [4, 10, 15, 20, 25],
      "output_file": "figs/Alisson67/chip67_ITS_overlay_4_10_15_20_25.png"
    },
    {
      "timestamp": "2025-10-21T12:15:00",
      "chip_number": 72,
      "chip_group": "Alisson",
      "plot_type": "IVg",
      "mode": "custom",
      "filters": {"vds": 0.1},
      "seq_numbers": [2, 8, 14],
      "output_file": "figs/Alisson72/Encap72_IVg_sequence_2_8_14.png"
    }
  ],
  "defaults": {
    "chip_group": "Alisson",
    "metadata_dir": "metadata",
    "raw_dir": ".",
    "history_dir": "chip_histories",
    "output_dir": "figs"
  },
  "preferences": {
    "theme": "tokyo-night",
    "max_recent": 10
  }
}
```

**Class**: `ConfigManager`
**File**: `src/tui/config_manager.py`

**Methods**:
```python
class ConfigManager:
    def load_recent() -> List[Dict]
    def save_config(config: Dict) -> None
    def load_defaults() -> Dict
    def update_defaults(defaults: Dict) -> None
    def export_config(config: Dict, filepath: Path) -> None
    def import_config(filepath: Path) -> Dict
```

---

## Batch Mode

```
┌──────────────────────────────────────────────────┐
│  Batch Mode - Plot Queue                         │
├──────────────────────────────────────────────────┤
│  Queue (3 plots):                                │
│                                                  │
│  1. ✓ Alisson67 - ITS Quick                     │
│     Status: Queued                               │
│                                                  │
│  2.   Alisson72 - IVg Custom (VDS=0.1)          │
│     Status: Queued                               │
│                                                  │
│  3.   Alisson67 - Transconductance Auto         │
│     Status: Queued                               │
│                                                  │
│  [Add Plot] [Remove] [Reorder] [Process Queue]   │
└──────────────────────────────────────────────────┘
```

**During batch processing**:

```
┌──────────────────────────────────────────────────┐
│  Batch Processing...                  [2/3]      │
├──────────────────────────────────────────────────┤
│  ✓ Alisson67 - ITS Quick (completed)            │
│  ⣾ Alisson72 - IVg Custom (processing...)        │
│    Alisson67 - Transconductance (pending)        │
│                                                  │
│  Overall progress: 33%                           │
│  ████████████░░░░░░░░░░░░░░░░░░░░░░░░            │
│                                                  │
│  [Pause] [Cancel]                                │
└──────────────────────────────────────────────────┘
```

**Class**: `BatchModeScreen`
**File**: `src/tui/screens/batch_mode.py`

---

## Settings Screen

```
┌──────────────────────────────────────────────────┐
│  Settings                                        │
├──────────────────────────────────────────────────┤
│  ─── Directories ────────────────────────────────│
│  Metadata:       [metadata/              ]       │
│  Raw data:       [./                     ]       │
│  Chip histories: [chip_histories/        ]       │
│  Output:         [figs/                  ]       │
│                                                  │
│  ─── Defaults ───────────────────────────────────│
│  Chip group:     [Alisson ▼]                     │
│  Theme:          [tokyo-night ▼]                 │
│                                                  │
│  ─── History ────────────────────────────────────│
│  Max recent configs: [10]                        │
│                                                  │
│  [Clear Recent] [Reset Defaults] [Save] [Cancel] │
└──────────────────────────────────────────────────┘
```

**Class**: `SettingsScreen`
**File**: `src/tui/screens/settings.py`

---

## Theme Consistency (Tokyo Night)

**Apply globally in `src/tui/app.py`**:

```python
class PlotterApp(App):
    """Main TUI application."""

    def on_mount(self) -> None:
        self.theme = "tokyo-night"
```

**Custom CSS for consistency**:

```python
CSS = """
/* Tokyo Night color palette */
/* Background: #1a1b26 */
/* Foreground: #c0caf5 */
/* Selection: #414868 */
/* Accent: #7aa2f7 */
/* Cyan: #7dcfff */
/* Green: #9ece6a */

.wizard-step {
    background: #1a1b26;
    color: #c0caf5;
}

.step-indicator {
    color: #7dcfff;
}

.success {
    color: #9ece6a;
}

.error {
    color: #f7768e;
}
```

---

## Error Handling Strategy

### Types of errors to handle:

1. **File not found**: Metadata, chip histories, raw data
   - Message: "Cannot find {file}. Check Settings."
   - Action: Offer to open Settings screen

2. **No experiments found**: After filtering
   - Message: "No experiments match filters. Try adjusting VG/wavelength/date."
   - Action: Return to config screen with filters highlighted

3. **Plot generation failed**: Exception in plotting code
   - Message: Show error type and suggestion
   - Action: Return to config screen, log full traceback

4. **Invalid input**: Bad voltage, date format, etc.
   - Message: Inline validation with red border
   - Action: Focus on invalid field

### Error screen template:

```python
class ErrorScreen(Screen):
    def __init__(self, error_type, message, suggestion, return_screen):
        self.error_type = error_type
        self.message = message
        self.suggestion = suggestion
        self.return_screen = return_screen

    def action_retry(self):
        self.app.pop_screen()  # Return to previous screen

    def action_main_menu(self):
        self.app.switch_screen(MainMenuScreen())
```

---

## Entry Point: `tui_app.py`

```python
#!/usr/bin/env python3
"""
TUI Application Entry Point

Launch the Experiment Plotting Assistant with:
    python tui_app.py
"""

from src.tui.app import PlotterApp

def main():
    app = PlotterApp()
    app.run()

if __name__ == "__main__":
    main()
```

---

## Implementation Phases

### **Phase 1: MVP (Core Wizard)**
**Goal**: Get basic wizard flow working end-to-end

1. ✅ Create directory structure
2. ✅ Create entry point `tui_app.py`
3. ✅ Create `PlotterApp` with Tokyo Night theme
4. ✅ Implement Main Menu screen
5. ✅ Implement Plot Type Selector
6. ✅ Implement chip auto-discovery
7. ✅ Implement Chip Selector
8. ✅ Implement Config Mode Selector (Quick only for MVP)
9. ✅ Integrate existing interactive selector
10. ✅ Implement Preview screen
11. ✅ Implement Progress/Success/Error screens
12. ✅ Test complete flow: Menu → ITS Quick Plot → Success

**Deliverable**: Working wizard that can generate quick ITS plots

---

### **Phase 2: Custom Configuration**
**Goal**: Add full parameter control

1. ✅ Create ConfigForm widget
2. ✅ Implement ITS Config screen
3. ✅ Implement IVg Config screen
4. ✅ Implement Transconductance Config screen
5. ✅ Add validation for all inputs
6. ✅ Test custom configuration for all plot types

**Deliverable**: Full parameter control for all plot types

---

### **Phase 3: Persistence**
**Goal**: Save and reuse configurations

1. ✅ Implement ConfigManager
2. ✅ Add recent configurations storage
3. ✅ Implement Recent Configs screen
4. ✅ Add config export/import
5. ✅ Test configuration persistence

**Deliverable**: Reusable configurations and history

---

### **Phase 4: Advanced Features**
**Goal**: Batch mode and settings

1. ✅ Implement Batch Mode screen
2. ✅ Implement batch queue management
3. ✅ Implement batch execution
4. ✅ Implement Settings screen
5. ✅ Test batch processing

**Deliverable**: Complete feature set

---

### **Phase 5: Polish**
**Goal**: Production-ready UX

1. ✅ Add help screens
2. ✅ Refine error messages
3. ✅ Add loading indicators
4. ✅ Comprehensive testing
5. ✅ Documentation

**Deliverable**: Production-ready TUI

---

## Testing Strategy

### Unit Tests (if needed)
- `test_config_manager.py`: Config save/load
- `test_utils.py`: Chip discovery
- `test_validation.py`: Input validation

### Integration Tests
- Complete workflow tests for each plot type
- Error handling tests
- Batch mode tests

### User Testing
- Lab members try the TUI
- Collect feedback on UX
- Iterate on confusing parts

---

## Success Criteria

- ✅ Lab member can generate ITS plot in < 1 minute without CLI knowledge
- ✅ All plot types (ITS, IVg, Transconductance) work correctly
- ✅ Error messages are clear and actionable
- ✅ Configuration can be saved and reused
- ✅ Batch plotting works for multiple chips
- ✅ Theme is consistent (Tokyo Night)
- ✅ No crashes on invalid input

---

## Future Enhancements (Optional)

1. **Plot preview**: Show thumbnail before generating full plot
2. **Data inspector**: View raw data in TUI before plotting
3. **Comparison mode**: Overlay plots from different chips
4. **Export reports**: Generate PDF/HTML reports with multiple plots
5. **Live plotting**: Real-time plot updates during data acquisition
6. **Web interface**: Complementary web UI for remote access

---

## Questions/Decisions Log

- **Q**: Should batch mode allow mixing plot types?
  **A**: Yes, queue can have ITS, IVg, Transconductance mixed

- **Q**: Should we validate file paths before plotting?
  **A**: Yes, check in Preview screen, warn if files missing

- **Q**: How to handle very long experiment lists in preview?
  **A**: Show first 10, then "... and 45 more"

- **Q**: Should config export include absolute or relative paths?
  **A**: Relative paths for portability

---

**End of Plan**

Ready to implement Phase 1!
