import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from brillouinview_main_window_ui import Ui_MainWindow


class BrillouinViewApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = BrillouinViewApp()
    main_window.show()
    sys.exit(app.exec_())