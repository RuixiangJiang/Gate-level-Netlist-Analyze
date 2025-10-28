from NodeDefinition import *
from LibParser import *

def build_semantic_graph(
    lib_pin_dirs: Dict[str, Dict[str, str]],
    var_nodes: Dict[str, VarNode],
    gates: Dict[str, GateNode],
    edges_raw: List[Tuple[str, str, str, str]],
) -> Tuple[List[Tuple[str, str]], Dict[str, Dict[str, str]]]:
    """
    Returns:
      edges_sem: [ (source_name, target_name) ]
      node_meta: { name: { 'type': 'variable'|'gate', 'cell': str, 'inst': str } }
    """
    def gate_display_name(g: GateNode) -> str:
        return f"{g.inst} {g.cell.lower()}"

    node_meta: Dict[str, Dict[str, str]] = {}
    edges_sem: List[Tuple[str, str]] = []

    # Register all gate nodes in meta
    for g in gates.values():
        gname = gate_display_name(g)
        node_meta[gname] = {"type": "gate", "cell": g.cell, "inst": g.inst}

    # Register var nodes lazily when they appear in edges (or pre-register here)
    for v in var_nodes.values():
        node_meta.setdefault(v.name, {"type": "variable", "cell": "", "inst": ""})

    for (src, srcp, dst, dstp) in edges_raw:
        # print(f"src: {src}, srcp: {srcp}, dst: {dst}: {dstp}")
        if dst not in gates or src not in var_nodes:
            continue
        # n -> c : variable to gate pin (dstp)
        if src.startswith("n") and dst.startswith("c"):
            g = gates[dst]
            gname = gate_display_name(g)
            pin = g.port_map.get(dstp, "")
            pindir = lib_pin_dirs.get(g.cell, {}).get(pin, "")
            vname = var_nodes[src].name
            # print(f"pin: {pin}, pindir: {pindir}, vname: {vname}, gname: {gname}")
            if pindir == "input":
                edges_sem.append((vname, gname))
            elif pindir == "output":
                edges_sem.append((gname, vname))
            else:
                # Unknown direction: assume variable drives gate (conservative)
                edges_sem.append((vname, gname))

        # c -> n : gate pin (srcp) to variable
        elif src.startswith("c") and dst.startswith("n"):
            g = gates[src]
            gname = gate_display_name(g)
            pin = g.port_map.get(srcp, "")
            pindir = lib_pin_dirs.get(g.cell, {}).get(pin, "")
            vname = var_nodes[dst].name
            if pindir == "output":
                edges_sem.append((gname, vname))
            elif pindir == "input":
                edges_sem.append((vname, gname))
            else:
                # Unknown direction: assume gate drives variable (common case)
                edges_sem.append((gname, vname))

        # Otherwise (n->n / c->c)：ignore
        else:
            continue

    return edges_sem, node_meta