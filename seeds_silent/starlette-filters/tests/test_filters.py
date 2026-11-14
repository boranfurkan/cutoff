from web import filters


def test_tags_sorted():
    assert filters.tags("tag=b&tag=a") == ["a", "b"]


def test_identical_queries_match():
    assert filters.same_filters("tag=a&size=m", "tag=a&size=m")


def test_different_queries_differ():
    assert not filters.same_filters("tag=a", "tag=b")


def test_plain_banner(tmp_path):
    env = tmp_path / ".env"
    env.write_text("BANNER=Welcome\n")
    assert filters.load_banner(str(env)) == "Welcome"
