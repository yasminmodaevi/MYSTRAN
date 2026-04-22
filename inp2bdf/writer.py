from .models import FEModel
import os
import math

class BdfWriter:
    def __init__(self, model: FEModel):
        self.model = model
        self.format = 'fixed'
        self.material_ids = {}
        self.property_ids = {}
        self.spc_id = 1
        self.load_id = 1

    def set_format(self, format_type):
        if format_type in ['fixed', 'large', 'free']:
            self.format = format_type

    def write(self, filepath):
        with open(filepath, 'w') as f:
            self._write_executive_control(f)
            self._write_case_control(f)
            f.write("BEGIN BULK\n")
            self._write_bulk_data(f)
            f.write("ENDDATA\n")

    def _write_executive_control(self, f):
        f.write(f"ID {self.model.title[:60]}\n")
        sol = 101
        if self.model.steps and self.model.steps[0].analysis_type == 'BUCKLE':
            sol = 105
        f.write(f"SOL {sol}\n")
        f.write("CEND\n")

    def _write_case_control(self, f):
        f.write(f"TITLE = {self.model.title}\n")
        f.write("ECHO = NONE\n")

        for i, step in enumerate(self.model.steps):
            f.write(f"SUBCASE {i+1}\n")
            if step.name:
                f.write(f"  LABEL = {step.name}\n")
            if step.boundaries:
                f.write(f"  SPC = {self.spc_id}\n")
            if step.loads:
                f.write(f"  LOAD = {self.load_id}\n")
            f.write("  DISP = ALL\n")
            f.write("  STRESS = ALL\n")

    def _format_field_fixed(self, val):
        if val is None:
            return "        "
        if isinstance(val, float):
            if val == 0.0:
                return "0.0     "
            s = f"{val:g}"
            if len(s) <= 8:
                return s.ljust(8)
            s = f"{val:.4e}"
            parts = s.split('e')
            mantissa = parts[0]
            exp = int(parts[1])
            exp_str = f"{exp:+03d}"
            max_m_len = 8 - len(exp_str)
            mantissa = mantissa[:max_m_len]
            if mantissa.endswith('.'): mantissa = mantissa[:-1]
            s = mantissa + exp_str
            return s.ljust(8)
        s = str(val)[:8]
        return s.ljust(8)

    def _format_field_large(self, val):
        if val is None:
            return "                "
        s = str(val)
        if len(s) > 16:
            if isinstance(val, float):
                s = f"{val:.9e}"
        return s[:16].ljust(16)

    def _write_card(self, f, fields):
        if not fields: return

        if self.format == 'free':
            f.write(",".join(str(f) if f is not None else "" for f in fields) + "\n")
        elif self.format == 'large':
            keyword = fields[0]
            # Keyword followed by * must fit in 8 chars for field 1
            f.write(f"{keyword[:7] + '*':<8}")
            for i in range(1, min(5, len(fields))):
                f.write(self._format_field_large(fields[i]))
            f.write("\n")

            remaining = fields[5:]
            while remaining:
                f.write("        *")
                for i in range(min(4, len(remaining))):
                    f.write(self._format_field_large(remaining[i]))
                f.write("\n")
                remaining = remaining[4:]
        else: # Fixed
            keyword = fields[0]
            line = f"{keyword:<8}"
            for i in range(1, len(fields)):
                if i > 1 and (i - 1) % 8 == 0:
                    cont = f"+C{i//8:06d}"
                    line += cont
                    f.write(line + "\n")
                    line = cont.ljust(8)
                line += self._format_field_fixed(fields[i])
            if line.strip():
                while len(line) < 72: line += "        "
                f.write(line + "\n")

    def _write_bulk_data(self, f):
        for inc in self.model.includes:
            f.write(f"INCLUDE '{inc.filename}'\n")

        for node in self.model.nodes.values():
            self._write_card(f, ["GRID", node.id, None, node.coords[0], node.coords[1], node.coords[2]])

        for i, (name, mat) in enumerate(self.model.materials.items()):
            mid = i + 1
            self.material_ids[name] = mid
            if mat.elastic:
                self._write_card(f, ["MAT1", mid, mat.elastic[0], None, mat.elastic[1], mat.density])

        for i, sec in enumerate(self.model.sections):
            pid = i + 1
            self.property_ids[sec.elset] = pid
            mid = self.material_ids.get(sec.material, "")
            if sec.type == 'SOLID':
                self._write_card(f, ["PSOLID", pid, mid])
            elif sec.type == 'SHELL':
                self._write_card(f, ["PSHELL", pid, mid, sec.thickness if sec.thickness else 1.0])
            elif sec.type == 'BEAM':
                area, i1, i2 = 1.0, 1.0, 1.0
                if sec.section_type == 'RECT' and len(sec.section_params) >= 2:
                    b, h = sec.section_params[0], sec.section_params[1]
                    area = b * h
                    i1 = (b * h**3) / 12.0
                    i2 = (h * b**3) / 12.0
                self._write_card(f, ["PBAR", pid, mid, area, i1, i2])

        elem_map = {
            'S4': 'CQUAD4', 'S4R': 'CQUAD4',
            'C3D8': 'CHEXA', 'C3D8R': 'CHEXA',
            'B31': 'CBAR', 'SPRING1': 'CELAS2'
        }

        for elem in self.model.elements.values():
            nastran_type = elem_map.get(elem.type, "UNKNOWN")
            pid = self.property_ids.get(elem.elset, 1)

            if nastran_type == 'CQUAD4':
                self._write_card(f, ["CQUAD4", elem.id, pid] + elem.nodes)
            elif nastran_type == 'CHEXA':
                self._write_card(f, ["CHEXA", elem.id, pid] + elem.nodes)
            elif nastran_type == 'CBAR':
                self._write_card(f, ["CBAR", elem.id, pid] + elem.nodes + [0.0, 0.0, 1.0])
            elif nastran_type == 'CELAS2':
                 stiffness = elem.stiffness if elem.stiffness is not None else 1000.0
                 node1 = elem.nodes[0]
                 self._write_card(f, ["CELAS2", elem.id, stiffness, node1, 1, 0, 0])

        for step in self.model.steps:
            for bc in step.boundaries:
                dofs = "".join(str(d) for d in range(bc.first_dof, bc.last_dof + 1))
                if bc.target in self.model.node_sets:
                    for node_id in self.model.node_sets[bc.target].ids:
                        self._write_card(f, ["SPC1", self.spc_id, dofs, node_id])
                else:
                    try:
                        node_id = int(bc.target)
                        self._write_card(f, ["SPC1", self.spc_id, dofs, node_id])
                    except ValueError: pass

        for step in self.model.steps:
            for load in step.loads:
                if load.type == 'CLOAD':
                    mag = load.magnitude
                    dof = int(load.dof_or_label)
                    dir_vec = [0.0, 0.0, 0.0]
                    card_type = "FORCE"
                    if 1 <= dof <= 3:
                        dir_vec[dof - 1] = 1.0
                    elif 4 <= dof <= 6:
                        card_type = "MOMENT"
                        dir_vec[dof - 4] = 1.0

                    targets = []
                    if load.target in self.model.node_sets:
                        targets = self.model.node_sets[load.target].ids
                    else:
                        try: targets = [int(load.target)]
                        except ValueError: pass

                    for node_id in targets:
                        self._write_card(f, [card_type, self.load_id, node_id, 0, mag] + dir_vec)
