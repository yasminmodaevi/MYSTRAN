from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union

@dataclass
class Node:
    id: int
    coords: List[float]

@dataclass
class Element:
    id: int
    type: str
    nodes: List[int]
    elset: Optional[str] = None
    stiffness: Optional[float] = None # For springs

@dataclass
class Material:
    name: str
    elastic: Optional[List[float]] = None
    density: Optional[float] = None

@dataclass
class Section:
    elset: str
    material: Optional[str]
    type: str
    thickness: Optional[float] = None
    section_type: Optional[str] = None
    section_params: List[float] = field(default_factory=list)

@dataclass
class Set:
    name: str
    ids: List[int] = field(default_factory=list)
    type: str = "node"

@dataclass
class BoundaryCondition:
    target: str
    first_dof: int
    last_dof: int
    value: float = 0.0

@dataclass
class Load:
    type: str
    target: str
    dof_or_label: Union[int, str]
    magnitude: float

@dataclass
class Step:
    name: Optional[str] = None
    analysis_type: str = "STATIC"
    boundaries: List[BoundaryCondition] = field(default_factory=list)
    loads: List[Load] = field(default_factory=list)

@dataclass
class IncludeFile:
    filename: str

class FEModel:
    def __init__(self):
        self.nodes: Dict[int, Node] = {}
        self.elements: Dict[int, Element] = {}
        self.materials: Dict[str, Material] = {}
        self.sections: List[Section] = []
        self.node_sets: Dict[str, Set] = {}
        self.element_sets: Dict[str, Set] = {}
        self.steps: List[Step] = []
        self.parameters: Dict[str, Any] = {}
        self.includes: List[IncludeFile] = []
        self.title: str = "Converted from CalculiX"

    def add_node(self, node_id: int, x: float, y: float, z: float):
        self.nodes[node_id] = Node(node_id, [x, y, z])

    def add_element(self, elem_id: int, elem_type: str, nodes: List[int], elset: str = None):
        self.elements[elem_id] = Element(elem_id, elem_type, nodes, elset)
        if elset:
            self.get_or_create_elset(elset).ids.append(elem_id)

    def get_or_create_nset(self, name: str) -> Set:
        if name not in self.node_sets:
            self.node_sets[name] = Set(name, type="node")
        return self.node_sets[name]

    def get_or_create_elset(self, name: str) -> Set:
        if name not in self.element_sets:
            self.element_sets[name] = Set(name, type="element")
        return self.element_sets[name]
