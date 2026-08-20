"""
visualize_graph.py — renders the ACTUAL compiled graph structure, straight
from the LangGraph object itself.
"""
from graph import proptech_system

try:
    png_bytes = proptech_system.get_graph().draw_mermaid_png()
    with open("graph_diagram.png", "wb") as f:
        f.write(png_bytes)
    print("Saved graph_diagram.png")
except Exception as e:
    print(f"PNG render skipped (needs internet): {e}")

mermaid_source = proptech_system.get_graph().draw_mermaid()
with open("graph_diagram.mmd", "w") as f:
    f.write(mermaid_source)
print("Saved graph_diagram.mmd (mermaid source)")

print("\n--- ASCII graph ---\n")
print(proptech_system.get_graph().draw_ascii())