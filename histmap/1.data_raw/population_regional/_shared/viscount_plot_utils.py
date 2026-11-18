"""Shared publication-grade plotting, Equal-Area bounds padding, bbox callout
placement, layout verification and European number formatting utilities for
Operation Viscount regional demographic studies.
"""

import math
import os

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.transforms import Bbox


def apply_human_colorbar_ticks (arg0_cbar, arg1_semantic=False, arg2_digits=2):
  """Applies plain European/semantic ticks to a LogNorm colorbar and clears minor scientific notation."""
  if arg0_cbar is None:
    return
  vmin = float(arg0_cbar.vmin) if hasattr(arg0_cbar, "vmin") and arg0_cbar.vmin is not None else 1e-4
  vmax = float(arg0_cbar.vmax) if hasattr(arg0_cbar, "vmax") and arg0_cbar.vmax is not None else 1e3
  fmt = euro_log_formatter(bool(arg1_semantic), int(arg2_digits))
  decades = [10.0 ** e for e in range(-6, 10) if vmin * 0.92 <= (10.0 ** e) <= vmax * 1.08]
  if len(decades) < 3:
    cands = []
    for e in range(-6, 10):
      for m in (1.0, 2.0, 5.0):
        t = m * (10.0 ** e)
        if vmin * 0.92 <= t <= vmax * 1.08:
          cands.append(t)
    if len(cands) >= 2:
      decades = cands
  if len(decades) >= 2:
    arg0_cbar.set_ticks(decades)
  axis_obj = arg0_cbar.ax.xaxis if getattr(arg0_cbar, "orientation", "vertical") == "horizontal" else arg0_cbar.ax.yaxis
  axis_obj.set_major_formatter(fmt)
  axis_obj.set_minor_formatter(mticker.NullFormatter())


def apply_human_log_ticks (arg0_ax, arg1_axes="both", arg2_semantic=True):
  """Applies plain European human log tick labels (no `10^k` scientific notation) and hides noisy minor log ticks."""
  if arg0_ax is None:
    return
  mode = str(arg1_axes or "both").lower()
  fmt = euro_log_formatter(bool(arg2_semantic))
  targets = []
  if mode in {"x", "both"} and hasattr(arg0_ax, "xaxis"):
    targets.append((arg0_ax.xaxis, arg0_ax.get_xlim()))
  if mode in {"y", "both"} and hasattr(arg0_ax, "yaxis"):
    targets.append((arg0_ax.yaxis, arg0_ax.get_ylim()))
  for axis_obj, lims in targets:
    lo = max(1e-12, min(float(lims[0]), float(lims[1])))
    hi = max(lo * 1.01, max(float(lims[0]), float(lims[1])))
    if math.log10(hi / lo) < 2.2:
      axis_obj.set_major_locator(mticker.LogLocator(base=10.0, subs=(1.0, 2.0, 5.0)))
    axis_obj.set_major_formatter(fmt)
    axis_obj.set_minor_formatter(mticker.NullFormatter())


def apply_viscount_style (arg0_ax=None, arg1_options=None, **kwargs):
  """Resets to default Matplotlib styling (DejaVu Sans, 4-sided boxed spines) with optional subtle grid."""
  opts = arg1_options if isinstance(arg1_options, dict) else {}
  if "grid" in kwargs:
    grid_enabled = bool(kwargs.pop("grid"))
  else:
    grid_enabled = bool(opts.get("grid", True))

  #Reset global rcParams strictly to Matplotlib defaults
  mpl.rcdefaults()
  plt.style.use("default")
  mpl.rcParams["savefig.dpi"] = 300

  if arg0_ax is not None:
    for spine_name in ("top", "right", "bottom", "left"):
      if spine_name in arg0_ax.spines:
        arg0_ax.spines[spine_name].set_visible(True)
    if grid_enabled:
      arg0_ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.35)
    else:
      arg0_ax.grid(False)


