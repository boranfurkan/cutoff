from scoring import model


def test_describe():
    slope, intercept = model.fit([0, 1, 2], [1, 3, 5])
    assert model.describe(slope, intercept) == "y = 2.00x + 1.00"


def test_bucket():
    assert model.bucket(55, [50, 70, 90]) == 1
