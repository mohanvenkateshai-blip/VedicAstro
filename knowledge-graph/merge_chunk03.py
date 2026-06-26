import json
from pathlib import Path

out = Path("graphify-out")
g = json.loads((out / "graph.json").read_text())
c3 = json.loads((out / ".graphify_chunk_03.json").read_text())

# graph.json uses "links" not "edges"
existing_node_ids = {n["id"] for n in g["nodes"]}
new_nodes = [n for n in c3["nodes"] if n["id"] not in existing_node_ids]
g["nodes"].extend(new_nodes)
g["links"].extend(c3["edges"])  # chunk uses "edges", graph uses "links"
g.setdefault("hyperedges", []).extend(c3.get("hyperedges", []))

(out / "graph.json").write_text(json.dumps(g, indent=2))
print(f"New nodes added: {len(new_nodes)}")
print(f"After merge: {len(g['nodes'])} nodes, {len(g['links'])} links")
