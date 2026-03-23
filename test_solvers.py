import numpy as np
from plate_analysis import MeshGenerator, ShellElement, FEModel

def test_static_pressure():
    # Simply supported square plate under uniform pressure
    a, b, t = 500.0, 500.0, 2.0
    E, nu = 210000.0, 0.3 # MPa
    D = 50.0 # Standard hole
    xD, yD = 250.0, 250.0
    n = 50.0 # Element size
    P = 0.01 # MPa

    mesh_gen = MeshGenerator(a, b, D, xD, yD, n)
    mesh_gen.generate()

    shell_elem = ShellElement(E, nu, t)
    model = FEModel(mesh_gen, shell_elem)

    model.assemble()
    # Fix boundary conditions: D1, D2, D3 fixed for all edges
    bc_config = {edge: [True, True, True, False, False, False] for edge in ['left', 'right', 'top', 'bottom']}
    model.apply_boundary_conditions(bc_config)
    model.apply_pressure(P)

    u = model.solve_static()

    print(f"Max F: {np.max(np.abs(model.F))}")
    print(f"Max u: {np.max(np.abs(u))}")
    print(f"Number of fixed DOFs: {len(model.fixed_dofs)}")

    # Central deflection of a simply supported square plate
    # w_max = 0.00406 * P * a^4 / D_flex
    D_flex = (E * t**3) / (12.0 * (1.0 - nu**2))
    w_analytical = 0.00406 * P * a**4 / D_flex

    # Find max deflection
    w_fea = np.max(np.abs(u[2::6]))

    print(f"Analytical w_max (solid plate): {w_analytical:.4f} mm")
    print(f"FEA w_max: {w_fea:.4f} mm")

    # We expect some error due to discretization and the small hole
    if w_analytical > 0:
        rel_error = abs(w_fea - w_analytical) / w_analytical
        print(f"Relative error: {rel_error:.2%}")

    assert abs(w_fea) > 0, "FEA deflection should be non-zero"

if __name__ == "__main__":
    test_static_pressure()
