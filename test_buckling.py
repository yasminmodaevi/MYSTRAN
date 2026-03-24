import numpy as np
from plate_analysis import MeshGenerator, ShellElement, FEModel

def test_buckling():
    # Simply supported square plate under uniform compression
    a, b, t = 500.0, 500.0, 2.0
    E, nu = 210000.0, 0.3 # MPa
    D_hole = 0.1 # Minimal hole
    xD, yD = 250.0, 250.0
    n = 25.0 # Finer mesh

    mesh_gen = MeshGenerator(a, b, D_hole, xD, yD, n)
    mesh_gen.generate()

    shell_elem = ShellElement(E, nu, t)
    model = FEModel(mesh_gen, shell_elem)
    model.assemble()

    # BCs: Simply Supported (D1, D2, D3 fixed)
    bc_config = {edge: [True, True, True, False, False, False] for edge in ['left', 'right', 'top', 'bottom']}
    # For buckling compression in X, the right edge must be free to move in X
    bc_config['right'][0] = False
    model.apply_boundary_conditions(bc_config)

    # Apply unit compressive load (negative X) on the right edge
    nodes = mesh_gen.edge_nodes['right']
    total_force = -1.0 # 1 N compression
    for n_idx in nodes:
        model.F[n_idx*6] = total_force / len(nodes)

    factors, modes = model.solve_buckling(num_modes=1)

    # Analytical: N_cr = 4 * pi^2 * D_flex / a^2  (Force per unit length)
    # F_cr = N_cr * a = 4 * pi^2 * D_flex / a
    D_flex = (E * t**3) / (12.0 * (1.0 - nu**2))
    F_cr_analytical = (4.0 * np.pi**2 * D_flex) / a

    F_cr_fea = abs(factors[0] * total_force)

    print(f"Analytical F_cr: {F_cr_analytical:.2f} N")
    print(f"FEA F_cr: {F_cr_fea:.2f} N")

    rel_error = abs(F_cr_fea - F_cr_analytical) / F_cr_analytical
    print(f"Relative error: {rel_error:.2%}")

    # Expect reasonable agreement
    assert rel_error < 0.5, f"Buckling error too high: {rel_error:.2%}"

if __name__ == "__main__":
    test_buckling()
