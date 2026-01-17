from itertools import count
from pathlib import Path
from PyQt5.QtWidgets import QMainWindow, QLineEdit, QFileDialog, QMessageBox

import pandas as pd

from brillouinview_main_window_ui import Ui_MainWindow
from brillouinview.calibration import ExperimentSetup
from brillouinview.io_fileparsing import experiment_setup_calibration

from brillouinview.gui.calibration_tab import ExperimentSetupWindow
from brillouinview.io_fileparsing import read_ghost_file

class BrillouinViewApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        #calibration tab setup
        self.experiment_setup = ExperimentSetup()
        self.ui.button_edit_settings.clicked.connect(self.open_subwindow_experiment_setup)
        self.ui.button_calibration_load_settings.clicked.connect(self.load_experiment_setup)
        self.ui.button_load_calibration.clicked.connect(self.load_calibration_data)
        self.init_plot()

    def init_plot(self):
        self.calibration_data = pd.DataFrame()
        self.ui.graph.setBackground("w")
        self.ui.graph.setLabel('left', 'Counts', size=14)
        self.ui.graph.setLabel('bottom', 'Channel', size=14)
        self.ui.graph.showGrid(x=True, y=True)
        # Example data
        # time = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        # temperature = [30, 32, 34, 32, 33, 31, 29, 32, 35, 45]
        # self.ui.graph.plot(time, temperature)

    def load_experiment_setup(self):
        working_dir = str(Path.cwd().absolute())
        file_name = QFileDialog.getOpenFileName(self, 'Choose Settings File', 
         working_dir,"YAML files (*.yaml *.yml);;Text files (*.txt)")
        file_path = Path(file_name[0])
        
        if not file_path.exists():
            QMessageBox.critical(self, "Error", "The chosen file does not exist.")
            return
            
        self.experiment_setup = experiment_setup_calibration(file_path)  
        
        self.open_subwindow_experiment_setup()

    def open_subwindow_experiment_setup(self):
        self.sub = ExperimentSetupWindow(self.experiment_setup)
        self.sub.sig.connect(self.apply_new_setup)
        self.sub.show()

    def apply_new_setup(self, new_setup):
        self.experiment_setup = new_setup
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
        for key, meta in ui_fields_dict.items():
            value = getattr(self.experiment_setup, key)
            line_edit: QLineEdit = meta["widget"]
            line_edit.setText(str(value))
        
    def load_calibration_data(self):
        working_dir = str(Path.cwd().absolute())
        file_name = QFileDialog.getOpenFileName(self, 'Choose Calibration Data File', 
         working_dir,"DAT files (*.DAT)")
        file_path = Path(file_name[0])
        
        if not file_path.exists():
            QMessageBox.critical(self, "Error", "The chosen file does not exist.")
            return

        try:
            self.calibration_data, _ = read_ghost_file(file_path)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load calibration data: {e}")
            return
        
        # Plot the calibration data
        self.ui.graph.clear()
        self.ui.graph.plot(
            self.calibration_data.index, 
            self.calibration_data.iloc[:, 0], 
            pen='b'
        )
        
        # Add Filename to table
        self.ui.le_calibration_data.setText(str(file_path))