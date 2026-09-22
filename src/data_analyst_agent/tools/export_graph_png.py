"""Dev utility: render the compiled research graph as a Mermaid PNG.

Not an LLM-callable tool -- run manually with `python -m
data_analyst_agent.tools.export_graph_png` to regenerate docs/images/graph.png
after changing graph.py.
"""

from __future__ import annotations

import os

from data_analyst_agent.graph import build_graph


def main() -> None:
    graph = build_graph("research")
    png_bytes = graph.get_graph().draw_mermaid_png()

    out_dir = os.path.join("docs", "images")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "graph.png")
    with open(out_path, "wb") as f:
        f.write(png_bytes)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
