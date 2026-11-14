from hub import refs


def test_parse_url():
    assert refs.parse("https://huggingface.co/datasets/acme/reviews") == {
        "type": "dataset", "namespace": "acme", "name": "reviews"}


def test_parse_short():
    assert refs.parse("acme/bert-tiny") == {"type": "model", "namespace": "acme", "name": "bert-tiny"}


def test_endpoint_kinds():
    kinds = refs.private_endpoint_kinds()
    assert len(kinds) == 2 and "private" in kinds



def test_large_upload():
    assert refs.has_large_upload()
