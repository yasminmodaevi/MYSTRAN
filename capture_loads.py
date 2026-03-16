import sys
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from qtpy.QtWidgets import QApplication, QTabWidget
from plate_buckling_gui import PlateAnalysisGUI

def capture():
    app = QApplication(sys.argv)
    gui = PlateAnalysisGUI()
    # Switch to Loads tab
    tabs = gui.findChild(QTabWidget)
    tabs.setCurrentIndex(1)
    gui.show()
    gui.grab().save('loads_screenshot.png')
    print("Screenshot saved to loads_screenshot.png")

if __name__ == "__main__":
    capture()
