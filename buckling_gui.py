import sys
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox, QFormLayout, QGroupBox, QSplitter)
from PyQt6.QtCore import Qt
import pyvista as pv
from pyvistaqt import QtInteractor
from plate_analysis import PlateAnalysis

class BucklingGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plate Buckling Analysis - QUAD4 Shell")
        self.resize(1300, 850)

        self.analysis = None
        self.modes = []

        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Sidebar for inputs
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar.setMaximumWidth(400)

        # Geometry Group
        geo_group = QGroupBox("Geometry (mm)")
        geo_layout = QFormLayout()
        self.txt_L = QLineEdit("200")
        self.txt_W = QLineEdit("200")
        self.txt_t = QLineEdit("2.0")
        self.txt_d_hole = QLineEdit("100")
        geo_layout.addRow("Length (X):", self.txt_L)
        geo_layout.addRow("Width (Y):", self.txt_W)
        geo_layout.addRow("Thickness:", self.txt_t)
        geo_layout.addRow("Hole Diameter:", self.txt_d_hole)
        geo_group.setLayout(geo_layout)
        sidebar_layout.addWidget(geo_group)

        # Material Group
        mat_group = QGroupBox("Material")
        mat_layout = QFormLayout()
        self.txt_E = QLineEdit("71.7") # GPa
        self.txt_nu = QLineEdit("0.33")
        mat_layout.addRow("E (GPa):", self.txt_E)
        mat_layout.addRow("Poisson's nu:", self.txt_nu)
        mat_group.setLayout(mat_layout)
        sidebar_layout.addWidget(mat_group)

        # Analysis Group
        ana_group = QGroupBox("Analysis")
        ana_layout = QFormLayout()
        self.txt_stress = QLineEdit("10.0") # MPa
        self.cmb_dir = QComboBox()
        self.cmb_dir.addItems(["X-Direction", "Y-Direction"])
        self.cmb_load_type = QComboBox()
        self.cmb_load_type.addItems(["Uniform Nodal Force", "Consistent Nodal Loads"])
        self.cmb_form = QComboBox()
        self.cmb_form.addItems(["Mindlin", "Kirchhoff"])
        self.txt_modes = QLineEdit("10")
        ana_layout.addRow("Applied Stress (MPa):", self.txt_stress)
        ana_layout.addRow("Load Direction:", self.cmb_dir)
        ana_layout.addRow("Load Type:", self.cmb_load_type)
        ana_layout.addRow("Formulation:", self.cmb_form)
        ana_layout.addRow("Num Modes:", self.txt_modes)
        ana_group.setLayout(ana_layout)
        sidebar_layout.addWidget(ana_group)

        # Run Button
        self.btn_run = QPushButton("Run Analysis")
        self.btn_run.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_run.clicked.connect(self.run_analysis)
        sidebar_layout.addWidget(self.btn_run)

        # Results Group
        res_group = QGroupBox("Results")
        res_layout = QVBoxLayout()
        self.lbl_status = QLabel("Ready")
        self.cmb_modes = QComboBox()
        self.cmb_modes.currentIndexChanged.connect(self.update_plot)
        res_layout.addWidget(self.lbl_status)
        res_layout.addWidget(QLabel("Select Mode:"))
        res_layout.addWidget(self.cmb_modes)
        res_group.setLayout(res_layout)
        sidebar_layout.addWidget(res_group)

        sidebar_layout.addStretch()

        # Visualization
        self.plotter = QtInteractor(self)

        splitter.addWidget(sidebar)
        splitter.addWidget(self.plotter)

    def run_analysis(self):
        try:
            L = float(self.txt_L.text())
            W = float(self.txt_W.text())
            t = float(self.txt_t.text())
            d_hole = float(self.txt_d_hole.text())
            E = float(self.txt_E.text()) * 1000 # Convert GPa to MPa
            nu = float(self.txt_nu.text())
            stress = float(self.txt_stress.text())
            num_modes = int(self.txt_modes.text())
            formulation = self.cmb_form.currentText()
            direction = self.cmb_dir.currentText()[0] # 'X' or 'Y'
            load_type = 'uniform' if "Uniform" in self.cmb_load_type.currentText() else 'consistent'

            self.lbl_status.setText("Solving...")
            QApplication.processEvents()

            nr, nt = 15, 60
            self.analysis = PlateAnalysis(L, W, t, E, nu, d_hole, (nr, nt))
            self.modes = self.analysis.solve_buckling(stress, direction, num_modes, formulation, load_type)

            self.cmb_modes.clear()
            for i, (val, _) in enumerate(self.modes):
                crit_stress = val * stress
                self.cmb_modes.addItem(f"Mode {i+1}: Crit Stress = {crit_stress:.4f} MPa (Factor: {val:.4f})")

            self.lbl_status.setText("Analysis Successful.")
            self.update_plot()

        except Exception as e:
            self.lbl_status.setText(f"Error: {str(e)}")

    def update_plot(self):
        if not self.analysis or self.cmb_modes.currentIndex() < 0:
            return

        idx = self.cmb_modes.currentIndex()
        val, u_active = self.modes[idx]

        # Reconstruct full u
        all_edge_nodes = np.unique(np.concatenate([
            np.where(np.abs(self.analysis.nodes[:,0])<1e-6)[0],
            np.where(np.abs(self.analysis.nodes[:,0]-self.analysis.L)<1e-6)[0],
            np.where(np.abs(self.analysis.nodes[:,1])<1e-6)[0],
            np.where(np.abs(self.analysis.nodes[:,1]-self.analysis.W)<1e-6)[0]
        ]))
        fixed_dofs = [n*6+2 for n in all_edge_nodes]
        active_dofs = np.setdiff1d(np.arange(self.analysis.num_dofs), fixed_dofs)
        u_full = np.zeros(self.analysis.num_dofs)
        u_full[active_dofs] = u_active

        uz = u_full[2::6]

        cells = np.column_stack([np.full(len(self.analysis.elements), 4), self.analysis.elements]).flatten()
        cell_type = np.full(len(self.analysis.elements), 9, dtype=np.int8)
        grid = pv.UnstructuredGrid(cells, cell_type, self.analysis.nodes)

        # Scale for visualization (max deformation 10% of L)
        scale = self.analysis.L * 0.1 / (np.max(np.abs(uz)) + 1e-9)
        warped = grid.copy()
        warped.points[:, 2] = uz * scale

        self.plotter.clear()
        self.plotter.add_mesh(warped, scalars=uz, cmap="viridis", show_edges=True,
                              scalar_bar_args={"title": "Buckling Mode Shape (UZ Displacement)"})
        self.plotter.add_text(f"Mode {idx+1}\nFactor: {val:.6f}", position='upper_left', font_size=10)
        self.plotter.reset_camera()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BucklingGUI()
    window.show()
    sys.exit(app.exec())
