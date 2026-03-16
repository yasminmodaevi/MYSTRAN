import sys
import os
# Use offscreen platform for headless environment
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from qtpy.QtWidgets import QApplication
from plate_buckling_gui import PlateAnalysisGUI

def capture():
    app = QApplication(sys.argv)
    gui = PlateAnalysisGUI()
    gui.show()
    # Give it a moment to render?
    gui.grab().save('gui_screenshot.png')
    print("Screenshot saved to gui_screenshot.png")

if __name__ == "__main__":
    capture()
