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
from mpl_toolkits.mplot3d import Axes3D

import pygmsh
import gmsh
from pyNastran.bdf.bdf import BDF, MAT1, PSHELL, GRID, CQUAD4, FORCE, SPC1

try:
    import pyvista as pv
    from pyvistaqt import QtInteractor
    PYVISTA_AVAILABLE = True
except ImportError:
    PYVISTA_AVAILABLE = False

class MYSTRANGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MYSTRAN Mesh & BC Generator")
        self.resize(1200, 800)

        self.init_ui()
        self.mesh = None
        self.nodes = None
        self.elements = None

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Left Panel: Inputs
        left_panel = QScrollArea()
        left_panel.setFixedWidth(400)
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
        self.e_input = QLineEdit("2.1e5")
        mat_layout.addWidget(self.e_input, 0, 1)

        mat_layout.addWidget(QLabel("Poisson's Ratio (nu):"), 1, 0)
        self.nu_input = QLineEdit("0.3")
        mat_layout.addWidget(self.nu_input, 1, 1)

        mat_layout.addWidget(QLabel("Thickness:"), 2, 0)
        self.thick_input = QLineEdit("1.0")
        mat_layout.addWidget(self.thick_input, 2, 1)

        mat_group.setLayout(mat_layout)
        left_layout.addWidget(mat_group)

        # Units and Analysis
        misc_group = QGroupBox("Settings")
        misc_layout = QGridLayout()
        misc_layout.addWidget(QLabel("Units:"), 0, 0)
        self.units_combo = QComboBox()
        self.units_combo.addItems(["SI (mm, N, MPa)", "SI (m, N, Pa)", "Imperial (in, lb, psi)", "Unitless"])
        misc_layout.addWidget(self.units_combo, 0, 1)

        misc_layout.addWidget(QLabel("Analysis Type:"), 1, 0)
        self.sol_combo = QComboBox()
        self.sol_combo.addItems(["SOL 105 (Buckling)", "SOL 101 (Static)"])
        misc_layout.addWidget(self.sol_combo, 1, 1)

        misc_group.setLayout(misc_layout)
        left_layout.addWidget(misc_group)

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
        load_group = QGroupBox("Loads")
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
        self.mesh_btn = QPushButton("Generate Mesh & Visualize")
        self.mesh_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        left_layout.addWidget(self.mesh_btn)

        self.export_btn = QPushButton("Generate BDF")
        self.export_btn.setStyleSheet("background-color: #008CBA; color: white; font-weight: bold;")
        left_layout.addWidget(self.export_btn)

        left_layout.addStretch()
        left_panel.setWidget(left_widget)
        main_layout.addWidget(left_panel)

        # Right Panel: Visualization
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        viz_header = QHBoxLayout()
        viz_header.addWidget(QLabel("Visualization Method:"))
        self.viz_toggle = QButtonGroup(self)
        self.rb_mpl = QRadioButton("Matplotlib (2D/3D)")
        self.rb_pv = QRadioButton("PyVista (3D)")
        self.rb_mpl.setChecked(True)
        self.viz_toggle.addButton(self.rb_mpl)
        self.viz_toggle.addButton(self.rb_pv)
        viz_header.addWidget(self.rb_mpl)
        viz_header.addWidget(self.rb_pv)
        viz_header.addStretch()
        right_layout.addLayout(viz_header)

        self.viz_tabs = QTabWidget()

        # Matplotlib Tab
        self.mpl_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.viz_tabs.addTab(self.mpl_canvas, "Matplotlib")

        # PyVista Tab
        if PYVISTA_AVAILABLE:
            self.pv_widget = QtInteractor(self)
            self.viz_tabs.addTab(self.pv_widget, "PyVista")
        else:
            self.viz_tabs.addTab(QLabel("PyVista not available"), "PyVista")

        right_layout.addWidget(self.viz_tabs)
        main_layout.addWidget(right_panel, stretch=1)

        # Connect signals
        self.mesh_btn.clicked.connect(self.on_generate_mesh)
        self.export_btn.clicked.connect(self.on_export_bdf)
        self.viz_toggle.buttonClicked.connect(self.on_viz_toggle)

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

    def on_viz_toggle(self, button):
        if button.text().startswith("Matplotlib"):
            self.viz_tabs.setCurrentIndex(0)
        else:
            self.viz_tabs.setCurrentIndex(1)

    def on_generate_mesh(self):
        try:
            width = float(self.width_input.text())
            height = float(self.height_input.text())
            r = float(self.hole_rad_input.text())
            hx = float(self.hole_x_input.text())
            hy = float(self.hole_y_input.text())
            ms = float(self.mesh_size_input.text())

            # Validation
            if hx - r < 0 or hx + r > width or hy - r < 0 or hy + r > height:
                QMessageBox.warning(self, "Validation Error", "Hole must be inside the rectangle!")
                return

            with pygmsh.occ.Geometry() as geom:
                rect = geom.add_rectangle([0.0, 0.0, 0.0], width, height)
                hole = geom.add_disk([hx, hy, 0.0], r)
                geom.boolean_difference(rect, hole)

                gmsh.option.setNumber("Mesh.RecombineAll", 1)
                gmsh.option.setNumber("Mesh.Algorithm", 8) # Frontal-Delaunay for quads
                gmsh.option.setNumber("Mesh.SubdivisionAlgorithm", 1) # All Quads
                geom.characteristic_length_min = ms
                geom.characteristic_length_max = ms

                self.mesh = geom.generate_mesh()

            self.nodes = self.mesh.points
            self.elements = self.mesh.cells_dict.get('quad', [])

            if len(self.elements) == 0:
                QMessageBox.warning(self, "Mesh Error", "No QUAD4 elements generated!")
                return

            self.update_visualization()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate mesh: {str(e)}")

    def update_visualization(self):
        if self.nodes is None or self.elements is None: return

        # Update Matplotlib
        self.mpl_canvas.axes.clear()

        # Plot mesh
        for elem in self.elements:
            pts = self.nodes[elem]
            # Close the loop
            pts = np.vstack([pts, pts[0]])
            self.mpl_canvas.axes.plot(pts[:, 0], pts[:, 1], pts[:, 2], color='blue', linewidth=0.5)

        # Draw BCs and Loads
        self.draw_bcs_loads_mpl()

        self.mpl_canvas.axes.set_xlabel('X')
        self.mpl_canvas.axes.set_ylabel('Y')
        self.mpl_canvas.axes.set_zlabel('Z')
        self.mpl_canvas.axes.set_title("Mesh with BCs and Loads")
        self.mpl_canvas.draw()

        # Update PyVista
        if PYVISTA_AVAILABLE:
            self.pv_widget.clear()
            # Prepare PyVista mesh
            cells = []
            for elem in self.elements:
                cells.append(4)
                cells.extend(elem)

            cell_types = np.full(len(self.elements), pv.CellType.QUAD, dtype=np.uint8)
            grid = pv.UnstructuredGrid(cells, cell_types, self.nodes)
            self.pv_widget.add_mesh(grid, show_edges=True, color='cyan', opacity=0.7)

            self.draw_bcs_loads_pv()
            self.pv_widget.add_axes()
            self.pv_widget.reset_camera()

    def get_edge_nodes(self, edge_name):
        width = float(self.width_input.text())
        height = float(self.height_input.text())
        tol = 1e-5

        if edge_name == "Left":
            return [i for i, p in enumerate(self.nodes) if abs(p[0]) < tol]
        elif edge_name == "Right":
            return [i for i, p in enumerate(self.nodes) if abs(p[0] - width) < tol]
        elif edge_name == "Bottom":
            return [i for i, p in enumerate(self.nodes) if abs(p[1]) < tol]
        elif edge_name == "Top":
            return [i for i, p in enumerate(self.nodes) if abs(p[1] - height) < tol]
        return []

    def draw_bcs_loads_mpl(self):
        # BCs as triangles
        for edge, dofs in self.bc_data.items():
            node_ids = self.get_edge_nodes(edge)
            pts = self.nodes[node_ids]
            self.mpl_canvas.axes.scatter(pts[:,0], pts[:,1], pts[:,2], marker='^', color='red', s=50, label=f'BC {edge}')

        # Loads as arrows
        for edge, data in self.load_data.items():
            node_ids = self.get_edge_nodes(edge)
            if not node_ids: continue

            # Sort nodes along the edge to apply linear load
            pts = self.nodes[node_ids]
            if edge in ["Top", "Bottom"]:
                idx = np.argsort(pts[:, 0])
            else:
                idx = np.argsort(pts[:, 1])

            sorted_nodes = np.array(node_ids)[idx]
            n = len(sorted_nodes)

            for i, nid in enumerate(sorted_nodes):
                p = self.nodes[nid]
                mag = data['start'] + (data['end'] - data['start']) * (i / (n-1 if n>1 else 1))

                dx, dy, dz = 0, 0, 0
                if data['dir'] == 'X': dx = mag
                elif data['dir'] == 'Y': dy = mag
                elif data['dir'] == 'Z': dz = mag

                # Scale arrows for visibility
                scale = 0.1 * float(self.width_input.text()) / (abs(mag) if mag != 0 else 1)
                self.mpl_canvas.axes.quiver(p[0], p[1], p[2], dx, dy, dz, length=scale*abs(mag), color='green')

    def draw_bcs_loads_pv(self):
        # BCs as red points
        for edge, dofs in self.bc_data.items():
            node_ids = self.get_edge_nodes(edge)
            if not node_ids: continue
            pts = self.nodes[node_ids]
            self.pv_widget.add_points(pts, color='red', point_size=10, render_points_as_spheres=True, label=f'BC {edge}')

        # Loads as arrows
        for edge, data in self.load_data.items():
            node_ids = self.get_edge_nodes(edge)
            if not node_ids: continue

            pts = self.nodes[node_ids]
            if edge in ["Top", "Bottom"]:
                idx = np.argsort(pts[:, 0])
            else:
                idx = np.argsort(pts[:, 1])

            sorted_nodes = np.array(node_ids)[idx]
            n = len(sorted_nodes)

            for i, nid in enumerate(sorted_nodes):
                p = self.nodes[nid]
                mag = data['start'] + (data['end'] - data['start']) * (i / (n-1 if n>1 else 1))
                if mag == 0: continue

                direction = np.array([0.0, 0.0, 0.0])
                if data['dir'] == 'X': direction[0] = 1.0
                elif data['dir'] == 'Y': direction[1] = 1.0
                elif data['dir'] == 'Z': direction[2] = 1.0

                # Use a vector to represent load
                # Scaling for visibility
                scale = 0.2 * float(self.width_input.text()) / (abs(mag) if mag != 0 else 1)
                vector = direction * mag * scale

                # Arrows in PyVista
                arrow = pv.Arrow(start=p - vector, direction=vector, scale=np.linalg.norm(vector))
                self.pv_widget.add_mesh(arrow, color='green')

    def on_export_bdf(self):
        if self.nodes is None or self.elements is None:
            QMessageBox.warning(self, "Error", "Generate mesh first!")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save BDF", "", "Nastran Input (*.bdf *.dat)")
        if not file_path: return

        try:
            model = BDF()
            # Material
            mid = 1
            e = float(self.e_input.text())
            nu = float(self.nu_input.text())
            model.add_mat1(mid, e, None, nu)

            # Property
            pid = 1
            thick = float(self.thick_input.text())
            model.add_pshell(pid, mid1=mid, t=thick)

            # Nodes
            for i, p in enumerate(self.nodes):
                model.add_grid(i + 1, p)

            # Elements
            for i, elem in enumerate(self.elements):
                model.add_cquad4(i + 1, pid, [int(n+1) for n in elem])

            # Boundary Conditions (SPC1)
            spc_id = 1
            for edge, dofs in self.bc_data.items():
                node_ids = [int(n+1) for n in self.get_edge_nodes(edge)]
                if node_ids:
                    model.add_spc1(spc_id, dofs, node_ids)

            # Loads (FORCE)
            load_id = 1
            for edge, data in self.load_data.items():
                node_ids = self.get_edge_nodes(edge)
                if not node_ids: continue

                pts = self.nodes[node_ids]
                if edge in ["Top", "Bottom"]:
                    idx = np.argsort(pts[:, 0])
                else:
                    idx = np.argsort(pts[:, 1])
                sorted_nodes = np.array(node_ids)[idx]
                n = len(sorted_nodes)

                for i, nid in enumerate(sorted_nodes):
                    mag = data['start'] + (data['end'] - data['start']) * (i / (n-1 if n>1 else 1))
                    if mag == 0: continue

                    v = [0., 0., 0.]
                    if data['dir'] == 'X': v[0] = 1.0
                    elif data['dir'] == 'Y': v[1] = 1.0
                    elif data['dir'] == 'Z': v[2] = 1.0

                    model.add_force(load_id, int(nid+1), mag, v)

            # Executive and Case Control
            model.sol = 105 if "105" in self.sol_combo.currentText() else 101

            # Use CaseControlDeck correctly
            case_control_lines = [
                "TITLE = MYSTRAN GEOMETRY EXPORT",
                f"SPC = {spc_id}",
                f"LOAD = {load_id}",
                "METHOD = 1",
                "DISP = ALL",
                "STRESS = ALL",
                "BEGIN BULK"
            ]
            from pyNastran.bdf.case_control_deck import CaseControlDeck
            model.case_control_deck = CaseControlDeck(case_control_lines)
            # Add EIGRL for SOL 105
            if model.sol == 105:
                model.add_eigrl(1, v1=0.0, nd=10)

            model.write_bdf(file_path)
            QMessageBox.information(self, "Success", f"BDF exported to {file_path}")

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
    if os.environ.get('QT_QPA_PLATFORM') != 'offscreen':
        window.show()
    print("GUI Initialized successfully")
    if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
        # To avoid hanging in tests
        sys.exit(0)
    else:
        sys.exit(app.exec_())
