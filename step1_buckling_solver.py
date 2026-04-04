import numpy as np
from scipy import linalg
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh

class BucklingSolver:
    def __init__(self, nodes, elements, thickness, E, nu, rho=0.0):
        self.nodes = np.array(nodes)
        self.elements = np.array(elements)
        self.thickness = thickness
        self.E = E
        self.nu = nu
        self.rho = rho
        self.num_nodes = len(nodes)
        self.num_dofs = self.num_nodes * 6

        # Material matrices
        self.Dm = (E * thickness / (1 - nu**2)) * np.array([
            [1, nu, 0],
            [nu, 1, 0],
            [0, 0, (1 - nu) / 2]
        ])

        self.Db = (E * thickness**3 / (12 * (1 - nu**2))) * np.array([
            [1, nu, 0],
            [nu, 1, 0],
            [0, 0, (1 - nu) / 2]
        ])

        # Shear stiffness with correction factor 5/6
        self.Ds = (5/6) * (E * thickness / (2 * (1 + nu))) * np.eye(2)

    def get_shape_functions(self, xi, eta):
        N = 0.25 * np.array([
            (1 - xi) * (1 - eta),
            (1 + xi) * (1 - eta),
            (1 + xi) * (1 + eta),
            (1 - xi) * (1 + eta)
        ])
        dN_dxi = 0.25 * np.array([
            [-(1 - eta), (1 - eta), (1 + eta), -(1 + eta)],
            [-(1 - xi), -(1 + xi), (1 + xi), (1 - xi)]
        ])
        return N, dN_dxi

    def get_element_matrices(self, elem_nodes):
        Ke = np.zeros((24, 24))

        # Gauss points for 2x2 integration
        gauss_pts = [-1/np.sqrt(3), 1/np.sqrt(3)]
        weights = [1, 1]

        # For MITC4, we need specific tying points for shear
        # But for a simpler implementation, we'll use selective reduced integration for shear

        for i, xi in enumerate(gauss_pts):
            for j, eta in enumerate(gauss_pts):
                N, dN_dxi = self.get_shape_functions(xi, eta)

                # Jacobian
                J = dN_dxi @ elem_nodes[:, :2] # Assuming XY plane
                detJ = np.linalg.det(J)
                invJ = np.linalg.inv(J)
                dN_dx = invJ @ dN_dxi

                # Membrane B matrix (u, v)
                Bm = np.zeros((3, 24))
                for n in range(4):
                    Bm[0, n*6] = dN_dx[0, n]
                    Bm[1, n*6+1] = dN_dx[1, n]
                    Bm[2, n*6] = dN_dx[1, n]
                    Bm[2, n*6+1] = dN_dx[0, n]

                # Bending B matrix (theta_x, theta_y)
                # Note: kappa = [d_theta_y/dx, -d_theta_x/dy, d_theta_y/dy - d_theta_x/dx]
                Bb = np.zeros((3, 24))
                for n in range(4):
                    Bb[0, n*6+4] = dN_dx[0, n]
                    Bb[1, n*6+3] = -dN_dx[1, n]
                    Bb[2, n*6+3] = -dN_dx[0, n]
                    Bb[2, n*6+4] = dN_dx[1, n]

                Ke += (Bm.T @ self.Dm @ Bm + Bb.T @ self.Db @ Bb) * detJ * weights[i] * weights[j]

        # Reduced integration for shear (1x1 at origin)
        xi, eta = 0.0, 0.0
        N, dN_dxi = self.get_shape_functions(xi, eta)
        J = dN_dxi @ elem_nodes[:, :2]
        detJ = np.linalg.det(J)
        invJ = np.linalg.inv(J)
        dN_dx = invJ @ dN_dxi

        Bs = np.zeros((2, 24))
        for n in range(4):
            # gamma = [dw/dx + theta_y, dw/dy - theta_x]
            Bs[0, n*6+2] = dN_dx[0, n]
            Bs[0, n*6+4] = N[n]
            Bs[1, n*6+2] = dN_dx[1, n]
            Bs[1, n*6+3] = -N[n]

        Ke += (Bs.T @ self.Ds @ Bs) * detJ * 4 # 4 is weight sum (2*2)

        # Add drilling DOF stiffness (small value)
        for n in range(4):
            Ke[n*6+5, n*6+5] += self.E * self.thickness**3 * 1e-9

        return Ke

    def get_geometric_stiffness(self, elem_nodes, stresses):
        # stresses: [Nx, Ny, Nxy]
        Kg = np.zeros((24, 24))
        gauss_pts = [-1/np.sqrt(3), 1/np.sqrt(3)]
        weights = [1, 1]

        S0 = np.array([
            [stresses[0], stresses[2]],
            [stresses[2], stresses[1]]
        ])

        for i, xi in enumerate(gauss_pts):
            for j, eta in enumerate(gauss_pts):
                N, dN_dxi = self.get_shape_functions(xi, eta)
                J = dN_dxi @ elem_nodes[:, :2]
                detJ = np.linalg.det(J)
                invJ = np.linalg.inv(J)
                dN_dx = invJ @ dN_dxi

                # Gw matrix for dw/dx, dw/dy
                Gw = np.zeros((2, 24))
                for n in range(4):
                    Gw[0, n*6+2] = dN_dx[0, n]
                    Gw[1, n*6+2] = dN_dx[1, n]

                Kg += (Gw.T @ S0 @ Gw) * detJ * weights[i] * weights[j]
        return Kg

    def assemble_global_matrices(self, nodal_forces=None):
        K = np.zeros((self.num_dofs, self.num_dofs))
        for elem in self.elements:
            elem_nodes = self.nodes[elem]
            Ke = self.get_element_matrices(elem_nodes)
            for i in range(4):
                for j in range(4):
                    K[elem[i]*6:elem[i]*6+6, elem[j]*6:elem[j]*6+6] += Ke[i*6:i*6+6, j*6:j*6+6]
        return K

    def solve_static(self, K, F, fixed_dofs):
        free_dofs = np.setdiff1d(np.arange(self.num_dofs), fixed_dofs)
        u = np.zeros(self.num_dofs)
        u[free_dofs] = linalg.solve(K[np.ix_(free_dofs, free_dofs)], F[free_dofs])
        return u

    def get_element_stresses(self, u_elem, elem_nodes):
        # Evaluate stress at center
        xi, eta = 0.0, 0.0
        N, dN_dxi = self.get_shape_functions(xi, eta)
        J = dN_dxi @ elem_nodes[:, :2]
        invJ = np.linalg.inv(J)
        dN_dx = invJ @ dN_dxi

        Bm = np.zeros((3, 24))
        for n in range(4):
            Bm[0, n*6] = dN_dx[0, n]
            Bm[1, n*6+1] = dN_dx[1, n]
            Bm[2, n*6] = dN_dx[1, n]
            Bm[2, n*6+1] = dN_dx[0, n]

        strains = Bm @ u_elem
        stresses = self.Dm @ strains # Resultant forces N [N/m]
        return stresses

    def solve_buckling(self, K_E, F, fixed_dofs, num_modes=5):
        # Step 1: Static pre-stress solution
        u0 = self.solve_static(K_E, F, fixed_dofs)

        # Step 2: Assemble Kg
        K_G = np.zeros((self.num_dofs, self.num_dofs))
        for elem in self.elements:
            elem_nodes = self.nodes[elem]
            u_elem = np.zeros(24)
            for i in range(4):
                u_elem[i*6:i*6+6] = u0[elem[i]*6:elem[i]*6+6]
            stresses = self.get_element_stresses(u_elem, elem_nodes)
            Kge = self.get_geometric_stiffness(elem_nodes, stresses)
            for i in range(4):
                for j in range(4):
                    K_G[elem[i]*6:elem[i]*6+6, elem[j]*6:elem[j]*6+6] += Kge[i*6:i*6+6, j*6:j*6+6]

        # Step 3: Eigenvalue Extraction
        free_dofs = np.setdiff1d(np.arange(self.num_dofs), fixed_dofs)
        Ke_ff = K_E[np.ix_(free_dofs, free_dofs)]
        Kg_ff = K_G[np.ix_(free_dofs, free_dofs)]

        # Solve (Ke + lambda * Kg) * phi = 0  => Ke * phi = -lambda * Kg * phi
        # Or Ke * phi = alpha * (-Kg) * phi where alpha is lambda

        # Check for singularity
        if np.all(Kg_ff == 0):
            return [0], [np.zeros(self.num_dofs)]

        # Use general eigensolver for stability
        try:
            # We want the smallest positive eigenvalues
            # eigsh is good for sparse, but for now use eigh on dense
            # alpha = -1/lambda => Kg * phi = alpha * Ke * phi
            evals, evecs = linalg.eigh(Kg_ff, Ke_ff)

            # lambda = -1 / alpha
            lambdas = []
            modes = []
            for i in range(len(evals)):
                if abs(evals[i]) > 1e-12:
                    l = -1.0 / evals[i]
                    if l > 0:
                        lambdas.append(l)
                        phi = np.zeros(self.num_dofs)
                        phi[free_dofs] = evecs[:, i]
                        modes.append(phi)

            # Sort by absolute value of lambda
            idx = np.argsort(np.abs(lambdas))
            lambdas = np.array(lambdas)[idx]
            modes = [modes[i] for i in idx]

            return lambdas[:num_modes], modes[:num_modes]
        except Exception as e:
            print(f"Buckling solver failed: {e}")
            return [], []

