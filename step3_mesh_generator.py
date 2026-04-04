import gmsh
import numpy as np

_gmsh_initialized = False

class MeshGenerator:
    def __init__(self, length, height, element_size, holes=None):
        self.length = length
        self.height = height
        self.element_size = element_size
        self.holes = holes if holes else [] # List of (x, y, diameter)

    def generate_mesh(self):
        global _gmsh_initialized
        if not _gmsh_initialized:
            gmsh.initialize()
            _gmsh_initialized = True

        # Clear existing models to prevent duplicates in GUI sessions
        gmsh.model.add("PlateWithHoles")

        # Geometry
        p1 = gmsh.model.geo.addPoint(0, 0, 0, self.element_size)
        p2 = gmsh.model.geo.addPoint(self.length, 0, 0, self.element_size)
        p3 = gmsh.model.geo.addPoint(self.length, self.height, 0, self.element_size)
        p4 = gmsh.model.geo.addPoint(0, self.height, 0, self.element_size)

        l1 = gmsh.model.geo.addLine(p1, p2)
        l2 = gmsh.model.geo.addLine(p2, p3)
        l3 = gmsh.model.geo.addLine(p3, p4)
        l4 = gmsh.model.geo.addLine(p4, p1)

        loops = []
        outer_loop = gmsh.model.geo.addCurveLoop([l1, l2, l3, l4])
        loops.append(outer_loop)

        for i, (hx, hy, hd) in enumerate(self.holes):
            r = hd / 2.0
            # Simple circle using 4 points
            hp1 = gmsh.model.geo.addPoint(hx - r, hy, 0, self.element_size)
            hp2 = gmsh.model.geo.addPoint(hx, hy - r, 0, self.element_size)
            hp3 = gmsh.model.geo.addPoint(hx + r, hy, 0, self.element_size)
            hp4 = gmsh.model.geo.addPoint(hx, hy + r, 0, self.element_size)

            c1 = gmsh.model.geo.addCircleArc(hp1, gmsh.model.geo.addPoint(hx, hy, 0), hp2)
            c2 = gmsh.model.geo.addCircleArc(hp2, gmsh.model.geo.addPoint(hx, hy, 0), hp3)
            c3 = gmsh.model.geo.addCircleArc(hp3, gmsh.model.geo.addPoint(hx, hy, 0), hp4)
            c4 = gmsh.model.geo.addCircleArc(hp4, gmsh.model.geo.addPoint(hx, hy, 0), hp1)

            h_loop = gmsh.model.geo.addCurveLoop([c1, c2, c3, c4])
            loops.append(h_loop)

        surface = gmsh.model.geo.addPlaneSurface(loops)

        # Mesh settings for QUAD4 dominant
        gmsh.model.geo.synchronize()
        gmsh.option.setNumber("Mesh.RecombineAll", 1)
        gmsh.option.setNumber("Mesh.Algorithm", 8) # Frontal-Delaunay for quads
        gmsh.option.setNumber("Mesh.SubdivisionAlgorithm", 1) # All Quads

        gmsh.model.mesh.generate(2)

        # Extract nodes and elements
        node_tags, coords, _ = gmsh.model.mesh.getNodes()
        nodes = coords.reshape(-1, 3)
        node_id_map = {tag: i for i, tag in enumerate(node_tags)}

        element_types, element_tags, element_node_tags = gmsh.model.mesh.getElements(2)
        quad_elements = []
        for i, etype in enumerate(element_types):
            if etype == 3: # QUAD4
                nodes_in_elem = element_node_tags[i].reshape(-1, 4)
                for enodes in nodes_in_elem:
                    quad_elements.append([node_id_map[tag] for tag in enodes])
            elif etype == 2: # TRIA3 (should be rare)
                nodes_in_elem = element_node_tags[i].reshape(-1, 3)
                for enodes in nodes_in_elem:
                    # Convert TRIA3 to degenerate QUAD4
                    quad_elements.append([node_id_map[enodes[0]], node_id_map[enodes[1]], node_id_map[enodes[2]], node_id_map[enodes[2]]])

        # Physical groups for BC identification
        # Boundary nodes
        left_nodes = [i for i, n in enumerate(nodes) if np.isclose(n[0], 0, atol=1e-6)]
        right_nodes = [i for i, n in enumerate(nodes) if np.isclose(n[0], self.length, atol=1e-6)]
        bottom_nodes = [i for i, n in enumerate(nodes) if np.isclose(n[1], 0, atol=1e-6)]
        top_nodes = [i for i, n in enumerate(nodes) if np.isclose(n[1], self.height, atol=1e-6)]

        edge_nodes = list(set(left_nodes + right_nodes + bottom_nodes + top_nodes))

        # Corner nodes for CBUSH1D
        corners = [
            [0, 0],
            [self.length, 0],
            [self.length, self.height],
            [0, self.height]
        ]
        corner_node_ids = []
        for c in corners:
            dist = np.linalg.norm(nodes[:, :2] - c, axis=1)
            corner_node_ids.append(np.argmin(dist))

        # Do not finalize gmsh here to allow repeated calls in the same session
        # gmsh.finalize()
        return nodes, quad_elements, edge_nodes, corner_node_ids

if __name__ == "__main__":
    mg = MeshGenerator(1.0, 1.0, 0.1, [(0.5, 0.5, 0.2)])
    nodes, elements, edge_nodes, corners = mg.generate_mesh()
    print(f"Nodes: {len(nodes)}, Elements: {len(elements)}")
    print(f"Corner node IDs: {corners}")
    print(f"Edge nodes: {len(edge_nodes)}")
    gmsh.finalize()
