from web import filters


def test_repeated_key_order_does_not_matter():
    assert filters.same_filters("tag=a&tag=b", "tag=b&tag=a")


def test_doubly_quoted_banner_is_bare(tmp_path):
    env = tmp_path / ".env"
    env.write_text("BANNER=\"'Sale now on'\"\n")
    assert filters.load_banner(str(env)) == "Sale now on"
