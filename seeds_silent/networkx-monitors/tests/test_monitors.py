from graphs import monitors

LINKS = [("a", "b"), ("b", "c"), ("c", "d"), ("d", "e")]


def test_monitors_are_independent():
    g = monitors.build(LINKS)
    chosen = monitors.monitor_nodes(g)
    assert not any(g.has_edge(u, v) for u in chosen for v in chosen)


def test_degree_ranking():
    assert monitors.degree_ranking(monitors.build(LINKS))[0] == "b"
