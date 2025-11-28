import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QLineEdit
from PyQt5.QtGui import QDoubleValidator
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
        self.sub = ExperimentSetupWindow()
        self.sub.show()
        

class ExperimentSetupWindow(QDialog):
    def __init__(self):
        super().__init__()
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

        self.set_double_validator()
        self.ui.button_calibration_save_settings.clicked.connect(self.update_experiment_setup)

    def set_double_validator(self):
        validator = QDoubleValidator()
        validator.setNotation(QDoubleValidator.StandardNotation)
        for field in self.ui_fields_dict.values():
            line_edit: QLineEdit = field["widget"]
            line_edit.setValidator(validator)

    def update_experiment_setup(self):
        self.new_experiment_setup_data = self.read_all_fields()
        pass

    def read_all_fields(self):
        data = {}
        for key, meta in self.ui_fields_dict.items():
            text = meta["widget"].text()
            try:
                data[key] = meta["type"](text)
            except ValueError:
                data[key] = None
        return data


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = BrillouinViewApp()
    main_window.show()
    sys.exit(app.exec_())