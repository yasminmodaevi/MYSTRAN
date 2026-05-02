from mesh_gen import MeshGenerator
import gmsh

def test_mesh_gen():
    mg = MeshGenerator()
    stiffeners = [
        {'type': 'Flat', 'start': [20, 0], 'end': [20, 100], 'height': 10, 'thickness': 1, 'offset': 0},
        {'type': 'T', 'start': [0, 50], 'end': [100, 50], 'height': 10, 'thickness': 1, 'flange_width': 10, 'offset': 0}
    ]
    mg.generate_stiffened_plate(100, 100, stiffeners, 10)
    nodes, elements = mg.get_mesh_data()
    print(f"Nodes: {len(nodes)}, Elements: {len(elements)}")

    # Check if we have common nodes
    # If fragment worked, the number of nodes should be reasonable and they should share edges.
    # We can save to vtk for manual check if needed, or just print counts.
    gmsh.write("stiffened_plate.msh")

if __name__ == "__main__":
    test_mesh_gen()
