import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh, spsolve

class PlateAnalysis:
    def __init__(self, L, W, thickness, E, nu, hole_diameter, mesh_params):
        self.L, self.W, self.t, self.E, self.nu, self.d_hole, self.mesh_params = L, W, thickness, E, nu, hole_diameter, mesh_params
        self.nodes, self.elements = self.create_mesh()
        self.num_nodes, self.num_dofs = len(self.nodes), len(self.nodes) * 6
        self.G, self.k_s = E / (2 * (1 + nu)), 5.0 / 6.0
        self.gauss_pts = [-1/np.sqrt(3), 1/np.sqrt(3)]

    def create_mesh(self):
        nr, nt = self.mesh_params
        r_hole = self.d_hole / 2
        nodes = []
        dtheta = 2 * np.pi / nt
        for i in range(nr + 1):
            for j in range(nt):
                theta = j * dtheta
                t_val = theta % (2 * np.pi)
                if (t_val <= np.pi/4) or (t_val > 7*np.pi/4): R = (self.L/2) / np.cos(t_val if t_val <= np.pi/4 else t_val - 2*np.pi)
                elif (t_val <= 3*np.pi/4): R = (self.W/2) / np.sin(t_val)
                elif (t_val <= 5*np.pi/4): R = -(self.L/2) / np.cos(t_val)
                else: R = -(self.W/2) / np.sin(t_val)
                r = r_hole + (R - r_hole) * (i / nr)
                nodes.append([np.round(self.L/2 + r*np.cos(theta), 10), np.round(self.W/2 + r*np.sin(theta), 10), 0.0])
        elements = []
        for i in range(nr):
            for j in range(nt):
                elements.append([i*nt+j, i*nt+(j+1)%nt, (i+1)*nt+(j+1)%nt, (i+1)*nt+j])
        return np.array(nodes), np.array(elements)

    def shape_functions(self, xi, eta):
        N = 0.25 * np.array([(1-xi)*(1-eta), (1+xi)*(1-eta), (1+xi)*(1+eta), (1-xi)*(1+eta)])
        dN_dxi = 0.25 * np.array([[-(1-eta), (1-eta), (1+eta), -(1+eta)], [-(1-xi), -(1+xi), (1+xi), (1-xi)]])
        return N, dN_dxi

    def get_element_matrices(self, el_nodes, formulation='Mindlin'):
        ke = np.zeros((24, 24))
        D_m = (self.E*self.t/(1-self.nu**2)) * np.array([[1, self.nu, 0], [self.nu, 1, 0], [0, 0, (1-self.nu)/2]])
        D_b = (self.E*self.t**3/(12*(1-self.nu**2))) * np.array([[1, self.nu, 0], [self.nu, 1, 0], [0, 0, (1-self.nu)/2]])
        # For Kirchhoff, use a very high shear stiffness as a penalty
        shear_factor = 1.0 if formulation == 'Mindlin' else 1e4 # 1e4 is safer for numeric stability
        D_s = (shear_factor * self.k_s * self.G * self.t) * np.eye(2)

        for xi in self.gauss_pts:
            for eta in self.gauss_pts:
                N, dN_dxi = self.shape_functions(xi, eta)
                invJ = np.linalg.inv(dN_dxi @ el_nodes[:, :2])
                detJ = np.linalg.det(dN_dxi @ el_nodes[:, :2])
                dN_dx = invJ @ dN_dxi
                B_m, B_b = np.zeros((3, 24)), np.zeros((3, 24))
                for i in range(4):
                    B_m[0, i*6] = dN_dx[0, i]; B_m[1, i*6+1] = dN_dx[1, i]; B_m[2, i*6] = dN_dx[1, i]; B_m[2, i*6+1] = dN_dx[0, i]
                    B_b[0, i*6+4] = dN_dx[0, i]; B_b[1, i*6+3] = -dN_dx[1, i]; B_b[2, i*6+3] = -dN_dx[0, i]; B_b[2, i*6+4] = dN_dx[1, i]
                ke += (B_m.T @ D_m @ B_m + B_b.T @ D_b @ B_b) * detJ

        # Shear stiffness (Mindlin uses 1-point integration to avoid locking)
        xi, eta = 0.0, 0.0
        N, dN_dxi = self.shape_functions(xi, eta)
        invJ = np.linalg.inv(dN_dxi @ el_nodes[:, :2])
        detJ = np.linalg.det(dN_dxi @ el_nodes[:, :2])
        dN_dx = invJ @ dN_dxi
        B_s = np.zeros((2, 24))
        for i in range(4): B_s[0, i*6+2] = dN_dx[0, i]; B_s[0, i*6+4] = N[i]; B_s[1, i*6+2] = dN_dx[1, i]; B_s[1, i*6+3] = -N[i]
        ke += (B_s.T @ D_s @ B_s) * 4 * detJ
        return ke

    def solve_buckling(self, total_load, k_spring, direction='X', num_modes=10, formulation='Mindlin', load_type='uniform'):
        F = np.zeros(self.num_dofs)
        tol = 1e-6
        left = np.where(np.abs(self.nodes[:, 0]) < tol)[0]
        right = np.where(np.abs(self.nodes[:, 0] - self.L) < tol)[0]
        bottom = np.where(np.abs(self.nodes[:, 1]) < tol)[0]
        top = np.where(np.abs(self.nodes[:, 1] - self.W) < tol)[0]
        all_edge_nodes = np.unique(np.concatenate([left, right, bottom, top]))

        if direction == 'X':
            if load_type == 'uniform':
                for n in right: F[n*6] -= total_load / len(right)
                for n in left: F[n*6] += total_load / len(left)
            else:
                def apply_c(nodes, s, tf, off):
                    c = self.nodes[nodes, 1-off]; idx = np.argsort(c); sn = nodes[idx]; w = np.ones(len(nodes)); w[0]=w[-1]=0.5
                    for i, n in enumerate(sn): F[n*6+off] += s * w[i] * tf / np.sum(w)
                apply_c(right, -1, total_load, 0); apply_c(left, 1, total_load, 0)
        else:
            if load_type == 'uniform':
                for n in top: F[n*6+1] -= total_load / len(top)
                for n in bottom: F[n*6+1] += total_load / len(bottom)
            else:
                def apply_c(nodes, s, tf, off):
                    c = self.nodes[nodes, 1-off]; idx = np.argsort(c); sn = nodes[idx]; w = np.ones(len(nodes)); w[0]=w[-1]=0.5
                    for i, n in enumerate(sn): F[n*6+off] += s * w[i] * tf / np.sum(w)
                apply_c(top, -1, total_load, 1); apply_c(bottom, 1, total_load, 1)

        K_i, K_j, K_v = [], [], []
        for el in self.elements:
            ke = self.get_element_matrices(self.nodes[el], formulation)
            dofs = [node*6+i for node in el for i in range(6)]
            for i in range(24):
                for j in range(24): K_i.append(dofs[i]); K_j.append(dofs[j]); K_v.append(ke[i, j])
        K = csr_matrix((K_v, (K_i, K_j)), shape=(self.num_dofs, self.num_dofs))
        corners = [
            np.argmin(np.linalg.norm(self.nodes[:, :2] - [0, 0], axis=1)),
            np.argmin(np.linalg.norm(self.nodes[:, :2] - [self.L, 0], axis=1)),
            np.argmin(np.linalg.norm(self.nodes[:, :2] - [self.L, self.W], axis=1)),
            np.argmin(np.linalg.norm(self.nodes[:, :2] - [0, self.W], axis=1))
        ]
        self.corner_indices = corners
        for c in corners: K[c*6, c*6] += k_spring; K[c*6+1, c*6+1] += k_spring
        for i in range(self.num_nodes): K[i*6+5, i*6+5] += self.E * self.t**3 * 1e-9

        fixed = [n*6+2 for n in all_edge_nodes]
        active = np.setdiff1d(np.arange(self.num_dofs), fixed)
        U_act = spsolve(K[active, :][:, active], F[active])
        U = np.zeros(self.num_dofs); U[active] = U_act

        Kg_i, Kg_j, Kg_v = [], [], []
        for el in self.elements:
            nodes_el = self.nodes[el]
            u_el = U[[n*6+i for n in el for i in range(6)]]
            invJ0 = np.linalg.inv(self.shape_functions(0,0)[1] @ nodes_el[:, :2])
            dN_dx = invJ0 @ self.shape_functions(0,0)[1]
            B_m = np.zeros((3, 24))
            for i in range(4): B_m[0, i*6]=dN_dx[0, i]; B_m[1, i*6+1]=dN_dx[1, i]; B_m[2, i*6]=dN_dx[1, i]; B_m[2, i*6+1]=dN_dx[0, i]
            sigma = ((self.E/(1-self.nu**2))*np.array([[1, self.nu, 0], [self.nu, 1, 0], [0, 0, (1-self.nu)/2]])) @ (B_m @ u_el)
            S = np.array([[sigma[0], sigma[2]], [sigma[2], sigma[1]]]) * self.t
            kge = np.zeros((24, 24))
            for xg in self.gauss_pts:
                for eg in self.gauss_pts:
                    dN_dxg = np.linalg.inv(self.shape_functions(xg,eg)[1] @ nodes_el[:, :2]) @ self.shape_functions(xg,eg)[1]
                    G = np.zeros((2, 24))
                    for i in range(4): G[0, i*6+2]=dN_dxg[0, i]; G[1, i*6+2]=dN_dxg[1, i]
                    kge += (G.T @ S @ G) * np.linalg.det(self.shape_functions(xg,eg)[1] @ nodes_el[:, :2])
            dofs = [n*6+i for n in el for i in range(6)]
            for i in range(24):
                for j in range(24): Kg_i.append(dofs[i]); Kg_j.append(dofs[j]); Kg_v.append(kge[i, j])
        Kg = csr_matrix((Kg_v, (Kg_i, Kg_j)), shape=(self.num_dofs, self.num_dofs))
        # Find positive eigenvalues only
        vals, vecs = eigsh(K[active, :][:, active], k=num_modes, M=-Kg[active, :][:, active], which='LM', sigma=10.0)
        idx = np.argsort(np.abs(vals))
        return [(vals[i], vecs[:, i]) for i in idx]
