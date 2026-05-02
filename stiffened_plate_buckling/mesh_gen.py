import gmsh
import numpy as np

class MeshGenerator:
    def __init__(self):
        if not gmsh.is_initialized(): gmsh.initialize()
    def __del__(self): pass

    def generate_stiffened_plate(self, L, W, stiffeners, mesh_size):
        gmsh.model.add("StiffenedPlate")
        p1 = gmsh.model.occ.addPoint(0, 0, 0); p2 = gmsh.model.occ.addPoint(L, 0, 0)
        p3 = gmsh.model.occ.addPoint(L, W, 0); p4 = gmsh.model.occ.addPoint(0, W, 0)
        l1 = gmsh.model.occ.addLine(p1, p2); l2 = gmsh.model.occ.addLine(p2, p3)
        l3 = gmsh.model.occ.addLine(p3, p4); l4 = gmsh.model.occ.addLine(p4, p1)
        cl = gmsh.model.occ.addCurveLoop([l1, l2, l3, l4]); plate_surf = gmsh.model.occ.addPlaneSurface([cl])
        surfaces = [(2, plate_surf)]; stiffener_surface_map = []
        for idx, s in enumerate(stiffeners):
            x1, y1 = s['start']; x2, y2 = s['end']; h, offset = s['height'], s.get('offset', 0)
            pw1 = gmsh.model.occ.addPoint(x1, y1, offset); pw2 = gmsh.model.occ.addPoint(x2, y2, offset)
            pw3 = gmsh.model.occ.addPoint(x2, y2, offset + h); pw4 = gmsh.model.occ.addPoint(x1, y1, offset + h)
            lw1 = gmsh.model.occ.addLine(pw1, pw2); lw2 = gmsh.model.occ.addLine(pw2, pw3)
            lw3 = gmsh.model.occ.addLine(pw3, pw4); lw4 = gmsh.model.occ.addLine(pw4, pw1)
            clw = gmsh.model.occ.addCurveLoop([lw1, lw2, lw3, lw4]); web_surf = gmsh.model.occ.addPlaneSurface([clw])
            surfaces.append((2, web_surf)); stiffener_surface_map.append((idx, web_surf))
            if s['type'] in ['L', 'T', 'I']:
                fw = s['flange_width']; v = np.array([x2-x1, y2-y1, 0]); d = np.linalg.norm(v)
                vn = v/d if d>1e-12 else np.array([1,0,0]); n = np.array([-vn[1], vn[0], 0])
                def add_f(zl, wid, cen=True):
                    if cen: pts = [[x1-n[0]*wid/2, y1-n[1]*wid/2, zl],[x2-n[0]*wid/2, y2-n[1]*wid/2, zl],[x2+n[0]*wid/2, y2+n[1]*wid/2, zl],[x1+n[0]*wid/2, y1+n[1]*wid/2, zl]]
                    else: pts = [[x1,y1,zl],[x2,y2,zl],[x2+n[0]*wid,y2+n[1]*wid,zl],[x1+n[0]*wid,y1+n[1]*wid,zl]]
                    pids = [gmsh.model.occ.addPoint(*p) for p in pts]
                    lids = [gmsh.model.occ.addLine(pids[i], pids[(i+1)%4]) for i in range(4)]
                    clf = gmsh.model.occ.addCurveLoop(lids); return gmsh.model.occ.addPlaneSurface([clf])
                if s['type'] == 'L': f = add_f(offset+h, fw, False); surfaces.append((2,f)); stiffener_surface_map.append((idx,f))
                elif s['type'] == 'T': f = add_f(offset+h, fw, True); surfaces.append((2,f)); stiffener_surface_map.append((idx,f))
                elif s['type'] == 'I':
                    f1 = add_f(offset+h, fw, True); surfaces.append((2,f1)); stiffener_surface_map.append((idx,f1))
                    f2 = add_f(offset, fw, True); surfaces.append((2,f2)); stiffener_surface_map.append((idx,f2))
        gmsh.model.occ.synchronize()
        if len(surfaces) > 1:
            out, out_map = gmsh.model.occ.fragment(surfaces, [])
            gmsh.model.occ.synchronize()
            groups = {1000: [o[1] for o in out_map[0]]}
            for i, (s_idx, s_tag) in enumerate(stiffener_surface_map):
                tag = 2000 + s_idx
                if tag not in groups: groups[tag] = []
                groups[tag].extend([o[1] for o in out_map[i+1]])
            for tag, frags in groups.items(): gmsh.model.addPhysicalGroup(2, list(set(frags)), tag)
        else:
            gmsh.model.addPhysicalGroup(2, [plate_surf], 1000)

        gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size); gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size)
        gmsh.option.setNumber("Mesh.Algorithm", 8); gmsh.option.setNumber("Mesh.RecombineAll", 1); gmsh.option.setNumber("Mesh.SubdivisionAlgorithm", 1)
        gmsh.model.mesh.generate(2)

    def get_mesh_data(self):
        node_tags, coords, _ = gmsh.model.mesh.getNodes(); nodes = coords.reshape((-1, 3))
        node_map = {tag: i for i, tag in enumerate(node_tags)}; elements = []
        groups = gmsh.model.getPhysicalGroups(2)
        for dim, tag in groups:
            for entity in gmsh.model.getEntitiesForPhysicalGroup(dim, tag):
                elem_types, elem_tags, elem_node_tags = gmsh.model.mesh.getElements(dim, entity)
                for i, etype in enumerate(elem_types):
                    if etype == 3:
                        for j in range(len(elem_tags[i])):
                            n_idx = [node_map[t] for t in elem_node_tags[i][j*4 : (j+1)*4]]
                            elements.append({'nodes': n_idx, 'group': tag})
        return nodes, elements
