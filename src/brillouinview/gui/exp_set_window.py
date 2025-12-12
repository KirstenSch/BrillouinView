
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import  QDialog, QLineEdit

from edit_calibration_settings_ui import Ui_EditCalibrationSettings
from brillouinview.calibration import ExperimentSetup

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
