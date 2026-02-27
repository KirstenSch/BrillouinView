from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QProgressBar
from PyQt5.QtCore import Qt


# Helper: extract nominal value from uncertainties.ufloat-like objects
def nominal(v):
    if v is None:
        return 0.0
    # uncertainties objects expose nominal_value
    if hasattr(v, "nominal_value"):
        try:
            return float(v.nominal_value)
        except Exception:
            pass
    try:
        return float(v)
    except Exception:
        return 0.0
    

class WaitDialog(QDialog):
    def __init__(self, parent=None, text="I am working on it, give me a moment ..."):
        super().__init__(parent)
        self.setWindowTitle("Please Wait")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(text))
        bar = QProgressBar()
        bar.setRange(0, 0)  # indeterminate animated bar
        layout.addWidget(bar)
        self.setFixedSize(300, 100)