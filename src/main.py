import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QLineEdit
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import pyqtSignal
from brillouinview_main_window_ui import Ui_MainWindow
from edit_calibration_settings_ui import Ui_EditCalibrationSettings
from brillouinview.calibration import ExperimentSetup

class BrillouinViewApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # calibration tab setup
        self.experiment_setup = ExperimentSetup()
        self.ui.button_edit_settings.clicked.connect(self.open_subwindow_experiment_setup)

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
            new_experiment_setup = ExperimentSetup(**self.new_experiment_setup_data)
            self.sig.emit(new_experiment_setup)
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = BrillouinViewApp()
    main_window.show()
    sys.exit(app.exec_())