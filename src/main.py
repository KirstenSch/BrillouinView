import os
import sys
import multiprocessing as mp

# Force X11 backend before importing PyQt5
os.environ['QT_QPA_PLATFORM'] = 'xcb'

from PyQt5.QtWidgets import QApplication
from brillouinview.gui.app import BrillouinViewApp

if __name__ == "__main__":
    mp.freeze_support()
    app = QApplication(sys.argv)
    main_window = BrillouinViewApp()
    main_window.show()
    sys.exit(app.exec_())