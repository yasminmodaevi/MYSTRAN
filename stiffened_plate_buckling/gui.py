import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QGroupBox, QFormLayout, QTabWidget, QSplitter,
                             QDialog, QCheckBox)
from PySide6.QtCore import Qt
import numpy as np

try:
    import pyvista as pv
    from pyvistaqt import QtInteractor
    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False

from mesh_gen import MeshGenerator
from solver import FEModel, Solver, apply_edge_loads, apply_pressure_load

class BCDialog(QDialog):
    def __init__(self, current_bcs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Granular BC Control")
        self.layout = QFormLayout(self)
        self.checks = {}
        for edge in ["Left (x=0)", "Right (x=L)", "Bottom (y=0)", "Top (y=W)"]:
            h_layout = QHBoxLayout()
            self.checks[edge] = []
            for dof in ["Ux", "Uy", "Uz", "Rx", "Ry", "Rz"]:
                cb = QCheckBox(dof)
                if current_bcs.get(edge, {}).get(dof, False): cb.setChecked(True)
                h_layout.addWidget(cb)
                self.checks[edge].append(cb)
            self.layout.addRow(edge, h_layout)

        self.btn = QPushButton("OK")
        self.btn.clicked.connect(self.accept)
        self.layout.addRow(self.btn)

    def get_bcs(self):
        res = {}
        dof_names = ["Ux", "Uy", "Uz", "Rx", "Ry", "Rz"]
        for edge, cbs in self.checks.items():
            res[edge] = {dof_names[i]: cbs[i].isChecked() for i in range(6)}
        return res

class BucklingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stiffened Plate Buckling Analysis")
        self.resize(1200, 800)

        self.nodes = None; self.elements = None
        self.custom_bcs = {
            "Left (x=0)": {"Uz": True}, "Right (x=L)": {"Uz": True},
            "Bottom (y=0)": {"Uz": True}, "Top (y=W)": {"Uz": True}
        }

        self.central_widget = QWidget(); self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        self.setup_sidebar()
        if HAS_PYVISTA and os.environ.get('QT_QPA_PLATFORM') != 'offscreen': self.setup_viewer()
        else: self.plotter = None; self.main_layout.addWidget(QLabel("Visualization not available"))

    def setup_sidebar(self):
        self.sidebar = QTabWidget(); self.sidebar.setFixedWidth(400)

        self.plate_tab = QWidget(); self.plate_layout = QFormLayout(self.plate_tab)
        self.unit_sys = QComboBox(); self.unit_sys.addItems(["SI (mm, N, MPa)", "Imperial (in, lb, psi)"])
        self.plate_layout.addRow("Unit System:", self.unit_sys)
        self.plate_L = QLineEdit("1000"); self.plate_W = QLineEdit("1000"); self.plate_t = QLineEdit("10")
        self.plate_layout.addRow("Length (L):", self.plate_L); self.plate_layout.addRow("Width (W):", self.plate_W); self.plate_layout.addRow("Thickness (t):", self.plate_t)
        self.mat_type = QComboBox(); self.mat_type.addItems(["Steel", "Aluminum", "Custom"]); self.mat_type.currentIndexChanged.connect(self.update_material_fields)
        self.plate_layout.addRow("Material:", self.mat_type)
        self.mat_E = QLineEdit("210000"); self.mat_nu = QLineEdit("0.3")
        self.plate_layout.addRow("Young's Modulus (E):", self.mat_E); self.plate_layout.addRow("Poisson's Ratio (nu):", self.mat_nu)
        self.sidebar.addTab(self.plate_tab, "Plate")

        self.stiff_tab = QWidget(); self.stiff_layout = QVBoxLayout(self.stiff_tab)
        self.stiff_table = QTableWidget(0, 8); self.stiff_table.setHorizontalHeaderLabels(["Type", "x1", "y1", "x2", "y2", "h", "tw", "fw"])
        self.stiff_layout.addWidget(self.stiff_table)
        self.add_stiff_btn = QPushButton("Add Stiffener"); self.add_stiff_btn.clicked.connect(self.add_stiffener_row)
        self.stiff_layout.addWidget(self.add_stiff_btn)
        self.sidebar.addTab(self.stiff_tab, "Stiffeners")

        self.load_tab = QWidget(); self.load_layout = QFormLayout(self.load_tab)
        self.load_nx = QLineEdit("1.0"); self.load_ny = QLineEdit("0.0"); self.load_nxy = QLineEdit("0.0"); self.load_press = QLineEdit("0.0")
        self.load_layout.addRow("Nx (Comp +):", self.load_nx); self.load_layout.addRow("Ny (Comp +):", self.load_ny); self.load_layout.addRow("Nxy (Shear):", self.load_nxy); self.load_layout.addRow("Pressure (z):", self.load_press)
        self.bc_type = QComboBox(); self.bc_type.addItems(["SSSS", "CCCC", "Custom"])
        self.bc_cfg_btn = QPushButton("Configure Custom BCs"); self.bc_cfg_btn.clicked.connect(self.configure_bcs)
        self.load_layout.addRow("BC Type:", self.bc_type); self.load_layout.addRow(self.bc_cfg_btn)
        self.sidebar.addTab(self.load_tab, "Loads/BCs")

        self.action_layout = QVBoxLayout()
        self.run_mesh_btn = QPushButton("Generate Mesh"); self.run_mesh_btn.clicked.connect(self.run_mesh)
        self.run_solve_btn = QPushButton("Run Analysis"); self.run_solve_btn.clicked.connect(self.run_analysis)
        self.action_layout.addWidget(self.run_mesh_btn); self.action_layout.addWidget(self.run_solve_btn)
        self.plate_layout.addRow(self.action_layout)
        self.main_layout.addWidget(self.sidebar)

    def setup_viewer(self):
        self.plotter = QtInteractor(self.central_widget)
        self.main_layout.addWidget(self.plotter.interactor)
        self.plotter.show_axes(); self.plotter.view_isometric()

    def update_material_fields(self):
        m = self.mat_type.currentText()
        if m == "Steel": self.mat_E.setText("210000"); self.mat_nu.setText("0.3")
        elif m == "Aluminum": self.mat_E.setText("70000"); self.mat_nu.setText("0.33")

    def configure_bcs(self):
        dlg = BCDialog(self.custom_bcs, self)
        if dlg.exec(): self.custom_bcs = dlg.get_bcs()

    def add_stiffener_row(self):
        row = self.stiff_table.rowCount(); self.stiff_table.insertRow(row)
        type_cb = QComboBox(); type_cb.addItems(["Flat", "L", "T", "I"])
        self.stiff_table.setCellWidget(row, 0, type_cb)
        for i in range(1, 8): self.stiff_table.setItem(row, i, QTableWidgetItem("0"))

    def get_stiffeners_from_ui(self):
        stiffs = []
        for r in range(self.stiff_table.rowCount()):
            stiffs.append({
                'type': self.stiff_table.cellWidget(r, 0).currentText(),
                'start': [float(self.stiff_table.item(r, 1).text()), float(self.stiff_table.item(r, 2).text())],
                'end': [float(self.stiff_table.item(r, 3).text()), float(self.stiff_table.item(r, 4).text())],
                'height': float(self.stiff_table.item(r, 5).text()),
                'thickness': float(self.stiff_table.item(r, 6).text()),
                'flange_width': float(self.stiff_table.item(r, 7).text())
            })
        return stiffs

    def run_mesh(self):
        L, W = float(self.plate_L.text()), float(self.plate_W.text())
        mg = MeshGenerator()
        mg.generate_stiffened_plate(L, W, self.get_stiffeners_from_ui(), mesh_size=L/20)
        self.nodes, self.elements = mg.get_mesh_data()
        if self.plotter: self.plot_mesh()

    def plot_mesh(self, mode_vec=None, scale=1.0):
        self.plotter.clear()
        nodes = self.nodes
        if mode_vec is not None: nodes = nodes + mode_vec.reshape((-1, 6))[:, :3] * scale
        mesh = pv.PolyData(nodes, [item for e in self.elements for item in [4] + e['nodes']])
        self.plotter.add_mesh(mesh, show_edges=True, color='lightblue'); self.plotter.reset_camera()

    def run_analysis(self):
        if self.nodes is None: self.run_mesh()
        model = FEModel(); E, nu = float(self.mat_E.text()), float(self.mat_nu.text())
        model.set_material(1000, E, nu)
        stiffs = self.get_stiffeners_from_ui()
        for idx in range(len(stiffs)): model.set_material(2000 + idx, E, nu)
        for p in self.nodes: model.add_node(*p)
        for e in self.elements:
            t = float(self.plate_t.text()) if e['group'] == 1000 else stiffs[e['group']-2000]['thickness']
            model.add_element(e['nodes'], e['group'], t)

        L, W = float(self.plate_L.text()), float(self.plate_W.text())
        dof_names = ["Ux", "Uy", "Uz", "Rx", "Ry", "Rz"]
        for i, p in enumerate(self.nodes):
            bc = [None]*6
            edges = []
            if np.isclose(p[0], 0): edges.append("Left (x=0)")
            if np.isclose(p[0], L): edges.append("Right (x=L)")
            if np.isclose(p[1], 0): edges.append("Bottom (y=0)")
            if np.isclose(p[1], W): edges.append("Top (y=W)")

            for edge in edges:
                if self.bc_type.currentText() == "SSSS": bc[2] = 0
                elif self.bc_type.currentText() == "CCCC": bc = [0, 0, 0, 0, 0, 0]
                elif self.bc_type.currentText() == "Custom":
                    for d_idx, d_name in enumerate(dof_names):
                        if self.custom_bcs[edge][d_name]: bc[d_idx] = 0

            # Stability
            if np.isclose(p[0], 0) and np.isclose(p[1], 0): bc[0]=0; bc[1]=0
            elif np.isclose(p[0], L) and np.isclose(p[1], 0): bc[1]=0
            model.set_bc(i, bc)

        apply_edge_loads(model, float(self.load_nx.text()), float(self.load_ny.text()), float(self.load_nxy.text()), L, W)
        apply_pressure_load(model, float(self.load_press.text()))

        solver = Solver(model); solver.assemble(); vals, vecs = solver.solve_buckling(n_modes=1)
        print(f"Lowest Buckling Factor: {vals[0]}")
        if self.plotter: self.plot_mesh(mode_vec=vecs[0], scale=L/10 / np.abs(vecs[0]).max())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BucklingApp()
    window.show()
    sys.exit(app.exec())