def euro_log_formatter (arg0_semantic=True, arg1_digits=2):
  """Returns a Matplotlib FuncFormatter formatting positive log-axis ticks as plain European/semantic numerals (never `10^k`)."""
  use_semantic = bool(arg0_semantic)
  digits = int(arg1_digits)

  def _fmt (arg0_x, arg1_pos):
    val = float(arg0_x)
    if not math.isfinite(val) or val <= 0.0:
      return ""
    if val >= 1.0:
      if use_semantic:
        return format_semantic_population(val)
      if abs(val - round(val)) < 1e-6:
        return f"{int(round(val)):,}".replace(",", ".")
      return format_euro_number(val, digits)
    if val >= 1e-4:
      eff_digits = max(digits, 4 if val < 1e-3 else (3 if val < 1e-2 else digits))
      return format_euro_number(val, eff_digits)
    if val < 1e-9:
      return "0"
    return format_euro_number(val, max(digits, 6))

  #Return statement
  return mticker.FuncFormatter(_fmt)


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


def mute_rgb_hex (arg0_rgb, arg1_idx=0, arg2_blend=0.45):
  """Blends vivid areal-mask RGB tuples toward warm parchment for legible vector overlays."""
  fallback = [
    (91, 143, 185), (129, 178, 126), (221, 154, 102), (168, 134, 186),
    (204, 118, 114), (108, 174, 168), (195, 174, 105), (138, 152, 194)
  ]
  if isinstance(arg0_rgb, (list, tuple)) and len(arg0_rgb) >= 3:
    r0, g0, b0 = int(arg0_rgb[0]), int(arg0_rgb[1]), int(arg0_rgb[2])
  else:
    r0, g0, b0 = fallback[int(arg1_idx) % len(fallback)]
  t = max(0.0, min(1.0, float(arg2_blend)))
  rm = max(0, min(255, int(round((1.0 - t) * r0 + t * 244.0))))
  gm = max(0, min(255, int(round((1.0 - t) * g0 + t * 241.0))))
  bm = max(0, min(255, int(round((1.0 - t) * b0 + t * 234.0))))

  #Return statement
  return f"#{rm:02x}{gm:02x}{bm:02x}"


def pad_projected_bounds (arg0_bounds, arg1_target_aspect=1.48, arg2_pad_factor=1.14, arg3_min_span_km=280.0):
  """Symmetrically pads projected Equal-Area bounds (`[xmin, ymin, xmax, ymax]`) without ocean overextension."""
  x0, y0, x1, y1 = [float(v) for v in arg0_bounds]
  aspect = max(0.15, float(arg1_target_aspect))
  pad_f = max(1.0, float(arg2_pad_factor))
  min_span = max(10.0, float(arg3_min_span_km))

  cx = 0.5 * (x0 + x1)
  cy = 0.5 * (y0 + y1)
  w = max((x1 - x0) * pad_f, min_span)
  h = max((y1 - y0) * pad_f, min_span / aspect)
  if w / h > aspect:
    h = w / aspect
  else:
    w = h * aspect

  #Return statement
  return (cx - 0.5 * w, cx + 0.5 * w), (cy - 0.5 * h, cy + 0.5 * h)


