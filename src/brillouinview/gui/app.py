from itertools import count
from pathlib import Path
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QDialog

from brillouinview.helping_functions import nominal
from uncertainties import ufloat
import pandas as pd
import pyqtgraph as pg
import numpy as np
import sys
from brillouinview_main_window_ui import Ui_MainWindow

from brillouinview.gui.calibration_tab import CalibrationFitWindow
from brillouinview.io_fileparsing import read_ghost_file
from brillouinview.toml_io import write_calibration_toml, update_dac_toml
from brillouinview.fitting_algorithm import gaussian
from brillouinview.plotting_modul import PeakPlotter
from PyQt5.QtCore import Qt
from brillouinview.setup_classes import CalibrationParameters
from brillouinview.gui.dac_experiment_setup import WelcomeWindow

class BrillouinViewApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.button_run_calibration.setEnabled(False)
        self.ui.button_start_fit.setEnabled(False)
        
        #Welcome Window
        self.run_welcome_window()
        
        self.ui.le_dac.setText(self.dac_parameters.dac_name)
        self.ui.le_experiment.setText(self.experiment_parameters.exp_name)
        self.ui.le_machine.setText(self.machine_parameters.machine_name)
        self.ui.le_spacing.setText(str(self.machine_parameters.spacing))
        self.ui.le_spacing_unc.setText(str(self.machine_parameters.spacing_unc))

        #calibration tab setup
        # Todo:Check for existing calibration parameters in experiment
        self.calibration_setup = CalibrationParameters()
        self.ui.button_load_calibration.clicked.connect(self.load_calibration_data)
        self.ui.button_start_fit.clicked.connect(self.start_calibration_fit)
        self.ui.button_run_calibration.clicked.connect(self.calculate_calibration)
        self.ui.button_reset.clicked.connect(self.reset_entires)
        self.ui.button_export.clicked.connect(self.export_calibration_parameters)
        self.init_plot()

    def run_welcome_window(self):
        dialog = WelcomeWindow(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.dac_parameters = dialog.dac_parameters
            self.experiment_parameters = dialog.experiment_parameters
            self.machine_parameters = dialog.experiment_parameters.exp_machine_parameters
        else:
            # User closed the welcome window with X button
            sys.exit(0)

    def init_plot(self):
        self.calibration_data = pd.DataFrame()
        self.ui.graph.setBackground("w")
        self.ui.graph.setLabel('left', 'Counts', size=14)
        self.ui.graph.setLabel('bottom', 'Channel', size=14)
        self.ui.graph.showGrid(x=True, y=True)

    def load_calibration_data(self):
        working_dir = str(Path.cwd().absolute())
        file_name = QFileDialog.getOpenFileName(self, 'Choose Calibration Data File', 
         working_dir,"DAT files (*.DAT)")

        self.calibration_filepath = Path(file_name[0])
        self.calibration_setup.calibration_file_path = self.calibration_filepath

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

        self.calibration_setup.calibration_peak_number = int(self.ui.sB_numpeaks.value())
        self.calibration_setup.calibration_peak_function = self.ui.cBox_peakfunction.currentText()

        self.cal_fit_window = CalibrationFitWindow(self.calibration_setup)
        self.cal_fit_window.start_fit_window()
        self.cal_fit_window.sig.connect(self.apply_new_setup_calfit)
        self.cal_fit_window.show()

    def apply_new_setup_calfit(self, new_setup):
        self.calibration_setup = new_setup
        centers = [param['center'] for param in self.calibration_setup.calibration_peak_parameters]

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
        self.ui.button_run_calibration.setStyleSheet("background-color: red; color: white;")
        self.ui.cBox_peakfunction.setCurrentText(self.experiment_setup.calibration_peak_function)

    def plot_calibration_peaks(self):

        """Add individual peaks from calibration parameters to the existing calibration plot"""
        
        if not hasattr(self, 'calibration_data') or self.calibration_data is None:
            return
        
        if not hasattr(self.calibration_setup, 'calibration_peak_parameters') or not self.calibration_setup.calibration_peak_parameters:
            return
        
        # Define specific colors for up to 3 peaks
        peak_colors = ['r', 'b', 'm']  # Red, Blue, Magenta
        
        # Get x values for plotting
        x_values = self.calibration_data.index.values
        
        # Plot each individual peak
        for i, peak in enumerate(self.calibration_setup.calibration_peak_parameters):
            amp = nominal(peak.get("amplitude", 0.0))
            cen = nominal(peak.get("center", 0.0))
            sig = nominal(peak.get("sigma", 1.0))
            
            # Calculate individual Gaussian (assuming baseline is 0 or extract from somewhere)
            baseline = nominal(self.calibration_setup.calibration_background) if hasattr(self.calibration_setup, 'calibration_background') else 0.0
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

        # Extract center values
        centers = [param['center'] for param in self.calibration_setup.calibration_peak_parameters]
        # Calculate delta_channel based on number of peaks
        if len(centers) == 2:
            delta_channel = np.abs(centers[1] - centers[0])
        elif len(centers) == 3:
            # Average of all pairwise distances
            delta_channel = (np.abs(centers[1] - centers[0]) * 2 + 
                            np.abs(centers[2] - centers[1]) * 2 + 
                            (np.abs(centers[2] - centers[0]))) / 3
        else:
            QMessageBox.critical(self, "Error", "Calibration calculation failed. Number of peaks must be 2 or 3.")
            return


        self.calibration_setup.calibration_value = nominal(delta_channel)
        self.calibration_setup.calibration_value_unc = delta_channel.std_dev

        # Caluclate channel shift factor
        self.calibration_setup.calibration_OD = self.ui.spinBox_OD.value()
        self.calibration_setup.exp_machine_parameters = self.machine_parameters
        self.calibration_setup.calibration_factor, self.calibration_setup.calibration_factor_unc = self.calculate_channel_bshift_factor()  # Assuming first order diffraction for now

        # Update experiment setup and UI
        self.ui.le_calibration.setText(f"{self.calibration_setup.calibration_value:.6f}")
        self.ui.le_calibration_unc.setText(f"{self.calibration_setup.calibration_value_unc:.6f}")
        self.ui.le_calfactor.setText(f"{self.calibration_setup.calibration_factor:.6e}")
        self.ui.le_calfactor_unc.setText(f"{self.calibration_setup.calibration_factor_unc:.6e}")
        self.ui.button_export.setEnabled(True)

    def calculate_channel_bshift_factor(self) -> float:
        # Calculate the Factor to be multiplied with the Brillouin Shift in Channels to get the Shift as a Frequency
        # OD: Order of Diffraction
        # calibration_value: Calibration Value in Channels
        # spacing: Mirror Spacing in meters
        # Returns: calibration_factor in Hz/Channel
        
        OD = self.calibration_setup.calibration_OD
        calibration_value = ufloat(self.calibration_setup.calibration_value, self.calibration_setup.calibration_value_unc)
        spacing = ufloat(self.calibration_setup.exp_machine_parameters.spacing, self.calibration_setup.exp_machine_parameters.spacing_unc)
        
        speed_of_light = 299792458 # Speed of light in m/s
        calibration_factor = speed_of_light * OD / (2 * spacing * calibration_value)
        
        return calibration_factor.nominal_value, calibration_factor.std_dev

    def reset_entires(self):
        """Reset all entries, plots, and experiment setup to initial state"""
        
        # Clear the plot
        self.ui.graph.clear()
        
        # Reset experiment setup to a fresh instance
        self.calibration_setup = CalibrationParameters()
        
        # Clear all line edits in ui_fields_dict
        self.ui.le_calibration.clear()
        self.ui.le_calibration_unc.clear()
        self.ui.le_calfactor.clear()
        self.ui.le_calfactor_unc.clear()
        self.ui.le_pos_d1.clear()
        self.ui.le_pos_d2.clear()
        self.ui.le_pos_d3.clear()
        self.ui.le_calibration_data.clear()
        
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
        self.ui.button_export.setEnabled(False)
        
        # Reinitialize the plot to ensure clean state
        self.init_plot()

    def export_calibration_parameters(self):
        # Define the directory to save the calibration parameters 
        # DAC Path + Machine Name + "Calibration"
        dac_directory = self.dac_parameters.dac_directory
        machine_name = self.machine_parameters.machine_name
        calibration_directory = dac_directory.parent / "Machine" / machine_name / "Calibration"
        calibration_directory.mkdir(parents=True, exist_ok=True)    

        # Extract filename from calibration file name and use it for the toml file
        calibration_filename = self.calibration_filepath.stem
        calibration_toml_path = calibration_directory / f"{calibration_filename}.toml"
            
        # Chekc if file already exists and ask user if they want to overwrite it
        if calibration_toml_path.exists():
            reply = QMessageBox.question(
                self, 
                "File Exists", 
                f"The file {calibration_toml_path} already exists. Do you want to overwrite it?", 
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No  
                )
            if reply == QMessageBox.No:
                QMessageBox.information(self, "Cancelled", "Export cancelled.")
                return  
            elif reply == QMessageBox.Yes:
                pass  # Proceed with overwriting the file
            else:
                QMessageBox.information(self, "Cancelled", "Export cancelled.")
                return  

        # copy calibration file to calbration directory and rewrite path in calibration_file_path to new location in calibration directory to copied file
        try:
            # Copy the original calibration file to the new location
            new_calibration_file_path = calibration_directory / self.calibration_filepath.name
            if not new_calibration_file_path.exists():
                new_calibration_file_path.write_bytes(self.calibration_filepath.read_bytes())
            
            # Update the calibration_file_path in the calibration setup to point to the new location
            self.calibration_setup.calibration_file_path = new_calibration_file_path

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export calibration file: {e}")
        # write Calibration toml
        try:
            write_calibration_toml(params=self.calibration_setup, path=calibration_toml_path)
                    # Update ExperimentParameters with calibration_factor + unc and exp_calibratio_parameters
        
            self.experiment_parameters.calibration_factor = self.calibration_setup.calibration_factor
            self.experiment_parameters.calibration_factor_unc = self.calibration_setup.calibration_factor_unc
            self.experiment_parameters.exp_calibration_toml = calibration_toml_path

            # Update DAC toml
            try:
                update_dac_toml(path=self.dac_parameters.dac_directory, experiments=[self.experiment_parameters], edit_experiment=True)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update DAC parameters: {e}")

            pass
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export calibration parameters to toml: {e}")


