#!/usr/bin/env python3
"""
Knowledge Graph Visualizer

Generates an interactive HTML visualization of the Vedic Knowledge Graph.

Usage:
  python3 scripts/visualize-knowledge-graph.py --output graph-viz.html
  python3 scripts/visualize-knowledge-graph.py --communities 5 --limit 300

Dependencies: plotly (pip install plotly)
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go


def load_graph(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_viz(graph: dict, max_nodes: int = 500, community_limit: int = 0):
    nodes = graph.get("nodes", [])[:max_nodes]
    links = graph.get("links", [])

    # Community coloring
    communities = defaultdict(list)
    for n in nodes:
        cid = n.get("community", -1)
        communities[cid].append(n["id"])

    if community_limit > 0:
        top_communities = sorted(communities.items(), key=lambda x: -len(x[1]))[:community_limit]
        allowed = {nid for _, ids in top_communities for nid in ids}
        nodes = [n for n in nodes if n["id"] in allowed]

    node_ids = [n["id"] for n in nodes]
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

    # Node positions (simple circular layout by community)
    import math
    positions = {}
    for cid, ids in communities.items():
        angle_step = 2 * math.pi / max(len(ids), 1)
        for i, nid in enumerate(ids):
            angle = i * angle_step
            r = 1 + (cid % 8) * 0.8
            positions[nid] = (r * math.cos(angle), r * math.sin(angle))

    x = [positions.get(nid, (0, 0))[0] for nid in node_ids]
    y = [positions.get(nid, (0, 0))[1] for nid in node_ids]
    labels = [n.get("label", nid)[:40] for nid, n in zip(node_ids, nodes)]
    colors = [n.get("community", -1) for n in nodes]

    # Edges (sample for performance)
    edge_x, edge_y = [], []
    for link in links[:2000]:
        s, t = link.get("source"), link.get("target")
        if s in id_to_idx and t in id_to_idx:
            x0, y0 = positions.get(s, (0, 0))
            x1, y1 = positions.get(t, (0, 0))
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color="#888"),
        hoverinfo="none",
        mode="lines",
    )

    node_trace = go.Scatter(
        x=x, y=y,
        mode="markers",
        hoverinfo="text",
        text=labels,
        marker=dict(
            showscale=True,
            colorscale="Viridis",
            size=8,
            color=colors,
            colorbar=dict(thickness=15, title="Community"),
            line_width=1,
        ),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title="Vedic Knowledge Graph — Interactive View",
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=900,
        ),
    )

    return fig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", default="knowledge-graph/graphify-out/graph.json")
    parser.add_argument("--output", default="knowledge-graph-viz.html")
    parser.add_argument("--limit", type=int, default=600)
    parser.add_argument("--communities", type=int, default=0)
    args = parser.parse_args()

    graph_path = Path(args.graph)
    if not graph_path.exists():
        print(f"Graph not found: {graph_path}")
        return

    graph = load_graph(graph_path)
    fig = build_viz(graph, max_nodes=args.limit, community_limit=args.communities)
    fig.write_html(args.output, include_plotlyjs="cdn")
    print(f"✓ Visualization written to {args.output}")


if __name__ == "__main__":
    main()
