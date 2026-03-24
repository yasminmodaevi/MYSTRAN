import sys
import numpy as np
from qtpy.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QGridLayout, QLabel, QLineEdit,
                            QPushButton, QComboBox, QGroupBox, QCheckBox, QMessageBox,
                            QScrollArea)
from qtpy.QtCore import Qt
import pyvista as pv
from pyvistaqt import QtInteractor
import gmsh
from scipy.sparse import csr_matrix, eye
from scipy.sparse.linalg import spsolve, eigsh

class MeshGenerator:
    def __init__(self, a, b, D, xD, yD, n):
        self.a = a; self.b = b; self.D = D; self.xD = xD; self.yD = yD; self.n = n
        self.nodes = None; self.elements = None
        self.edge_nodes = {'left': [], 'right': [], 'top': [], 'bottom': []}

    def generate(self):
        gmsh.initialize()
        gmsh.model.add("PlateHole")
        p1 = gmsh.model.geo.addPoint(0, 0, 0, self.n)
        p2 = gmsh.model.geo.addPoint(self.a, 0, 0, self.n)
        p3 = gmsh.model.geo.addPoint(self.a, self.b, 0, self.n)
        p4 = gmsh.model.geo.addPoint(0, self.b, 0, self.n)
        l1 = gmsh.model.geo.addLine(p1, p2); l2 = gmsh.model.geo.addLine(p2, p3)
        l3 = gmsh.model.geo.addLine(p3, p4); l4 = gmsh.model.geo.addLine(p4, p1)
        outer = gmsh.model.geo.addCurveLoop([l1, l2, l3, l4])
        r = self.D / 2
        ph1 = gmsh.model.geo.addPoint(self.xD + r, self.yD, 0, self.n)
        ph2 = gmsh.model.geo.addPoint(self.xD, self.yD + r, 0, self.n)
        ph3 = gmsh.model.geo.addPoint(self.xD - r, self.yD, 0, self.n)
        ph4 = gmsh.model.geo.addPoint(self.xD, self.yD - r, 0, self.n)
        pc = gmsh.model.geo.addPoint(self.xD, self.yD, 0, self.n)
        a1 = gmsh.model.geo.addCircleArc(ph1, pc, ph2); a2 = gmsh.model.geo.addCircleArc(ph2, pc, ph3)
        a3 = gmsh.model.geo.addCircleArc(ph3, pc, ph4); a4 = gmsh.model.geo.addCircleArc(ph4, pc, ph1)
        inner = gmsh.model.geo.addCurveLoop([a1, a2, a3, a4])
        surf = gmsh.model.geo.addPlaneSurface([outer, inner])
        gmsh.model.geo.synchronize()
        gmsh.model.mesh.setRecombine(2, surf)
        gmsh.option.setNumber("Mesh.RecombineAll", 1); gmsh.option.setNumber("Mesh.Algorithm", 8)
        gmsh.option.setNumber("Mesh.SubdivisionAlgorithm", 1); gmsh.option.setNumber("Mesh.ElementOrder", 1)
        gmsh.model.mesh.generate(2)
        node_tags, coords, _ = gmsh.model.mesh.getNodes()
        self.nodes = coords.reshape((-1, 3))
        self.node_tag_map = {tag: i for i, tag in enumerate(node_tags)}
        elem_types, _, elem_node_tags = gmsh.model.mesh.getElements(2)
        quad_idx = np.where(elem_types == 3)[0]
        if len(quad_idx) > 0:
            self.elements = np.vectorize(self.node_tag_map.get)(elem_node_tags[quad_idx[0]].reshape((-1, 4)))
        else: self.elements = np.array([]).reshape((0, 4))
        for i, (x, y, z) in enumerate(self.nodes):
            if np.isclose(x, 0, atol=1e-3): self.edge_nodes['left'].append(i)
            if np.isclose(x, self.a, atol=1e-3): self.edge_nodes['right'].append(i)
            if np.isclose(y, 0, atol=1e-3): self.edge_nodes['bottom'].append(i)
            if np.isclose(y, self.b, atol=1e-3): self.edge_nodes['top'].append(i)
        gmsh.finalize()

