from dataclasses import dataclass, field
from typing import Dict, List, Tuple

@dataclass
class VarNode:
    dot_id: str
    name: str

@dataclass
class GateNode:
    dot_id: str
    inst: str
    cell: str
    port_map: Dict[str, str] = field(default_factory=dict)