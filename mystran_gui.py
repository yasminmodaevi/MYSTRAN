import sys
import os
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QGridLayout, QLabel, QLineEdit, QComboBox, QPushButton,
                             QCheckBox, QGroupBox, QRadioButton, QButtonGroup, QTabWidget,
                             QScrollArea, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import pygmsh
import gmsh

# pyccx for buckling problem setup
try:
    import pyccx
    from pyccx.mesh import Mesher
    from pyccx.analysis import Simulation, AnalysisType, ShellMaterialAssignment
    from pyccx.material import ElastoPlasticMaterial
    from pyccx.loadcase import LoadCase
    from pyccx.bc import BoundaryCondition
    PYCCX_AVAILABLE = True
except ImportError:
    PYCCX_AVAILABLE = False

class MYSTRANGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("pyccx Buckling Mesh & BC Generator")
        self.resize(1000, 800)

        self.init_ui()
        self.mesh_data = None
        self.nodes = None
        self.elements = None

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Left Panel: Inputs
        left_panel = QScrollArea()
        left_panel.setFixedWidth(380)
        left_panel.setWidgetResizable(True)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Geometry Group
        geom_group = QGroupBox("Geometry")
        geom_layout = QGridLayout()
        geom_layout.addWidget(QLabel("Width:"), 0, 0)
        self.width_input = QLineEdit("100.0")
        geom_layout.addWidget(self.width_input, 0, 1)

        geom_layout.addWidget(QLabel("Height:"), 1, 0)
        self.height_input = QLineEdit("50.0")
        geom_layout.addWidget(self.height_input, 1, 1)

        geom_layout.addWidget(QLabel("Hole Radius:"), 2, 0)
        self.hole_rad_input = QLineEdit("10.0")
        geom_layout.addWidget(self.hole_rad_input, 2, 1)

        geom_layout.addWidget(QLabel("Hole X:"), 3, 0)
        self.hole_x_input = QLineEdit("50.0")
        geom_layout.addWidget(self.hole_x_input, 3, 1)

        geom_layout.addWidget(QLabel("Hole Y:"), 4, 0)
        self.hole_y_input = QLineEdit("25.0")
        geom_layout.addWidget(self.hole_y_input, 4, 1)

        geom_layout.addWidget(QLabel("Mesh Size:"), 5, 0)
        self.mesh_size_input = QLineEdit("5.0")
        geom_layout.addWidget(self.mesh_size_input, 5, 1)

        geom_group.setLayout(geom_layout)
        left_layout.addWidget(geom_group)

        # Material Group
        mat_group = QGroupBox("Material & Thickness")
        mat_layout = QGridLayout()
        mat_layout.addWidget(QLabel("Young's Modulus (E):"), 0, 0)
        self.e_input = QLineEdit("210000.0")
        mat_layout.addWidget(self.e_input, 0, 1)

        mat_layout.addWidget(QLabel("Poisson's Ratio (nu):"), 1, 0)
        self.nu_input = QLineEdit("0.3")
        mat_layout.addWidget(self.nu_input, 1, 1)

        mat_layout.addWidget(QLabel("Thickness:"), 2, 0)
        self.thick_input = QLineEdit("1.0")
        mat_layout.addWidget(self.thick_input, 2, 1)

        mat_group.setLayout(mat_layout)
        left_layout.addWidget(mat_group)

        # Buckling Analysis Group
        buck_group = QGroupBox("Buckling Settings")
        buck_layout = QGridLayout()
        buck_layout.addWidget(QLabel("Number of Modes:"), 0, 0)
        self.modes_input = QLineEdit("10")
        buck_layout.addWidget(self.modes_input, 0, 1)
        buck_group.setLayout(buck_layout)
        left_layout.addWidget(buck_group)

        # Boundary Conditions Group
        bc_group = QGroupBox("Boundary Conditions")
        bc_layout = QVBoxLayout()

        self.bc_edge_combo = QComboBox()
        self.bc_edge_combo.addItems(["None", "Left", "Right", "Top", "Bottom"])
        bc_layout.addWidget(QLabel("Select Edge:"))
        bc_layout.addWidget(self.bc_edge_combo)

        bc_layout.addWidget(QLabel("Constrain DOFs:"))
        dof_layout = QHBoxLayout()
        self.dof_checks = []
        for i in range(1, 7):
            cb = QCheckBox(str(i))
            self.dof_checks.append(cb)
            dof_layout.addWidget(cb)
        bc_layout.addLayout(dof_layout)

        self.add_bc_btn = QPushButton("Set BC for Selected Edge")
        bc_layout.addWidget(self.add_bc_btn)

        self.bc_list_label = QLabel("Active BCs: None")
        bc_layout.addWidget(self.bc_list_label)

        bc_group.setLayout(bc_layout)
        left_layout.addWidget(bc_group)

        # Loads Group
        load_group = QGroupBox("Loads (Pre-stress)")
        load_layout = QVBoxLayout()

        self.load_edge_combo = QComboBox()
        self.load_edge_combo.addItems(["None", "Left", "Right", "Top", "Bottom"])
        load_layout.addWidget(QLabel("Select Edge:"))
        load_layout.addWidget(self.load_edge_combo)

        load_layout.addWidget(QLabel("Direction:"))
        self.load_dir_combo = QComboBox()
        self.load_dir_combo.addItems(["X", "Y", "Z"])
        load_layout.addWidget(self.load_dir_combo)

        load_layout.addWidget(QLabel("Type:"))
        self.load_type_combo = QComboBox()
        self.load_type_combo.addItems(["Constant", "Linear"])
        load_layout.addWidget(self.load_type_combo)

        load_mag_layout = QGridLayout()
        load_mag_layout.addWidget(QLabel("Magnitude (Start):"), 0, 0)
        self.load_mag_start = QLineEdit("100.0")
        load_mag_layout.addWidget(self.load_mag_start, 0, 1)

        load_mag_layout.addWidget(QLabel("Magnitude (End):"), 1, 0)
        self.load_mag_end = QLineEdit("100.0")
        load_mag_layout.addWidget(self.load_mag_end, 1, 1)
        load_layout.addLayout(load_mag_layout)

        self.add_load_btn = QPushButton("Set Load for Selected Edge")
        load_layout.addWidget(self.add_load_btn)

        self.load_list_label = QLabel("Active Loads: None")
        load_layout.addWidget(self.load_list_label)

        load_group.setLayout(load_layout)
        left_layout.addWidget(load_group)

        # Action Buttons
        self.mesh_btn = QPushButton("Generate Mesh")
        self.mesh_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        left_layout.addWidget(self.mesh_btn)

        self.export_inp_btn = QPushButton("Generate CalculiX .inp")
        self.export_inp_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        left_layout.addWidget(self.export_inp_btn)

        self.export_bdf_btn = QPushButton("Generate MYSTRAN .bdf")
        self.export_bdf_btn.setStyleSheet("background-color: #008CBA; color: white; font-weight: bold;")
        left_layout.addWidget(self.export_bdf_btn)

        left_layout.addStretch()
        left_panel.setWidget(left_widget)
        main_layout.addWidget(left_panel)

        # Right Panel: Visualization
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.mpl_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        right_layout.addWidget(self.mpl_canvas)
        main_layout.addWidget(right_panel, stretch=1)

        # Connect signals
        self.mesh_btn.clicked.connect(self.on_generate_mesh)
        self.export_inp_btn.clicked.connect(self.on_export_inp)
        self.export_bdf_btn.clicked.connect(self.on_export_bdf)

        # Data storage
        self.bc_data = {}
        self.load_data = {}

        self.add_bc_btn.clicked.connect(self.add_bc)
        self.add_load_btn.clicked.connect(self.add_load)

    def add_bc(self):
        edge = self.bc_edge_combo.currentText()
        if edge == "None": return
        dofs = "".join([str(i+1) for i, cb in enumerate(self.dof_checks) if cb.isChecked()])
        if not dofs:
            if edge in self.bc_data: del self.bc_data[edge]
        else:
            self.bc_data[edge] = dofs
        self.update_bc_label()

    def update_bc_label(self):
        if not self.bc_data:
            self.bc_list_label.setText("Active BCs: None")
        else:
            txt = "Active BCs: " + ", ".join([f"{k}:{v}" for k, v in self.bc_data.items()])
            self.bc_list_label.setText(txt)

    def add_load(self):
        edge = self.load_edge_combo.currentText()
        if edge == "None": return
        mag_start = float(self.load_mag_start.text())
        mag_end = float(self.load_mag_end.text())
        direction = self.load_dir_combo.currentText()
        l_type = self.load_type_combo.currentText()

        self.load_data[edge] = {
            'dir': direction,
            'type': l_type,
            'start': mag_start,
            'end': mag_end
        }
        self.update_load_label()

    def update_load_label(self):
        if not self.load_data:
            self.load_list_label.setText("Active Loads: None")
        else:
            txt = "Active Loads: " + ", ".join([f"{k}:{v['start']}->{v['end']} {v['dir']}" for k, v in self.load_data.items()])
            self.load_list_label.setText(txt)

    def on_generate_mesh(self):
        try:
            width = float(self.width_input.text())
            height = float(self.height_input.text())
            r = float(self.hole_rad_input.text())
            hx = float(self.hole_x_input.text())
            hy = float(self.hole_y_input.text())
            ms = float(self.mesh_size_input.text())

            if hx - r < 0 or hx + r > width or hy - r < 0 or hy + r > height:
                QMessageBox.warning(self, "Validation Error", "Hole must be inside the rectangle!")
                return

            with pygmsh.occ.Geometry() as geom:
                rect = geom.add_rectangle([0.0, 0.0, 0.0], width, height)
                hole = geom.add_disk([hx, hy, 0.0], r)
                geom.boolean_difference(rect, hole)
                gmsh.option.setNumber("Mesh.RecombineAll", 1)
                gmsh.option.setNumber("Mesh.Algorithm", 8)
                gmsh.option.setNumber("Mesh.SubdivisionAlgorithm", 1)
                geom.characteristic_length_min = ms
                geom.characteristic_length_max = ms
                self.mesh_data = geom.generate_mesh()

            self.nodes = self.mesh_data.points
            self.elements = self.mesh_data.cells_dict.get('quad', [])

            if len(self.elements) == 0:
                QMessageBox.warning(self, "Mesh Error", "No QUAD4 elements generated!")
                return

            self.update_visualization()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate mesh: {str(e)}")

    def update_visualization(self):
        if self.nodes is None or self.elements is None: return
        self.mpl_canvas.axes.clear()
        for elem in self.elements:
            pts = self.nodes[elem]
            pts = np.vstack([pts, pts[0]])
            self.mpl_canvas.axes.plot(pts[:, 0], pts[:, 1], pts[:, 2], color='blue', linewidth=0.5)
        self.draw_bcs_loads_mpl()
        self.mpl_canvas.axes.set_xlabel('X')
        self.mpl_canvas.axes.set_ylabel('Y')
        self.mpl_canvas.axes.set_aspect('equal')
        self.mpl_canvas.draw()

    def get_edge_nodes(self, edge_name):
        width = float(self.width_input.text())
        height = float(self.height_input.text())
        tol = 1e-5
        if edge_name == "Left": return [i for i, p in enumerate(self.nodes) if abs(p[0]) < tol]
        elif edge_name == "Right": return [i for i, p in enumerate(self.nodes) if abs(p[0] - width) < tol]
        elif edge_name == "Bottom": return [i for i, p in enumerate(self.nodes) if abs(p[1]) < tol]
        elif edge_name == "Top": return [i for i, p in enumerate(self.nodes) if abs(p[1] - height) < tol]
        return []

    def draw_bcs_loads_mpl(self):
        for edge, dofs in self.bc_data.items():
            node_ids = self.get_edge_nodes(edge)
            pts = self.nodes[node_ids]
            self.mpl_canvas.axes.scatter(pts[:,0], pts[:,1], pts[:,2], marker='^', color='red', s=50)
        for edge, data in self.load_data.items():
            node_ids = self.get_edge_nodes(edge)
            if not node_ids: continue
            pts = self.nodes[node_ids]
            idx = np.argsort(pts[:, 0 if edge in ["Top", "Bottom"] else 1])
            sorted_nodes = np.array(node_ids)[idx]
            for i, nid in enumerate(sorted_nodes):
                p = self.nodes[nid]
                mag = data['start'] + (data['end'] - data['start']) * (i / (len(sorted_nodes)-1 if len(sorted_nodes)>1 else 1))
                dx, dy, dz = (mag, 0, 0) if data['dir'] == 'X' else (0, mag, 0) if data['dir'] == 'Y' else (0, 0, mag)
                scale = 0.1 * float(self.width_input.text()) / (abs(mag) if mag != 0 else 1)
                self.mpl_canvas.axes.quiver(p[0], p[1], p[2], dx, dy, dz, length=scale*abs(mag), color='green')

    def on_export_inp(self):
        if self.nodes is None or self.elements is None:
            QMessageBox.warning(self, "Error", "Generate mesh first!")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save CalculiX INP", "", "CalculiX Input (*.inp)")
        if not file_path: return
        try:
            with open(file_path, 'w') as f:
                f.write("*HEADING\nBuckling Analysis with pyccx\n")
                f.write("*NODE\n")
                for i, p in enumerate(self.nodes): f.write(f"{i+1}, {p[0]}, {p[1]}, {p[2]}\n")
                f.write("*ELEMENT, TYPE=S4, ELSET=PLATE\n")
                for i, elem in enumerate(self.elements): f.write(f"{i+1}, {elem[0]+1}, {elem[1]+1}, {elem[2]+1}, {elem[3]+1}\n")
                f.write("*SHELL SECTION, ELSET=PLATE, MATERIAL=MAT1\n")
                f.write(f"{self.thick_input.text()}\n")
                f.write("*MATERIAL, NAME=MAT1\n*ELASTIC\n")
                f.write(f"{self.e_input.text()}, {self.nu_input.text()}\n")
                # Boundary Conditions
                for edge, dofs in self.bc_data.items():
                    nids = self.get_edge_nodes(edge)
                    for nid in nids:
                        for d in dofs: f.write(f"*BOUNDARY\n{nid+1}, {d}, {d}, 0.0\n")
                # Step 1: Pre-stress
                f.write("*STEP\n*STATIC\n")
                for edge, data in self.load_data.items():
                    nids = self.get_edge_nodes(edge)
                    direction = 1 if data['dir'] == 'X' else 2 if data['dir'] == 'Y' else 3
                    for nid in nids: f.write(f"*CLOAD\n{nid+1}, {direction}, {data['start']}\n")
                f.write("*END STEP\n")
                # Step 2: Buckling
                f.write("*STEP\n*BUCKLE\n")
                f.write(f"{self.modes_input.text()}\n")
                f.write("*END STEP\n")
            QMessageBox.information(self, "Success", f"CalculiX INP exported to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export INP: {str(e)}")

    def on_export_bdf(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save MYSTRAN BDF", "", "Nastran Input (*.bdf *.dat)")
        if not file_path: return
        try:
            with open(file_path, 'w') as f:
                f.write("ID BUCKLING, GEN\nSOL 105\nCEND\nTITLE = BUCKLING ANALYSIS\n")
                f.write("SPC = 1\nMETHOD = 1\nLOAD = 1\nBEGIN BULK\n")
                f.write(f"MAT1, 1, {float(self.e_input.text()):1.8E}, , {float(self.nu_input.text()):1.4f}\n")
                f.write(f"PSHELL, 1, 1, {float(self.thick_input.text()):1.4f}\n")
                for i, p in enumerate(self.nodes): f.write(f"GRID, {i+1}, , {p[0]:1.4E}, {p[1]:1.4E}, {p[2]:1.4E}\n")
                for i, elem in enumerate(self.elements): f.write(f"CQUAD4, {i+1}, 1, {elem[0]+1}, {elem[1]+1}, {elem[2]+1}, {elem[3]+1}\n")
                for edge, dofs in self.bc_data.items():
                    node_ids = [int(n+1) for n in self.get_edge_nodes(edge)]
                    if node_ids:
                        for j in range(0, len(node_ids), 4):
                            chunk = node_ids[j:j+4]
                            f.write(f"SPC1, 1, {dofs}, {', '.join(map(str, chunk))}\n")
                for edge, data in self.load_data.items():
                    node_ids = self.get_edge_nodes(edge)
                    if not node_ids: continue
                    for i, nid in enumerate(node_ids):
                        dir_v = "1.0, 0.0, 0.0" if data['dir'] == 'X' else "0.0, 1.0, 0.0" if data['dir'] == 'Y' else "0.0, 0.0, 1.0"
                        f.write(f"FORCE, 1, {nid+1}, 0, {data['start']:1.4E}, {dir_v}\n")
                f.write(f"EIGRL, 1, 0.0, , {self.modes_input.text()}\n")
                f.write("ENDDATA\n")
            QMessageBox.information(self, "Success", f"MYSTRAN BDF exported to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export BDF: {str(e)}")

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111, projection='3d')
        super().__init__(fig)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MYSTRANGUI()
    if os.environ.get('QT_QPA_PLATFORM') != 'offscreen': window.show()
    print("GUI Initialized successfully")
    if os.environ.get('QT_QPA_PLATFORM') == 'offscreen': sys.exit(0)
    else: sys.exit(app.exec_())