if __name__ == "__main__":
    # Simple verification test: Simply supported plate under compression
    L, H = 1.0, 1.0
    t = 0.01
    E = 210e9
    nu = 0.3

    # Mesh
    nx, ny = 10, 10
    x = np.linspace(0, L, nx+1)
    y = np.linspace(0, H, ny+1)
    X, Y = np.meshgrid(x, y)
    nodes = np.column_stack([X.flatten(), Y.flatten(), np.zeros(X.size)])

    elements = []
    for j in range(ny):
        for i in range(nx):
            n1 = j * (nx + 1) + i
            n2 = n1 + 1
            n3 = n1 + (nx + 1) + 1
            n4 = n1 + (nx + 1)
            elements.append([n1, n2, n3, n4])

    solver = BucklingSolver(nodes, elements, t, E, nu)
    K_E = solver.assemble_global_matrices()

    # Boundary conditions: SSSS
    # UZ=0 on all edges
    # For stability: Grounded springs or pin some nodes
    fixed_dofs = []
    for i, node in enumerate(nodes):
        # All edges UZ=0
        if np.isclose(node[0], 0) or np.isclose(node[0], L) or \
           np.isclose(node[1], 0) or np.isclose(node[1], H):
            fixed_dofs.append(i*6 + 2) # UZ

        # Left edge UX=0
        if np.isclose(node[0], 0):
            fixed_dofs.append(i*6)

        # Bottom-left corner UY=0
        if np.isclose(node[0], 0) and np.isclose(node[1], 0):
            fixed_dofs.append(i*6 + 1)

    fixed_dofs = np.unique(fixed_dofs)

    # Reference Load: 1.0 N/m compression on right edge (x=L)
    F = np.zeros(solver.num_dofs)
    for i, node in enumerate(nodes):
        if np.isclose(node[0], L):
            # Distribute load over nodes. For simplicity, total load = 1.0 distributed
            val = -1.0 / (ny + 1)
            if np.isclose(node[1], 0) or np.isclose(node[1], H):
                val /= 2.0
            F[i*6] = val * H # Total force in X direction

    lambdas, modes = solver.solve_buckling(K_E, F, fixed_dofs)

    if len(lambdas) > 0:
        print(f"Critical Buckling Load Multiplier: {lambdas[0]:.4e}")
        # Analytical solution for SSSS square plate
        D = E * t**3 / (12 * (1 - nu**2))
        Pcr_analytical = (4 * np.pi**2 * D) / (L**2)
        print(f"Analytical Pcr (N/m): {Pcr_analytical:.4e}")
        print(f"Applied load was 1.0 N/m, so expected lambda is ~ {Pcr_analytical:.4e}")
    else:
        print("No buckling modes found.")
