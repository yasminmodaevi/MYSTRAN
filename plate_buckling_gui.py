import sys
import os
import numpy as np
from qtpy.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QLabel, QLineEdit,
                             QPushButton, QComboBox, QCheckBox, QTabWidget,
                             QGroupBox, QFormLayout, QMessageBox, QDoubleSpinBox,
                             QSpinBox)
from qtpy.QtCore import Qt
import subprocess
import os
import gmsh
import pyvista as pv
from pyvistaqt import QtInteractor

class PlateAnalysisGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plate Buckling & Analysis - CalculiX")
        self.resize(1200, 800)

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left Side: Inputs
        input_scroll = QWidget()
        input_layout = QVBoxLayout(input_scroll)

        # 1. Geometry Group
        geom_group = QGroupBox("Geometry (mm)")
        geom_form = QFormLayout()
        self.inp_a = QDoubleSpinBox(); self.inp_a.setRange(0.1, 10000); self.inp_a.setValue(100)
        self.inp_b = QDoubleSpinBox(); self.inp_b.setRange(0.1, 10000); self.inp_b.setValue(200)
        self.inp_t = QDoubleSpinBox(); self.inp_t.setRange(0.01, 1000); self.inp_t.setValue(2)
        self.inp_D = QDoubleSpinBox(); self.inp_D.setRange(0, 10000); self.inp_D.setValue(20)
        self.inp_xD = QDoubleSpinBox(); self.inp_xD.setRange(-10000, 10000); self.inp_xD.setValue(50)
        self.inp_yD = QDoubleSpinBox(); self.inp_yD.setRange(-10000, 10000); self.inp_yD.setValue(100)

        geom_form.addRow("Width (a):", self.inp_a)
        geom_form.addRow("Length (b):", self.inp_b)
        geom_form.addRow("Thickness (t):", self.inp_t)
        geom_form.addRow("Hole Diameter (D):", self.inp_D)
        geom_form.addRow("Hole x-coord (xD):", self.inp_xD)
        geom_form.addRow("Hole y-coord (yD):", self.inp_yD)
        geom_group.setLayout(geom_form)
        input_layout.addWidget(geom_group)

        # 2. Material Group
        mat_group = QGroupBox("Material")
        mat_form = QFormLayout()
        self.mat_combo = QComboBox()
        self.mat_combo.addItems(["Al2024", "Al7075", "Steel", "Ti6Al4V", "User Defined"])
        self.inp_E = QDoubleSpinBox(); self.inp_E.setRange(0.1, 1000); self.inp_E.setValue(72.4) # GPa
        self.inp_nu = QDoubleSpinBox(); self.inp_nu.setRange(0, 0.5); self.inp_nu.setSingleStep(0.01); self.inp_nu.setValue(0.33)
        self.mat_combo.currentIndexChanged.connect(self.update_material_fields)

        mat_form.addRow("Predefined:", self.mat_combo)
        mat_form.addRow("E (GPa):", self.inp_E)
        mat_form.addRow("Poisson's Ratio:", self.inp_nu)
        mat_group.setLayout(mat_form)
        input_layout.addWidget(mat_group)

        # 3. Mesh Group
        mesh_group = QGroupBox("Mesh")
        mesh_form = QFormLayout()
        self.inp_esize = QDoubleSpinBox(); self.inp_esize.setRange(0.1, 1000); self.inp_esize.setValue(5.0)
        self.etype_combo = QComboBox()
        self.etype_combo.addItems(["QUAD4", "QUAD8"])
        mesh_form.addRow("Element Size (n):", self.inp_esize)
        mesh_form.addRow("Element Type:", self.etype_combo)
        mesh_group.setLayout(mesh_form)
        input_layout.addWidget(mesh_group)

        # 4. Analysis Group
        analysis_group = QGroupBox("Analysis")
        analysis_form = QFormLayout()
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems(["Linear Static", "Nonlinear Static", "Linear Buckling", "Normal Modes"])
        self.inp_bm = QSpinBox(); self.inp_bm.setRange(1, 100); self.inp_bm.setValue(5)
        analysis_form.addRow("Type:", self.analysis_combo)
        analysis_form.addRow("Modes (BM):", self.inp_bm)
        analysis_group.setLayout(analysis_form)
        input_layout.addWidget(analysis_group)

        # Buttons
        self.btn_mesh = QPushButton("Generate Mesh")
        self.btn_mesh.clicked.connect(self.generate_mesh)
        self.btn_run = QPushButton("Run Analysis")
        self.btn_run.clicked.connect(self.run_analysis)
        input_layout.addWidget(self.btn_mesh)
        input_layout.addWidget(self.btn_run)

        input_layout.addStretch()

        # Right Side: Tabs for BCs, Loads and Visualization
        right_panel = QTabWidget()

        # BCs Tab
        self.bc_tab = QWidget()
        self.setup_bc_tab()
        right_panel.addTab(self.bc_tab, "Boundary Conditions")

        # Loads Tab
        self.load_tab = QWidget()
        self.setup_load_tab()
        right_panel.addTab(self.load_tab, "Loads")

        # Result Tab (Visualization)
        self.result_tab = QWidget()
        result_layout = QVBoxLayout(self.result_tab)
        self.plotter = QtInteractor(self.result_tab)
        result_layout.addWidget(self.plotter.interactor)

        # Add result selection
        result_ctrl_layout = QHBoxLayout()
        self.res_combo = QComboBox()
        self.res_combo.addItems(["Mesh Only"])
        self.res_combo.currentIndexChanged.connect(self.update_visualization)
        result_ctrl_layout.addWidget(QLabel("View Result:"))
        result_ctrl_layout.addWidget(self.res_combo)
        result_layout.addLayout(result_ctrl_layout)

        right_panel.addTab(self.result_tab, "Visualization")

        main_layout.addWidget(input_scroll, 1)
        main_layout.addWidget(right_panel, 3)

        # Material Data
        self.materials = {
            "Al2024": {"E": 73.1, "nu": 0.33},
            "Al7075": {"E": 71.7, "nu": 0.33},
            "Steel": {"E": 210.0, "nu": 0.30},
            "Ti6Al4V": {"E": 113.8, "nu": 0.34}
        }

    def update_material_fields(self):
        name = self.mat_combo.currentText()
        if name in self.materials:
            self.inp_E.setValue(self.materials[name]["E"])
            self.inp_nu.setValue(self.materials[name]["nu"])
            self.inp_E.setEnabled(False)
            self.inp_nu.setEnabled(False)
        else:
            self.inp_E.setEnabled(True)
            self.inp_nu.setEnabled(True)

    def setup_bc_tab(self):
        layout = QVBoxLayout(self.bc_tab)
        grid = QGridLayout()
        edges = ["Left (x=0)", "Right (x=a)", "Bottom (y=0)", "Top (y=b)"]
        self.bc_checks = {} # edge -> [dof1, dof2, ... dof6]

        for i, edge in enumerate(edges):
            grid.addWidget(QLabel(edge), i+1, 0)
            self.bc_checks[edge] = []
            for dof in range(1, 7):
                cb = QCheckBox(f"U{dof}" if dof <=3 else f"UR{dof-3}")
                grid.addWidget(cb, i+1, dof)
                self.bc_checks[edge].append(cb)

        # Headers
        for dof in range(1, 7):
            grid.addWidget(QLabel(f"DOF {dof}"), 0, dof)

        layout.addLayout(grid)

        # Presets
        preset_layout = QHBoxLayout()
        btn_ss = QPushButton("Set Simply Supported")
        btn_clamped = QPushButton("Set Clamped")
        btn_free = QPushButton("Set Free")

        btn_ss.clicked.connect(lambda: self.set_bc_preset("SS"))
        btn_clamped.clicked.connect(lambda: self.set_bc_preset("Clamped"))
        btn_free.clicked.connect(lambda: self.set_bc_preset("Free"))

        preset_layout.addWidget(btn_ss)
        preset_layout.addWidget(btn_clamped)
        preset_layout.addWidget(btn_free)
        layout.addLayout(preset_layout)
        layout.addStretch()

    def set_bc_preset(self, type):
        for edge, checks in self.bc_checks.items():
            for i, cb in enumerate(checks):
                if type == "Free":
                    cb.setChecked(False)
                elif type == "Clamped":
                    cb.setChecked(True)
                elif type == "SS":
                    # Simply supported: U1, U2, U3 fixed (indices 0, 1, 2)
                    cb.setChecked(True if i < 3 else False)

    def setup_load_tab(self):
        layout = QVBoxLayout(self.load_tab)

        # In-plane linear loads
        inplane_group = QGroupBox("In-plane Linear Loads (N)")
        inplane_grid = QGridLayout()
        edges = ["Left", "Right", "Bottom", "Top"]
        self.load_inputs = {} # edge -> (start, end)

        for i, edge in enumerate(edges):
            inplane_grid.addWidget(QLabel(f"{edge} Edge:"), i, 0)
            inplane_grid.addWidget(QLabel("Start:"), i, 1)
            s_inp = QDoubleSpinBox(); s_inp.setRange(-1e6, 1e6); s_inp.setValue(0)
            inplane_grid.addWidget(s_inp, i, 2)
            inplane_grid.addWidget(QLabel("End:"), i, 3)
            e_inp = QDoubleSpinBox(); e_inp.setRange(-1e6, 1e6); e_inp.setValue(0)
            inplane_grid.addWidget(e_inp, i, 4)
            self.load_inputs[edge] = (s_inp, e_inp)

        inplane_group.setLayout(inplane_grid)
        layout.addWidget(inplane_group)

        # Z-Pressure
        pressure_group = QGroupBox("Out-of-plane Pressure")
        p_form = QFormLayout()
        self.inp_pressure = QDoubleSpinBox(); self.inp_pressure.setRange(-1000, 1000); self.inp_pressure.setValue(0)
        p_form.addRow("Pressure Z (MPa):", self.inp_pressure)
        pressure_group.setLayout(p_form)
        layout.addWidget(pressure_group)

        layout.addStretch()

    def generate_mesh(self):
        try:
            a = self.inp_a.value()
            b = self.inp_b.value()
            D = self.inp_D.value()
            xD = self.inp_xD.value()
            yD = self.inp_yD.value()
            lc = self.inp_esize.value()
            etype = self.etype_combo.currentText()

            # Error checking for hole
            if D > 0:
                if (xD - D/2 < 0) or (xD + D/2 > a) or (yD - D/2 < 0) or (yD + D/2 > b):
                    QMessageBox.warning(self, "Geometry Error", "The hole is outside the plate boundaries!")
                    return

            gmsh.initialize()
            gmsh.model.add("Plate")

            # Points for rectangle
            p1 = gmsh.model.geo.addPoint(0, 0, 0, lc)
            p2 = gmsh.model.geo.addPoint(a, 0, 0, lc)
            p3 = gmsh.model.geo.addPoint(a, b, 0, lc)
            p4 = gmsh.model.geo.addPoint(0, b, 0, lc)

            # Lines for rectangle
            l1 = gmsh.model.geo.addLine(p1, p2)
            l2 = gmsh.model.geo.addLine(p2, p3)
            l3 = gmsh.model.geo.addLine(p3, p4)
            l4 = gmsh.model.geo.addLine(p4, p1)

            outer_loop = gmsh.model.geo.addCurveLoop([l1, l2, l3, l4])

            inner_loops = []
            if D > 0:
                # Hole points
                pc = gmsh.model.geo.addPoint(xD, yD, 0, lc)
                p5 = gmsh.model.geo.addPoint(xD + D/2, yD, 0, lc)
                p6 = gmsh.model.geo.addPoint(xD, yD + D/2, 0, lc)
                p7 = gmsh.model.geo.addPoint(xD - D/2, yD, 0, lc)
                p8 = gmsh.model.geo.addPoint(xD, yD - D/2, 0, lc)

                # Arcs
                c1 = gmsh.model.geo.addCircleArc(p5, pc, p6)
                c2 = gmsh.model.geo.addCircleArc(p6, pc, p7)
                c3 = gmsh.model.geo.addCircleArc(p7, pc, p8)
                c4 = gmsh.model.geo.addCircleArc(p8, pc, p5)

                inner_loops.append(gmsh.model.geo.addCurveLoop([c1, c2, c3, c4]))

            surface = gmsh.model.geo.addPlaneSurface([outer_loop] + inner_loops)

            gmsh.model.geo.synchronize()

            # Physical Groups for BCs
            gmsh.model.addPhysicalGroup(1, [l1], 1, name="Bottom")
            gmsh.model.addPhysicalGroup(1, [l2], 2, name="Right")
            gmsh.model.addPhysicalGroup(1, [l3], 3, name="Top")
            gmsh.model.addPhysicalGroup(1, [l4], 4, name="Left")
            gmsh.model.addPhysicalGroup(2, [surface], 5, name="Plate")

            # Recombine to Quads
            gmsh.option.setNumber("Mesh.RecombineAll", 1)
            gmsh.option.setNumber("Mesh.Algorithm", 8) # Frontal-Delaunay for quads
            gmsh.option.setNumber("Mesh.SubdivisionAlgorithm", 1 if etype == "QUAD8" else 0)

            gmsh.model.mesh.generate(2)

            if etype == "QUAD8":
                gmsh.model.mesh.setOrder(2)

            # Save and Visualize
            msh_file = "plate.msh"
            gmsh.write(msh_file)

            self.visualize_mesh(msh_file)
            gmsh.finalize()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            if gmsh.isInitialized():
                gmsh.finalize()

    def visualize_mesh(self, filename):
        import meshio
        mesh = meshio.read(filename)

        # Convert to VTK/PyVista
        points = mesh.points
        cells = mesh.cells_dict

        # We look for 'quad' or 'quad9' (Gmsh 2nd order)
        if 'quad' in cells:
            quad_cells = cells['quad']
            cell_type = pv.CellType.QUAD
        elif 'quad9' in cells:
            quad_cells = cells['quad9'][:, :8] # Convert to QUAD8 for PV (which uses 8 points)
            cell_type = pv.CellType.QUADRATIC_QUAD
        elif 'quad8' in cells:
            quad_cells = cells['quad8']
            cell_type = pv.CellType.QUADRATIC_QUAD
        else:
            quad_cells = None

        if quad_cells is not None:
            # PyVista UnstructuredGrid needs [n_points, p1, p2, ...] format
            num_cells = quad_cells.shape[0]
            pts_per_cell = quad_cells.shape[1]
            cells_pv = np.hstack([np.full((num_cells, 1), pts_per_cell), quad_cells])
            cell_types = np.full(num_cells, cell_type, dtype=np.uint8)

            grid = pv.UnstructuredGrid(cells_pv, cell_types, points)

            self.plotter.clear()
            self.plotter.add_mesh(grid, show_edges=True, color="lightblue")
            self.plotter.view_xy()
            self.plotter.reset_camera()

    def run_analysis(self):
        try:
            self.generate_mesh() # Ensure mesh is up to date
            self.write_calculix_inp()

            # Run CalculiX
            ccx_path = r"C:\calculix_2.23_4win\ccx_static.exe"
            job_name = "analysis"

            # Note: We use the absolute path for ccx.
            # If on Linux/Mac, the Windows path will fail, but we follow the user's requirement.
            process = subprocess.Popen([ccx_path, job_name],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     text=True)
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                QMessageBox.critical(self, "Solver Error", f"CalculiX failed:\n{stderr}\n{stdout}")
            else:
                QMessageBox.information(self, "Analysis Complete", "CalculiX finished successfully.")
                self.load_results()

        except FileNotFoundError:
            ccx_path = r"C:\calculix_2.23_4win\ccx_static.exe"
            QMessageBox.critical(self, "Error", f"CalculiX executable not found at: {ccx_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def load_results(self):
        from pyccx.results.results import ResultProcessor, ResultsValue

        frd_file = "analysis.frd"
        if not os.path.exists(frd_file):
            return

        try:
            self.results_processor = ResultProcessor("analysis")
            self.results_processor.read()

            self.res_combo.clear()
            self.res_combo.addItem("Mesh Only")

            for inc in range(1, self.results_processor.numIncrements + 1):
                self.res_combo.addItem(f"Increment {inc}")

            QMessageBox.information(self, "Results", f"Loaded {self.results_processor.numIncrements} increments from {frd_file}")

        except Exception as e:
            QMessageBox.critical(self, "Results Error", f"Failed to load .frd file: {str(e)}")

    def update_visualization(self):
        current = self.res_combo.currentText()
        if current == "Mesh Only":
            if os.path.exists("plate.msh"):
                self.visualize_mesh("plate.msh")
        elif current.startswith("Increment"):
            inc_idx = int(current.split()[-1])
            self.visualize_result(inc_idx)

    def visualize_result(self, inc_idx):
        from pyccx.results.results import ResultsValue
        try:
            # Get displacement
            node_ids, disp_vals = self.results_processor.getNodeResult(inc_idx, ResultsValue.DISP)

            # Use original mesh
            import meshio
            mesh = meshio.read("plate.msh")
            points = mesh.points.copy()
            cells = mesh.cells_dict

            # Map disp_vals to points (CalculiX nodes start at 1)
            # node_ids is 1-indexed
            displacement = np.zeros_like(points)
            for i, nid in enumerate(node_ids):
                if nid <= len(points):
                    displacement[nid-1] = disp_vals[i]

            # Deform points (scale for visibility)
            scale = 10.0 # Default scale
            deformed_points = points + displacement * scale

            # PyVista
            etype = self.etype_combo.currentText()
            if etype == "QUAD4":
                quad_cells = cells['quad']
                cell_type = pv.CellType.QUAD
            else:
                if 'quad9' in cells:
                    quad_cells = cells['quad9'][:, :8]
                else:
                    quad_cells = cells['quad8']
                cell_type = pv.CellType.QUADRATIC_QUAD

            num_cells = quad_cells.shape[0]
            pts_per_cell = quad_cells.shape[1]
            cells_pv = np.hstack([np.full((num_cells, 1), pts_per_cell), quad_cells])
            cell_types = np.full(num_cells, cell_type, dtype=np.uint8)

            grid = pv.UnstructuredGrid(cells_pv, cell_types, deformed_points)

            # Add displacement magnitude as scalar
            mag = np.linalg.norm(displacement, axis=1)
            grid.point_data["Displacement"] = mag

            self.plotter.clear()
            self.plotter.add_mesh(grid, show_edges=True, scalars="Displacement", cmap="jet")
            self.plotter.add_text(f"Increment {inc_idx} - Displacement (Scale: {scale}x)", font_size=10)
            self.plotter.view_xy()
            # self.plotter.reset_camera() # Keep camera if possible?
        except Exception as e:
            QMessageBox.critical(self, "Viz Error", str(e))

    def write_calculix_inp(self):
        import meshio
        mesh = meshio.read("plate.msh")
        points = mesh.points
        cells = mesh.cells_dict

        etype = self.etype_combo.currentText()
        if etype == "QUAD4":
            ccx_etype = "S4"
            elements = cells['quad']
        else:
            ccx_etype = "S8"
            if 'quad9' in cells:
                elements = cells['quad9'][:, :8]
            else:
                elements = cells['quad8']

        with open("analysis.inp", "w") as f:
            f.write("*HEADING\nPlate Analysis\n")

            # Nodes
            f.write("*NODE\n")
            for i, p in enumerate(points):
                f.write(f"{i+1}, {p[0]}, {p[1]}, {p[2]}\n")

            # Elements
            f.write(f"*ELEMENT, TYPE={ccx_etype}, ELSET=EALL\n")
            for i, el in enumerate(elements):
                f.write(f"{i+1}, {', '.join(map(str, el + 1))}\n")

            # Material
            f.write("*MATERIAL, NAME=MAT1\n")
            f.write("*ELASTIC\n")
            # E in MPa, nu
            f.write(f"{self.inp_E.value() * 1000}, {self.inp_nu.value()}\n")

            # Shell Section
            f.write(f"*SHELL SECTION, ELSET=EALL, MATERIAL=MAT1\n")
            f.write(f"{self.inp_t.value()}\n")

            # Boundary Conditions
            f.write("*BOUNDARY\n")
            # We need to find nodes on edges. GMSH physical groups can help.
            # For simplicity here, we use the coordinate-based selection as per plan.
            eps = 1e-6
            a = self.inp_a.value()
            b = self.inp_b.value()

            edge_map = {
                "Left (x=0)": [n for n, p in enumerate(points) if abs(p[0]) < eps],
                "Right (x=a)": [n for n, p in enumerate(points) if abs(p[0] - a) < eps],
                "Bottom (y=0)": [n for n, p in enumerate(points) if abs(p[1]) < eps],
                "Top (y=b)": [n for n, p in enumerate(points) if abs(p[1] - b) < eps],
            }

            for edge, nodes in edge_map.items():
                checks = self.bc_checks[edge]
                for dof_idx, cb in enumerate(checks):
                    if cb.isChecked():
                        dof = dof_idx + 1
                        for node in nodes:
                            f.write(f"{node+1}, {dof}, {dof}\n")

            # Step
            analysis_type = self.analysis_combo.currentText()
            if analysis_type == "Linear Static":
                f.write("*STEP\n*STATIC\n")
            elif analysis_type == "Nonlinear Static":
                f.write("*STEP, NLGEOM=YES\n*STATIC\n0.1, 1.0\n")
            elif analysis_type == "Linear Buckling":
                f.write("*STEP\n*BUCKLE\n")
                f.write(f"{self.inp_bm.value()}\n")
            elif analysis_type == "Normal Modes":
                f.write("*STEP\n*FREQUENCY\n")
                f.write(f"{self.inp_bm.value()}\n")

            # Loads
            if analysis_type in ["Linear Static", "Nonlinear Static", "Linear Buckling"]:
                # Concentrated loads for linear distribution
                f.write("*CLOAD\n")
                for edge_name, (s_val, e_val) in self.load_inputs.items():
                    # Map edge_name to coordinate-based nodes
                    if edge_name == "Left":
                        edge_nodes = [n for n, p in enumerate(points) if abs(p[0]) < eps]
                        coord_idx = 1 # y varies
                        L = b
                    elif edge_name == "Right":
                        edge_nodes = [n for n, p in enumerate(points) if abs(p[0] - a) < eps]
                        coord_idx = 1
                        L = b
                    elif edge_name == "Bottom":
                        edge_nodes = [n for n, p in enumerate(points) if abs(p[1]) < eps]
                        coord_idx = 0 # x varies
                        L = a
                    elif edge_name == "Top":
                        edge_nodes = [n for n, p in enumerate(points) if abs(p[1] - b) < eps]
                        coord_idx = 0
                        L = a

                    if not edge_nodes: continue

                    # Sort nodes along edge
                    edge_nodes.sort(key=lambda n: points[n][coord_idx])

                    # Distribute total linear load to nodes
                    # For a line of length L, with load q(s) = q0 + (q1-q0)*s/L
                    # Nodal force at node i: Integral of q(s)*phi_i(s) ds
                    # Simplified: Use trapezoidal rule for nodal distribution
                    sv = s_val.value()
                    ev = e_val.value()

                    for i, n_idx in enumerate(edge_nodes):
                        # Coordinate s along edge
                        s = points[n_idx][coord_idx]
                        q_at_node = sv + (ev - sv) * s / L

                        # Influence length
                        if i == 0:
                            dl = (points[edge_nodes[1]][coord_idx] - points[edge_nodes[0]][coord_idx]) / 2
                        elif i == len(edge_nodes) - 1:
                            dl = (points[edge_nodes[-1]][coord_idx] - points[edge_nodes[-2]][coord_idx]) / 2
                        else:
                            dl = (points[edge_nodes[i+1]][coord_idx] - points[edge_nodes[i-1]][coord_idx]) / 2

                        force = q_at_node * dl
                        # In-plane load direction:
                        # Left/Right -> Force in X (1)
                        # Top/Bottom -> Force in Y (2)
                        dof = 1 if edge_name in ["Left", "Right"] else 2
                        if abs(force) > 1e-9:
                            f.write(f"{n_idx+1}, {dof}, {force}\n")

                # Z-Pressure
                pres = self.inp_pressure.value()
                if abs(pres) > 1e-9:
                    f.write("*DLOAD\n")
                    f.write(f"EALL, P, {pres}\n")

            # Output to FRD for visualization
            f.write("*NODE FILE\nU\n")
            f.write("*EL FILE\nS\n")
            # For linear buckling/frequency, we also want the displacements
            # CalculiX should output them to FRD by default with *NODE FILE, U
            f.write("*END STEP\n")

        QMessageBox.information(self, "Success", "CalculiX input file 'analysis.inp' generated.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PlateAnalysisGUI()
    window.show()
    sys.exit(app.exec())
