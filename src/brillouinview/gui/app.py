from itertools import count
from pathlib import Path
from PyQt5.QtWidgets import QMainWindow, QLineEdit, QFileDialog, QMessageBox

from brillouinview.helping_functions import nominal
from uncertainties import ufloat
import pandas as pd
import pyqtgraph as pg
import numpy as np
from brillouinview_main_window_ui import Ui_MainWindow
from brillouinview.calibration import ExperimentSetup
from brillouinview.io_fileparsing import experiment_setup_calibration

from brillouinview.gui.calibration_tab import ExperimentSetupWindow, CalibrationFitWindow
from brillouinview.io_fileparsing import read_ghost_file
from brillouinview.fitting_algorithm import gaussian
from PyQt5.QtCore import Qt

class BrillouinViewApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.button_run_calibration.setEnabled(False)
        self.ui.button_start_fit.setEnabled(False)
        
        #calibration tab setup
        self.experiment_setup = ExperimentSetup()
        self.ui.button_edit_settings.clicked.connect(self.open_subwindow_experiment_setup)
        self.ui.button_calibration_load_settings.clicked.connect(self.load_experiment_setup)
        self.ui.button_load_calibration.clicked.connect(self.load_calibration_data)
        self.ui.button_start_fit.clicked.connect(self.start_calibration_fit)
        self.ui.button_run_calibration.clicked.connect(self.calculate_calibration)
        self.ui.button_reset.clicked.connect(self.reset_entires)
        self.init_plot()

    def init_plot(self):
        self.calibration_data = pd.DataFrame()
        self.ui.graph.setBackground("w")
        self.ui.graph.setLabel('left', 'Counts', size=14)
        self.ui.graph.setLabel('bottom', 'Channel', size=14)
        self.ui.graph.showGrid(x=True, y=True)

    def load_experiment_setup(self):
        working_dir = str(Path.cwd().absolute())
        file_name = QFileDialog.getOpenFileName(self, 'Choose Settings File', 
         working_dir,"YAML files (*.yaml *.yml);;Text files (*.txt)")
        file_path = Path(file_name[0])
        
        if not file_path.exists():
            QMessageBox.critical(self, "Error", "The chosen file does not exist.")
            return
            
        experiment_setup_read = experiment_setup_calibration(file_path)  
        
        # Copy all public attributes from the loaded ExperimentSetup into the current one,
        # leaving any attributes that aren't present in the loaded object unchanged.
        if hasattr(experiment_setup_read, "__dict__"):
            for key, val in vars(experiment_setup_read).items():
                setattr(self.experiment_setup, key, val)
        else:
            for attr in dir(experiment_setup_read):
                if attr.startswith("_"):
                    continue
                try:
                    val = getattr(experiment_setup_read, attr)
                except AttributeError:
                    continue
                if callable(val):
                    continue
                setattr(self.experiment_setup, attr, val)
        

        self.open_subwindow_experiment_setup()

    def open_subwindow_experiment_setup(self):
        self.sub = ExperimentSetupWindow(self.experiment_setup)
        self.sub.sig.connect(self.apply_new_setup)
        self.sub.show()

    def apply_new_setup(self, new_setup):
        ui_fields_dict = {
            "scattering_angle": {"widget": self.ui.le_angle, "type": float},
            "scattering_angle_unc": {"widget": self.ui.le_angle_unc, "type": float},
            "laser_wavelength": {"widget": self.ui.le_wavelength, "type": float},
            "laser_wavelength_unc": {"widget": self.ui.le_wavelength_unc, "type": float},
            "spacing": {"widget": self.ui.le_spacing, "type": float},
            "spacing_unc": {"widget": self.ui.le_spacing_unc, "type": float},
            "calibration_factor": {"widget": self.ui.le_calibration, "type": float},
            "calibration_factor_unc": {"widget": self.ui.le_calibration_unc, "type": float},
        }
        
        # Update only the specified fields from new_setup to experiment_setup
        for key in ui_fields_dict.keys():
            if hasattr(new_setup, key):
                setattr(self.experiment_setup, key, getattr(new_setup, key))
        
        # Update UI widgets with current experiment_setup values
        for key, meta in ui_fields_dict.items():
            value = getattr(self.experiment_setup, key)
            line_edit: QLineEdit = meta["widget"]
            line_edit.setText(str(value))
        
    def load_calibration_data(self):
        working_dir = str(Path.cwd().absolute())
        file_name = QFileDialog.getOpenFileName(self, 'Choose Calibration Data File', 
         working_dir,"DAT files (*.DAT)")

        self.calibration_filepath = Path(file_name[0])
        self.experiment_setup.calibration_file_path = self.calibration_filepath

        if not self.calibration_filepath.exists():
            QMessageBox.critical(self, "Error", "The chosen file does not exist.")
            return

        try:
            self.calibration_data, _ = read_ghost_file(self.calibration_filepath)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load calibration data: {e}")
            return
        
        # Plot the calibration data
        self.ui.graph.clear()
        self.ui.graph.plot(
            self.calibration_data.index, 
            self.calibration_data.iloc[:, 0], 
            pen='black'
        )
        
        # Add Filename to table
        self.ui.le_calibration_data.setText(str(self.calibration_filepath))

        # Enable the fit button
        self.ui.button_start_fit.setEnabled(True)

    def start_calibration_fit(self):
        if self.calibration_data.empty:
            QMessageBox.critical(self, "Error", "No calibration data loaded.")
            return
        if int(self.ui.sB_numpeaks.value()) == 0:
            QMessageBox.critical(self, "Error", "Select the number of peaks that are in the calibration data.")
            return

        self.experiment_setup.calibration_peak_number = int(self.ui.sB_numpeaks.value())
        self.experiment_setup.calibration_peak_function = self.ui.cBox_peakfunction.currentText()

        self.cal_fit_window = CalibrationFitWindow(self.experiment_setup)
        self.cal_fit_window.start_fit_window()
        self.cal_fit_window.sig.connect(self.apply_new_setup_calfit)
        self.cal_fit_window.show()

    def apply_new_setup_calfit(self, new_setup):
        self.experiment_setup = new_setup
        centers = [param['center'] for param in self.experiment_setup.calibration_peak_parameters]

        # List of line edits
        line_edits = [self.ui.le_pos_d1, self.ui.le_pos_d2, self.ui.le_pos_d3]

        # Populate line edits
        for i, le in enumerate(line_edits):
            if i < len(centers):
                le.setText(str(centers[i]))
            else:
                le.setText('')

        self.plot_calibration_peaks()
        self.ui.button_run_calibration.setEnabled(True)

    def plot_calibration_peaks(self):

        """Add individual peaks from calibration parameters to the existing calibration plot"""
        
        if not hasattr(self, 'calibration_data') or self.calibration_data is None:
            return
        
        if not hasattr(self.experiment_setup, 'calibration_peak_parameters') or not self.experiment_setup.calibration_peak_parameters:
            return
        
        # Define specific colors for up to 3 peaks
        peak_colors = ['r', 'b', 'm']  # Red, Blue, Magenta
        
        # Get x values for plotting
        x_values = self.calibration_data.index.values
        
        # Plot each individual peak
        for i, peak in enumerate(self.experiment_setup.calibration_peak_parameters):
            amp = nominal(peak.get("amplitude", 0.0))
            cen = nominal(peak.get("center", 0.0))
            sig = nominal(peak.get("sigma", 1.0))
            
            # Calculate individual Gaussian (assuming baseline is 0 or extract from somewhere)
            baseline = nominal(self.experiment_setup.calibration_background) if hasattr(self.experiment_setup, 'calibration_background') else 0.0
            individual = baseline + gaussian(x_values, amp, cen, sig)
            
            # Use predefined colors
            color = peak_colors[i] if i < len(peak_colors) else pg.intColor(i, hues=6)
            pen_peak = pg.mkPen(color=color, width=1.5, style=Qt.SolidLine)
            self.ui.graph.plot(
                x_values,
                individual,
                pen=pen_peak
            )

    def calculate_calibration(self):
    
        # Validate laser wavelength
        if not isinstance(self.experiment_setup.laser_wavelength, (float, int)) or \
        not isinstance(self.experiment_setup.laser_wavelength_unc, (float, int)):
            QMessageBox.critical(self, "Error", "Laser wavelength must be a positive number and have an uncertainty.")
            self.open_subwindow_experiment_setup()
            return
        
        laser_wavelength = ufloat(
            self.experiment_setup.laser_wavelength,
            self.experiment_setup.laser_wavelength_unc
        )
        
        # Extract center values
        centers = [param['center'] for param in self.experiment_setup.calibration_peak_parameters]
        # Calculate delta_channel based on number of peaks
        if len(centers) == 2:
            delta_channel = np.abs(centers[1] - centers[0])
        elif len(centers) == 3:
            # Average of all pairwise distances
            delta_channel = (np.abs(centers[1] - centers[0]) + 
                            np.abs(centers[2] - centers[1]) + 
                            (np.abs(centers[2] - centers[0]))/2) / 3
        else:
            QMessageBox.critical(self, "Error", "Calibration calculation failed. Number of peaks must be 2 or 3.")
            return

        channel_calibration_factor = delta_channel / laser_wavelength

        # Update experiment setup and UI
        self.experiment_setup.calibration_factor = nominal(channel_calibration_factor)
        self.experiment_setup.calibration_factor_unc = channel_calibration_factor.std_dev
        self.ui.le_calibration.setText(f"{self.experiment_setup.calibration_factor:.6f}")
        self.ui.le_calibration_unc.setText(f"{self.experiment_setup.calibration_factor_unc:.6f}")

    def reset_entires(self):
        """Reset all entries, plots, and experiment setup to initial state"""
        
        # Clear the plot
        self.ui.graph.clear()
        
        # Reset experiment setup to a fresh instance
        self.experiment_setup = ExperimentSetup()
        
        # Clear all line edits in ui_fields_dict
        ui_fields = [
            self.ui.le_angle,
            self.ui.le_angle_unc,
            self.ui.le_wavelength,
            self.ui.le_wavelength_unc,
            self.ui.le_spacing,
            self.ui.le_spacing_unc,
            self.ui.le_calibration,
            self.ui.le_calibration_unc,
        ]
        
        for line_edit in ui_fields:
            line_edit.clear()
        
        # Clear calibration-specific fields
        self.ui.le_calibration_data.clear()
        self.ui.le_pos_d1.clear()
        self.ui.le_pos_d2.clear()
        self.ui.le_pos_d3.clear()
        
        # Reset calibration data
        self.calibration_data = pd.DataFrame()
        
        # Reset calibration filepath if it exists
        if hasattr(self, 'calibration_filepath'):
            self.calibration_filepath = None
        
        # Reset spinbox and combobox to defaults
        self.ui.sB_numpeaks.setValue(0)
        self.ui.cBox_peakfunction.setCurrentIndex(0)
        
        # Disable buttons that require data
        self.ui.button_start_fit.setEnabled(False)
        self.ui.button_run_calibration.setEnabled(False)
        
        # Reinitialize the plot to ensure clean state
        self.init_plot()