def place_inbounds_callouts (arg0_fig, arg1_ax, arg2_items, arg3_proj=None, arg4_xlim=None, arg5_ylim=None, arg6_options=None):
  """Places callout annotations inside panel spines using live renderer bboxes with zero overlap."""
  opts = arg6_options if isinstance(arg6_options, dict) else {}
  max_labels = int(opts.get("max_labels", 8))
  min_sep_px = float(opts.get("min_sep_px", 36.0))
  fontsize = float(opts.get("fontsize", 6.4))
  margin_px = float(opts.get("margin_px", 6.0))
  dot_col = opts.get("dot_color", "#b91c1c")

  xlim = arg4_xlim if arg4_xlim is not None else arg1_ax.get_xlim()
  ylim = arg5_ylim if arg5_ylim is not None else arg1_ax.get_ylim()
  x0_lim, x1_lim = float(xlim[0]), float(xlim[1])
  y0_lim, y1_lim = float(ylim[0]), float(ylim[1])

  in_pts = []
  for it in arg2_items:
    if isinstance(it, dict):
      lbl = str(it.get("label", ""))
      raw_x = float(it.get("lon", it.get("x", 0.0)))
      raw_y = float(it.get("lat", it.get("y", 0.0)))
    else:
      lbl, raw_x, raw_y = str(it[0]), float(it[1]), float(it[2])
    if arg3_proj is not None and hasattr(arg3_proj, "fwd_pt"):
      px, py = arg3_proj.fwd_pt(raw_x, raw_y)
    else:
      px, py = raw_x, raw_y
    if x0_lim <= px <= x1_lim and y0_lim <= py <= y1_lim:
      in_pts.append((lbl, px, py))
  if not in_pts:
    return []

  arg0_fig.canvas.draw()
  rend = arg0_fig.canvas.get_renderer()
  ax_bb = arg1_ax.get_window_extent(rend)
  safe_bb = Bbox.from_extents(
    ax_bb.x0 + margin_px,
    ax_bb.y0 + margin_px,
    ax_bb.x1 - margin_px,
    ax_bb.y1 - margin_px
  )

  occupied = []
  for child_ax in arg1_ax.child_axes:
    if child_ax.get_visible():
      occupied.append(child_ax.get_window_extent(rend).expanded(1.04, 1.08))
  leg = arg1_ax.get_legend()
  if leg is not None and leg.get_visible():
    occupied.append(leg.get_window_extent(rend).expanded(1.04, 1.06))
  for t_ex in arg1_ax.texts:
    if t_ex.get_visible() and t_ex.get_text().strip():
      occupied.append(t_ex.get_window_extent(rend).expanded(1.05, 1.12))

  disp_pts = []
  placed_anchors = []
  for lbl, px, py in in_pts:
    dx_p, dy_p = arg1_ax.transData.transform((px, py))
    if any(((dx_p - axp) ** 2 + (dy_p - ayp) ** 2) ** 0.5 < min_sep_px for axp, ayp in placed_anchors):
      continue
    placed_anchors.append((dx_p, dy_p))
    disp_pts.append((lbl, px, py, dx_p, dy_p))
    occupied.append(Bbox.from_bounds(dx_p - 5.5, dy_p - 5.5, 11.0, 11.0))
    if len(disp_pts) >= max_labels:
      break

  import math
  offsets_px = []
  for rad in (28.0, 48.0, 72.0, 100.0):
    for ang_deg in (30, 150, 330, 210, 75, 105, 255, 285):
      ar = math.radians(ang_deg)
      offsets_px.append((rad * 1.15 * math.cos(ar), rad * 0.85 * math.sin(ar)))

  placed = []
  inv_trans = arg1_ax.transData.inverted()
  for lbl, px, py, dx_p, dy_p in disp_pts:
    t_obj = arg1_ax.text(
      px, py, lbl, fontsize=fontsize, color="#0f172a", ha="center", va="center", zorder=10.0,
      bbox=dict(boxstyle="round,pad=0.14", facecolor="white", edgecolor="#475569", alpha=0.95, linewidth=0.5)
    )
    chosen_bb = None
    chosen_xy = None
    for ox, oy in offsets_px:
      tx_w, ty_w = inv_trans.transform((dx_p + ox, dy_p + oy))
      t_obj.set_position((tx_w, ty_w))
      arg0_fig.canvas.draw()
      bb_cur = t_obj.get_window_extent(rend).expanded(1.05, 1.14)
      if not (bb_cur.x0 >= safe_bb.x0 and bb_cur.x1 <= safe_bb.x1 and bb_cur.y0 >= safe_bb.y0 and bb_cur.y1 <= safe_bb.y1):
        continue
      if any(bb_cur.overlaps(o_bb) for o_bb in occupied):
        continue
      chosen_bb = bb_cur
      chosen_xy = (tx_w, ty_w)
      break

    if chosen_xy is None:
      t_obj.remove()
      continue
    arg1_ax.plot([px, chosen_xy[0]], [py, chosen_xy[1]], color="#1e293b", linewidth=0.55, zorder=6.0)
    arg1_ax.scatter([px], [py], s=22.0, c=dot_col, edgecolors="white", linewidths=0.60, zorder=7.0)
    occupied.append(chosen_bb)
    placed.append(t_obj)

  #Return statement
  return placed


