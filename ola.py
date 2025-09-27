import matplotlib as mpl
import matplotlib.pyplot as plt
import scienceplots
from src.styles import set_plot_style
from src.plots import *
from src.timeline import *
from src.utils import load_and_prepare_metadata
set_plot_style("prism_rain")
import polars as pl


METADATA_CSV = "metadata/Alisson_25_sept/metadata.csv"        # path to the table you pasted
BASE_DIR     = Path(".")             # where the raw CSVs live, e.g. "Alisson_04_sept/"
print_day_timeline(METADATA_CSV, Path("raw_data"), save_csv=False)