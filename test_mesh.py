import gmsh
import os

def test():
    a, b, D, xD, yD, lc = 100, 200, 20, 50, 100, 10
    gmsh.initialize()
    gmsh.model.add("Plate")
    p1 = gmsh.model.geo.addPoint(0, 0, 0, lc)
    p2 = gmsh.model.geo.addPoint(a, 0, 0, lc)
    p3 = gmsh.model.geo.addPoint(a, b, 0, lc)
    p4 = gmsh.model.geo.addPoint(0, b, 0, lc)
    l1 = gmsh.model.geo.addLine(p1, p2)
    l2 = gmsh.model.geo.addLine(p2, p3)
    l3 = gmsh.model.geo.addLine(p3, p4)
    l4 = gmsh.model.geo.addLine(p4, p1)
    outer_loop = gmsh.model.geo.addCurveLoop([l1, l2, l3, l4])

    pc = gmsh.model.geo.addPoint(xD, yD, 0, lc)
    p5 = gmsh.model.geo.addPoint(xD + D/2, yD, 0, lc)
    p6 = gmsh.model.geo.addPoint(xD, yD + D/2, 0, lc)
    p7 = gmsh.model.geo.addPoint(xD - D/2, yD, 0, lc)
    p8 = gmsh.model.geo.addPoint(xD, yD - D/2, 0, lc)
    c1 = gmsh.model.geo.addCircleArc(p5, pc, p6)
    c2 = gmsh.model.geo.addCircleArc(p6, pc, p7)
    c3 = gmsh.model.geo.addCircleArc(p7, pc, p8)
    c4 = gmsh.model.geo.addCircleArc(p8, pc, p5)
    inner_loop = gmsh.model.geo.addCurveLoop([c1, c2, c3, c4])

    surface = gmsh.model.geo.addPlaneSurface([outer_loop, inner_loop])
    gmsh.model.geo.synchronize()
    gmsh.option.setNumber("Mesh.RecombineAll", 1)
    gmsh.model.mesh.generate(2)
    gmsh.write("test.msh")
    gmsh.finalize()
    print("Mesh generated successfully")

if __name__ == "__main__":
    test()
