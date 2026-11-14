import networkx as nx

from graphs import analysis


def test_shape():
    assert analysis.maybe_same_shape(nx.path_graph(4), nx.path_graph(4))
    assert not analysis.maybe_same_shape(nx.path_graph(4), nx.star_graph(3))


def test_merge():
    t = analysis.merge_trees([(nx.path_graph(2), 0), (nx.path_graph(3), 0)])
    assert t.number_of_nodes() == 6 and nx.is_tree(t)


def test_blocked():
    dag = nx.DiGraph([("rain", "wet"), ("wet", "slip")])
    assert analysis.blocked(dag, "rain", "slip", ["wet"])
    assert not analysis.blocked(dag, "rain", "slip", [])


def test_sample_tree():
    assert nx.is_tree(analysis.sample_tree(8))


def test_weights():
    assert analysis.weights(nx.path_graph(3)) == 4
