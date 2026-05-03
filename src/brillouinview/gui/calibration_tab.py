from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import  QDialog, QFileDialog, QMessageBox, QTableWidgetItem
from calibration_fit_window_ui import Ui_CalibrationFitWindow
from brillouinview.io_fileparsing import read_ghost_file
from brillouinview.fitting_algorithm import fit_peaks    
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from brillouinview.fitting_algorithm import gaussian, lorentzian, voigt, pseudo_voigt
from brillouinview.helping_functions import nominal, WaitDialog
from brillouinview.plotting_modul import PeakPlotter
import re
from brillouinview.setup_classes import CalibrationParameters

class CalibrationFitWindow(QDialog):
    sig = pyqtSignal(object)
    
    # Peak function mapping for plotting individual peaks
    PEAK_FUNCTIONS = {
        'Gaussian': gaussian,
        'Lorentzian': lorentzian,
        'Voigt': voigt,
        'Pseudo Voigt': pseudo_voigt
    }
    
    def __init__(self, experiment_setup: CalibrationParameters):
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
        self.ui_calplot.button_adjust_calfit.clicked.connect(self.adjust_calibration_fit)
        self.ui_calplot.button_save_screen.clicked.connect(self.save_screenshot)

    def start_fit_window(self):
        # --- pre-checks (no threading needed, these are fast) ---
        if not self.file_path.exists():
            QMessageBox.critical(self, "Error", "The chosen file does not exist.")
            return

        try:
            self.calibration_data, _ = read_ghost_file(self.file_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load calibration data: {e}")
            return

        self.start_fitting()
        self.ui_calplot.combo_calfit.setCurrentText(self.experiment_setup.calibration_peak_function)


    def start_fitting(self, starting_params=None):
        # --- show wait dialog and start fitting in background ---
        dialog_text = "Fitting is running, give me a moment ..."
        self.wait_dialog = WaitDialog(self, text=dialog_text)
        self.worker = FittingWorker(
            self.calibration_data,
            self.peak_number,
            self.experiment_setup.calibration_peak_function, 
            starting_params=starting_params
        )
        self.worker.finished.connect(self.on_fitting_done)
        self.worker.error.connect(self.on_fitting_error)
        self.worker.start()
        self.wait_dialog.exec_()  # blocks interaction with main window until dialog is closed

    def on_fitting_done(self, result):
        self.results = result
        self.wait_dialog.accept()
        self.plot_data()
        self.populate_fit_results_table()

    def on_fitting_error(self, error_msg):
        self.wait_dialog.accept()
        QMessageBox.critical(self, "Error", f"Failed to fit peaks: {error_msg}")

    def apply_calibration_fit(self):
            if len(self.get_checked_peak_params()) < 2:
                QMessageBox.warning(self, "Warning", 
                                "At least two dips must be selected for calibration.")
                return

            self.experiment_setup.calibration_peak_parameters = self.get_checked_peak_params()
            self.experiment_setup.calibration_peak_function = self.ui_calplot.combo_calfit.currentText()
            self.experiment_setup.calibration_background = self.results.get('baseline', 0.0)
            self.sig.emit(self.experiment_setup)
            self.close()

    def populate_fit_results_table(self, use_checkbox=True, editable=False):
        """
        Populate a QTableWidget with multi-peak fit results.
        
        Parameters:
        -----------
        table_widget : QTableWidget
            The table widget to populate
        fit_results : dict
            Dictionary containing 'params' list with fit parameters for each peak
        """
        try:
            self.ui_calplot.tableWidget.itemChanged.disconnect()
        except TypeError:
            pass  # not connected yet, that's fine

        # Extract parameters list
        params = self.results.get('params', [])
        
        if not params:
            return
        
        # Get parameter names from first peak (all peaks have same structure)
        param_names = list(params[0].keys())
        
        # Configure table
        num_peaks = len(params)
        num_params = len(param_names)
        
        # +1 for peak number column, +1 for checkbox column if enabled
        total_cols = num_params + 1 + (1 if use_checkbox else 0)
        
        self.ui_calplot.tableWidget.setRowCount(num_peaks)
        self.ui_calplot.tableWidget.setColumnCount(total_cols)
        
        # Set headers
        headers = ["Peak #"] + param_names
        if use_checkbox:
            headers.append("For Cal.")
        self.ui_calplot.tableWidget.setHorizontalHeaderLabels(headers)
        
        # Populate rows
        for row, peak_params in enumerate(params):
            # Peak number column
            peak_num_item = QTableWidgetItem(str(row + 1))
            peak_num_item.setTextAlignment(Qt.AlignCenter)
            peak_num_item.setFlags(Qt.ItemIsEnabled)  # Non-editable
            self.ui_calplot.tableWidget.setItem(row, 0, peak_num_item)
            
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
                if editable:
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
                else:
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
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

        if editable:
            self.ui_calplot.tableWidget.itemChanged.connect(self.on_parameter_changed)

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
        """Plot calibration data with fitted curves for all supported peak functions."""        
        cal_data = self.calibration_data
        results = self.experiment_setup
        results.calibration_peak_parameters = sorted(self.results.get("params", []), key=lambda p: nominal(p.get("center", 0)))
        ui_graph = self.ui_calplot.fit_plot
        checked_indices = self.get_checked_peak_indices()
        baseline = nominal(self.results.get("baseline", 0.0))
        y_fitted = self.results.get("fitted_curve")
        results.full_curve_y = y_fitted
        plotter = PeakPlotter(ui_graph, cal_data, results)
        plotter.clear()
        plotter.setup_axes()
        plotter.plot_raw_data()
        plotter.plot_fitted_curve()
        plotter.plot_baseline(baseline=baseline)
        plotter.plot_individual_peaks(baseline=baseline, checked_indices=checked_indices)
        
        self.ui_calplot.fit_plot.show()

    def adjust_calibration_fit(self):
        self.ui_calplot.combo_calfit.setEnabled(True)
        self.ui_calplot.combo_calfit.currentIndexChanged.connect(self.on_parameter_changed)
        self.populate_fit_results_table(use_checkbox=False, editable=True)
        self.ui_calplot.button_recalc_calfit.setEnabled(True) 
        self.ui_calplot.button_recalc_calfit.clicked.connect(self.recalculate_fit)

    def on_parameter_changed(self):
        self.ui_calplot.button_accept_calfit.setEnabled(False)
        self.ui_calplot.button_recalc_calfit.setStyleSheet("background-color: red; color: white;")

    def recalculate_fit(self):
        self.experiment_setup.calibration_peak_function = self.ui_calplot.combo_calfit.currentText()
        starting_params = self.read_fit_params_from_table(table=self.ui_calplot.tableWidget)
        self.start_fitting(starting_params)

        self.ui_calplot.button_accept_calfit.setEnabled(True)
        self.ui_calplot.button_recalc_calfit.setStyleSheet("")
        pass

    def read_fit_params_from_table(self, table):
        """
        Read current parameter values from the table widget.

        Returns:
        --------
        list[float] : Flat list of parameter values suitable for use as starting_params in fit_peaks
        """
        # Get parameter names from headers (skip "Peak #" in col 0, and "For Cal." if present)
        headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
        param_names = [h for h in headers if h not in ("Peak #", "For Cal.", "fwhm", "area")]

        num_peaks = table.rowCount()
        starting_params = []

        for row in range(num_peaks):
            for col, param_name in enumerate(param_names):
                item = table.item(row, col + 1)  # +1 to skip "Peak #" column
                if item is None:
                    raise ValueError(f"Missing value for peak {row + 1}, parameter '{param_name}'")
                try:
                    starting_params.append(self.parse_table_value(item.text()))
                except ValueError:
                    raise ValueError(f"Invalid value for peak {row + 1}, parameter '{param_name}': '{item.text()}'")

        return starting_params
    
    def parse_table_value(self, text):
        """
        Parse a table cell value to float.
        Handles plain floats and uncertainty strings like '(-1.68+/-0.04)e+04'
        """
        text = text.strip()
        
        # Match uncertainty format: (-1.68+/-0.04)e+04 or (1.23+/-0.04)
        match = re.match(r'\(([+-]?\d+\.?\d*)\+/-[\d.]+\)([eE][+-]?\d+)?|([+-]?\d+\.?\d*)\+/-[\d.]+', text)
        if match:
            value_str = match.group(1) or match.group(3)
            exponent = match.group(2) or ''
            return float(value_str + exponent)
        
        # Plain float
        return float(text)

    def save_screenshot(self):
        # 1. Grab the window (including all its children)
        # Using self.grab() captures the QMainWindow and its contents
        screenshot = self.grab()
        
        # 2. Save the pixmap to a file
        save_directory =QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Save Screenshot",
            "",
            options = QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        dat_name = self.experiment_setup.calibration_file_path.name.split(".")[0]
        filename = save_directory + f"/{dat_name}_fit_screenshot.png"
        screenshot.save(filename, "PNG")

class FittingWorker(QThread):
    # Todo:
    # Add Abort Button to Wait window. (Stop Thread and return to main window)
    # Add maximum number of iterations. If Fitting finished withput sucesss, plot anyway and tell operator to give besser starting parameters.
    
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, calibration_data, peak_number, peak_function, starting_params=None):
        super().__init__()
        self.calibration_data = calibration_data
        self.peak_number = peak_number
        self.peak_function = peak_function
        self.starting_params = starting_params

    def run(self):
        try:
            result = fit_peaks(
                self.calibration_data,
                n_peaks=self.peak_number,
                column="intensity",
                peak_function=self.peak_function,
                **({"starting_params": self.starting_params} if self.starting_params is not None else {})
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))