class ShellElement:
    def __init__(self, E, nu, t, rho=7.85e-9):
        self.E = E; self.nu = nu; self.t = t; self.rho = rho
        self.D_m = (E * t / (1.0 - nu**2)) * np.array([[1.0, nu, 0.0], [nu, 1.0, 0.0], [0.0, 0.0, (1.0 - nu)/2.0]])
        self.D_b = (E * t**3 / (12.0 * (1.0 - nu**2))) * np.array([[1.0, nu, 0.0], [nu, 1.0, 0.0], [0.0, 0.0, (1.0 - nu)/2.0]])
        self.D_s = (E * t / (2.4 * (1 + nu))) * np.eye(2)

    def shape_functions(self, xi, eta):
        N = 0.25 * np.array([(1-xi)*(1-eta), (1+xi)*(1-eta), (1+xi)*(1+eta), (1-xi)*(1+eta)])
        dN_dxi = 0.25 * np.array([-(1-eta), (1-eta), (1+eta), -(1+eta)])
        dN_deta = 0.25 * np.array([-(1-xi), -(1+xi), (1+xi), (1-xi)])
        return N, dN_dxi, dN_deta

    def get_matrices(self, coords):
        Ke = np.zeros((24, 24)); Me = np.zeros((24, 24))
        gauss = [-1/np.sqrt(3), 1/np.sqrt(3)]
        for xi in gauss:
            for eta in gauss:
                N, dN_dxi, dN_deta = self.shape_functions(xi, eta)
                J = np.dot(np.array([dN_dxi, dN_deta]), coords[:, :2])
                detJ = np.linalg.det(J); invJ = np.linalg.inv(J)
                dN = invJ @ np.array([dN_dxi, dN_deta])
                Bm = np.zeros((3, 8))
                for i in range(4): Bm[0,2*i]=dN[0,i]; Bm[1,2*i+1]=dN[1,i]; Bm[2,2*i]=dN[1,i]; Bm[2,2*i+1]=dN[0,i]
                Km = Bm.T @ self.D_m @ Bm * detJ
                for i in range(4):
                    for j in range(4): Ke[6*i:6*i+2, 6*j:6*j+2] += Km[2*i:2*i+2, 2*j:2*j+2]
                Bb = np.zeros((3, 8))
                for i in range(4): Bb[0,2*i+1]=dN[0,i]; Bb[1,2*i]=-dN[1,i]; Bb[2,2*i]=-dN[0,i]; Bb[2,2*i+1]=dN[1,i]
                Kb = Bb.T @ self.D_b @ Bb * detJ
                for i in range(4):
                    for j in range(4): Ke[6*i+3:6*i+5, 6*j+3:6*j+5] += Kb[2*i:2*i+2, 2*j:2*j+2]
                M_l = np.zeros((6,6)); M_l[0,0]=M_l[1,1]=M_l[2,2]=self.rho*self.t; M_l[3,3]=M_l[4,4]=self.rho*self.t**3/12.0
                for i in range(4):
                    for j in range(4): Me[6*i:6*i+6, 6*j:6*j+6] += N[i]*N[j]*M_l*detJ
        xi, eta = 0.0, 0.0
        N, dN_dxi, dN_deta = self.shape_functions(xi, eta)
        J = np.dot(np.array([dN_dxi, dN_deta]), coords[:, :2])
        detJ = np.linalg.det(J); invJ = np.linalg.inv(J)
        dN = invJ @ np.array([dN_dxi, dN_deta])
        Bs = np.zeros((2, 12))
        for i in range(4): Bs[0,3*i]=dN[0,i]; Bs[0,3*i+2]=N[i]; Bs[1,3*i]=dN[1,i]; Bs[1,3*i+1]=-N[i]
        Ks = Bs.T @ self.D_s @ Bs * detJ * 4.0
        for i in range(4):
            for j in range(4): Ke[6*i+2:6*i+5, 6*j+2:6*j+5] += Ks[3*i:3*i+3, 3*j:3*j+3]
        for i in range(4): Ke[6*i+5, 6*i+5] += 1e-6 * self.E * self.t * detJ * 4.0
        return Ke, Me

    def get_kg(self, coords, strs):
        Kge = np.zeros((24, 24))
        gauss = [-1/np.sqrt(3), 1/np.sqrt(3)]
        for xi in gauss:
            for eta in gauss:
                _, dN_dxi, dN_deta = self.shape_functions(xi, eta)
                J = np.dot(np.array([dN_dxi, dN_deta]), coords[:, :2])
                detJ = np.linalg.det(J); invJ = np.linalg.inv(J)
                dN = invJ @ np.array([dN_dxi, dN_deta])
                G = np.zeros((2, 4))
                for i in range(4): G[0,i]=dN[0,i]; G[1,i]=dN[1,i]
                S = np.array([[strs[0], strs[2]], [strs[2], strs[1]]])
                kg_l = G.T @ S @ G * self.t * detJ
                for i in range(4):
                    for j in range(4): Kge[6*i+2, 6*j+2] += kg_l[i, j]
        return Kge

