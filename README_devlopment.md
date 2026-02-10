# Activate venv
```console
. .venv/bin/activate
```

# GUI changes
The GUI is set up with QT Designer
Use QT Designer to perform any changes in the GUI interface. Currently the following *.ui files exists. 
They are stored in /src/brillouinview/gui/ui
| File | Function |
| --- | --- |
| brillouinview_main_window.ui| Main Window of the App with tabs for the different Steps of the process |
| edit_calibration_settings.ui | Window to edit the Settings in the calibration tab |

## Change the GUI Interface
Open the file to be changed in the Qt Designer. Perform the changes, save and close the file.  

In a next step convert the *.ui file to a *.py file with the following command:
```console
pyuic5 src/brillouinview/gui/ui/brillouinview_main_window.ui -o src/brillouinview_main_window.ui.py  
```
```console
pyuic5 src/brillouinview/gui/ui/edit_calibration_settings.ui -o src/edit_calibration_settings.ui.py
```


# Building Executables

### Quick Build

**Linux/macOS:**
```bash
./build_dist.sh
```

**Windows:**
```cmd
build_dist.bat
```

**Using Python directly:**
```bash
python build_dist.py --name myapp --entry-point main_pyqt5.py
```

### Build Options

```bash
# One-file executable (default)
python build_dist.py --name myapp --entry-point main_pyqt5.py

# One-directory bundle (faster startup, larger folder)
python build_dist.py --name myapp --entry-point main_pyqt5.py --onedir

# Don't clean build directories
python build_dist.py --no-clean

```



