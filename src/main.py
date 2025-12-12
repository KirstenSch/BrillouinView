import sys
from PyQt5.QtWidgets import QApplication

from brillouinview.gui.app import BrillouinViewApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = BrillouinViewApp()
    main_window.show()
    sys.exit(app.exec_())