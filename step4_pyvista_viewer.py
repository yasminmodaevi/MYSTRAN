import pyvista as pv
from pyvistaqt import QtInteractor
from qtpy import QtWidgets
import numpy as np

class BucklingViewer(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.plotter = QtInteractor(self)
        self.layout.addWidget(self.plotter.interactor)

        # Default settings
        self.plotter.set_background("white")
        self.plotter.add_axes()

    def plot_mesh(self, nodes, elements, scalar=None, scalar_name=""):
        self.plotter.clear()

        # Construct cells for pyvista
        # Each cell: [num_nodes, node1, node2, node3, node4]
        cells = []
        for e in elements:
            cells.extend([len(e)] + list(e))

        # Cell types: pv.CellType.QUAD or pv.CellType.TRIANGLE
        # For our case, we always convert to QUAD or keep as is.
        # gmsh might produce triangles even if recombine is on.
        # But we simplified in mesh generator to all quads (degenerate)
        cell_types = [pv.CellType.QUAD] * len(elements)

        mesh = pv.UnstructuredGrid(cells, cell_types, nodes)

        if scalar is not None:
            mesh.point_data[scalar_name] = scalar
            self.plotter.add_mesh(mesh, show_edges=True, scalars=scalar_name, cmap="jet")
            self.plotter.add_scalar_bar(title=scalar_name)
        else:
            self.plotter.add_mesh(mesh, show_edges=True, color="lightblue")

        self.plotter.reset_camera()
        self.plotter.view_isometric()

    def plot_mode_shape(self, nodes, elements, mode_phi, scale=1.0):
        # mode_phi has 6 DOFs per node. We extract UZ for deformation and magnitude.
        num_nodes = len(nodes)
        displacements = mode_phi.reshape(num_nodes, 6)

        # Extract translational displacements (UX, UY, UZ)
        u_trans = displacements[:, :3]

        # Deformed nodes
        deformed_nodes = nodes + u_trans * scale

        # Scalar for coloring (UZ)
        uz = displacements[:, 2]

        self.plot_mesh(deformed_nodes, elements, scalar=uz, scalar_name="UZ Mode Shape")

if __name__ == "__main__":
    # Test widget
    app = QtWidgets.QApplication([])
    viewer = BucklingViewer()

    # Simple mesh
    nodes = np.array([[0,0,0], [1,0,0], [1,1,0], [0,1,0]])
    elements = [[0, 1, 2, 3]]
    viewer.plot_mesh(nodes, elements)

    viewer.show()
    # app.exec() # Headless test won't work with exec
