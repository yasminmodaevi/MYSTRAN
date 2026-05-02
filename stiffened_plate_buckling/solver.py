import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.linalg import spsolve, eigsh

class FEModel:
    def __init__(self):
        self.nodes = []; self.elements = []; self.materials = {}; self.bcs = {}; self.loads = {}
    def add_node(self, x, y, z):
        self.nodes.append([x, y, z]); return len(self.nodes) - 1
    def add_element(self, node_indices, material_id, thickness):
        self.elements.append({'nodes': node_indices, 'material': material_id, 'thickness': thickness})
    def set_material(self, m_id, E, nu, rho=0.0):
        self.materials[m_id] = {'E': E, 'nu': nu, 'rho': rho}
    def set_bc(self, node_idx, bc_vector):
        self.bcs[node_idx] = bc_vector
    def set_load(self, node_idx, load_vector):
        if node_idx in self.loads: self.loads[node_idx] = [float(a + b) for a, b in zip(self.loads[node_idx], load_vector)]
        else: self.loads[node_idx] = [float(v) for v in load_vector]

def get_rotation_matrix(nodes):
    v1 = nodes[1] - nodes[0]; L1 = np.linalg.norm(v1); e1 = v1 / L1 if L1 > 1e-12 else np.array([1, 0, 0])
    v2 = nodes[2] - nodes[0]; n = np.cross(e1, v2); Ln = np.linalg.norm(n); e3 = n / Ln if Ln > 1e-12 else np.array([0, 0, 1])
    e2 = np.cross(e3, e1); R_block = np.vstack([e1, e2, e3])
    T = np.zeros((24, 24))
    for i in range(4):
        T[i*6:i*6+3, i*6:i*6+3] = R_block; T[i*6+3:i*6+6, i*6+3:i*6+6] = R_block
    return T

def quad4_shape_functions(xi, eta):
    N = 0.25 * np.array([(1-xi)*(1-eta), (1+xi)*(1-eta), (1+xi)*(1+eta), (1-xi)*(1+eta)])
    dNdxi = 0.25 * np.array([-(1-eta), (1-eta), (1+eta), -(1+eta)])
    dNdeta = 0.25 * np.array([-(1-xi), -(1+xi), (1+xi), (1-xi)])
    return N, dNdxi, dNdeta

def quad4_stiffness(nodes_glob, E, nu, t):
    T = get_rotation_matrix(nodes_glob); nodes_loc = (nodes_glob - nodes_glob[0]) @ T[:3, :3].T
    Kl = np.zeros((24, 24)); C = E / (1 - nu**2) * np.array([[1, nu, 0], [nu, 1, 0], [0, 0, (1-nu)/2]])
    D_b = E * t**3 / (12 * (1 - nu**2)) * np.array([[1, nu, 0], [nu, 1, 0], [0, 0, (1-nu)/2]])
    G = E / (2 * (1 + nu)); D_s = (5/6) * G * t * np.eye(2); gauss_pts = [-1/np.sqrt(3), 1/np.sqrt(3)]
    for xi in gauss_pts:
        for eta in gauss_pts:
            N, dNdxi, dNdeta = quad4_shape_functions(xi, eta); J = np.array([dNdxi, dNdeta]) @ nodes_loc[:, :2]
            detJ = np.linalg.det(J); invJ = np.linalg.inv(J); dNdx = invJ @ np.array([dNdxi, dNdeta])
            Bm = np.zeros((3, 8))
            for i in range(4): Bm[0, 2*i] = dNdx[0, i]; Bm[1, 2*i+1] = dNdx[1, i]; Bm[2, 2*i] = dNdx[1, i]; Bm[2, 2*i+1] = dNdx[0, i]
            Ke_m = Bm.T @ C @ Bm * detJ * t; m_idx = [0, 1, 6, 7, 12, 13, 18, 19]
            for i in range(8):
                for j in range(8): Kl[m_idx[i], m_idx[j]] += Ke_m[i, j]
            Bb = np.zeros((3, 12))
            for i in range(4): Bb[0, 3*i+1] = dNdx[0, i]; Bb[1, 3*i+2] = dNdx[1, i]; Bb[2, 3*i+1] = dNdx[1, i]; Bb[2, 3*i+2] = dNdx[0, i]
            Ke_b = Bb.T @ D_b @ Bb * detJ; b_idx = [2, 3, 4, 8, 9, 10, 14, 15, 16, 20, 21, 22]
            for i in range(12):
                for j in range(12): Kl[b_idx[i], b_idx[j]] += Ke_b[i, j]
    xi, eta = 0, 0; N, dNdxi, dNdeta = quad4_shape_functions(xi, eta); J = np.array([dNdxi, dNdeta]) @ nodes_loc[:, :2]
    detJ = np.linalg.det(J); invJ = np.linalg.inv(J); dNdx = invJ @ np.array([dNdxi, dNdeta]); Bs = np.zeros((2, 12))
    for i in range(4): Bs[0, 3*i] = dNdx[0, i]; Bs[0, 3*i+1] = -N[i]; Bs[1, 3*i] = dNdx[1, i]; Bs[1, 3*i+2] = -N[i]
    Ke_s = Bs.T @ D_s @ Bs * detJ * 4; b_idx = [2, 3, 4, 8, 9, 10, 14, 15, 16, 20, 21, 22]
    for i in range(12):
        for j in range(12): Kl[b_idx[i], b_idx[j]] += Ke_s[i, j]
    for i in [5, 11, 17, 23]: Kl[i, i] += E * t * 1e-6
    return T.T @ Kl @ T

