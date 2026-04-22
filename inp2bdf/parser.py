import os
from .models import FEModel, Section, BoundaryCondition, Load, Step, Material, IncludeFile

class InpParser:
    def __init__(self, model: FEModel = None, inline_includes: bool = False):
        self.model = model if model else FEModel()
        self.current_step = None
        self.in_step = False
        self.current_material = None
        self.parameters = {}
        self.inline_includes = inline_includes

    def parse(self, filepath):
        filepath = os.path.abspath(filepath)
        if not os.path.exists(filepath):
            return self.model

        base_dir = os.path.dirname(filepath)

        with open(filepath, 'r') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('**'):
                i += 1
                continue

            if line.startswith('*'):
                keyword_line = line[1:].split(',')
                keyword = keyword_line[0].strip().upper()
                params = {}
                for p in keyword_line[1:]:
                    if '=' in p:
                        parts = p.split('=')
                        k = parts[0].strip().upper()
                        v = parts[1].strip()
                        params[k] = self._resolve_val(v)
                    else:
                        params[p.strip().upper()] = True

                i += 1
                data_lines = []
                while i < len(lines) and not lines[i].strip().startswith('*'):
                    raw_line = lines[i].strip()
                    if raw_line and not raw_line.startswith('**'):
                        data_lines.append(raw_line)
                    i += 1

                self._handle_keyword(keyword, params, data_lines, base_dir)
            else:
                i += 1

        return self.model

    def _resolve_val(self, val):
        if isinstance(val, str) and val.startswith('<') and val.endswith('>'):
            param_name = val[1:-1]
            return self.parameters.get(param_name, val)
        return val

    def _handle_keyword(self, keyword, params, data, base_dir):
        if keyword == 'NODE':
            for line in data:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 4: continue
                self.model.add_node(int(self._resolve_val(parts[0])),
                                    float(self._resolve_val(parts[1])),
                                    float(self._resolve_val(parts[2])),
                                    float(self._resolve_val(parts[3])))
                if 'NSET' in params:
                    self.model.get_or_create_nset(params['NSET']).ids.append(int(self._resolve_val(parts[0])))

        elif keyword == 'ELEMENT':
            elem_type = params.get('TYPE')
            elset = params.get('ELSET')
            # Multi-line handling for elements with many nodes (e.g. C3D20)
            current_elem_id = None
            current_nodes = []

            for line in data:
                parts = [p.strip() for p in line.split(',')]
                if not parts: continue

                if line.startswith(' '): # Continuation
                    current_nodes.extend([int(self._resolve_val(n)) for n in parts if n])
                else:
                    if current_elem_id is not None:
                        self.model.add_element(current_elem_id, elem_type, current_nodes, elset)

                    current_elem_id = int(self._resolve_val(parts[0]))
                    current_nodes = [int(self._resolve_val(n)) for n in parts[1:] if n]

            if current_elem_id is not None:
                self.model.add_element(current_elem_id, elem_type, current_nodes, elset)

        elif keyword == 'SPRING':
            elset = params.get('ELSET')
            if data:
                stiffness = float(self._resolve_val(data[0].strip()))
                if elset in self.model.element_sets:
                    for eid in self.model.element_sets[elset].ids:
                        if eid in self.model.elements:
                            self.model.elements[eid].stiffness = stiffness

        elif keyword == 'NSET':
            name = params.get('NSET')
            nset = self.model.get_or_create_nset(name)
            if 'GENERATE' in params:
                for line in data:
                    vals = [int(self._resolve_val(v.strip())) for v in line.split(',')]
                    start, end = vals[0], vals[1]
                    step = vals[2] if len(vals) > 2 else 1
                    nset.ids.extend(range(start, end + 1, step))
            else:
                for line in data:
                    nset.ids.extend([int(self._resolve_val(n.strip())) for n in line.split(',') if n.strip()])

        elif keyword == 'ELSET':
            name = params.get('ELSET')
            elset = self.model.get_or_create_elset(name)
            if 'GENERATE' in params:
                for line in data:
                    vals = [int(self._resolve_val(v.strip())) for v in line.split(',')]
                    start, end = vals[0], vals[1]
                    step = vals[2] if len(vals) > 2 else 1
                    elset.ids.extend(range(start, end + 1, step))
            else:
                for line in data:
                    elset.ids.extend([int(self._resolve_val(n.strip())) for n in line.split(',') if n.strip()])

        elif keyword == 'MATERIAL':
            name = params.get('NAME')
            self.current_material = Material(name)
            self.model.materials[name] = self.current_material

        elif keyword == 'ELASTIC':
            if self.current_material:
                parts = [float(self._resolve_val(p.strip())) for p in data[0].split(',')]
                self.current_material.elastic = parts

        elif keyword == 'DENSITY':
            if self.current_material:
                self.current_material.density = float(self._resolve_val(data[0].strip()))

        elif keyword in ['SOLID SECTION', 'SHELL SECTION', 'BEAM SECTION']:
            elset = params.get('ELSET')
            mat = params.get('MATERIAL')
            thickness = None
            if keyword == 'SHELL SECTION':
                if data:
                    thickness = float(self._resolve_val(data[0].split(',')[0]))

            section = Section(elset=elset, material=mat, type=keyword.split()[0], thickness=thickness)
            if keyword == 'BEAM SECTION':
                section.section_type = params.get('SECTION')
                if data:
                    section.section_params = [float(self._resolve_val(p.strip())) for p in data[0].split(',')]
            self.model.sections.append(section)

        elif keyword == 'STEP':
            self.in_step = True
            self.current_step = Step(name=params.get('NAME'))
            self.model.steps.append(self.current_step)

        elif keyword == 'END STEP':
            self.in_step = False
            self.current_step = None

        elif keyword == 'STATIC':
            if self.current_step:
                self.current_step.analysis_type = 'STATIC'

        elif keyword == 'BUCKLE':
             if self.current_step:
                self.current_step.analysis_type = 'BUCKLE'

        elif keyword == 'BOUNDARY':
            for line in data:
                parts = [self._resolve_val(p.strip()) for p in line.split(',')]
                if not parts: continue
                target = parts[0]
                first = int(parts[1])
                last = int(parts[2]) if len(parts) > 2 and parts[2] else first
                val = float(parts[3]) if len(parts) > 3 else 0.0
                bc = BoundaryCondition(target, first, last, val)
                if self.in_step:
                    self.current_step.boundaries.append(bc)
                else:
                    if not self.model.steps:
                         self.model.steps.append(Step(name="Initial Step"))
                    self.model.steps[0].boundaries.append(bc)

        elif keyword == 'CLOAD':
            for line in data:
                parts = [self._resolve_val(p.strip()) for p in line.split(',')]
                if not parts: continue
                target = parts[0]
                dof = int(parts[1])
                mag = float(parts[2])
                load = Load('CLOAD', target, dof, mag)
                if self.current_step:
                    self.current_step.loads.append(load)

        elif keyword == 'INCLUDE':
            inc_file = params.get('INPUT')
            if inc_file:
                if self.inline_includes:
                    full_path = os.path.join(base_dir, inc_file)
                    self.parse(full_path)
                else:
                    self.model.includes.append(IncludeFile(inc_file))

        elif keyword == 'PARAMETER':
            for line in data:
                if '=' in line:
                    parts = line.split('=')
                    self.parameters[parts[0].strip()] = parts[1].strip()
