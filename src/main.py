import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QLineEdit, QFileDialog, QMessageBox

from brillouinview_main_window_ui import Ui_MainWindow
from brillouinview.calibration import ExperimentSetup
from brillouinview.io_fileparsing import experiment_setup_calibration

from brillouinview.gui.exp_set_window import ExperimentSetupWindow

class BrillouinViewApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        #calibration tab setup
        self.experiment_setup = ExperimentSetup()
        self.ui.button_edit_settings.clicked.connect(self.open_subwindow_experiment_setup)
        self.ui.button_calibration_load_settings.clicked.connect(self.load_experiment_setup)

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
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = BrillouinViewApp()
    main_window.show()
    sys.exit(app.exec_())