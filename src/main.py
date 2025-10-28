import argparse

from Print import *
from DotParser import *

ap = argparse.ArgumentParser(description="Build semantic logic graph from Liberty + Yosys DOT.")
ap.add_argument("--lib", required=True, help="Path to cmos_cells.lib (Liberty)")
ap.add_argument("--dot", required=True, help="Path to cmos.dot (Yosys 'show' output)")
ap.add_argument("--out-prefix", required=True, help="Output prefix, e.g., 'graph'")
ap.add_argument("--emit-pdf", action="store_true", help="Also emit {prefix}_sem_graph.pdf (requires Graphviz)")
args = ap.parse_args()

lib_pin_dirs = parse_liberty_pin_dirs(f"../data/{args.lib}/{args.lib}.lib")
if not lib_pin_dirs:
    raise SystemExit(f"[ERROR] No cells parsed from Liberty: {args.lib}")

var_nodes, gates, edges_raw = parse_yosys_dot(f"../data/{args.dot}/{args.dot}.dot")
if not gates:
    raise SystemExit(f"[ERROR] No gates parsed from DOT: {args.dot}")

edges_sem, node_meta = build_semantic_graph(lib_pin_dirs, var_nodes, gates, edges_raw)

nodes_csv, edges_csv = save_csv_nodes_edges(args.out_prefix, node_meta, edges_sem)
dot_out = save_semantic_dot(args.out_prefix, node_meta, edges_sem)

print(f"[OK] Nodes CSV: {nodes_csv}")
print(f"[OK] Edges CSV: {edges_csv}")
print(f"[OK] DOT:       {dot_out}")

if args.emit_pdf:
    pdf_out = f"{args.out_prefix}_sem_graph.pdf"
    try_emit_pdf(dot_out, pdf_out)