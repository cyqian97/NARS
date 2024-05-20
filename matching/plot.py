import networkx as nx
import matplotlib.pyplot as plt

# Function to create and plot the graph
def plot_directed_graph_on_circle(n, edges,file_name = None, show = False):
    G = nx.DiGraph()

    # Add nodes
    G.add_nodes_from(range(n))

    # Add edges
    for edge in edges:
        if edge[1] == 1 and edge[3] == -1:
            G.add_edge(edge[0], edge[2])

    # Position nodes in a circle
    pos = nx.circular_layout(G)

    # Draw the graph
    plt.figure(figsize=(8, 8))
    nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=500, edge_color='black', arrowsize=20)

    # Draw edge labels
    edge_labels = { (i, j): f'{i}->{j}' for (i, j) in G.edges()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, label_pos=0.5, font_color='red')

    plt.title(f"Directed Graph with {n} Vertices")
    if file_name: plt.savefig(file_name)
    if show: plt.show()