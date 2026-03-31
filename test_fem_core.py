import unittest
import numpy as np
from plate_analysis import PlateAnalysis

class TestPlateAnalysis(unittest.TestCase):
    def setUp(self):
        self.L, self.W, self.t = 200, 200, 2.0
        self.E, self.nu = 71.7e3, 0.33
        self.d_hole = 100
        self.nr, self.nt = 5, 20
        self.analysis = PlateAnalysis(self.L, self.W, self.t, self.E, self.nu, self.d_hole, (self.nr, self.nt))

    def test_mesh_generation(self):
        self.assertEqual(len(self.analysis.elements), self.nr * self.nt)
        self.assertEqual(len(self.analysis.nodes), (self.nr + 1) * self.nt)

    def test_stiffness_matrix(self):
        el_nodes = self.analysis.nodes[self.analysis.elements[0]]
        ke = self.analysis.get_element_matrices(el_nodes)
        self.assertEqual(ke.shape, (24, 24))
        # Symmetry check
        np.testing.assert_allclose(ke, ke.T, atol=1e-5)
        # Check for rigid body modes (should have 6 near-zero eigenvalues)
        evals = np.linalg.eigvalsh(ke)
        # evals are sorted
        num_zero = np.sum(evals < 1e-5)
        # Depending on element quality, some might be slightly negative due to precision
        self.assertTrue(num_zero >= 6)

    def test_buckling_solve(self):
        modes = self.analysis.solve_buckling(edge_stress=10.0, num_modes=3)
        self.assertEqual(len(modes), 3)

        # Check active dofs count
        tol = 1e-6
        left = np.where(np.abs(self.analysis.nodes[:, 0]) < tol)[0]
        right = np.where(np.abs(self.analysis.nodes[:, 0] - self.L) < tol)[0]
        bottom = np.where(np.abs(self.analysis.nodes[:, 1]) < tol)[0]
        top = np.where(np.abs(self.analysis.nodes[:, 1] - self.W) < tol)[0]
        all_edge_nodes = np.unique(np.concatenate([left, right, bottom, top]))
        fixed = [n*6+2 for n in all_edge_nodes]
        num_active = self.analysis.num_dofs - len(fixed)

        for val, u_active in modes:
            self.assertIsInstance(val, (float, np.float64))
            self.assertEqual(len(u_active), num_active)

if __name__ == "__main__":
    unittest.main()
