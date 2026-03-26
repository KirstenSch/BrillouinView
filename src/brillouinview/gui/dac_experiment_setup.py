from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QDoubleValidator
from datetime import date

from welcome_window_ui import Ui_Prequel_Dialog
from setup_dac_window_ui import Ui_SetupDAC
from setup_experiment_window_ui import Ui_SetupExperiment
from setup_brillouin_machine_ui import Ui_Dialog as Ui_SetupMachine
from brillouinview.setup_classes import DACParameters, ExperimentParameters, MachineParameters

# ---------------------------------------------------------------------------
# SeupBrillouinMachineWindow
# ---------------------------------------------------------------------------

class SetupMachineWindow(QtWidgets.QDialog, Ui_SetupMachine):
    """Modal dialog for machine setup. Returns MachineParameters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowModality(QtCore.Qt.ApplicationModal)

        validator = QDoubleValidator(0.0, 10000.0, 6)
        self.le_machine_angle.setValidator(validator)
        self.le_machine_angle_unc.setValidator(validator)
        self.le_machine_laser.setValidator(validator)
        self.le_machine_laser_unc.setValidator(validator)
        self.le_machine_mirror.setValidator(validator)
        self.le_machine_mirror_unc.setValidator(validator)

        self.machine_parameters: MachineParameters = None

        self.button_machine_create.clicked.connect(self.on_create_machine)
        self.button_machine_clear.clicked.connect(self.on_clear_all)

    # --- main actions --------------------------------------------------

    def on_create_machine(self):
        if not self.le_machine_name.text().strip():
            QtWidgets.QMessageBox.warning(self, "Missing Field", "Please enter a machine name.")
            return
        if not self.le_machine_location.text().strip():
            QtWidgets.QMessageBox.warning(self, "Missing Field", "Please enter a machine location.")
            return

        if not self.le_machine_angle.text().strip():
            QtWidgets.QMessageBox.warning(self, "Missing Field", "Please enter a scattering angle.")
            return
        try:
            float(self.le_machine_angle.text().strip())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Field", "Please enter a valid number for scattering angle.")
            return

        if not self.le_machine_laser.text().strip():
            QtWidgets.QMessageBox.warning(self, "Missing Field", "Please enter a laser wavelength.")
            return
        try:
            float(self.le_machine_laser.text().strip())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Field", "Please enter a valid number for laser wavelength.")
            return

        if not self.le_machine_mirror.text().strip():
            QtWidgets.QMessageBox.warning(self, "Missing Field", "Please enter a mirror spacing.")
            return
        try:
            float(self.le_machine_mirror.text().strip())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Field", "Please enter a valid number for mirror spacing.")
            return

        self.machine_parameters = self.get_machine_data()
        self.accept()

    def get_machine_data(self) -> MachineParameters:
        def parse_float(text):
            try:
                return float(text.strip())
            except (ValueError, AttributeError):
                return None

        return MachineParameters(
            machine_name=self.le_machine_name.text().strip(),
            machine_location=self.le_machine_location.text().strip(),
            scattering_angle=parse_float(self.le_machine_angle.text()),
            scattering_angle_unc=parse_float(self.le_machine_angle_unc.text()),
            laser_wavelength=parse_float(self.le_machine_laser.text()),
            laser_wavelength_unc=parse_float(self.le_machine_laser_unc.text()),
            spacing=parse_float(self.le_machine_mirror.text()),
            spacing_unc=parse_float(self.le_machine_mirror_unc.text()),
            machine_notes=self.text_machine_notes.toPlainText().strip(),
)

    def on_clear_all(self):
        self.le_machine_name.clear()
        self.le_machine_location.clear()
        self.le_machine_angle.clear()
        self.le_machine_angle_unc.clear()
        self.le_machine_laser.clear()
        self.le_machine_laser_unc.clear()
        self.le_machine_mirror.clear()
        self.le_machine_mirror_unc.clear()
        self.text_machine_notes.clear()

# ---------------------------------------------------------------------------
# SetupExperimentWindow
# ---------------------------------------------------------------------------

class SetupExperimentWindow(QtWidgets.QDialog, Ui_SetupExperiment):
    """Modal dialog for experiment setup. Returns ExperimentParameters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        validator = QDoubleValidator(0.0, 1000.0, 3)
        self.le_exp_temp.setValidator(validator)
        self.le_exp_temp_unc.setValidator(validator)
        self.le_exp_pressure.setValidator(validator)
        self.le_exp_pressure_unc.setValidator(validator)

        self.experiment_parameters: ExperimentParameters = None

        # Bottom bar buttons
        self.button_exp_proceed.clicked.connect(self.on_create_experiment)  # Create Experiment
        self.button_exp_clear.clicked.connect(self.on_clear_all)             # Clear All

        # Machine buttons
        self.button_exp_machine_new.clicked.connect(self.on_create_machine)      # Create New Machine File
        self.button_exp_machine.clicked.connect(self.on_load_machine)        # Use Existing Machine File

        # Internal machine parameters — set via machine sub-dialogs
        self._machine_parameters: MachineParameters = None

    # --- machine helpers ---------------------------------------------------

    def on_create_machine(self):
        dialog = SetupMachineWindow(parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self._machine_parameters = dialog.machine_parameters
            self.le_exp_machine_display.setText(f"{self._machine_parameters.machine_name} "
                                                f"at {self._machine_parameters.machine_location or ""}")

    def on_load_machine(self):
        # TODO: open a file dialog to load a MachineParameters file
        pass

    # --- main actions ------------------------------------------------------

    def on_create_experiment(self):
        if not self.le_exp_name.text().strip():
            QtWidgets.QMessageBox.warning(self, "Missing Field", "Please enter an experiment name.")
            return

        if not self.le_exp_operator.text().strip():
            QtWidgets.QMessageBox.warning(self, "Missing Field", "Please enter an experiment operator.")
            return
    
        if not self.le_exp_machine_display.text().strip():
            QtWidgets.QMessageBox.warning(self, "Missing Field", "Please add an experiment machine.")
            return

        self.experiment_parameters = self.get_experiment_data()
        self.accept()

    def get_experiment_data(self) -> ExperimentParameters:
        def parse_float(text):
            try:
                return float(text.strip())
            except (ValueError, AttributeError):
                return None

        def qdate_to_date(qdate):
            return date(qdate.year(), qdate.month(), qdate.day())

        return ExperimentParameters(
            exp_name=self.le_exp_name.text().strip(),
            exp_operator=self.le_exp_operator.text().strip(),
            exp_temperature=parse_float(self.le_exp_temp.text()),
            exp_pressure=parse_float(self.le_exp_pressure.text()),
            exp_date_start=qdate_to_date(self.de_exp_start.date()),
            exp_date_end=qdate_to_date(self.de_exp_end.date()),
            exp_notes=self.plainTextEdit.toPlainText().strip(),
            exp_machine_parameters=self._machine_parameters,
        )


    def on_clear_all(self):
        self.lineEdit.clear()
        self.lineEdit_2.clear()
        self.lineEdit_3.clear()
        self.lineEdit_4.clear()
        self.lineEdit_5.clear()
        self.dateEdit.setDate(QtCore.QDate.currentDate())
        self.dateEdit_2.setDate(QtCore.QDate.currentDate())
        self.plainTextEdit.clear()
        self._machine_parameters = None


# ---------------------------------------------------------------------------
# SetupDACWindow
# ---------------------------------------------------------------------------

class SetupDACWindow(QtWidgets.QDialog, Ui_SetupDAC):
    """Modal dialog for DAC setup. On confirm, opens SetupExperimentWindow,
    then returns both DACParameters and ExperimentParameters to the caller."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.dac_parameters: DACParameters = None
        self.experiment_parameters: ExperimentParameters = None

        self.bt_dac_create_exp.clicked.connect(self.on_create_experiment)
        self.bt_dac_clear_exp.clicked.connect(self.on_clear_all)

    def on_create_experiment(self):
        """Collect DAC data, then open the experiment setup dialog."""
        if not self.le_dac_name.text().strip():
            QtWidgets.QMessageBox.warning(self, "Missing Field", "Please enter a DAC name.")
            return
        if not self.le_dac_owner.text().strip():
            QtWidgets.QMessageBox.warning(self, "Missing Field", "Please enter a DAC owner.")
            return

        self.dac_parameters = self.get_dac_data()

        exp_dialog = SetupExperimentWindow(parent=self)
        if exp_dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.experiment_parameters = exp_dialog.experiment_parameters
            self.accept()   

    def get_dac_data(self) -> DACParameters:
        qdate = self.date_dac_prep.date()
        return DACParameters(
            dac_name=self.le_dac_name.text().strip(),
            dac_owner=self.le_dac_owner.text().strip(),
            dac_pressuremedium=self.cb_dac_pressure_medium.currentText(),
            dac_date_load=date(qdate.year(), qdate.month(), qdate.day()),
            dac_notes=self.te_dac_notes.toPlainText().strip(),
        )

    def on_clear_all(self):
        self.le_dac_name.clear()
        self.le_dac_owner.clear()
        self.cb_dac_pressure_medium.setCurrentIndex(0)
        self.date_dac_prep.setDate(QtCore.QDate.currentDate())
        self.te_dac_notes.clear()


# ---------------------------------------------------------------------------
# WelcomeWindow
# ---------------------------------------------------------------------------

class WelcomeWindow(QtWidgets.QDialog, Ui_Prequel_Dialog):
    """Dialog for setting up the experiment parameters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.dac_parameters: DACParameters = None
        self.experiment_parameters: ExperimentParameters = None

        self.button_new_dac.clicked.connect(self.on_new_dac)
        self.button_load_dac.clicked.connect(self.on_load_dac)
        self.button_load_experiment.clicked.connect(self.on_load_experiment)
        self.button_read_manual.clicked.connect(self.on_read_manual)

    def on_new_dac(self):
        dialog = SetupDACWindow(parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.dac_parameters = dialog.dac_parameters
            self.experiment_parameters = dialog.experiment_parameters
            self.accept()   # propagate up to BrillouinViewApp

    def on_load_dac(self):
        # TODO: load existing DACParameters from file
        pass

    def on_load_experiment(self):
        # TODO: load existing ExperimentParameters from file
        pass

    def on_read_manual(self):
        # TODO: open manual
        pass