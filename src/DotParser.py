import re

from NodeDefinition import *


DOT_VAR_RE = re.compile(r'^(n\d+)\s*\[\s*shape=(octagon|diamond).*?label="([^"]+)"')
DOT_GATE_RE = re.compile(r'^(c\d+)\s*\[\s*shape=record,\s*label="(.+?)"')
DOT_EDGE_RE = re.compile(
    r'^((?:n|c|x)\d+)'      # allow node ids starting with n / c / x
    r'(?::(p\d+))?'         # optional source port tag like :p12
    r'(?::[nesw])?'         # optional compass dir like :e/:w/:n/:s
    r'\s*->\s*'
    r'((?:n|c|x)\d+)'       # allow dest ids starting with n / c / x
    r'(?::(p\d+))?'         # optional dest port tag
    r'(?::[nesw])?'         # optional compass dir
    r'.*$'                  # ignore the [ ... ]; part at the end of the line
)
PORT_TAG_RE = re.compile(r'<(p\d+)>\s*([^|}\s]+)')
CENTRAL_LABEL_RE = re.compile(r'\}\|\s*([^|]+?)\s*\|\{')

def parse_yosys_dot(dot_path: str) -> Tuple[Dict[str, VarNode], Dict[str, GateNode], List[Tuple[str, str, str, str]]]:
    """
    Returns:
      var_nodes: {dot_id -> VarNode}
      gate_nodes: {dot_id -> GateNode}
      edges_raw: list of (src_id, src_port, dst_id, dst_port) from DOT
    """
    with open(dot_path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines()]

    var_nodes: Dict[str, VarNode] = {}
    gates: Dict[str, GateNode] = {}
    edges_raw: List[Tuple[str, str, str, str]] = []

    for line in lines:
        m = DOT_VAR_RE.search(line)
        if m:
            dot_id, _shape, label = m.groups()
            var_nodes[dot_id] = VarNode(dot_id=dot_id, name=label.strip())
            continue
        m = DOT_GATE_RE.search(line)
        if m:
            dot_id, label = m.groups()
            # Port tags
            ports = {p: n for p, n in PORT_TAG_RE.findall(label)}
            # Instance + Cell from central section
            inst, cell = dot_id, "GATE"
            cm = CENTRAL_LABEL_RE.search(label)
            if cm:
                mid = cm.group(1)          # e.g. "$183\nNOR"
                mid = mid.replace("\\n", "\n")
                parts = [x.strip() for x in mid.split("\n") if x.strip()]
                if len(parts) == 2:
                    inst, cell = parts[0], parts[1].upper()
                elif len(parts) == 1:
                    cell = parts[0].upper()
            gates[dot_id] = GateNode(dot_id=dot_id, inst=inst, cell=cell, port_map=ports)
            continue
        m = DOT_EDGE_RE.search(line)
        if m:
            src, srcp, dst, dstp = m.groups()
            edges_raw.append((src, srcp or "", dst, dstp or ""))

    return var_nodes, gates, edges_raw