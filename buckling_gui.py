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

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

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

        # Spring Group
        spring_group = QGroupBox("Spring Elements")
        spring_layout = QFormLayout()
        self.txt_k = QLineEdit("1.0")
        self.txt_s_len = QLineEdit("20.0")
        spring_layout.addRow("Stiffness (N/mm):", self.txt_k)
        spring_layout.addRow("Spring Length (mm):", self.txt_s_len)
        spring_group.setLayout(spring_layout)
        sidebar_layout.addWidget(spring_group)

        # Material Group
        mat_group = QGroupBox("Material")
        mat_layout = QFormLayout()
        self.txt_E = QLineEdit("70.0") # GPa
        self.txt_nu = QLineEdit("0.33")
        self.txt_rho = QLineEdit("2.72e-9") # t/mm3
        mat_layout.addRow("E (GPa):", self.txt_E)
        mat_layout.addRow("Poisson's nu:", self.txt_nu)
        mat_layout.addRow("Density (t/mm3):", self.txt_rho)
        mat_group.setLayout(mat_layout)
        sidebar_layout.addWidget(mat_group)

        # Analysis Group
        ana_group = QGroupBox("Analysis")
        ana_layout = QFormLayout()
        self.txt_load = QLineEdit("100.0") # N
        self.cmb_dir = QComboBox()
        self.cmb_dir.addItems(["X-Direction", "Y-Direction"])
        self.cmb_load_type = QComboBox()
        self.cmb_load_type.addItems(["Uniform Nodal Force", "Consistent Nodal Loads"])
        self.cmb_form = QComboBox()
        self.cmb_form.addItems(["Mindlin", "Kirchhoff"])
        self.txt_modes = QLineEdit("10")
        ana_layout.addRow("Total Load (N):", self.txt_load)
        ana_layout.addRow("Load Direction:", self.cmb_dir)
        ana_layout.addRow("Load Type:", self.cmb_load_type)
        ana_layout.addRow("Formulation:", self.cmb_form)
        ana_layout.addRow("Num Modes:", self.txt_modes)
        ana_group.setLayout(ana_layout)
        sidebar_layout.addWidget(ana_group)

        self.btn_run = QPushButton("Run Analysis")
        self.btn_run.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_run.clicked.connect(self.run_analysis)
        sidebar_layout.addWidget(self.btn_run)

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

        self.plotter = QtInteractor(self)
        splitter.addWidget(sidebar)
        splitter.addWidget(self.plotter)

    def run_analysis(self):
        try:
            L, W, t, d_hole = float(self.txt_L.text()), float(self.txt_W.text()), float(self.txt_t.text()), float(self.txt_d_hole.text())
            E, nu = float(self.txt_E.text()) * 1000, float(self.txt_nu.text())
            load, k_spring = float(self.txt_load.text()), float(self.txt_k.text())
            num_modes = int(self.txt_modes.text())
            formulation = self.cmb_form.currentText()
            direction = self.cmb_dir.currentText()[0]
            load_type = 'uniform' if "Uniform" in self.cmb_load_type.currentText() else 'consistent'

            self.lbl_status.setText("Solving...")
            QApplication.processEvents()

            nr, nt = 15, 60
            self.analysis = PlateAnalysis(L, W, t, E, nu, d_hole, (nr, nt))
            self.modes = self.analysis.solve_buckling(load, k_spring, direction, num_modes, formulation, load_type)

            self.cmb_modes.clear()
            for i, (val, _) in enumerate(self.modes):
                crit_load = val * load
                self.cmb_modes.addItem(f"Mode {i+1}: Crit Load = {crit_load:.4f} N (Factor: {val:.4f})")

            self.lbl_status.setText("Analysis Successful.")
            self.update_plot()
        except Exception as e:
            self.lbl_status.setText(f"Error: {str(e)}")

    def update_plot(self):
        if not self.analysis or self.cmb_modes.currentIndex() < 0: return
        idx = self.cmb_modes.currentIndex()
        val, u_active = self.modes[idx]

        tol = 1e-6
        all_edge_nodes = np.unique(np.concatenate([
            np.where(np.abs(self.analysis.nodes[:,0])<tol)[0],
            np.where(np.abs(self.analysis.nodes[:,0]-self.analysis.L)<tol)[0],
            np.where(np.abs(self.analysis.nodes[:,1])<tol)[0],
            np.where(np.abs(self.analysis.nodes[:,1]-self.analysis.W)<tol)[0]
        ]))
        fixed_dofs = [n*6+2 for n in all_edge_nodes]
        active_dofs = np.setdiff1d(np.arange(self.analysis.num_dofs), fixed_dofs)
        u_full = np.zeros(self.analysis.num_dofs); u_full[active_dofs] = u_active
        uz = u_full[2::6]

        cells = np.column_stack([np.full(len(self.analysis.elements), 4), self.analysis.elements]).flatten()
        grid = pv.UnstructuredGrid(cells, np.full(len(self.analysis.elements), 9, dtype=np.int8), self.analysis.nodes)

        scale = self.analysis.L * 0.1 / (np.max(np.abs(uz)) + 1e-9)
        warped = grid.copy(); warped.points[:, 2] = uz * scale

        self.plotter.clear()
        self.plotter.add_mesh(warped, scalars=uz, cmap="viridis", show_edges=True, scalar_bar_args={"title": "Buckling Mode (UZ)"})
        # Add nodes
        self.plotter.add_mesh(warped.points, color="black", point_size=3, render_points_as_spheres=True, label="Nodes")

        # Visualize 8 Springs (2 at each corner: X and Y)
        try:
            s_len = float(self.txt_s_len.text())
            spring_points, spring_lines = [], []
            for i, c_idx in enumerate(self.analysis.corner_indices):
                p_start = warped.points[c_idx]

                # Spring in X
                p_end_x = p_start.copy()
                if p_start[0] < self.analysis.L/2: p_end_x[0] -= s_len
                else: p_end_x[0] += s_len
                spring_points.extend([p_start, p_end_x])
                spring_lines.extend([2, 4*i, 4*i+1])

                # Spring in Y
                p_end_y = p_start.copy()
                if p_start[1] < self.analysis.W/2: p_end_y[1] -= s_len
                else: p_end_y[1] += s_len
                spring_points.extend([p_start, p_end_y])
                spring_lines.extend([2, 4*i+2, 4*i+3])

            spring_mesh = pv.PolyData(np.array(spring_points), lines=np.array(spring_lines))
            self.plotter.add_mesh(spring_mesh, color="red", line_width=4, label="Corner Springs")
            # Show spring tips (ground)
            ground_pts = np.array(spring_points)[1::2]
            self.plotter.add_mesh(ground_pts, color="blue", point_size=6, render_points_as_spheres=True)
        except: pass

        self.plotter.add_text(f"Mode {idx+1}\nFactor: {val:.6f}", position='upper_left', font_size=10)
        self.plotter.reset_camera()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BucklingGUI()
    window.show()
    sys.exit(app.exec())
