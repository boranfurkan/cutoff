"""Choose which servers in a network host monitoring agents."""
import json

import networkx as nx


def build(links):
    g = nx.Graph()
    g.add_edges_from(links)
    return g


def monitor_nodes(g, seed=7):
    """Servers that host a monitor: no two are directly linked, and every other server neighbours one."""
    return nx.maximal_independent_set(g, seed=seed)


def degree_ranking(g):
    return [n for n, _ in sorted(g.degree, key=lambda kv: (-kv[1], kv[0]))]


def rollout_plan(g, seed=7):
    """JSON rollout plan: the first monitor is the primary, the rest follow in order."""
    nodes = monitor_nodes(g, seed)
    nodes.sort()
    return json.dumps({"primary": nodes[0], "others": nodes[1:]})
