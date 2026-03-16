import sys
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import qtpy.QtWidgets
from unittest.mock import MagicMock
qtpy.QtWidgets.QMessageBox = MagicMock()
from plate_buckling_gui import PlateAnalysisGUI

def test():
    app = qtpy.QtWidgets.QApplication(sys.argv)
    gui = PlateAnalysisGUI()
    gui.etype_combo.setCurrentText('QUAD8')
    gui.generate_mesh()
    if os.path.exists('plate.msh'):
        print('QUAD8 Mesh generated')
        gui.write_calculix_inp()
        with open('analysis.inp', 'r') as f:
            content = f.read()
            if '*ELEMENT, TYPE=S8' in content:
                print('Found S8 elements in .inp')
            else:
                print('S8 NOT found in .inp')
    else:
        print('QUAD8 Mesh failed')

if __name__ == "__main__":
    test()
