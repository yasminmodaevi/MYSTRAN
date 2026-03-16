import sys
import os
import numpy as np
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
# Mock QMessageBox to avoid blocking
import qtpy.QtWidgets
from unittest.mock import MagicMock
qtpy.QtWidgets.QMessageBox = MagicMock()

from qtpy.QtWidgets import QApplication, QTabWidget
from plate_buckling_gui import PlateAnalysisGUI

def capture():
    app = QApplication(sys.argv)
    gui = PlateAnalysisGUI()
    # Generate mesh
    gui.generate_mesh()
    # Switch to Visualization tab
    tabs = gui.findChild(QTabWidget)
    tabs.setCurrentIndex(2)
    gui.show()
    # Give it a bit more time for vtk
    app.processEvents()
    gui.grab().save('mesh_screenshot.png')
    print("Screenshot saved to mesh_screenshot.png")

if __name__ == "__main__":
    capture()
