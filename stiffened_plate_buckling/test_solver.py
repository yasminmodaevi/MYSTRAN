import numpy as np
from solver import FEModel, Solver

def test_unstiffened_plate_buckling():
    L = 100.0; t = 1.0; E = 210000.0; nu = 0.3
    model = FEModel(); model.set_material(0, E, nu)
    nx, ny = 10, 10; nodes_map = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            nodes_map[(i, j)] = model.add_node(i*L/nx, j*L/ny, 0)
    for i in range(nx):
        for j in range(ny):
            model.add_element([nodes_map[(i,j)], nodes_map[(i+1,j)], nodes_map[(i+1,j+1)], nodes_map[(i,j+1)]], 0, t)
    for (i, j), idx in nodes_map.items():
        bc = [None] * 6
        if i == 0 or i == nx or j == 0 or j == ny: bc[2] = 0
        if i == 0 and j == 0: bc[0] = 0; bc[1] = 0
        elif i == nx and j == 0: bc[1] = 0
        if any(v is not None for v in bc): model.set_bc(idx, bc)

    force_total = 100.0
    for j in range(ny + 1):
        weight = 0.5 if (j == 0 or j == ny) else 1.0
        model.set_load(nodes_map[(0, j)], [force_total/ny*weight, 0, 0, 0, 0, 0])
        model.set_load(nodes_map[(nx, j)], [-force_total/ny*weight, 0, 0, 0, 0, 0])

    solver = Solver(model); solver.assemble(); solver.solve_static(); solver.assemble_geometric()
    vals, vecs = solver.solve_buckling(n_modes=5)
    print(f"Eigenvalues: {vals}")

    D = E * t**3 / (12 * (1 - nu**2))
    Ncr_analytical = 4 * np.pi**2 * D / (L**2)
    print(f"Analytical Ncr: {Ncr_analytical}")

if __name__ == "__main__":
    test_unstiffened_plate_buckling()
