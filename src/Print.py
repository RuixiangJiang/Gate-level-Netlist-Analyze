import csv
import os
import shutil
import subprocess

from GraphBuilder import *

overall_prefix = f"../out/"


def save_csv_nodes_edges(prefix: str, node_meta: Dict[str, Dict[str, str]], edges: List[Tuple[str, str]]) -> Tuple[str, str]:
    nodes_csv = f"{overall_prefix}{prefix}_nodes.csv"
    edges_csv = f"{overall_prefix}{prefix}_edges.csv"

    # Nodes
    with open(nodes_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "type", "cell", "inst"])
        w.writeheader()
        for name, meta in sorted(node_meta.items(), key=lambda kv: (kv[1]["type"], kv[0])):
            row = {"name": name, **meta}
            w.writerow(row)

    # Edges
    with open(edges_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source", "target"])
        w.writeheader()
        for s, t in edges:
            w.writerow({"source": s, "target": t})

    return nodes_csv, edges_csv

def save_semantic_dot(prefix: str, node_meta: Dict[str, Dict[str, str]], edges: List[Tuple[str, str]]) -> str:
    dot_path = f"{overall_prefix}{prefix}_sem_graph.dot"
    lines = ["digraph G {", "rankdir=LR;"]
    for name, meta in node_meta.items():
        if meta["type"] == "variable":
            lines.append(f"\"{name}\" [shape=ellipse];")
        else:
            lines.append(f"\"{name}\" [shape=box];")
    for s, t in edges:
        lines.append(f"\"{s}\" -> \"{t}\";")
    lines.append("}")
    with open(dot_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return dot_path

def try_emit_pdf(dot_path: str, pdf_path: str) -> None:
    if shutil.which("dot") is None:
        print("[WARN] Graphviz 'dot' not found; skip PDF export.")
        return
    subprocess.run(["dot", "-Tpdf", dot_path, "-o", f"{overall_prefix}{pdf_path}"], check=False)
    if os.path.exists(pdf_path):
        print(f"[INFO] Wrote PDF: {pdf_path}")