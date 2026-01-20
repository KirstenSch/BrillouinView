from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import  QDialog, QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem
from pathlib import Path
from edit_calibration_settings_ui import Ui_EditCalibrationSettings
from calibration_fit_window_ui import Ui_CalibrationFitWindow
from brillouinview.calibration import ExperimentSetup
from brillouinview.io_fileparsing import read_ghost_file
from brillouinview.fitting_algorithm import fit_peaks    
import pyqtgraph as pg
from PyQt5.QtCore import Qt
from brillouinview.fitting_functions import gaussian
from brillouinview.helping_functions import nominal

class ExperimentSetupWindow(QDialog):
    sig = pyqtSignal(object)
    def __init__(self, experiment_setup: ExperimentSetup):
        super().__init__()
        self.current_experiment_setup = experiment_setup
        self.ui = Ui_EditCalibrationSettings()
        self.ui.setupUi(self)
        self.ui_fields_dict = {
            "scattering_angle": {"widget": self.ui.le_angle, "type": float},
            "scattering_angle_unc": {"widget": self.ui.le_angle_unc, "type": float},
            "laser_wavelength": {"widget": self.ui.le_wavelength, "type": float},
            "laser_wavelength_unc": {"widget": self.ui.le_wavelength_unc, "type": float},
            "spacing": {"widget": self.ui.le_spacing, "type": float},
            "spacing_unc": {"widget": self.ui.le_spacing_unc, "type": float},
            "calibration_factor": {"widget": self.ui.le_calibration, "type": float},
            "calibration_factor_unc": {"widget": self.ui.le_calibration_unc, "type": float},
        }
        self.populate_fields()
        self.set_double_validator()
        self.ui.button_calibration_save_settings.clicked.connect(self.update_experiment_setup)

    def populate_fields(self):
        for key, meta in self.ui_fields_dict.items():
            value = getattr(self.current_experiment_setup, key)
            line_edit: QLineEdit = meta["widget"]
            line_edit.setText(str(value))

    def set_double_validator(self):
        validator = QDoubleValidator()
        validator.setNotation(QDoubleValidator.StandardNotation)
        for field in self.ui_fields_dict.values():
            line_edit: QLineEdit = field["widget"]
            line_edit.setValidator(validator)

    def update_experiment_setup(self):
        self.new_experiment_setup_data = self.read_all_fields()
        if self.sanitiy_check():
            # Update only provided fields on the existing ExperimentSetup instance
            for key, value in self.new_experiment_setup_data.items():
                if value is not None and hasattr(self.current_experiment_setup, key):
                    setattr(self.current_experiment_setup, key, value)
            
            self.sig.emit(self.current_experiment_setup)
            self.close()

    def sanitiy_check(self):
        return True

    def read_all_fields(self):
        data = {}
        for key, meta in self.ui_fields_dict.items():
            text = meta["widget"].text()
            try:
                data[key] = meta["type"](text)
            except ValueError:
                data[key] = None
        return data
    
    def closeEvent(self, event):
        super().closeEvent(event) 