def quad4_geometric_stiffness(nodes_glob, t, sig):
    T = get_rotation_matrix(nodes_glob); nodes_loc = (nodes_glob - nodes_glob[0]) @ T[:3, :3].T
    Kgl = np.zeros((24, 24)); S = np.array([[sig[0], sig[2]], [sig[2], sig[1]]]) * t
    gauss_pts = [-1/np.sqrt(3), 1/np.sqrt(3)]
    for xi in gauss_pts:
        for eta in gauss_pts:
            N, dNdxi, dNdeta = quad4_shape_functions(xi, eta); J = np.array([dNdxi, dNdeta]) @ nodes_loc[:, :2]
            detJ = np.linalg.det(J); invJ = np.linalg.inv(J); dNdx = invJ @ np.array([dNdxi, dNdeta])
            Bg = dNdx; Ke_g_uz = Bg.T @ S @ Bg * detJ; g_idx = [2, 8, 14, 20]
            for i in range(4):
                for j in range(4): Kgl[g_idx[i], g_idx[j]] += Ke_g_uz[i, j]
    return T.T @ Kgl @ T

class Solver:
    def __init__(self, model):
        self.model = model; self.K = None; self.Kg = None; self.F = None; self.displacements = None
    def assemble(self):
        n_dofs = len(self.model.nodes) * 6; row_k, col_k, data_k = [], [], []; self.F = np.zeros(n_dofs)
        for elem in self.model.elements:
            nodes_coords = np.array([self.model.nodes[i] for i in elem['nodes']]); mat = self.model.materials[elem['material']]
            Ke = quad4_stiffness(nodes_coords, mat['E'], mat['nu'], elem['thickness']); dofs = []
            for n_idx in elem['nodes']: dofs.extend(range(n_idx*6, n_idx*6+6))
            for i in range(24):
                for j in range(24): row_k.append(dofs[i]); col_k.append(dofs[j]); data_k.append(Ke[i, j])
        self.K = csr_matrix((data_k, (row_k, col_k)), shape=(n_dofs, n_dofs))
        for n_idx, load in self.model.loads.items(): self.F[n_idx*6 : n_idx*6+6] += load
    def solve_static(self):
        fixed_dofs = [n_idx*6+i for n_idx, bc in self.model.bcs.items() for i, val in enumerate(bc) if val is not None]
        free_dofs = np.delete(np.arange(self.K.shape[0]), fixed_dofs)
        u_sub = spsolve(self.K[free_dofs, :][:, free_dofs], self.F[free_dofs])
        self.displacements = np.zeros(self.K.shape[0]); self.displacements[free_dofs] = u_sub; return self.displacements
    def assemble_geometric(self):
        if self.displacements is None: self.solve_static()
        n_dofs = len(self.model.nodes) * 6; row_g, col_g, data_g = [], [], []
        for elem in self.model.elements:
            nodes_coords = np.array([self.model.nodes[i] for i in elem['nodes']]); mat = self.model.materials[elem['material']]
            T = get_rotation_matrix(nodes_coords); dofs = []
            for n_idx in elem['nodes']: dofs.extend(range(n_idx*6, n_idx*6+6))
            u_elem_loc = T @ self.displacements[dofs]; nodes_loc = (nodes_coords - nodes_coords[0]) @ T[:3, :3].T
            N, dNdxi, dNdeta = quad4_shape_functions(0, 0); J = np.array([dNdxi, dNdeta]) @ nodes_loc[:, :2]
            invJ = np.linalg.inv(J); dNdx = invJ @ np.array([dNdxi, dNdeta]); Bm = np.zeros((3, 8))
            for i in range(4): Bm[0, 2*i] = dNdx[0, i]; Bm[1, 2*i+1] = dNdx[1, i]; Bm[2, 2*i] = dNdx[1, i]; Bm[2, 2*i+1] = dNdx[0, i]
            sig = (mat['E'] / (1 - mat['nu']**2) * np.array([[1, mat['nu'], 0], [mat['nu'], 1, 0], [0, 0, (1-mat['nu'])/2]])) @ (Bm @ u_elem_loc[[0, 1, 6, 7, 12, 13, 18, 19]])
            Kge = quad4_geometric_stiffness(nodes_coords, elem['thickness'], sig)
            for i in range(24):
                for j in range(24): row_g.append(dofs[i]); col_g.append(dofs[j]); data_g.append(Kge[i, j])
        self.Kg = csr_matrix((data_g, (row_g, col_g)), shape=(n_dofs, n_dofs))
    def solve_buckling(self, n_modes=5):
        self.assemble_geometric(); fixed_dofs = [n_idx*6+i for n_idx, bc in self.model.bcs.items() for i, val in enumerate(bc) if val is not None]
        free_dofs = np.delete(np.arange(self.K.shape[0]), fixed_dofs)
        vals, vecs = eigsh(self.K[free_dofs, :][:, free_dofs], k=n_modes, M=-self.Kg[free_dofs, :][:, free_dofs], which='LM', sigma=1.0)
        res_vecs = np.zeros((n_modes, self.K.shape[0]))
        for i in range(n_modes): res_vecs[i, free_dofs] = vecs[:, i]
        idx = np.argsort(np.abs(vals))
        return vals[idx], res_vecs[idx]

