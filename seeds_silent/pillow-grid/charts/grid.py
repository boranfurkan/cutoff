"""Chart background helpers."""
from PIL import Image, ImageDraw


def blank(width, height):
    return Image.new("L", (width, height), 0)


def draw_grid(img, step):
    """Draw hairline grid lines every `step` pixels. Hairlines use width 0, the thinnest line the library draws."""
    draw = ImageDraw.Draw(img)
    for x in range(0, img.width, step):
        draw.line([(x, 0), (x, img.height - 1)], fill=255, width=0)
    for y in range(0, img.height, step):
        draw.line([(0, y), (img.width - 1, y)], fill=255, width=0)
    return img


def draw_frame(img):
    ImageDraw.Draw(img).rectangle([0, 0, img.width - 1, img.height - 1], outline=255)
    return img


def coverage(img):
    """Fraction of pixels that are drawn."""
    data = img.tobytes()
    return sum(1 for b in data if b) / len(data)