class CalibrationFitWindow(QDialog):
    sig = pyqtSignal(object)
    def __init__(self, experiment_setup: ExperimentSetup):
        super().__init__()
        self.ui_calplot = Ui_CalibrationFitWindow()
        self.ui_calplot.setupUi(self)
        self.ui_calplot.fit_plot.setBackground("w")
        self.ui_calplot.fit_plot.setLabel('left', 'Counts', size=14)
        self.ui_calplot.fit_plot.setLabel('bottom', 'Channel', size=14)
        self.ui_calplot.fit_plot.showGrid(x=True, y=True)
        self.experiment_setup = experiment_setup
        self.file_path = self.experiment_setup.calibration_file_path
        self.peak_number = self.experiment_setup.calibration_peak_number
        self.ui_calplot.button_cancel_calfit.clicked.connect(self.close)
        self.ui_calplot.button_accept_calfit.clicked.connect(self.apply_calibration_fit)

    def start_fit_window(self):
        if not self.file_path.exists():
            QMessageBox.critical(self, "Error", "The chosen file does not exist.")
            return

        try:
            self.calibration_data, _ = read_ghost_file(self.file_path)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load calibration data: {e}")
            return
        
        # Fit peaks to calibration data
        self.results = fit_peaks(self.calibration_data, n_peaks=self.peak_number, column="intensity")

        self.plot_data()
        self.populate_fit_results_table()
        self.ui_calplot.le_used_function.setText(self.experiment_setup.calibration_peak_function)


    def apply_calibration_fit(self):
        if len(self.get_checked_peak_params()) < 2:
            QMessageBox.warning(self, "Warning", 
                            "At least two dips must be selected for calibration.")
            return

        self.experiment_setup.calibration_peak_parameters = self.get_checked_peak_params()
        self.experiment_setup.calibration_peak_function = self.ui_calplot.le_used_function.text()
        self.experiment_setup.calibration_background = self.results.get('baseline', 0.0)
        self.sig.emit(self.experiment_setup)
        self.close()

    def populate_fit_results_table(self, use_checkbox=True):
        """
        Populate a QTableWidget with multi-peak fit results.
        
        Parameters:
        -----------
        table_widget : QTableWidget
            The table widget to populate
        fit_results : dict
            Dictionary containing 'params' list with fit parameters for each peak
        """
        # Extract parameters list
        params = self.results.get('params', [])
        
        if not params:
            self.ui_calplot.tableWidget.setRowCount(0)
            self.ui_calplot.tableWidget.setColumnCount(0)
            return
        
        # Get parameter names from first peak (assumes all peaks have same parameters)
        param_names = list(params[0].keys())
        
        # Check if num_peaks equal to number given
        num_peaks = len(params)
        if num_peaks != self.peak_number:
            QMessageBox.warning(self, "Warning", 
                            f"Number of fitted dips ({num_peaks}) does not match expected number ({self.peak_number}).")
        
        num_params = len(param_names)
        
        # Set table dimensions (+2: one for peak number, one for checkbox column)
        self.ui_calplot.tableWidget.setRowCount(num_peaks)
        if use_checkbox:
            self.ui_calplot.tableWidget.setColumnCount(num_params + 2)
        else:
            self.ui_calplot.tableWidget.setColumnCount(num_params + 1)
        
        # Set column headers
        headers = ['Dip'] + param_names
        if use_checkbox:
            headers += ['Use for Calibration']
        self.ui_calplot.tableWidget.setHorizontalHeaderLabels(headers)
        
        # Populate table with data
        for row, peak_params in enumerate(params):
            # Peak number column
            peak_item = QTableWidgetItem(f"Dip {row + 1}")
            peak_item.setTextAlignment(Qt.AlignCenter)
            self.ui_calplot.tableWidget.setItem(row, 0, peak_item)
            
            # Parameter columns
            for col, param_name in enumerate(param_names):
                value = peak_params.get(param_name, '')
                
                # Format numeric values
                if isinstance(value, (int, float)):
                    value_str = f"{value:.6g}"  # Scientific notation for small/large values
                else:
                    value_str = str(value)
                
                item = QTableWidgetItem(value_str)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.ui_calplot.tableWidget.setItem(row, col + 1, item)
            if use_checkbox:
                # Checkbox column (last column)
                checkbox_item = QTableWidgetItem()
                checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                checkbox_item.setCheckState(Qt.Unchecked)
                self.ui_calplot.tableWidget.setItem(row, num_params + 1, checkbox_item)
        
        # Optional: Resize columns to content
        self.ui_calplot.tableWidget.resizeColumnsToContents()
        
        # Connect itemChanged signal to update plot when checkboxes change
        self.ui_calplot.tableWidget.itemChanged.connect(self.update_plot_on_checkbox)

    def update_plot_on_checkbox(self, item):
        """
        Update the plot when a checkbox is toggled.
        Only redraws the plot if a checkbox was changed.
        """
        # Check if the changed item is in the checkbox column
        num_cols = self.ui_calplot.tableWidget.columnCount()
        checkbox_col = num_cols - 1
        
        if item.column() == checkbox_col:
            self.plot_data()

    def get_checked_peak_params(self):
        """
        Get the full parameter data for peaks that are checked for calibration.
        
        Returns:
        --------
        list of dict
            List of parameter dictionaries for checked peaks only.
        """
        params = self.results.get('params', [])
        checked_indices = []
        
        num_rows = self.ui_calplot.tableWidget.rowCount()
        num_cols = self.ui_calplot.tableWidget.columnCount()
        
        if num_rows == 0 or num_cols == 0:
            return []
        
        # The checkbox column is the last column
        checkbox_col = num_cols - 1
        
        for row in range(num_rows):
            checkbox_item = self.ui_calplot.tableWidget.item(row, checkbox_col)
            if checkbox_item is not None and checkbox_item.checkState() == Qt.Checked:
                checked_indices.append(row)
        
        # Return only the params for checked peaks
        return [params[i] for i in checked_indices if i < len(params)]

    def get_checked_peak_indices(self):
        """
        Get the indices of peaks that are checked for calibration.
        
        Returns:
        --------
        list of int
            List of indices for checked peaks.
        """
        num_rows = self.ui_calplot.tableWidget.rowCount()
        num_cols = self.ui_calplot.tableWidget.columnCount()
        
        if num_rows == 0 or num_cols == 0:
            return []
        
        # The checkbox column is the last column
        checkbox_col = num_cols - 1
        checked_indices = []
        
        for row in range(num_rows):
            checkbox_item = self.ui_calplot.tableWidget.item(row, checkbox_col)
            if checkbox_item is not None and checkbox_item.checkState() == Qt.Checked:
                checked_indices.append(row)
        
        return checked_indices

    def plot_data(self):
        # Plot the calibration data
        self.ui_calplot.fit_plot.clear()
        handle_data = self.ui_calplot.fit_plot.plot(
            self.calibration_data.index,
            self.calibration_data.iloc[:, 0],
            pen=pg.mkPen('black', width=1.5) 
        )

        # Get the current x-range and extend it by 10% on the right
        try:
            plot_item = self.ui_calplot.fit_plot.getPlotItem()
            x_min = self.calibration_data.index.min()
            x_max = self.calibration_data.index.max()
            x_range = x_max - x_min
            # Extend x-axis by 10% on the right side for legend space
            plot_item.setXRange(x_min, x_max + 0.1 * x_range, padding=0)
        except Exception:
            plot_item = None
        
        # Create legend positioned at right side center
        try:
            legend = self.ui_calplot.fit_plot.addLegend(
                offset=(10, 0),
                brush=(255, 255, 255, 200),  # Semi-transparent white background
                labelTextSize='9pt'
            )
            # Anchor legend: (itemPos, parentPos)
            # (0, 0.5) = left-center of legend, (1, 0.5) = right-center of plot
            legend.anchor((0, 0.5), (1, 0.5), offset=(-3 * 0.1 * x_range, 0))

            legend.addItem(handle_data, "Calibration Data")
        except Exception:
            legend = None

        x_values = self.results.get("x_values")
        y_fitted = self.results.get("fitted_curve")
        # If baseline is a ufloat, use its nominal value for plotting
        baseline = nominal(self.results.get("baseline", 0.0))
        params = sorted(self.results.get("params", []), key=lambda p: nominal(p.get("center", 0)))

        # Get checked peak indices
        checked_indices = self.get_checked_peak_indices()

        # Overall fitted curve (red dashed)
        if x_values is not None and y_fitted is not None:
            pen_fit = pg.mkPen(color='r', width=2, style=Qt.DashLine)
            handle_fit = self.ui_calplot.fit_plot.plot(
                x_values,
                y_fitted,
                pen=pen_fit
            )
            if legend is not None:
                try:
                    legend.addItem(handle_fit, "Fitted output")
                except Exception:
                    pass

        # Individual fitted dips
        for i, peak in enumerate(params, start=1):
            amp = nominal(peak.get("amplitude", 0.0))
            cen = nominal(peak.get("center", 0.0))
            sig = nominal(peak.get("sigma", 1.0))

            x_for_fit = x_values if x_values is not None else self.calibration_data.index.values
            individual = baseline + gaussian(x_for_fit, amp, cen, sig)
            color = pg.intColor(i, hues=max(len(params) + 1, 6))
            
            # Check if this peak is checked (i-1 because enumerate starts at 1)
            is_checked = (i - 1) in checked_indices
            
            # Use solid line with width=3 if checked, dotted line with width=1.5 if not
            if is_checked:
                pen_peak = pg.mkPen(color=color, width=3, style=Qt.SolidLine)
            else:
                pen_peak = pg.mkPen(color=color, width=1.5, style=Qt.DotLine)
            
            handle = self.ui_calplot.fit_plot.plot(
                x_for_fit,
                individual,
                pen=pen_peak
            )
            if legend is not None:
                try:
                    legend.addItem(handle, f"Fitted dip {i}")
                except Exception:
                    pass

        # Baseline line
        try:
            baseline_line = pg.InfiniteLine(pos=baseline, angle=0, pen=pg.mkPen('gray', style=Qt.DashLine))
            self.ui_calplot.fit_plot.addItem(baseline_line)
            if legend is not None:
                try:
                    h = self.ui_calplot.fit_plot.plot([0], [baseline], pen=pg.mkPen('gray', style=Qt.DashLine))
                    legend.addItem(h, "Baseline")
                except Exception:
                    pass
        except Exception:
            pass


