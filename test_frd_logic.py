import sys
import os
import numpy as np
from unittest.mock import MagicMock

# Mock
sys.modules['qtpy'] = MagicMock()
sys.modules['qtpy.QtWidgets'] = MagicMock()
sys.modules['qtpy.QtCore'] = MagicMock()
sys.modules['pyvistaqt'] = MagicMock()
sys.modules['gmsh'] = MagicMock()
sys.modules['pyvista'] = MagicMock()

import plate_buckling_gui

def test():
    gui = plate_buckling_gui.PlateAnalysisGUI()
    # Check if pyccx imports work in the methods
    print("Testing load_results logic...")
    # This will fail because analysis.frd doesn't exist, but we can mock it
    with open("analysis.frd", "w") as f:
        f.write("Fake FRD")

    # Mock ResultProcessor
    plate_buckling_gui.ResultProcessor = MagicMock()
    mock_rp = plate_buckling_gui.ResultProcessor.return_value
    mock_rp.numIncrements = 3

    gui.load_results()
    print(f"Items in combo: {[gui.res_combo.itemText(i) for i in range(gui.res_combo.count())]}")

if __name__ == "__main__":
    test()
