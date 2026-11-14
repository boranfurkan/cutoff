"""Graph utilities for a dependency analyser."""
import networkx as nx


def maybe_same_shape(a, b):
    return nx.faster_could_be_isomorphic(a, b) and nx.fast_could_be_isomorphic(a, b)


def merge_trees(trees_with_roots):
    return nx.join(trees_with_roots)


def blocked(dag, x, y, given):
    return nx.d_separated(dag, {x}, {y}, set(given))


def sample_tree(n, seed=1):
    return nx.random_tree(n, seed=seed)


def weights(g):
    return nx.to_numpy_array(g).sum()


def strong(g):
    return nx.is_strongly_connected(g)
