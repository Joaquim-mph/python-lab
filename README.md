# python-lab

Utilities for parsing and plotting IV/ITS measurement data from the lab.

## Repository structure

- `Alisson_04_sept/`, `Alisson_05_sept/`: Raw measurement CSV files.
- `src/parser.py`: Extracts metadata from the header of each measurement CSV and writes `<folder>_metadata.csv`.
- `src/utils.py`: Helper functions for reading measurements and standardizing column names.
- `src/plots.py`: Plotting helpers that use metadata to produce IVg sequences, pre/post comparisons, and ITS overlays.
- `src/styles.py`: Matplotlib style dictionaries for consistent figures.

## Requirements

Python 3.10+ with `polars`, `numpy`, and `matplotlib` installed.

## Usage

1. **Generate metadata from raw CSVs**

   Edit the `folder_name` variable near the end of `src/parser.py` to point at a directory of CSV files, then run:

   ```bash
   python src/parser.py
   ```

   A file named `<folder>_metadata.csv` will be created in the repository root.

2. **Plot sequences or overlays**

   The plotting utilities expect metadata generated as above.

   ```python
   from pathlib import Path
   from src.plots import load_and_prepare_metadata, plot_ivg_sequence

   meta = load_and_prepare_metadata('Alisson_04_sept_metadata.csv', chip=1)
   plot_ivg_sequence(meta, Path('Alisson_04_sept'), tag='demo')
   ```

   Figures are saved in the `figs/` directory.