def save_viscount_figure (arg0_fig, arg1_output_path, arg2_dpi=300, arg3_options=None, **kwargs):
  """Saves a Matplotlib figure cleanly at print resolution without clipping labels."""
  opts = arg3_options if isinstance(arg3_options, dict) else {}
  dpi_val = int(kwargs.pop("dpi", arg2_dpi))
  bbox_mode = opts.get("bbox_inches", "tight")
  if opts.get("verify_layout"):
    verify_panel_bounds_and_overlaps(
      arg0_fig,
      os.path.basename(str(arg1_output_path)),
      {"strict": bool(opts.get("strict_layout", False))}
    )
  out_dir = os.path.dirname(str(arg1_output_path))
  if out_dir:
    os.makedirs(out_dir, exist_ok=True)
  arg0_fig.savefig(arg1_output_path, dpi=dpi_val, bbox_inches=bbox_mode, facecolor="white")
  plt.close(arg0_fig)


def verify_panel_bounds_and_overlaps (arg0_fig, arg1_label="", arg2_options=None):
  """Audits rendered text, legends and child insets for panel/canvas bleeds and pairwise overlap."""
  opts = arg2_options if isinstance(arg2_options, dict) else {}
  tol = float(opts.get("tol_px", 2.5))
  strict = bool(opts.get("strict", False))

  arg0_fig.canvas.draw()
  rend = arg0_fig.canvas.get_renderer()
  fig_bb = arg0_fig.bbox
  child_set = {c_ax for p_ax in arg0_fig.axes for c_ax in p_ax.child_axes}
  top_axes = [(ax, ax.get_window_extent(rend)) for ax in arg0_fig.axes if ax not in child_set and ax.get_visible()]

  panel_bleeds = []
  canvas_bleeds = []
  overlaps = []

  def check_canvas (arg0_name, arg1_bb):
    if (
      arg1_bb.x0 < fig_bb.x0 - tol
      or arg1_bb.x1 > fig_bb.x1 + tol
      or arg1_bb.y0 < fig_bb.y0 - tol
      or arg1_bb.y1 > fig_bb.y1 + tol
    ):
      canvas_bleeds.append(f"{arg1_label}: '{arg0_name}' exceeds figure canvas bbox.")

  for ax in arg0_fig.axes:
    if not ax.get_visible():
      continue
    ax_bb = ax.get_window_extent(rend)
    local_boxes = []

    for child_ax in ax.child_axes:
      if child_ax.get_visible():
        c_bb = child_ax.get_window_extent(rend)
        local_boxes.append(("inset_axes", c_bb))

    leg = ax.get_legend()
    if leg is not None and leg.get_visible():
      leg_bb = leg.get_window_extent(rend)
      check_canvas("axes_legend", leg_bb)
      cx_l = 0.5 * (leg_bb.x0 + leg_bb.x1)
      cy_l = 0.5 * (leg_bb.y0 + leg_bb.y1)
      if ax_bb.x0 <= cx_l <= ax_bb.x1 and ax_bb.y0 <= cy_l <= ax_bb.y1:
        if (
          leg_bb.x0 < ax_bb.x0 - tol
          or leg_bb.x1 > ax_bb.x1 + tol
          or leg_bb.y0 < ax_bb.y0 - tol
          or leg_bb.y1 > ax_bb.y1 + tol
        ):
          panel_bleeds.append(f"{arg1_label}: interior axes legend crosses panel spine.")
      local_boxes.append(("legend", leg_bb))

    for t in ax.texts:
      if not t.get_visible():
        continue
      txt_s = t.get_text().strip()
      if not txt_s:
        continue
      bb = t.get_window_extent(rend)
      check_canvas(txt_s, bb)
      is_ext_header = False
      if t.get_transform() == ax.transAxes:
        px_a, py_a = t.get_position()
        if py_a > 1.0 or py_a < 0.0 or px_a > 1.0 or px_a < 0.0:
          is_ext_header = True
      if not is_ext_header:
        if (
          bb.x0 < ax_bb.x0 - tol
          or bb.x1 > ax_bb.x1 + tol
          or bb.y0 < ax_bb.y0 - tol
          or bb.y1 > ax_bb.y1 + tol
        ):
          panel_bleeds.append(f"{arg1_label}: label '{txt_s}' bleeds outside panel spine.")
        local_boxes.append((txt_s, bb))

    for i in range(len(local_boxes)):
      nm_i, bb_i = local_boxes[i]
      for x in range(i + 1, len(local_boxes)):
        nm_x, bb_x = local_boxes[x]
        if bb_i.overlaps(bb_x):
          inter_w = min(bb_i.x1, bb_x.x1) - max(bb_i.x0, bb_x.x0)
          inter_h = min(bb_i.y1, bb_x.y1) - max(bb_i.y0, bb_x.y0)
          if inter_w > 2.0 and inter_h > 2.0:
            overlaps.append(f"{arg1_label}: '{nm_i}' overlaps '{nm_x}' ({inter_w:.1f}x{inter_h:.1f} px).")

    for title_art in (ax.title, ax.xaxis.label, ax.yaxis.label):
      if title_art.get_visible() and title_art.get_text().strip():
        t_bb = title_art.get_window_extent(rend)
        check_canvas(title_art.get_text().strip(), t_bb)
        for other_ax, o_bb in top_axes:
          if other_ax is ax or other_ax in ax.child_axes or ax in other_ax.child_axes:
            continue
          if t_bb.overlaps(o_bb):
            inter_w = min(t_bb.x1, o_bb.x1) - max(t_bb.x0, o_bb.x0)
            inter_h = min(t_bb.y1, o_bb.y1) - max(t_bb.y0, o_bb.y0)
            if inter_w > 4.0 and inter_h > 4.0:
              overlaps.append(f"{arg1_label}: '{title_art.get_text().strip()}' overlaps adjacent panel.")

  if getattr(arg0_fig, "_suptitle", None) is not None and arg0_fig._suptitle.get_visible():
    st_bb = arg0_fig._suptitle.get_window_extent(rend)
    check_canvas(arg0_fig._suptitle.get_text().strip(), st_bb)
    for _ax, a_bb in top_axes:
      if st_bb.overlaps(a_bb):
        inter_w = min(st_bb.x1, a_bb.x1) - max(st_bb.x0, a_bb.x0)
        inter_h = min(st_bb.y1, a_bb.y1) - max(st_bb.y0, a_bb.y0)
        if inter_w > 3.0 and inter_h > 3.0:
          overlaps.append(f"{arg1_label}: suptitle overlaps subplot panel.")

  for fl in arg0_fig.legends:
    if fl.get_visible():
      fl_bb = fl.get_window_extent(rend)
      check_canvas("figure_legend", fl_bb)
      for _ax, a_bb in top_axes:
        if fl_bb.overlaps(a_bb):
          inter_w = min(fl_bb.x1, a_bb.x1) - max(fl_bb.x0, a_bb.x0)
          inter_h = min(fl_bb.y1, a_bb.y1) - max(fl_bb.y0, a_bb.y0)
          if inter_w > 3.0 and inter_h > 3.0:
            overlaps.append(f"{arg1_label}: figure legend overlaps subplot panel.")

  result = {
    "canvas_bleeds": canvas_bleeds,
    "ok": (len(panel_bleeds) == 0 and len(canvas_bleeds) == 0 and len(overlaps) == 0),
    "overlaps": overlaps,
    "panel_bleeds": panel_bleeds
  }
  if not result["ok"] and strict:
    issues = panel_bleeds + canvas_bleeds + overlaps
    raise ValueError(f"Figure layout check failed ({len(issues)} issue(s)): " + " | ".join(issues[:5]))

  #Return statement
  return result
