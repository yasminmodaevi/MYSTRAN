import sys
import numpy as np
from qtpy import QtWidgets, QtCore
from step1_buckling_solver import BucklingSolver
from step2_gui import BucklingGUI
from step3_mesh_generator import MeshGenerator
from step4_pyvista_viewer import BucklingViewer

class AnalysisWorker(QtCore.QThread):
    finished = QtCore.Signal(dict)
    error = QtCore.Signal(str)

    def __init__(self, data):
        super().__init__()
        self.data = data

    def run(self):
        try:
            # Step 3: Mesh Generation
            mg = MeshGenerator(
                self.data['length'],
                self.data['height'],
                self.data['elem_size'],
                self.data['holes']
            )
            nodes, elements, edge_nodes, corner_node_ids = mg.generate_mesh()

            # Step 1: Solving
            solver = BucklingSolver(
                nodes,
                elements,
                self.data['thickness'],
                self.data['E'],
                self.data['nu']
            )

            # Assembly
            K_E = solver.assemble_global_matrices()

            # Boundary Conditions
            # UZ=0 on all edge nodes
            fixed_dofs = []
            for n_id in edge_nodes:
                fixed_dofs.append(n_id * 6 + 2) # UZ

            # Grounded springs at corners (X and Y direction)
            # We implement this by adding k to the global stiffness matrix
            k_spring = self.data['spring_k']
            for c_id in corner_node_ids:
                K_E[c_id * 6, c_id * 6] += k_spring # UX
                K_E[c_id * 6 + 1, c_id * 6 + 1] += k_spring # UY

            # Regularize global stiffness for 6-DOF stability
            K_E += np.eye(solver.num_dofs) * 1e-6

            # Loading: Right Edge Compression
            # Total load = load_x (N/mm) * height (mm)
            F = np.zeros(solver.num_dofs)
            right_nodes = [i for i, n in enumerate(nodes) if np.isclose(n[0], self.data['length'], atol=1e-6)]

            # Distribute load over right edge nodes
            total_force = self.data['load_x'] * self.data['height']
            force_per_node = total_force / len(right_nodes)
            for n_id in right_nodes:
                F[n_id * 6] = force_per_node

            # Solve
            lambdas, modes = solver.solve_buckling(K_E, F, fixed_dofs, self.data['num_modes'])

            result = {
                'nodes': nodes,
                'elements': elements,
                'lambdas': lambdas,
                'modes': modes
            }
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class AppController:
    def __init__(self, gui, viewer):
        self.gui = gui
        self.viewer = viewer
        self.gui.run_analysis_signal.connect(self.start_analysis)

    def start_analysis(self, data):
        self.gui.log_message("Starting analysis...")
        self.gui.run_btn.setEnabled(False)
        self.worker = AnalysisWorker(data)
        self.worker.finished.connect(self.display_results)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def display_results(self, result):
        self.gui.run_btn.setEnabled(True)
        self.gui.log_message("Analysis completed.")

        lambdas = result['lambdas']
        nodes = result['nodes']
        elements = result['elements']
        modes = result['modes']

        if len(lambdas) > 0:
            self.gui.log_message(f"Critical Buckling Load Multiplier: {lambdas[0]:.4e}")
            for i, l in enumerate(lambdas):
                self.gui.log_message(f"Mode {i+1}: {l:.4e}")

            # Default: Plot mode 1
            self.viewer.plot_mode_shape(nodes, elements, modes[0], scale=100.0)
        else:
            self.gui.log_message("No buckling modes found.")
            self.viewer.plot_mesh(nodes, elements)

    def handle_error(self, err_msg):
        self.gui.run_btn.setEnabled(True)
        self.gui.log_message(f"Error: {err_msg}")
        QtWidgets.QMessageBox.critical(self.gui, "Error", err_msg)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Instantiate components
    gui = BucklingGUI()
    viewer = BucklingViewer()

    # Integration: Add viewer to GUI
    gui.viz_container.addWidget(viewer)
    gui.viz_container.setCurrentWidget(viewer)

    # Instantiate controller
    controller = AppController(gui, viewer)

    gui.show()
    sys.exit(app.exec())
