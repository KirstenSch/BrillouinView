"""
peak_plotter.py
---------------
Modular plotting class for calibration/peak-fit visualisations.

Typical usage
-------------
plotter = PeakPlotter(fit_plot_widget, calibration_data, results)
plotter.setup_axes()
plotter.plot_raw_data()
plotter.plot_fitted_curve()
plotter.plot_individual_peaks(checked_indices={0, 2})
plotter.plot_baseline()
"""

from typing import Any, Dict, List, Optional, Set

import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox

from brillouinview.fitting_algorithm import gaussian, lorentzian, voigt, pseudo_voigt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _nominal(value: Any) -> float:
    """Return the nominal (central) value whether *value* is a ufloat or plain float."""
    return float(getattr(value, "nominal_value", value))


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class PeakPlotter:
    """Composable plotter for calibration data and peak-fit results.

    Parameters
    ----------
    plot_widget:
        A ``pyqtgraph.PlotWidget`` (or any object that exposes the same API).
    calibration_data:
        A ``pandas.DataFrame`` whose *index* is the x-axis and whose first
        column is the y-axis signal.
    results:
        Dictionary produced by the fitting algorithm.  Expected keys:
        ``x_values``, ``fitted_curve``, ``baseline``, ``params``,
        ``peak_function``.
    parent:
        Optional Qt parent used for error message boxes.
    """

    PEAK_FUNCTIONS: Dict[str, Any] = {
        "Gaussian":     gaussian,
        "Lorentzian":   lorentzian,
        "Voigt":        voigt,
        "Pseudo Voigt": pseudo_voigt,
    }

    COLOR_PALETTE: List[str] = [
        "#1f77b4",  # muted blue
        "#ff7f0e",  # orange
        "#2ca02c",  # green
        "#9467bd",  # purple
        "#8c564b",  # brown
        "#e377c2",  # pink
        "#7f7f7f",  # gray
        "#bcbd22",  # olive
        "#17becf",  # cyan
    ]


    def __init__(self, plot_widget, calibration_data, results, parent=None):
        self.plot_widget    = plot_widget
        self.calibration_data = calibration_data
        self.results        = results
        self.parent         = parent

        # Internal state
        self._legend        = None
        self._x_range       = 1.0   # set properly by setup_axes()

    # ------------------------------------------------------------------
    # 1.  Initialisation helpers
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Clear the plot widget and reset internal legend reference."""
        self.plot_widget.clear()
        self._legend = None

    def setup_axes(self, x_extend: float = 0.10) -> None:
        """Configure the x-axis range and create the legend.

        Parameters
        ----------
        x_extend:
            Fraction of the x-range added on the right side to leave room
            for the legend (default 10 %).
        """
        try:
            plot_item = self.plot_widget.getPlotItem()
            x_min = self.calibration_data.index.min()
            x_max = self.calibration_data.index.max()
            self._x_range = x_max - x_min
            plot_item.setXRange(x_min, x_max + x_extend * self._x_range, padding=0)
        except Exception:
            self._x_range = 1.0

        try:
            self._legend = self.plot_widget.addLegend(
                offset=(10, 0),
                brush=(255, 255, 255, 200),
                labelTextSize="9pt",
            )
            self._legend.anchor(
                (0, 0.5), (1, 0.5),
                offset=(-3 * x_extend * self._x_range, 0),
            )
        except Exception:
            self._legend = None

    # ------------------------------------------------------------------
    # 2.  Individual plot layers
    # ------------------------------------------------------------------

    def plot_raw_data(
        self,
        label: str = "Calibration Data",
        color: str = "black",
        width: float = 1.5,
    ) -> pg.PlotDataItem:
        """Plot the raw calibration data points.

        Parameters
        ----------
        label:  Legend label.
        color:  Pen colour (any value accepted by ``pg.mkPen``).
        width:  Pen width in pixels.
        """
        handle = self.plot_widget.plot(
            self.calibration_data.index,
            self.calibration_data.iloc[:, 0],
            pen=pg.mkPen(color, width=width),
        )
        self._add_to_legend(handle, label)
        return handle

    def plot_fitted_curve(
        self,
        label: str = "Fitted output",
        color: str = "r",
        width: float = 2.0,
        style: Qt.PenStyle = Qt.DashLine,
    ) -> Optional[pg.PlotDataItem]:
        """Plot the overall fitted curve.

        Returns ``None`` when the results do not contain x/y data.
        """
        x_values = self.calibration_data.index.values
        y_fitted  = self.results.full_curve_y
        if x_values is None or y_fitted is None:
            return None

        handle = self.plot_widget.plot(
            x_values,
            y_fitted,
            pen=pg.mkPen(color=color, width=width, style=style),
        )
        self._add_to_legend(handle, label)
        return handle

    def plot_individual_peaks(
        self,
        baseline: float = 0.0,
        checked_indices: Optional[Set[int]] = None,
        label_prefix: str = "Fitted dip",
        highlight_width: float = 3.0,
        normal_width: float = 1.5,
        enhanced: bool = False,
    ) -> list[pg.PlotDataItem]:
        """Plot each individual fitted peak.

        Parameters
        ----------
        checked_indices:
            Zero-based set of peak indices that should be drawn with a bold,
            solid line.  All others are drawn as dotted lines.
            Pass ``None`` to treat all peaks as un-checked.
        label_prefix:
            Prefix used for legend entries, e.g. ``"Fitted dip 1"``.
        highlight_width:
            Pen width for checked (highlighted) peaks.
        normal_width:
            Pen width for un-checked peaks.
        enhanced:
            When ``True`` the baseline offset is *not* added to individual
            peaks, giving a baseline-subtracted (enhanced) view.
        """
        if checked_indices is None:
            checked_indices = set(range(0, len(self.results.calibration_peak_parameters)))
        
        params            = sorted(
            self.results.calibration_peak_parameters,
            key=lambda p: _nominal(p.get("center", 0)),
        )
        peak_function_name = self.results.calibration_peak_function
        peak_func          = self.PEAK_FUNCTIONS.get(peak_function_name)

        if peak_func is None:
            QMessageBox.critical(
                self.parent, "Error",
                f"Unknown peak function type: {peak_function_name}",
            )
            return []

        x_for_fit = self.calibration_data.index.values

        handles = []
        for i, peak in enumerate(params, start=1):
            individual = self._evaluate_peak(
                peak_function_name, peak_func, x_for_fit, peak,
                baseline=(0.0 if enhanced else baseline),
            )
            if individual is None:
                continue

            color_idx = (i - 1) % len(self.COLOR_PALETTE)
            color = self.COLOR_PALETTE[color_idx]
            is_checked = (i-1) in checked_indices
            pen = pg.mkPen(
                color=color,
                width=highlight_width if is_checked else normal_width,
                style=Qt.SolidLine if is_checked else Qt.DotLine,
            )

            handle = self.plot_widget.plot(x_for_fit, individual, pen=pen)
            self._add_to_legend(handle, f"{label_prefix} {i}")
            handles.append(handle)

        return handles

    def plot_baseline(
        self,
        baseline: float,
        label: str = "Baseline",
        color: str = "gray",
        width: float = 3.0,
        style: Qt.PenStyle = Qt.DashLine,
    ) -> Optional[pg.InfiniteLine]:
        """Plot the baseline as a horizontal dashed line.

        Returns the ``InfiniteLine`` item, or ``None`` on failure.
        """
        
        try:
            baseline_line = pg.InfiniteLine(
                pos=baseline,
                angle=0,
                pen=pg.mkPen(color, style=style, width=width),
            )
            self.plot_widget.addItem(baseline_line)

            # Legend proxy (InfiniteLine has no addItem handle, so we add a
            # tiny invisible plot just to carry the legend entry)
            self._add_legend_proxy([0], [baseline], color, style, width, label)
            return baseline_line
        except Exception as e:
            print(f"[PeakPlotter] Error plotting baseline: {e}")
            return None
    
    # ------------------------------------------------------------------
    # 3.  Convenience: build a complete plot in one call
    # ------------------------------------------------------------------

    def plot_all(
        self,
        baseline: float = 0.0,
        checked_indices: Optional[Set[int]] = None,
        show_baseline: bool = True,
        show_individual: bool = True,
        show_fitted: bool = True,
        enhanced: bool = False,
    ) -> None:
        """Clear and rebuild the entire plot.

        This is a convenience wrapper — call the individual methods directly
        for finer control.
        """
        self.clear()
        self.setup_axes()
        self.plot_raw_data()
        if show_fitted:
            self.plot_fitted_curve()
        if show_individual:
            self.plot_individual_peaks(checked_indices=checked_indices, enhanced=enhanced, baseline=baseline)
        if show_baseline:
            self.plot_baseline(baseline=baseline)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _add_to_legend(self, handle: pg.PlotDataItem, label: str) -> None:
        if self._legend is not None:
            try:
                self._legend.addItem(handle, label)
            except Exception:
                pass

    def _add_legend_proxy(self, x, y, color, style, width, label: str) -> None:
        if self._legend is not None:
            try:
                h = self.plot_widget.plot(x, y, pen=pg.mkPen(color, style=style, width=width))
                self._legend.addItem(h, label)
            except Exception:
                pass

    def _evaluate_peak(
        self,
        name: str,
        func,
        x,
        peak: Dict[str, Any],
        baseline: float = 0.0,
    ):
        """Evaluate a single peak function and return the y-array or ``None``."""
        amp = _nominal(peak.get("amplitude", 0.0))
        cen = _nominal(peak.get("center",    0.0))

        try:
            if name == "Gaussian":
                sig = _nominal(peak.get("sigma", 1.0))
                return baseline + func(x, amp, cen, sig)

            elif name == "Lorentzian":
                gamma = _nominal(peak.get("gamma", 1.0))
                return baseline + func(x, amp, cen, gamma)

            elif name in ("Voigt", "Pseudo Voigt"):
                sig   = _nominal(peak.get("sigma", 1.0))
                gamma = _nominal(peak.get("gamma", 1.0))
                return baseline + func(x, amp, cen, sig, gamma)

            else:
                QMessageBox.critical(
                    self.parent, "Error",
                    f"Unknown peak function type: {name}",
                )
                return None
        except Exception as exc:
            print(f"[PeakPlotter] Could not evaluate peak '{name}': {exc}")
            return None


