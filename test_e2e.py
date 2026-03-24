import os
import sys
# Set headless for Qt
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['PYVISTA_OFF_SCREEN'] = 'true'

from qtpy.QtWidgets import QApplication
from plate_analysis import PlateAnalysisApp
import numpy as np

def test_full_app():
    app = QApplication(sys.argv)
    window = PlateAnalysisApp()

    # Set small element size for speed
    window.inputs['n'].setText("100")
    window.inputs['a'].setText("500")
    window.inputs['b'].setText("500")

    print("Testing mesh generation...")
    window.generate_mesh()
    assert hasattr(window, 'mesh_gen')
    assert len(window.mesh_gen.elements) > 0
    print(f"Generated {len(window.mesh_gen.elements)} elements.")

    # Left fixed, others Simply Supported (D1,D2,D3)
    # Actually just use Simply Supported preset
    for edge in ['left', 'right', 'top', 'bottom']:
        for i, chk in enumerate(window.bc_checks[edge]):
            chk.setChecked(i < 3)

    # Right edge free in X to allow compression
    window.bc_checks['right'][0].setChecked(False)

    print("Testing linear static analysis...")
    window.analysis_type.setCurrentText("Linear Static")
    window.load_z.setText("0.1")
    window.run_analysis()

    print("Testing normal modes...")
    window.analysis_type.setCurrentText("Normal Modes")
    window.run_analysis()

    print("Testing buckling...")
    window.analysis_type.setCurrentText("Linear Buckling")
    window.load_x_start.setText("-1000")
    window.load_x_end.setText("-1000")
    window.run_analysis()

    print("Testing nonlinear...")
    window.analysis_type.setCurrentText("Nonlinear Static")
    window.run_analysis()

    print("End-to-end test completed successfully.")

if __name__ == "__main__":
    test_full_app()
