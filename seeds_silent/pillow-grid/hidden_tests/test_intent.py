from charts import grid


def test_grid_lines_are_visible():
    img = grid.draw_grid(grid.blank(20, 20), 5)
    assert img.getpixel((5, 12)) == 255 and img.getpixel((12, 10)) == 255
    assert img.getpixel((12, 12)) == 0
