import gmsh
import numpy as np
from plate_analysis import MeshGenerator

def test_mesh():
    # Parameters for a simple plate with a hole
    a, b = 100.0, 100.0
    D = 20.0
    xD, yD = 50.0, 50.0
    n = 10.0

    gen = MeshGenerator(a, b, D, xD, yD, n)
    gen.generate()

    print(f"Number of nodes: {len(gen.nodes)}")
    print(f"Number of elements: {len(gen.elements)}")

    # Check that all elements are 4-node quadrilaterals
    assert gen.elements.shape[1] == 4, "Elements should be 4-node quadrilaterals"

    # Check boundary nodes
    assert len(gen.edge_nodes['left']) > 0
    assert len(gen.edge_nodes['right']) > 0
    assert len(gen.edge_nodes['top']) > 0
    assert len(gen.edge_nodes['bottom']) > 0

    print("Mesh generation test passed!")

if __name__ == "__main__":
    test_mesh()
