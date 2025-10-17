import matplotlib.pyplot as plt

# ============================================================================
# Common settings across all themes
# ============================================================================
COMMON_RC = {
    "text.usetex": False,
    "lines.markersize": 6,
    "legend.fontsize": 12,
    "axes.grid": False,
}

# ============================================================================
# Color Palettes
# ============================================================================
PRISM_RAIN_PALETTE = [
    # Primary vibrant colors (classic, high-contrast)
    "#e41a1c",  # red
    "#377eb8",  # blue
    "#4daf4a",  # green
    "#984ea3",  # purple
    "#ff7f00",  # orange

    # Extended vivid tones (brighter, neon-like accents)
    "#00bfc4",  # cyan-teal
    "#f781bf",  # pink
    "#ffd92f",  # bright yellow
    "#a65628",  # warm brown-orange
    "#8dd3c7",  # aqua-mint

    # Deep complementary accents (maintain contrast)
    "#b2182b",  # crimson
    "#2166ac",  # royal blue
    "#1a9850",  # rich green
    "#762a83",  # deep violet
    "#e08214",  # vivid amber
]

PRISM_RAIN_PALETTE_VIVID = [
    "#ff0054", "#0099ff", "#00cc66", "#cc33ff", "#ffaa00",
    "#00e6e6", "#ff66b2", "#ffe600", "#ff3300", "#00b3b3",
    "#3366ff", "#66ff33", "#9933ff", "#ff9933", "#33ccff",
]

# ============================================================================
# Theme Definitions
# ============================================================================
THEMES = {
    "prism_rain": {
        "base": ["science"],
        "rc": {
            **COMMON_RC,
            
            # Background colors
            "figure.facecolor": "#ffffff",
            "axes.facecolor": "#ffffff",
            "savefig.facecolor": "#ffffff",
            
            # Typography - FIXED SIZES FOR BETTER BALANCE
            #"font.family": "serif",  # ← FIXED (was "serif")
            "font.sans-serif": ["Source Sans Pro Black", "Source Sans 3"],
            "font.size": 35,              # ← REDUCED from 35
            
            "axes.labelsize": 55,         # ← REDUCED from 55 (axis labels)
            "axes.titlesize": 55,         # ← REDUCED from 55 (title)
            "axes.labelweight": "normal",
            
            # Axes and ticks
            "axes.edgecolor": "#222222",
            "axes.labelcolor": "#222222",
            "axes.linewidth": 3.5,        # ← REDUCED from 3.5
            
            "xtick.color": "#333333",
            "ytick.color": "#333333",
            "xtick.major.size": 10.0,      # ← REDUCED from 10.0
            "ytick.major.size": 10.0,      # ← REDUCED from 10.0
            "xtick.major.width": 2,
            "ytick.major.width": 2,
            "xtick.labelsize": 55,        # ← REDUCED from 55 (tick numbers!)
            "ytick.labelsize": 55,        # ← REDUCED from 55 (tick numbers!)
            "xtick.major.pad": 20,        # ← REDUCED from 20
            "ytick.major.pad": 20,        # ← REDUCED from 20
            
            # Grid
            "grid.color": "#cccccc",
            "grid.linestyle": "--",
            "grid.linewidth": 0.4,
            "grid.alpha": 0.6,
            
            # Lines and markers
            "lines.linewidth": 6,         # ← REDUCED from 6
            "lines.markersize": 22,       # ← REDUCED from 22
            "lines.antialiased": True,
            
            # Legend
            "legend.frameon": False,
            "legend.fontsize": 35,        # ← REDUCED from 35
            "legend.loc": "best",
            "legend.fancybox": True,
            
            # Figure size (optimized for papers)
            "figure.figsize": (20, 20),
            "figure.dpi": 100,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.1,
            
            # Color cycle
            "axes.prop_cycle": plt.cycler(color=PRISM_RAIN_PALETTE),
        }
    },
}

# ============================================================================
# Helper function to apply theme
# ============================================================================
def set_plot_style(theme_name="prism_rain"):
    """Apply a publication-ready matplotlib theme.
    
    Parameters
    ----------
    theme_name : str, default="prism_rain"
        Name of the theme to apply
        
    Example
    -------
    >>> set_plot_style("prism_rain")
    >>> plt.plot([1, 2, 3], [1, 4, 9])
    >>> plt.show()
    """
    if theme_name not in THEMES:
        raise ValueError(f"Theme '{theme_name}' not found. Available: {list(THEMES.keys())}")
    
    theme = THEMES[theme_name]
    
    # Apply base styles if specified
    if "base" in theme:
        for base_style in theme["base"]:
            try:
                plt.style.use(base_style)
            except OSError:
                print(f"Warning: Base style '{base_style}' not found, skipping...")
    
    # Apply custom rc parameters
    plt.rcParams.update(theme["rc"])
    print(f"✓ Applied '{theme_name}' theme")