class FEModel:
    def __init__(self, mesh, elem):
        self.mesh = mesh; self.elem = elem; self.num_nodes = len(mesh.nodes); self.num_dofs = self.num_nodes * 6
        self.K = None; self.M = None; self.F = np.zeros(self.num_dofs); self.fixed_dofs = []

    def assemble(self):
        rows, cols, k_vals, m_vals = [], [], [], []
        for elem_nodes in self.mesh.elements:
            coords = self.mesh.nodes[elem_nodes]
            Ke, Me = self.elem.get_matrices(coords)
            dofs = []
            for n_idx in elem_nodes: dofs.extend(range(n_idx*6, n_idx*6+6))
            for i in range(24):
                for j in range(24):
                    rows.append(dofs[i]); cols.append(dofs[j]); k_vals.append(Ke[i, j]); m_vals.append(Me[i, j])
        self.K = csr_matrix((k_vals, (rows, cols)), shape=(self.num_dofs, self.num_dofs))
        self.M = csr_matrix((m_vals, (rows, cols)), shape=(self.num_dofs, self.num_dofs))
        self.K += 1e-9 * self.elem.E * eye(self.num_dofs)

    def apply_boundary_conditions(self, bc_config):
        self.fixed_dofs = []
        for edge, nodes in self.mesh.edge_nodes.items():
            if edge in bc_config:
                dofs_to_fix = bc_config[edge]
                for n_idx in nodes:
                    for i, fix in enumerate(dofs_to_fix):
                        if fix: self.fixed_dofs.append(n_idx * 6 + i)
        self.fixed_dofs = sorted(list(set(self.fixed_dofs)))

    def apply_pressure(self, P):
        for elem_nodes in self.mesh.elements:
            coords = self.mesh.nodes[elem_nodes]
            area = np.linalg.det(np.dot(np.array([[-0.25, 0.25, 0.25, -0.25], [-0.25, -0.25, 0.25, 0.25]]), coords[:, :2])) * 4.0
            for n_idx in elem_nodes: self.F[n_idx*6 + 2] += P * area / 4.0

    def get_free_dofs(self):
        return np.delete(np.arange(self.num_dofs), self.fixed_dofs)

    def solve_static(self):
        free = self.get_free_dofs()
        u = np.zeros(self.num_dofs)
        if free.size > 0:
            u[free] = spsolve(self.K[free, :][:, free].tocsr(), self.F[free])
        return u

    def solve_modes(self, num_modes=5):
        free = self.get_free_dofs()
        k_eff = min(num_modes, free.size - 2)
        if k_eff < 1: return [], []
        vals, vecs = eigsh(self.K[free, :][:, free], k=k_eff, M=self.M[free, :][:, free], sigma=1.0, which='LM')
        results = []
        for i in range(k_eff):
            u = np.zeros(self.num_dofs); u[free] = vecs[:, i]; results.append(u)
        return np.sqrt(np.abs(vals)) / (2*np.pi), results

    def get_element_stresses(self, u):
        strs = []
        for nodes in self.mesh.elements:
            coords = self.mesh.nodes[nodes]; u_e = np.zeros(8)
            for i, n_idx in enumerate(nodes): u_e[2*i:2*i+2] = u[n_idx*6:n_idx*6+2]
            J = np.dot(np.array([[-0.25, 0.25, 0.25, -0.25], [-0.25, -0.25, 0.25, 0.25]]), coords[:, :2])
            dN = np.linalg.inv(J) @ np.array([[-0.25, 0.25, 0.25, -0.25], [-0.25, -0.25, 0.25, 0.25]])
            Bm = np.zeros((3, 8))
            for i in range(4): Bm[0,2*i]=dN[0,i]; Bm[1,2*i+1]=dN[1,i]; Bm[2,2*i]=dN[1,i]; Bm[2,2*i+1]=dN[0,i]
            strs.append(self.elem.D_m @ Bm @ u_e / self.elem.t)
        return strs

    def get_nodal_static_fields(self, u):
        disp_mag = np.linalg.norm(u.reshape((-1, 6))[:, :3], axis=1)
        element_stresses = self.get_element_stresses(u)
        node_stress = np.zeros((self.num_nodes, 3)); node_count = np.zeros(self.num_nodes)
        for e_idx, nodes in enumerate(self.mesh.elements):
            node_stress[nodes] += element_stresses[e_idx]; node_count[nodes] += 1.0
        node_count[node_count == 0] = 1.0; node_stress /= node_count[:, None]
        sx, sy, txy = node_stress[:, 0], node_stress[:, 1], node_stress[:, 2]
        stress_vm = np.sqrt(np.maximum(sx**2 - sx*sy + sy**2 + 3.0*txy**2, 0.0))
        return {"displacement": disp_mag, "stress": stress_vm}

    def solve_buckling(self, num_modes=5):
        u_s = self.solve_static()
        if np.allclose(u_s, 0):
             # For unit load buckling factor, we need some stress
             # Temporarily apply a reference compressive load if no load exists
             old_F = self.F.copy()
             self.F[self.mesh.edge_nodes['right'][0]*6] = -1.0
             u_s = self.solve_static()
             self.F = old_F

        strs = self.get_element_stresses(u_s); rows, cols, vals = [], [] , []
        for i, nodes in enumerate(self.mesh.elements):
            Kge = self.elem.get_kg(self.mesh.nodes[nodes], strs[i]); dofs = []
            for n_idx in nodes: dofs.extend(range(n_idx*6, n_idx*6+6))
            for r in range(24):
                for c in range(24):
                    if Kge[r, c] != 0: rows.append(dofs[r]); cols.append(dofs[c]); vals.append(Kge[r, c])
        Kg = csr_matrix((vals, (rows, cols)), shape=(self.num_dofs, self.num_dofs))
        free = self.get_free_dofs()
        A = -Kg[free, :][:, free].tocsr(); B = self.K[free, :][:, free].tocsr()
        k_eff = min(num_modes, free.size - 2)
        if k_eff < 1: return [], []
        try:
            # Deterministic non-zero start vector to avoid ARPACK error -9
            v0 = np.linspace(1.0, 2.0, free.size, dtype=float)
            v0 /= np.linalg.norm(v0)
            eigvals, vecs = eigsh(A, k=k_eff, M=B, sigma=1e-4, which='LM', tol=1e-4, v0=v0)
        except:
            from scipy.linalg import eigh
            eigvals, vecs = eigh(A.toarray(), B.toarray())
            idx = np.argsort(np.abs(eigvals))[::-1]; eigvals = eigvals[idx[:k_eff]]; vecs = vecs[:, idx[:k_eff]]
        factors = 1.0 / eigvals; modes = []
        for i in range(len(eigvals)):
            u = np.zeros(self.num_dofs); u[free] = vecs[:, i]; modes.append(u)
        return factors, modes

    def solve_nonlinear_static(self, steps=5):
        u = np.zeros(self.num_dofs); free = self.get_free_dofs()
        for s in range(1, steps+1):
            F_ext = self.F * (s / steps)
            for i in range(5):
                strs = self.get_element_stresses(u); rows, cols, vals = [], [], []
                for idx, nodes in enumerate(self.mesh.elements):
                    Kge = self.elem.get_kg(self.mesh.nodes[nodes], strs[idx]); dofs = []
                    for n_idx in nodes: dofs.extend(range(n_idx*6, n_idx*6+6))
                    for r in range(24):
                        for c in range(24):
                            if Kge[r, c] != 0: rows.append(dofs[r]); cols.append(dofs[c]); vals.append(Kge[r, c])
                Kg = csr_matrix((vals, (rows, cols)), shape=(self.num_dofs, self.num_dofs))
                Kt = (self.K + Kg)[free, :][:, free].tocsr()
                F_int = self.K @ u; residual = F_ext - F_int; du = np.zeros(self.num_dofs)
                du[free] = spsolve(Kt, residual[free]); u += du
                if np.linalg.norm(du[free]) < 1e-6 * np.linalg.norm(u[free] + 1e-9): break
        return u

