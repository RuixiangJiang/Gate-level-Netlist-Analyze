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
                # print(f"new edge: {a} {a_port} {b} {b_port}")

    return new_edges

def build_semantic_graph(
    lib_pin_dirs: Dict[str, Dict[str, str]],
    var_nodes: Dict[str, VarNode],
    gates: Dict[str, GateNode],
    edges_raw: List[Tuple[str, str, str, str]],
) -> Tuple[List[Tuple[str, str]], Dict[str, Dict[str, str]]]:
    """
    Convert raw DOT edges to directed semantic edges.

    We now handle four edge shapes:
      1. n -> c  (variable/net -> gate pin)
         - if that pin is an INPUT  pin: var -> gate
         - if that pin is an OUTPUT pin: gate -> var  (reverse)
      2. c -> n  (gate pin -> variable/net)
         - usually gate -> var
      3. n -> n  (net-to-net connection, or collapsed through x-nodes)
         - keep as varA -> varB using DOT edge direction
      4. c -> c  (gate-to-gate direct connection after collapsing x-nodes)
         - keep as gateA -> gateB using DOT edge direction

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

        # n -> n : net-to-net (after collapsing x-nodes, or direct bus split/merge)
        elif src.startswith("n") and dst.startswith("n"):
            # print(f"src: {src}, dst: {dst}")
            if src not in var_nodes or dst not in var_nodes:
                continue
            v_src = var_nodes[src].name
            v_dst = var_nodes[dst].name
            # print(f"v_src: {v_src}, v_dst: {v_dst}\n")
            # Keep DOT direction: src net "drives" dst net
            edges_sem.append((v_src, v_dst))

        # c -> c : gate-to-gate (possible after collapsing x-nodes)
        elif src.startswith("c") and dst.startswith("c"):
            if src not in gates or dst not in gates:
                continue
            g_src = gates[src]
            g_dst = gates[dst]
            # Keep DOT direction: src gate "drives" dst gate
            edges_sem.append((gate_display_name(g_src), gate_display_name(g_dst)))

        # ignore anything else (shouldn't appear after collapse_x_nodes)
        else:
            continue

    return edges_sem, node_meta