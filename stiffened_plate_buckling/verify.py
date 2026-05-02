import numpy as np
from solver import FEModel, Solver, apply_edge_loads, apply_pressure_load
from mesh_gen import MeshGenerator

def run_verification():
    L, W, t_plate = 100.0, 100.0, 1.0
    E, nu = 210000.0, 0.3
    stiffeners = []
    mg = MeshGenerator()
    mg.generate_stiffened_plate(L, W, stiffeners, mesh_size=10)
    nodes, elements = mg.get_mesh_data()

    def test_case(nx, ny, nxy, pressure):
        model = FEModel(); model.set_material(1000, E, nu)
        for p in nodes: model.add_node(*p)
        for e in elements: model.add_element(e['nodes'], e['group'], t_plate)
        for i, p in enumerate(nodes):
            bc = [None]*6
            if np.isclose(p[0], 0) or np.isclose(p[0], L) or np.isclose(p[1], 0) or np.isclose(p[1], W): bc[2] = 0
            if np.isclose(p[0], 0) and np.isclose(p[1], 0): bc[0]=0; bc[1]=0; bc[5]=0
            elif np.isclose(p[0], L) and np.isclose(p[1], 0): bc[1]=0
            elif np.isclose(p[0], 0) and np.isclose(p[1], W): bc[0]=0
            model.set_bc(i, bc)
        apply_edge_loads(model, nx, ny, nxy, L, W); apply_pressure_load(model, pressure)
        solver = Solver(model); solver.assemble(); vals, vecs = solver.solve_buckling(n_modes=1)
        return vals[0]

    print("Verifying Pure Compression (Nx=1.0)...")
    val_nx = test_case(1.0, 0.0, 0.0, 0.0)
    print(f"Buckling Factor: {val_nx}")
    D = E * t_plate**3 / (12 * (1 - nu**2))
    Ncr_analytical = 4 * np.pi**2 * D / (L**2)
    print(f"Analytical Ncr: {Ncr_analytical}")

    print("Verifying Biaxial Compression (Nx=1.0, Ny=1.0)...")
    val_biaxial = test_case(1.0, 1.0, 0.0, 0.0)
    print(f"Buckling Factor: {val_biaxial}")
    # Biaxial analytical for square plate: Nx + Ny = Ncr => lambda(1+1) = Ncr => lambda = Ncr/2
    print(f"Analytical Biaxial: {Ncr_analytical/2}")

    print("Verification Complete.")

if __name__ == "__main__":
    run_verification()
