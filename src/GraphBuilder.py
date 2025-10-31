from NodeDefinition import *
from LibParser import *


def collapse_x_nodes(edges_raw: List[Tuple[str, str, str, str]]) -> List[Tuple[str, str, str, str]]:
    """
    Remove intermediate 'x...' routing nodes inserted by Yosys 'show'.

    Any pattern like:
        A -> xK -> B
    is turned into:
        A -> B

    We keep DOT port tags (pXX) on the original ends:
      - use the source port tag from A->xK
      - use the dest   port tag from xK->B

    Notes:
      - xK can have multiple fanouts, so one input edge may expand to many (A->B1, A->B2, ...)
      - xK can have multiple fanins (rare), we create all pairwise combinations.
    """
    fanin: Dict[str, List[Tuple[str, str, str, str]]] = {}
    fanout: Dict[str, List[Tuple[str, str, str, str]]] = {}

    for s, sp, d, dp in edges_raw:
        fanout.setdefault(s, []).append((s, sp, d, dp))
        fanin.setdefault(d, []).append((s, sp, d, dp))

    new_edges: List[Tuple[str, str, str, str]] = []

    # 1. Keep all direct edges that do NOT involve an x-node
    for s, sp, d, dp in edges_raw:
        if s.startswith("x") or d.startswith("x"):
            continue
        new_edges.append((s, sp, d, dp))

    # 2. For every x-node, connect its fanin sources directly to its fanout sinks
    x_nodes = set([n for n in fanin.keys() if n.startswith("x")] +
                  [n for n in fanout.keys() if n.startswith("x")])

    for x in x_nodes:
        ins = fanin.get(x, [])
        outs = fanout.get(x, [])
        # print(f"x node {x}: ins: {ins}, outs: {outs}")
        for (a, a_port, _x1, _x1_port) in ins:
            for (_x2, _x2_port, b, b_port) in outs:
                # Skip if the collapsed edge would still go through another x node
                if a.startswith("x") or b.startswith("x"):
                    continue
                new_edges.append((a, a_port, b, b_port))
                print(f"new edge: {a} {a_port} {b} {b_port}")

    return new_edges

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