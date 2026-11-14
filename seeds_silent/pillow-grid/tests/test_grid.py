from charts import grid


def test_blank_is_empty():
    assert grid.coverage(grid.blank(20, 20)) == 0


def test_frame_touches_corners():
    img = grid.draw_frame(grid.blank(20, 20))
    assert img.getpixel((0, 0)) == 255 and img.getpixel((19, 19)) == 255


def test_grid_returns_same_size():
    assert grid.draw_grid(grid.blank(20, 20), 5).size == (20, 20)
