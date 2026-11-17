"""Shared publication-grade plotting and European number formatting utilities
for Operation Viscount regional demographic studies.
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


def apply_viscount_style (arg0_ax=None):
  """Resets to default Matplotlib styling (DejaVu Sans, 4-sided boxed spines) and optional subtle grid."""
  #Reset global rcParams strictly to Matplotlib defaults
  mpl.rcdefaults()
  plt.style.use("default")
  mpl.rcParams["savefig.dpi"] = 300

  if arg0_ax is not None:
    for spine_name in ("top", "right", "bottom", "left"):
      if spine_name in arg0_ax.spines:
        arg0_ax.spines[spine_name].set_visible(True)
    arg0_ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.35)


def euro_tick_formatter (arg0_digits=2):
  """Returns a Matplotlib FuncFormatter formatting fractional axis ticks with European decimal commas."""
  digits = int(arg0_digits)

  #Return statement
  return mticker.FuncFormatter(lambda arg0_x, arg1_pos: format_euro_number(arg0_x, digits))


def format_euro_number (arg0_value, arg1_digits=2):
  """Formats numeric values using EN-GB European decimal commas (e.g. `58,88`)."""
  digits = int(arg1_digits)
  val = float(arg0_value)
  formatted = f"{val:,.{digits}f}"
  formatted = formatted.replace(",", "__THOUS__").replace(".", ",").replace("__THOUS__", ".")
  if "," in formatted:
    formatted = formatted.rstrip("0").rstrip(",")

  #Return statement
  return formatted


def format_mathtext_euro (arg0_value, arg1_digits=2):
  """Formats a numeric value with `{,}` European decimal comma for zero-space Matplotlib `$...$` MathText."""
  euro_str = format_euro_number(arg0_value, arg1_digits)

  #Return statement
  return euro_str.replace(",", "{,}")


def format_semantic_population (arg0_value):
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

  #Return statement
  return f"{int(round(val)):,}".replace(",", ".")


def save_viscount_figure (arg0_fig, arg1_output_path, arg2_dpi=300):
  """Saves a Matplotlib figure cleanly at print resolution without clipping labels."""
  arg0_fig.savefig(arg1_output_path, dpi=int(arg2_dpi), bbox_inches="tight", facecolor="white")
  plt.close(arg0_fig)
