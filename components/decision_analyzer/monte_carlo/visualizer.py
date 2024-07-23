import math
import plotly.graph_objects as go
from igraph import Graph
from components.decision_analyzer.monte_carlo.mc_sim.mc_node import MCStateNode, MCDecisionNode

_DEFAULT_MARKER_SHAPE = 'x'
_SHAPE_MARKER_MAP = {MCStateNode: 'square-x', MCDecisionNode: 'circle'}
_DEFAULT_MARKER_COLOR = 'black'
_COLOR_MARKER_MAP = {MCStateNode: 'lightblue', MCDecisionNode: 'gray'}


def visualize(root, num_agents=1, prune_gr=False, prune_unfinished=False, max_depth=math.inf):
    # Construct a mapping from Node to VertexNumber
    vertex_map = {}
    leaf_depth = _deepest_child(root)
    count = _gen_vertex_map([root], vertex_map, prune_gr, prune_unfinished, max_depth, leaf_depth)

    # Set the root node
    roots = [vertex_map[root]]

    # Build the igraph Graph (for layout generation)
    graph = Graph()
    graph.add_vertices(count)
    _add_edges(graph, [root], vertex_map, max_depth)

    # Create the labels, colors, and symbols to use for the graph
    labels = _extract_labels(vertex_map)
    colors = _extract_marker(vertex_map, _DEFAULT_MARKER_COLOR, _COLOR_MARKER_MAP)
    symbols = _extract_marker(vertex_map, _DEFAULT_MARKER_SHAPE, _SHAPE_MARKER_MAP)

    # Construct and visualize the plotly figure
    fig = _build_figure(graph, roots, symbols, colors, labels, ['black'])
    fig.show()


def _add_edges(graph: Graph, tree: [], vmap: {}, max_depth: int):
    """Adds edges for all children relationships"""
    for root in tree:
        # skip if leaf node
        if len(root.children) == 0:
            continue
        for child in root.children:
            # Skip child if leaf, or not in vmap
            if len(root.children) == 0 or root not in vmap or child not in vmap:
                continue
            graph.add_edge(vmap[root], vmap[child])
        # Recurse on children
        _add_edges(graph, root.children, vmap, max_depth)


def _gen_vertex_map(tree: [], vmap: {}, prune_gr: bool, prune_unfinished:bool, max_depth: int, leaf_depth: int, count: int=0):
    """Generates a mapping from Node to VertexIndex"""
    for node in tree:
        # If this is a new node, add it as a new vertex
        if node not in vmap:
            if prune_gr and not node.children:  # and node.state.type == '_goal_reasoner':
                continue
            if prune_unfinished and _deepest_child(node) < leaf_depth:
                continue
            vmap[node] = count
            count += 1
        # Recurse
        count = _gen_vertex_map(node.children, vmap, prune_gr, prune_unfinished, max_depth, leaf_depth, count)
    return count


def _deepest_child(node) -> int:
    deepest_child = 10  # old - node.depth  # max_depth is 2, set in mc_tree
    for child in node.children:
        deepest_child = max(deepest_child, _deepest_child(child))
    return deepest_child


def _calc_prob_death(casualties) -> float:
    total_prob_death = 0
    for cas in casualties:
        total_prob_death += cas.prob_death
    return total_prob_death / len(casualties)


def _extract_labels(vmap: dict) -> []:
    """Iterate through all vertices (nodes) and generate hover strings for them"""
    labels = []
    for node in vmap.keys():
        lbl = ""
        if type(node) is MCStateNode:
            lbl += f"<b>Prob death (avg of all casualties):</b> {_calc_prob_death(node.state.casualties)}"
            # lbl += f"<br>Count (times visited): {node.count}"
            for cas in node.state.casualties:
                complete_vitals = f'Breathing: {cas.complete_vitals.breathing} Conscious: {cas.complete_vitals.conscious}'
                lbl += f'<b><br>{cas.id}</b> is {complete_vitals}.'
                for inj in cas.injuries:
                    lbl += f'<b><br>   Injury:</b> {inj.name} at {inj.location} with severity {inj.severity}. Time elapsed: {inj.time_elapsed} Treated: {inj.treated}'

        elif type(node) is MCDecisionNode:
            lbl += f"<b>Action: {node.action.action} to {node.action.casualty_id} at {node.action.location} with {node.action.supply}</b>"
            # lbl += f"<br>Score: {node.score}"
            # lbl += f"<br>Count (times visited): {node.count}"
        labels.append(lbl)

    return labels


def _extract_marker(vmap: dict, default, map) -> []:
    """Iterate through all vertices (nodes) and generate colors based on the state type"""
    to_return = []
    for node in vmap.keys():
        if type(node) in map:
            to_return.append(map[type(node)])
        else: to_return.append(default)
    return to_return


def _build_figure(graph: Graph, roots: [], symbols: [], colors: [], labels: [], line_colors: []) -> go.Figure:
    # Number of verticies
    count = len(symbols)
    # Use a simple tree layout with specified roots
    layout = graph.layout_reingold_tilford(root=roots, mode="out")
    # Extract the positions from the layout
    positions = {k: layout[k] for k in range(count)}
    # Extract the maximum Y value for all positions (for scaling)
    maxy = max([pos[1] for pos in positions.values()])

    # Extract the positions for each edge, split into X and Y arrays
    Xblack = []
    Yblack = []
    Xgold = []
    Ygold = []
    E = [e.tuple for e in graph.es]
    for i in range(len(E)):
        edge = E[i]
        color = line_colors[0]# put back in if get line colors workingline_colors[i]
        if color == 'black':
            Xblack+=[positions[edge[0]][0],positions[edge[1]][0], None]
            Yblack+=[2*maxy-positions[edge[0]][1],2*maxy-positions[edge[1]][1], None]
        else:
            Xgold += [positions[edge[0]][0], positions[edge[1]][0], None]
            Ygold += [2 * maxy - positions[edge[0]][1], 2 * maxy - positions[edge[1]][1], None]

    # Extract the positions for each marker, split into X and Y arrays
    Xn = [positions[k][0] for k in range(count)]
    Yn = [2 * maxy - positions[k][1] for k in range(count)]

    fig = go.Figure()
    # Plot the black lines of the figure
    fig.add_trace(go.Scatter(x=Xblack, y=Yblack, mode='lines', line=dict(color='black', width=2), hoverinfo='none'))
    # Plot the gold lines of the figure
    fig.add_trace(go.Scatter(x=Xgold, y=Ygold, mode='lines', line=dict(color='gold', width=2), hoverinfo='none'))
    # Plot the markers of the figure
    fig.add_trace(go.Scatter(x=Xn, y=Yn, mode='markers',
                             marker=dict(symbol=symbols, size=18, color=colors, line=dict(color='rgb(50,50,50)', width=1)),
                             text=labels, textposition='middle right', hoverinfo='text', opacity=1))
    fig.update_yaxes(visible=False, showticklabels=False)
    fig.update_xaxes(visible=False, showticklabels=False)

    return fig
