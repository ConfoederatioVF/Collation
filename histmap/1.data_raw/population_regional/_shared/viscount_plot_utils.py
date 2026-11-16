"""Shared publication-grade plotting and European number formatting utilities
for Operation Viscount regional demographic studies.
"""

import matplotlib as mpl
import matplotlib.pyplot as plt


def apply_viscount_style():
  """Applies consistent serif academic typography and readable label sizing."""
  mpl.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.titlesize": 14,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
  })


def format_euro_number(arg0_value, arg1_digits=2):
  """Formats numeric values using EN-GB European decimal commas (e.g. `58,88`)."""
  val = float(arg0_value)
  formatted = f"{val:,.{int(arg1_digits)}f}"
  formatted = formatted.replace(",", "__THOUS__").replace(".", ",").replace("__THOUS__", ".")
  if "," in formatted:
    formatted = formatted.rstrip("0").rstrip(",")
  return formatted


def format_semantic_population(arg0_value):
  """Formats population magnitudes with semantic suffixes (`k`, `M`, `B`, `T`)."""
  val = float(arg0_value)
  abs_val = abs(val)
  if abs_val >= 1e12:
    return f"{format_euro_number(val / 1e12, 2)}T"
  if abs_val >= 1e9:
    return f"{format_euro_number(val / 1e9, 2)}B"
  if abs_val >= 1e6:
    return f"{format_euro_number(val / 1e6, 2)}M"
  if abs_val >= 1e3:
    return f"{format_euro_number(val / 1e3, 1)}k"
  return f"{int(round(val)):,}".replace(",", ".")


def save_viscount_figure(arg0_fig, arg1_output_path, arg2_dpi=300):
  """Saves a Matplotlib figure cleanly at print resolution without clipping labels."""
  arg0_fig.savefig(arg1_output_path, dpi=int(arg2_dpi), bbox_inches="tight", facecolor="white")
  plt.close(arg0_fig)