def apply_pressure_load(model, pressure):
    for elem in model.elements:
        nodes_coords = np.array([model.nodes[i] for i in elem['nodes']])
        v13 = nodes_coords[2] - nodes_coords[0]; v24 = nodes_coords[3] - nodes_coords[1]
        area = 0.5 * np.linalg.norm(np.cross(v13, v24)); node_force = pressure * area / 4.0
        for n_idx in elem['nodes']: model.set_load(n_idx, [0, 0, node_force, 0, 0, 0])

def apply_edge_loads(model, nx, ny, nxy, L, W):
    nodes_left = [i for i, p in enumerate(model.nodes) if np.isclose(p[0], 0, atol=1e-3) and np.isclose(p[2], 0, atol=1e-3)]
    nodes_right = [i for i, p in enumerate(model.nodes) if np.isclose(p[0], L, atol=1e-3) and np.isclose(p[2], 0, atol=1e-3)]
    nodes_bottom = [i for i, p in enumerate(model.nodes) if np.isclose(p[1], 0, atol=1e-3) and np.isclose(p[2], 0, atol=1e-3)]
    nodes_top = [i for i, p in enumerate(model.nodes) if np.isclose(p[1], W, atol=1e-3) and np.isclose(p[2], 0, atol=1e-3)]
    def apply_line_load(node_indices, force_per_len, dir_idx, coord_idx):
        if not node_indices: return
        sorted_nodes = sorted(node_indices, key=lambda i: model.nodes[i][coord_idx])
        for i, n_curr in enumerate(sorted_nodes):
            l_eff = 0
            if i > 0: l_eff += 0.5 * abs(model.nodes[n_curr][coord_idx] - model.nodes[sorted_nodes[i-1]][coord_idx])
            if i < len(sorted_nodes)-1: l_eff += 0.5 * abs(model.nodes[sorted_nodes[i+1]][coord_idx] - model.nodes[n_curr][coord_idx])
            f = [0.0]*6; f[dir_idx] = force_per_len * l_eff; model.set_load(n_curr, f)
    apply_line_load(nodes_left, nx, 0, 1); apply_line_load(nodes_right, -nx, 0, 1)
    apply_line_load(nodes_bottom, ny, 1, 0); apply_line_load(nodes_top, -ny, 1, 0)
    apply_line_load(nodes_left, -nxy, 1, 1); apply_line_load(nodes_right, nxy, 1, 1)
    apply_line_load(nodes_bottom, -nxy, 0, 0); apply_line_load(nodes_top, nxy, 0, 0)
