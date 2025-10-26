# TUI Guide - Experiment Plotting Assistant

## Overview

The **Experiment Plotting Assistant** is a Terminal User Interface (TUI) built with [Textual](https://textual.textualize.io/) that provides a wizard-style interface for generating plots from experimental data. It's designed for lab members who prefer a guided interface over command-line tools.

**Key Features:**
- 🎨 Beautiful Tokyo Night theme with visual focus indicators
- 🧭 Step-by-step wizard flow
- ⌨️ Full keyboard navigation (arrows, tab, enter, escape)
- 🔄 Live progress tracking for plot generation
- 📊 Interactive experiment selection
- 🎯 Quick workflow for generating multiple plots of the same type

## Quick Start

### Launch the TUI

```bash
python tui_app.py
```

### Basic Workflow

1. **Main Menu** → Select "New Plot" or "Recent Configurations"
2. **Select Chip** → Choose from auto-discovered chips
3. **Select Plot Type** → ITS, IVg, or Transconductance
4. **Choose Mode** → Quick (defaults) or Custom (full config)
5. **Configure** → Select experiments or customize parameters
6. **Preview** → Review all settings before generating
7. **Generate Plot** → Watch progress in real-time
8. **Success Screen** → View results, plot another, or return to menu

**New!** Load saved configurations from "Recent Configurations" to skip steps 2-5.

## Keyboard Navigation

### Universal Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+Q` | Quit application (works anywhere) |
| `Escape` | Go back / Cancel current screen |
| `Enter` | Confirm / Activate focused button |
| `Tab` | Move focus forward |
| `Shift+Tab` | Move focus backward |

### Arrow Key Navigation

**All screens with buttons support arrow keys:**
- `↑` / `↓` : Navigate between buttons vertically
- `←` / `→` : Navigate between buttons horizontally
- Focus changes are indicated by:
  - Color change (background → primary theme color)
  - Bold text
  - Accent border
  - Arrow indicator (→) before button label

### Screen-Specific Keys

**Main Menu:**
- `N` : New Plot
- `P` : Process New Data
- `Q` : Quit

**Experiment Selector:**
- `Space` : Toggle experiment selection
- `A` : Select all
- `C` : Clear all selections
- `↑` / `↓` : Navigate experiment list
- `Enter` : Confirm selection
- `Escape` : Cancel and go back

## Wizard Flow (Step by Step)

### Step 1: Main Menu

**Screen:** MainMenuScreen
**Purpose:** Entry point with main actions

**Options:**
- **New Plot** - Start the plotting wizard
- **Process New Data** - Generate metadata from raw CSV files
- **Recent Configurations** - Load previously saved plot configurations
- **Batch Mode** - (Coming soon)
- **Settings** - (Coming soon)
- **Help** - Show keyboard shortcuts
- **Quit** - Exit application

### Step 1b: Recent Configurations (Optional Shortcut)

**Screen:** RecentConfigsScreen
**Purpose:** Load and reuse previously saved plot configurations

**Features:**
- View all saved configurations in sortable table (Date, Time, Description, Type)
- Load config to skip wizard steps 2-5 (goes directly to Preview)
- Export individual configs as JSON files
- Import configs from JSON files
- Delete unwanted configurations
- Statistics showing total configs and breakdown by plot type

**Navigation:**
- Arrow keys to navigate table
- Enter to load selected configuration
- Delete key to remove configuration
- Buttons for Export/Import/Delete/Back

**Storage:**
- Configurations saved to `~/.lab_plotter_configs.json`
- Maximum 20 recent configs (oldest auto-deleted)
- Auto-generated descriptions (e.g., "Alisson67 - ITS (Vg=3V, λ=455nm)")

### Step 2: Chip Selection

**Screen:** ChipSelectorScreen
**Purpose:** Auto-discover and select a chip from available data

**Features:**
- Auto-discovery from metadata files
- Shows chip numbers found in data
- Displays experiment counts per chip
- Custom chip entry option (coming soon)

**Navigation:**
- Arrow keys to select chip
- Enter to confirm
- Escape to go back to main menu

### Step 3: Plot Type Selection

**Screen:** PlotTypeSelectorScreen
**Purpose:** Choose the type of plot to generate

**Options:**
- **ITS** - Time series measurements (I vs time)
  - Shows photoresponse over time
  - Includes light ON/OFF shading
  - Delta plots (ΔI from baseline)

- **IVg** - Gate voltage sweeps (I vs Vg)
  - Transfer characteristics
  - Shows device response to gate voltage

- **Transconductance** - Derivative analysis (dI/dVg)
  - Two methods: gradient or Savitzky-Golay
  - Shows device gain characteristics

### Step 4: Configuration Mode Selection

**Screen:** ConfigModeSelectorScreen
**Purpose:** Choose between Quick (smart defaults) or Custom (full control) configuration

**Options:**

**Quick Plot:**
- Use smart defaults for all parameters
- Goes directly to experiment selector
- Best for routine plotting
- Minimal configuration needed

**Custom Plot:**
- Configure all parameters manually
- Access to advanced options
- Plot-type specific settings
- For specialized analysis

**Navigation:**
- Arrow keys / Space to toggle selection
- Enter to confirm and proceed

### Step 5a: Experiment Selection (Quick Mode)

**Screen:** ExperimentSelectorScreen
**Purpose:** Interactively select which experiments to include

**Features:**
- **Multi-select interface** - Uses rich DataTable
- **Chronological listing** - Experiments in time order
- **Visual feedback** - Selected rows highlighted
- **Batch operations** - Select all / Clear all
- **Metadata display** - Shows date, time, seq, proc, VG, wavelength, etc.

**Selection Tips:**
- Select experiments from the same or different days
- Use `seq` column for cross-day analysis
- Check VG/wavelength columns to group related measurements
- Selected count shown in footer

**Columns Displayed:**
- `seq` - Sequential experiment number (unique across all days)
- `date` - Measurement date
- `time` - Start time
- `proc` - Procedure type (ITS, IVg, etc.)
- `VG` - Gate voltage
- `λ` - Laser wavelength (if applicable)
- `file` - Source filename

### Step 5b: Custom Configuration (Custom Mode)

**Screens:** `ITSConfigScreen` / `IVgConfigScreen` / `TransconductanceConfigScreen`
**Purpose:** Detailed parameter configuration for each plot type

#### ITS Custom Configuration

**Parameters:**
- **Legend By:** Group traces by (led_voltage, wavelength, vg)
- **Baseline Correction** (checkbox + input):
  - **Unchecked** → Raw data mode (`baseline_mode="none"`)
    - No baseline correction applied
    - Plots CSV data exactly as recorded
    - Filename gets `_raw` suffix (e.g., `encap67_ITS_52_raw.png`)
    - Best for: Noise analysis, drift studies, comparing raw vs corrected
  - **Checked + Empty** → Auto baseline (`baseline_mode="auto"`)
    - Calculates baseline from LED ON+OFF period metadata
    - Smart baseline = (period) / 2
    - Best for: Consistent photoresponse measurements
  - **Checked + "0"** → Baseline at t=0 (`baseline_t=0.0`)
    - Subtracts first visible point (at `plot_start_time`)
    - Each trace starts at y≈0
    - Avoids CSV artifacts in first ~1 second
    - Best for: Comparative drift analysis
  - **Checked + number** → Fixed baseline (`baseline_t=60.0`)
    - Standard interpolation at specific time
    - Traditional method
    - Best for: Consistent baseline across measurements
- **Y-axis Padding:** Extra space above/below data (0-1, default: 0.05)
- **Output Directory:** Where to save the plot (default: figs)

**Validation:**
- Baseline must be ≥ 0 (0 is valid!)
- Padding must be 0-1
- Output directory created automatically if needed

**Note:** Filters (VG, wavelength, date) have been removed - use Ctrl+F in the Experiment Selector for filtering

#### IVg Custom Configuration

**Parameters:**
- **Selection Mode:** Interactive / Auto / Manual
- **VDS Filter:** Only experiments with specific drain-source voltage
- **Date Filter:** Only experiments from specific date
- **Output Directory:** Where to save the plot

**Validation:**
- Date must be YYYY-MM-DD format
- Manual mode requires at least one seq number

#### Transconductance Custom Configuration

**Parameters:**
- **Method:**
  - Gradient: Standard numpy gradient (fast, simple)
  - Savgol: Savitzky-Golay filtering (smooth, reduces noise)
- **Savgol Parameters** (only if method = savgol):
  - Window Length: Points in smoothing window (must be odd, ≥3)
  - Polynomial Order: Polynomial degree (must be < window_length, ≥1)
  - Min Segment Length: Minimum points in voltage sweep segment (≥1)
- **Selection Mode:** Interactive / Auto / Manual
- **VDS Filter:** Only experiments with specific drain-source voltage
- **Date Filter:** Only experiments from specific date
- **Output Directory:** Where to save the plot

**Validation:**
- Window length must be odd and ≥3
- Polynomial order must be < window_length and ≥1
- Min segment length must be ≥1
- Date must be YYYY-MM-DD format
- Manual mode requires at least one seq number

**Navigation (All Custom Config Screens):**
- Tab / Shift+Tab to move between fields
- Arrow keys for button navigation
- Enter to proceed to next screen
- Escape to go back
- All validations show user-friendly error messages

### Step 6: Preview & Configuration

**Screen:** PreviewScreen
**Purpose:** Review configuration before generating plot

**Shows:**
- **Experiments:** Count and seq numbers
- **Configuration:**
  - Plot mode (Quick/Custom)
  - Legend style (for ITS: by voltage/wavelength/VG)
  - Baseline time (for ITS)
  - Y-axis padding
  - Filters applied
  - Method (for transconductance: gradient/savgol)
- **Output:** Directory and filename
- **Warning:** If file will be overwritten

**Buttons:**
- **← Edit Config** - Go back to change settings
- **Generate Plot** - Proceed with plot generation (default focus)
- **Save & Exit** - Save config for later (coming soon)

**Focus Navigation:**
- Arrow keys move between buttons
- Focused button highlighted with primary color + arrow (→)
- All buttons start with neutral color

### Step 7: Plot Generation

**Screen:** PlotGenerationScreen
**Purpose:** Show real-time progress during plot creation

**Progress Stages:**
1. **Initializing** (0%) - Starting background thread
2. **Loading metadata** (10%) - Reading experiment data
3. **Loaded N experiments** (30%) - Metadata ready
4. **Generating plot** (50%) - Running plotting function
5. **Saving file** (90%) - Writing output
6. **Complete** (100%) - Finished!

**Features:**
- Progress bar with percentage
- Status messages for each stage
- Animated spinner (⣾) during work
- Non-blocking UI (can cancel with Escape)

**Technical Details:**
- Runs plotting in background thread (daemon)
- Uses `matplotlib.use('Agg')` for headless plotting
- Thread-safe progress updates via `app.call_from_thread()`
- Automatic error handling with detailed messages

### Step 8: Success/Error Screens

**Success Screen (PlotSuccessScreen):**

**Shows:**
- ✓ Success message
- Output file path
- File size (MB)
- Number of experiments plotted
- Generation time (seconds)

**Actions Performed Automatically:**
- **Configuration saved** to `~/.lab_plotter_configs.json`
- Auto-generated description added
- Accessible from "Recent Configurations" in main menu

**Buttons:**
- **Open File** - Open plot in default viewer (coming soon)
- **Plot Another** - Return to experiment selection with same chip/type
- **Main Menu** - Start over from main menu

**Error Screen (PlotErrorScreen):**

**Shows:**
- ✗ Error type (ValueError, FileNotFoundError, etc.)
- Error message
- Helpful suggestions based on error type
- Option to view full traceback

**Buttons:**
- **View Details** - Show full error traceback
- **Edit Config** - Go back to preview screen
- **Main Menu** - Return to main menu

## Advanced Features

### Configuration Persistence

**Automatic Saving:**
- Every successful plot automatically saves its configuration
- Stored in `~/.lab_plotter_configs.json`
- Maximum 20 recent configs (oldest auto-deleted)
- Auto-generated descriptions (e.g., "Alisson67 - ITS (Vg=3V, λ=455nm)")

**Loading Saved Configs:**
1. Main Menu → "Recent Configurations"
2. Browse table of saved configs (sorted by date/time)
3. Select and press Enter
4. Skips directly to Preview screen
5. Modify if needed or generate immediately

**Export/Import:**
- **Export:** Save single config to JSON file (`plot_config_YYYYMMDD_HHMMSS.json`)
- **Import:** Load config from JSON file
- Share configs between users or backup important settings

**Searching:**
- Stats show total configs and breakdown by plot type
- Search by chip number, plot type, or parameters (via ConfigManager API)

### "Plot Another" Quick Workflow

After successfully generating a plot, use **"Plot Another"** to:
1. Automatically return to experiment selection
2. Keep the same chip number and plot type
3. Select different experiments
4. Generate another plot immediately

**Use case:** Quickly generate multiple ITS plots for the same chip with different VG values or wavelengths.

**Example workflow:**
```
1. Generate ITS plot for Chip 67 @ VG=-2V
2. Click "Plot Another"
3. Immediately shown experiment selector for Chip 67 ITS
4. Select experiments @ VG=-3V
5. Generate plot
6. Repeat!
```

### Process New Data

**Screen:** ProcessConfirmationScreen
**Purpose:** Generate metadata from raw CSV files

**What it does:**
- Runs `python process_and_analyze.py full-pipeline`
- Parses all CSV files in `raw_data/`
- Extracts metadata from headers
- Generates `metadata.csv` files
- Shows progress notification
- Runs in background (can continue using TUI)

**When to use:**
- After adding new raw data files
- Before first-time use
- After data collection sessions

## Configuration

### Default Paths

Set in `tui_app.py`:

```python
metadata_dir = Path("metadata")      # Metadata CSV location
raw_dir = Path(".")                  # Raw data root directory
history_dir = Path("chip_histories") # Chip history cache (unused currently)
output_dir = Path("figs")            # Plot output directory
chip_group = "Alisson"               # Default chip group prefix
```

### Plot Configuration

**ITS Plots:**
- `legend_by` - "led_voltage" (default), "wavelength", or "vg"
- `baseline` - Time in seconds for ΔI baseline (default: 60s)
- `padding` - Y-axis padding percentage (default: 0.05 = 5%)

**IVg Plots:**
- Minimal configuration needed
- Auto-detects light vs dark measurements

**Transconductance Plots:**
- `method` - "gradient" (default) or "savgol"
- `window_length` - Savitzky-Golay window (default: 9, must be odd)
- `polyorder` - Polynomial order (default: 3)

### Theme

The TUI uses the **Tokyo Night** theme:
- Dark background with vibrant accents
- Primary color: Bright blue (#7aa2f7)
- Accent color: Purple/magenta (#bb9af7)
- Success: Green, Warning: Yellow, Error: Red
- Focus indicators: Primary color with accent border

**Customization:**
Modify theme in `src/tui/app.py`:
```python
self.theme = "tokyo-night"  # Change to "textual-dark", "textual-light", etc.
```

## File Structure

### TUI Source Code

```
src/tui/
├── app.py                      # Main PlotterApp class
└── screens/
    ├── main_menu.py            # Main menu
    ├── chip_selector.py        # Chip selection
    ├── plot_type_selector.py   # Plot type selection
    ├── experiment_selector.py  # Interactive experiment picker
    ├── preview_screen.py       # Configuration preview
    ├── plot_generation.py      # Progress + success/error screens
    └── process_confirmation.py # Metadata generation dialog
```

### Entry Point

- `tui_app.py` - Launch script

### Related Modules

- `src/interactive_selector.py` - Base experiment selector widget
- `src/plotting/` - All plotting functions (its.py, ivg.py, transconductance.py)
- `src/core/` - Data utilities (timeline, utils)

## Technical Details

### Textual Framework

**Version:** 0.60.0
**Docs:** https://textual.textualize.io/

**Key concepts:**
- **App** - Main application class (PlotterApp)
- **Screen** - Full-screen view (MainMenuScreen, etc.)
- **Widget** - UI components (Button, Static, ProgressBar, etc.)
- **Container** - Layout containers (Vertical, Horizontal)
- **CSS** - Styling (scoped per screen)
- **Bindings** - Keyboard shortcuts
- **Reactive** - Auto-updating properties

### Background Threading

**Why needed:** Plotting can take several seconds; we need non-blocking UI.

**Implementation:**
```python
# In PlotGenerationScreen
def on_mount(self):
    thread = threading.Thread(target=self._generate_plot, daemon=True)
    thread.start()  # Returns immediately

def _generate_plot(self):
    # This runs in background thread
    # Cannot directly update UI!

    # Use call_from_thread to update UI safely:
    self.app.call_from_thread(self._update_progress, 50, "Generating...")
```

**Critical rules:**
1. Use `daemon=True` so thread dies with app
2. Never update UI from background thread directly
3. Use `app.call_from_thread()` to post messages to main thread
4. Handle exceptions in thread (won't crash app)

### Focus Management

**How focus works:**
1. Widgets with `can_focus=True` can receive focus (buttons default True)
2. Focus moves with Tab, Shift+Tab, or custom arrow keys
3. Focused widget receives keyboard events first
4. CSS `:focus` pseudo-class applies styles

**Custom arrow navigation:**
```python
def on_key(self, event: events.Key) -> None:
    buttons = [self.query_one("#btn1"), self.query_one("#btn2")]

    # Find focused button
    focused_idx = next((i for i, b in enumerate(buttons) if b.has_focus), None)

    if event.key in ("left", "up"):
        new_idx = (focused_idx - 1) % len(buttons)
        buttons[new_idx].focus()
        event.prevent_default()  # Don't propagate event
```

**Visual focus indicators:**
```css
.nav-button:focus {
    background: $primary;
    border: tall $accent;
    color: $primary-background;
    text-style: bold;
}
```

**Dynamic labels:**
```python
def on_button_focus(self, event: Button.Focus) -> None:
    # Remove arrows from all buttons
    for button in self.query(".nav-button"):
        if button.label.startswith("→ "):
            button.label = button.label[2:]

    # Add arrow to focused button
    if not event.button.label.startswith("→ "):
        event.button.label = f"→ {event.button.label}"
```

### Screen Navigation

**Stack-based:**
```python
# Main app starts with base screen (index 0)
# on_mount() pushes MainMenuScreen (index 1)

self.app.push_screen(ChipSelectorScreen(...))    # Add to stack
self.app.pop_screen()                            # Remove from stack

# Return to main menu:
while len(self.app.screen_stack) > 2:
    self.app.pop_screen()
# Keeps base (0) + MainMenuScreen (1)
```

**Callbacks:**
```python
self.app.push_screen(selector, callback=self._on_selection)

def _on_selection(self, result):
    if result:  # User confirmed
        # Process result
    else:  # User cancelled
        # Handle cancellation
```

### State Management

**Global config dictionary:**
```python
# In PlotterApp
self.plot_config = {
    "metadata_dir": metadata_dir,
    "raw_dir": raw_dir,
    "chip_group": chip_group,
    # ... updated as wizard progresses
}

# Screens access via:
self.app.plot_config
self.app.update_config(chip_number=67, plot_type="ITS")
self.app.reset_config()  # Clear for new plot
```

**Passing data between screens:**
```python
# Option 1: Constructor parameters
self.app.push_screen(PreviewScreen(
    chip_number=self.chip_number,
    plot_type=self.plot_type,
    seq_numbers=self.seq_numbers,
    config=self.app.plot_config.copy()
))

# Option 2: Update global config
self.app.update_config(seq_numbers=[52, 57, 58])
# Next screen reads from self.app.plot_config
```

## Troubleshooting

### Common Issues

**TUI doesn't start:**
```bash
# Check Python version (3.10+ required)
python --version

# Install/update dependencies
pip install -r requirements.txt
```

**Arrow keys don't work in preview screen:**
- Ensure you're using the latest version (after 2025-10-21 updates)
- Check that `on_key()` handler is defined in PreviewScreen

**Plot generation freezes at 0%:**
- Fixed in latest version (was `self.call_from_thread` → `self.app.call_from_thread`)
- Update to latest code

**Buttons don't change color on focus:**
- CSS `:focus` styles must be defined
- Check that buttons have `classes="nav-button"` or similar
- Verify theme is loaded (`self.theme = "tokyo-night"`)

**Can't return to main menu from success screen:**
- Fixed in latest version (changed `screen_stack > 1` → `screen_stack > 2`)
- Main menu is at stack position 1, base screen at 0

**"Plot Another" goes to main menu instead of experiment selector:**
- Update to latest version (after 2025-10-21)
- Ensures chip_number/chip_group/plot_type are passed to success screen

### Debug Mode

Add debug logging to any screen:
```python
def on_mount(self):
    self.app.notify(f"Debug: Config = {self.app.plot_config}")
```

Check screen stack:
```python
self.app.notify(f"Stack size: {len(self.app.screen_stack)}")
```

### Performance Tips

1. **Metadata loading** - Cache chip histories to avoid re-scanning
2. **Plot generation** - Already runs in background, no optimization needed
3. **Experiment selector** - For 1000+ experiments, consider pagination

## Future Enhancements

### Planned Features (Future Phases)

- **Recent Configurations** - Save/load plot configurations
- **Batch Mode** - Generate multiple plots at once
- **Settings Screen** - Configure paths, theme, defaults
- **Help Screen** - In-app documentation
- **Open File** - Launch plots in external viewer
- **Custom Chip Entry** - Manual chip number input
- **Filter UI** - Visual filter builder for experiments
- **Custom Config** - Advanced parameter tuning

### Potential Improvements

- **Search/filter** in experiment selector
- **Preview plot** before full generation
- **Progress estimation** (time remaining)
- **Cancellation** of running plot generation
- **Export config** to JSON for CLI use
- **Keyboard shortcuts** shown in footer per screen
- **Tooltips** on hover (mouse support)
- **Dark/light theme toggle**

## Contributing

### Adding a New Screen

1. **Create screen file:** `src/tui/screens/my_screen.py`

```python
from textual.screen import Screen
from textual.widgets import Header, Footer, Button
from textual.binding import Binding

class MyScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    CSS = """
    MyScreen {
        align: center middle;
    }
    """

    def compose(self):
        yield Header()
        yield Button("Click me", id="my-button")
        yield Footer()

    def on_button_pressed(self, event):
        self.app.notify("Button clicked!")

    def action_back(self):
        self.app.pop_screen()
```

2. **Add navigation:** From another screen:
```python
from src.tui.screens.my_screen import MyScreen

def action_open_my_screen(self):
    self.app.push_screen(MyScreen())
```

### Focus Styling Pattern

**Standard button focus CSS:**
```css
.my-button {
    width: 100%;
}

.my-button:focus {
    background: $primary;
    border: tall $accent;
    color: $primary-background;
    text-style: bold;
}
```

**Arrow indicator on focus:**
```python
def on_button_focus(self, event: Button.Focus) -> None:
    # Clear all arrows
    for btn in self.query(".my-button"):
        if btn.label.startswith("→ "):
            btn.label = btn.label[2:]

    # Add arrow to focused
    if not event.button.label.startswith("→ "):
        event.button.label = f"→ {event.button.label}"
```

### Arrow Key Navigation Pattern

```python
from textual import events

def on_key(self, event: events.Key) -> None:
    buttons = [
        self.query_one("#btn1", Button),
        self.query_one("#btn2", Button),
        self.query_one("#btn3", Button),
    ]

    focused_idx = next((i for i, b in enumerate(buttons) if b.has_focus), None)

    if focused_idx is not None:
        if event.key in ("left", "up"):
            new_idx = (focused_idx - 1) % len(buttons)
            buttons[new_idx].focus()
            event.prevent_default()
        elif event.key in ("right", "down"):
            new_idx = (focused_idx + 1) % len(buttons)
            buttons[new_idx].focus()
            event.prevent_default()
```

## License

This TUI is part of the Alisson Lab measurement analysis toolkit.

## Contact

For issues, questions, or suggestions:
- Create an issue in the repository
- Contact lab maintainers

---

**Version:** 1.0.0 (2025-10-21)
**Textual Version:** 0.60.0
**Python Version:** 3.10+
