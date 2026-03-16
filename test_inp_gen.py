import sys
from unittest.mock import MagicMock
import os

# Mock Qt stuff
sys.modules['qtpy'] = MagicMock()
sys.modules['qtpy.QtWidgets'] = MagicMock()
sys.modules['qtpy.QtCore'] = MagicMock()
sys.modules['pyvistaqt'] = MagicMock()

import plate_buckling_gui

class MockSpin:
    def __init__(self, val): self.val = val
    def value(self): return self.val

class MockCombo:
    def __init__(self, text): self.text = text
    def currentText(self): return self.text

class MockCheck:
    def __init__(self, checked): self.checked = checked
    def isChecked(self): return self.checked

# Monkey patch QMessageBox
plate_buckling_gui.QMessageBox = MagicMock()

gui = plate_buckling_gui.PlateAnalysisGUI()
gui.inp_a = MockSpin(100)
gui.inp_b = MockSpin(200)
gui.inp_E = MockSpin(70)
gui.inp_nu = MockSpin(0.3)
gui.inp_t = MockSpin(2)
gui.etype_combo = MockCombo('QUAD4')
gui.analysis_combo = MockCombo('Linear Static')
gui.inp_bm = MockSpin(5)
gui.inp_pressure = MockSpin(0.1)

# BCs
gui.bc_checks = {
    'Left (x=0)': [MockCheck(True)]*6,
    'Right (x=a)': [MockCheck(False)]*6,
    'Bottom (y=0)': [MockCheck(False)]*6,
    'Top (y=b)': [MockCheck(False)]*6,
}

# Loads
gui.load_inputs = {
    'Left': (MockSpin(0), MockSpin(0)),
    'Right': (MockSpin(100), MockSpin(100)),
    'Bottom': (MockSpin(0), MockSpin(0)),
    'Top': (MockSpin(0), MockSpin(0)),
}

gui.write_calculix_inp()
if os.path.exists('analysis.inp'):
    print('Inp file generated')
    with open('analysis.inp', 'r') as f:
        print(f.read()[:500])
else:
    print('Inp file NOT generated')