class PlateAnalysisApp(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Plate Analysis Tool"); self.resize(1200, 800)
        self.central = QWidget(); self.setCentralWidget(self.central); self.main_layout = QHBoxLayout(self.central)
        self.input_scroll = QScrollArea(); self.input_widget = QWidget(); self.input_layout = QVBoxLayout(self.input_widget)
        self.input_scroll.setWidget(self.input_widget); self.input_scroll.setWidgetResizable(True); self.main_layout.addWidget(self.input_scroll, 1)
        self.plot_panel = QVBoxLayout(); self.main_layout.addLayout(self.plot_panel, 3)
        self.plotter = QtInteractor(self.central); self.plot_panel.addWidget(self.plotter.interactor); self.init_gui()
        self.last_static_u = None

    def init_gui(self):
        geom_group = QGroupBox("Geometry & Material"); layout = QGridLayout(); self.inputs = {}
        fields = [("Width a", "a", "500"), ("Length b", "b", "500"), ("Thick t", "t", "2"),
                  ("E [GPa]", "E", "210"), ("nu", "nu", "0.3"), ("Hole D", "D", "100"),
                  ("Hole xD", "xD", "250"), ("Hole yD", "yD", "250"), ("Elem size", "n", "50"), ("Modes", "BM", "5")]
        for i, (l, k, d) in enumerate(fields):
            layout.addWidget(QLabel(l), i, 0); edit = QLineEdit(d); layout.addWidget(edit, i, 1); self.inputs[k] = edit
        geom_group.setLayout(layout); self.input_layout.addWidget(geom_group)
        bc_group = QGroupBox("Boundary Conditions"); bc_vbox = QVBoxLayout(); self.bc_checks = {}
        for edge in ['left', 'right', 'top', 'bottom']:
            eg = QGroupBox(f"{edge.capitalize()} Edge DOFs"); el = QHBoxLayout(); self.bc_checks[edge] = []
            for i in range(6):
                cb = QCheckBox(f"D{i+1}"); cb.setChecked(i < 3); el.addWidget(cb); self.bc_checks[edge].append(cb)
            eg.setLayout(el); bc_vbox.addWidget(eg)
        bc_group.setLayout(bc_vbox); self.input_layout.addWidget(bc_group)
        load_group = QGroupBox("Loading"); ll = QGridLayout()
        self.load_z = QLineEdit("0.1"); ll.addWidget(QLabel("Z-Pressure [MPa]"), 0, 0); ll.addWidget(self.load_z, 0, 1)
        self.load_x_start = QLineEdit("1000"); ll.addWidget(QLabel("X-Force Start [N]"), 1, 0); ll.addWidget(self.load_x_start, 1, 1)
        self.load_x_end = QLineEdit("1000"); ll.addWidget(QLabel("X-Force End [N]"), 2, 0); ll.addWidget(self.load_x_end, 2, 1)
        load_group.setLayout(ll); self.input_layout.addWidget(load_group)
        self.analysis_type = QComboBox(); self.analysis_type.addItems(["Linear Static", "Normal Modes", "Linear Buckling", "Nonlinear Static"])
        self.input_layout.addWidget(QLabel("Analysis:")); self.input_layout.addWidget(self.analysis_type)
        self.static_result_combo = QComboBox(); self.static_result_combo.addItems(["Displacement", "Stress"])
        self.static_result_combo.currentIndexChanged.connect(self.update_static_view)
        self.input_layout.addWidget(QLabel("Static Result:")); self.input_layout.addWidget(self.static_result_combo)
        btn_mesh = QPushButton("Generate Mesh"); btn_mesh.clicked.connect(self.generate_mesh); self.input_layout.addWidget(btn_mesh)
        btn_run = QPushButton("Run Analysis"); btn_run.clicked.connect(self.run_analysis); self.input_layout.addWidget(btn_run); self.input_layout.addStretch()

    def generate_mesh(self):
        self.mesh_gen = MeshGenerator(float(self.inputs['a'].text()), float(self.inputs['b'].text()),
                                     float(self.inputs['D'].text()), float(self.inputs['xD'].text()),
                                     float(self.inputs['yD'].text()), float(self.inputs['n'].text()))
        self.mesh_gen.generate(); self.plotter.clear()
        pv_elements = np.hstack([np.full((len(self.mesh_gen.elements), 1), 4), self.mesh_gen.elements]).flatten()
        self.pv_mesh = pv.UnstructuredGrid(pv_elements, np.full(len(self.mesh_gen.elements), pv.CellType.QUAD), self.mesh_gen.nodes)
        self.plotter.add_mesh(self.pv_mesh, show_edges=True, color='white'); self.plotter.reset_camera()

    def run_analysis(self):
        try:
            if not hasattr(self, 'mesh_gen'): self.generate_mesh()
            elem = ShellElement(float(self.inputs['E'].text())*1000, float(self.inputs['nu'].text()), float(self.inputs['t'].text()))
            self.model = FEModel(self.mesh_gen, elem); self.model.assemble()
            bc = {e: [c.isChecked() for c in checks] for e, checks in self.bc_checks.items()}; self.model.apply_boundary_conditions(bc)
            if (lz := float(self.load_z.text())) != 0: self.model.apply_pressure(lz)
            fxs, fxe = float(self.load_x_start.text()), float(self.load_x_end.text())
            if fxs != 0 or fxe != 0:
                nodes = sorted(self.mesh_gen.edge_nodes['right'], key=lambda i: self.mesh_gen.nodes[i, 1])
                ymin, ymax = self.mesh_gen.nodes[nodes[0], 1], self.mesh_gen.nodes[nodes[-1], 1]
                for n_idx in nodes:
                    y = self.mesh_gen.nodes[n_idx, 1]; f = fxs + (fxe - fxs) * (y - ymin) / (ymax - ymin) if ymax != ymin else fxs
                    self.model.F[n_idx*6] += f / len(nodes)
            atype = self.analysis_type.currentText()
            if atype == "Linear Static": self.last_static_u = self.model.solve_static(); self.show_results(self.last_static_u)
            elif atype == "Normal Modes": f, m = self.model.solve_modes(int(self.inputs['BM'].text())); self.show_mode(m[0], f"Mode 1: {f[0]:.2f} Hz")
            elif atype == "Linear Buckling": fact, m = self.model.solve_buckling(int(self.inputs['BM'].text())); self.show_mode(m[0], f"Buckling Factor: {fact[0]:.2f}")
            elif atype == "Nonlinear Static": self.show_results(self.model.solve_nonlinear_static())
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def update_static_view(self):
        if self.last_static_u is not None: self.show_results(self.last_static_u)

    def show_results(self, u):
        fields = self.model.get_nodal_static_fields(u); res_type = self.static_result_combo.currentText().lower()
        scalar = fields["displacement"] if res_type == "displacement" else fields["stress"]
        disp = u.reshape((-1, 6))[:, :3]; res = self.pv_mesh.copy(); res.points = res.points.astype(float)
        res.points += disp * (50.0 / (np.max(np.abs(disp)) + 1e-9)); res.point_data['Val'] = scalar
        self.plotter.clear(); self.plotter.add_mesh(res, scalars='Val', show_edges=True); self.plotter.reset_camera()

    def show_mode(self, u_m, title):
        w = u_m.reshape((-1, 6))[:, 2]; res = self.pv_mesh.copy(); res.points = res.points.astype(float)
        res.points[:, 2] += w * (50.0 / (np.max(np.abs(w)) + 1e-9)); res.point_data['W'] = w
        self.plotter.clear(); self.plotter.add_mesh(res, scalars='W', show_edges=True, cmap='coolwarm')
        self.plotter.add_text(title, position='upper_right'); self.plotter.reset_camera()

if __name__ == "__main__":
    app = QApplication(sys.argv); window = PlateAnalysisApp(); window.show(); sys.exit(app.exec_())
