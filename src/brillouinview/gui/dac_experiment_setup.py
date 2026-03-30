from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QDoubleValidator
from datetime import date, datetime
from pathlib import Path

from welcome_window_ui import Ui_Prequel_Dialog
from setup_dac_window_ui import Ui_SetupDAC
from setup_experiment_window_ui import Ui_SetupExperiment
from setup_brillouin_machine_ui import Ui_Dialog as Ui_SetupMachine
from brillouinview.setup_classes import DACParameters, ExperimentParameters, MachineParameters, SampleParameters
from brillouinview.toml_io import write_dac_toml, write_machine_toml

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
            
            # Write machine TOML file to dac_directory/Machine/
            if self.dac_parameters and self.dac_parameters.dac_directory:
                try:
                    machine_dir = self.dac_parameters.dac_directory / "Machine"
                    machine_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Create filename from machine_name with underscores instead of spaces
                    machine_filename = self._machine_parameters.machine_name.replace(" ", "_") + ".toml"
                    machine_file_path = machine_dir / machine_filename
                    
                    write_machine_toml(self._machine_parameters, machine_file_path)
                    
                    QtWidgets.QMessageBox.information(
                        self,
                        "Machine File Saved",
                        f"Machine parameters successfully saved to:\n{machine_file_path}"
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Error Saving Machine File",
                        f"Failed to save machine file: {str(e)}"
                    )

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
        self.sample_list: SampleParameters = None
        self.experiment_parameters: ExperimentParameters = None

        self.bt_dac_create_exp.clicked.connect(self.on_create_experiment)
        self.bt_dac_clear_exp.clicked.connect(self.on_clear_all)
        self.bt_add_sample.clicked.connect(self._add_sample_row)

        # Initialize the samples table inside the scroll area (header + first row)
        self._init_samples_table()

    def on_create_experiment(self):
        """Collect DAC data, ask user for directory location, create directory structure,
        then open the experiment setup dialog."""
        if not self.le_dac_name.text().strip():
            QtWidgets.QMessageBox.warning(self, "Missing Field", "Please enter a DAC name.")
            return
        if not self.le_dac_owner.text().strip():
            QtWidgets.QMessageBox.warning(self, "Missing Field", "Please enter a DAC owner.")
            return

        self.dac_parameters = self.get_dac_data()
        self.sample_parameters_list = self.get_sample_data()
        
        if not self.sample_parameters_list:
            QtWidgets.QMessageBox.warning(self, "No Samples", "Please add at least one sample with a name.")
            return

        # Ask user to select a directory for the DAC folder
        parent_directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select directory to create DAC folder",
            "",
            options=QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks
        )

        if not parent_directory:
            QtWidgets.QMessageBox.information(self, "Cancelled", "DAC directory creation cancelled.")
            return

        # Create the DAC directory structure
        try:
            dac_directory = self._create_dac_directory_structure(parent_directory, self.dac_parameters)
            self.dac_parameters.dac_directory = dac_directory
            
            # Write DAC TOML file
            dac_toml_path = dac_directory / f"{self.dac_parameters.dac_name.replace(' ', '_')}.toml"
            write_dac_toml(dac=self.dac_parameters, path=dac_toml_path, samples=self.sample_parameters_list)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to create DAC directory: {str(e)}")
            return

        exp_dialog = SetupExperimentWindow(parent=self)
        if exp_dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.experiment_parameters = exp_dialog.experiment_parameters
            self.accept()
        # If experiment dialog is rejected, stay in DAC dialog (don't close)

    def _create_dac_directory_structure(self, parent_directory: str, dac_params: 'DACParameters') -> Path:
        """Create DAC directory structure with subdirectories.
        
        Directory structure:
        <parent_directory>/YYYYMMDD_<dac_name>/
            ├── Calibration/
            ├── Machine/
            └── Experiments/
            └── Samples/
        
        Args:
            parent_directory: Path where the DAC folder will be created
            dac_params: DACParameters containing the DAC name and date
            
        Returns:
            Path object pointing to the created DAC directory
        """
        # Format the directory name with date prefix (YYYYMMDD_dac_name)
        # Replace spaces with underscores in DAC name
        date_prefix = dac_params.dac_date_load.strftime("%Y%m%d")
        dac_name_formatted = dac_params.dac_name.replace(" ", "_")
        dac_folder_name = f"{date_prefix}_{dac_name_formatted}"
        
        # Create the main DAC directory
        dac_directory = Path(parent_directory) / dac_folder_name
        dac_directory.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        subdirs = ["Calibration", "Machine", "Experiments", "Samples"]
        for subdir in subdirs:
            (dac_directory / subdir).mkdir(parents=True, exist_ok=True)
        
        return dac_directory   

    def get_sample_data(self) -> list:
        """Collect sample data from the samples table and return a list of SampleParameters."""
        sample_parameters_list = []
        for row_data in self._sample_rows:
            sample_name = row_data['name_edit'].text().strip()
            sample_structure = row_data['struct_combo'].currentText()
            sample_notes = row_data['notes_edit'].text().strip()

            if not sample_name:
                continue  # Skip rows without a sample name

            sample_params = SampleParameters(
                sample_dac_parameters=self.dac_parameters,
                sample_name=sample_name,
                sample_structure=sample_structure,
                sample_notes=sample_notes,
                sample_experiments=[]  # Will be filled later when experiments are created
            )
            sample_parameters_list.append(sample_params)
        
        return sample_parameters_list
    
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
        
        # Clear all sample rows
        self._sample_rows.clear()
        self._rebuild_samples_grid()
        
        # Add a fresh first row
        self._add_sample_row()


    # --- samples table UI helpers ---------------------------------------
    def _init_samples_table(self):
        """Create a simple grid-like table inside the QScrollArea to hold
        sample rows. Adds a bold header row and one editable sample row.
        Columns: Number | Name (QLineEdit) | Structure (QComboBox) |
                 Notes (QLineEdit) | Delete (QPushButton)
        """
        # Container widget for scroll area
        container = QtWidgets.QWidget()
        # Prevent the container from stretching vertically; keep it compact and anchored
        container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

        vbox = QtWidgets.QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        # Anchor contents to the top so they don't distribute vertically
        vbox.setAlignment(QtCore.Qt.AlignTop)

        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        # Allow Name and Notes columns to expand horizontally
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 2)

        vbox.addLayout(grid)
        # Make the scroll area show the container
        self.scroll_dac_samples.setWidgetResizable(True)
        self.scroll_dac_samples.setWidget(container)

        self._samples_grid = grid

        # Header
        headers = ["Number", "Name", "Structure", "Notes", "Delete"]
        for col, text in enumerate(headers):
            lbl = QtWidgets.QLabel(text)
            lbl.setStyleSheet("font-weight: bold;")
            # Left-align header text as requested, vertically centered
            lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            grid.addWidget(lbl, 0, col)

        # Ensure header does not stretch vertically
        grid.setRowStretch(0, 0)

        # Horizontal line separator between header and data rows
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid.addWidget(separator, 1, 0, 1, 5)  # span all 5 columns
        grid.setRowStretch(1, 0)

        # Storage for row widgets
        self._sample_rows = []

        # Add initial first row
        self._add_sample_row()

    def _add_sample_row(self):
        """Append one editable sample row to the grid. Numbering starts at 1."""
        row_number = len(self._sample_rows) + 1

        # Number label
        number_lbl = QtWidgets.QLabel(str(row_number))
        number_lbl.setAlignment(QtCore.Qt.AlignCenter)
        number_lbl.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        # Name (line edit)
        name_edit = QtWidgets.QLineEdit()
        name_edit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Structure (combo box)
        struct_combo = QtWidgets.QComboBox()
        struct_combo.addItems(["cubic", "tetragonal", "other"])
        struct_combo.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        # Notes (line edit)
        notes_edit = QtWidgets.QLineEdit()
        notes_edit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Delete button (little X)
        del_btn = QtWidgets.QPushButton("✖")
        del_btn.setFixedWidth(24)
        del_btn.setToolTip("Delete this sample row")
        del_btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        # Keep references so we can read/update rows later
        # Store as a dict to make deletion more robust
        # Use id() to create a unique identifier that persists even after rebuilds
        row_id = id(del_btn)  # Use button's id as unique identifier
        row_data = {
            'id': row_id,
            'number_lbl': number_lbl,
            'name_edit': name_edit,
            'struct_combo': struct_combo,
            'notes_edit': notes_edit,
            'del_btn': del_btn
        }
        self._sample_rows.append(row_data)

        # Connect delete button to a closure that captures the row_id
        # This way, we can always find the correct row by its unique id
        del_btn.clicked.connect(lambda: self._delete_sample_row_by_id(row_id))

        # Refresh the entire grid layout with current data
        self._rebuild_samples_grid()

    def _delete_sample_row_by_id(self, row_id):
        """Delete a sample row by its unique id."""
        # Find the row with this id
        row_index = -1
        for i, row_data in enumerate(self._sample_rows):
            if row_data['id'] == row_id:
                row_index = i
                break
        
        if row_index < 0:
            return
        
        # Remove from storage
        self._sample_rows.pop(row_index)

        # Rebuild the entire grid from scratch with remaining rows
        self._rebuild_samples_grid()

    def _delete_sample_row(self, row_index):
        """Delete a sample row by index (0-based), remove it from storage, and rebuild grid."""
        if row_index < 0 or row_index >= len(self._sample_rows):
            return

        # Remove from storage
        self._sample_rows.pop(row_index)

        # Rebuild the entire grid from scratch with remaining rows
        self._rebuild_samples_grid()

    def _rebuild_samples_grid(self):
        """Remove all data rows from grid and re-add them in correct positions.
        This ensures no overlapping or orphaned rows, and fixes numbering."""
        # Get all items currently in the grid (excluding header row 0 and separator row 1)
        items_to_remove = []
        for i in range(2, self._samples_grid.rowCount()):
            for col in range(self._samples_grid.columnCount()):
                item = self._samples_grid.itemAtPosition(i, col)
                if item and item.widget():
                    items_to_remove.append(item.widget())
        
        # Remove all widgets from grid
        for widget in items_to_remove:
            self._samples_grid.removeWidget(widget)
            # Don't delete them here - we're reusing them

        # Re-add all rows from storage
        for i, row_data in enumerate(self._sample_rows):
            grid_row = i + 2  # Account for header (row 0) and separator (row 1)

            # Update number label
            row_data['number_lbl'].setText(str(i + 1))

            # Add all widgets to grid at correct positions
            self._samples_grid.addWidget(row_data['number_lbl'], grid_row, 0)
            self._samples_grid.addWidget(row_data['name_edit'], grid_row, 1)
            self._samples_grid.addWidget(row_data['struct_combo'], grid_row, 2)
            self._samples_grid.addWidget(row_data['notes_edit'], grid_row, 3)
            self._samples_grid.addWidget(row_data['del_btn'], grid_row, 4)



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