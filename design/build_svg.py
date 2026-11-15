"""Generate the run-report screen as an SVG in the portfolio's design language (paste into Figma as editable layers)."""
from html import escape as e
from pathlib import Path

NIGHT, PAPER, MIST, INK, CARD, GRAPHITE = "#0c0b10", "#ece9f5", "#bdb6ea", "#111111", "#f3f0fa", "#24222e"
LAV, BUTTER, SKY, LIME, ROSE, CORAL, GO = "#c9c2ff", "#f7d774", "#9fd8f0", "#c9f07a", "#e4577a", "#f28b9e", "#2f9e5b"
SANS, SERIF, MONO = "Bricolage Grotesque", "Instrument Serif", "JetBrains Mono"
W = 1440
o = []


def rect(x, y, w, h, fill, r=0, stroke=None, sw=2.5):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"{s}/>')


def text(x, y, t, size, fill=INK, font=SANS, weight=400, anchor="start", italic=False, ls=0):
    st = ' font-style="italic"' if italic else ""
    sp = f' letter-spacing="{ls}"' if ls else ""
    o.append(f'<text xml:space="preserve" x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{st}{sp}>{e(t)}</text>')


def card(x, y, w, h, fill=CARD, r=18, shadow=5):
    rect(x + shadow, y + shadow, w, h, INK, r)
    rect(x, y, w, h, fill, r, INK)


def sticker(x, y, label, fill, size=15, pad=16, rot=0):
    w = int(len(label) * size * 0.64) + pad * 2
    h = size + 20
    o.append(f'<g transform="rotate({rot} {x + w / 2} {y + h / 2})">')
    rect(x + 4, y + 4, w, h, INK, h / 2)
    rect(x, y, w, h, fill, h / 2, INK)
    text(x + w / 2, y + h / 2 + size * 0.36, label, size, INK, MONO, 700, "middle", ls=0.5)
    o.append("</g>")
    return w


# ---------- hero band
H_HERO = 520
rect(0, 0, W, H_HERO, NIGHT)
text(96, 84, "cutoff", 40, PAPER, SERIF, 400, italic=True)
text(W - 96, 78, "RUN 1114-223529 · 46s · $0.10", 15, MIST, MONO, 500, "end", ls=1)
text(96, 190, "FASTAPI 0.146.0 → 0.163.0", 20, MIST, MONO, 500, ls=2)
text(96, 290, "The tests passed.", 96, PAPER, SERIF)
text(96, 392, "The behaviour didn’t.", 96, LAV, SERIF, italic=True)
x = 96
for label, fill, rot in [("UPGRADED · 7 TESTS PASS", LIME, -1.5), ("SILENT CHANGE CAUGHT", BUTTER, 1), ("2 / 2 SOURCE-BACKED", SKY, -1)]:
    x += sticker(x, 440, label, fill, rot=rot) + 22

# ---------- body
rect(0, H_HERO, W, 1660, PAPER)
y = H_HERO + 64
stats = [("2", "code changes", CARD), ("2/2", "backed by a source", LIME), ("1", "regression test added", CARD),
         ("36s", "to fix", CARD), ("46s", "with verification", CARD), ("$0.10", "model cost", BUTTER)]
cw, gap = 192, 19.2
for i, (v, k, fill) in enumerate(stats):
    cx = 96 + i * (cw + gap)
    card(cx, y, cw, 128, fill)
    text(cx + 22, y + 66, v, 46, INK, SANS, 800)
    text(cx + 22, y + 100, k, 16, GRAPHITE, SANS, 500)

y += 128 + 72
text(96, y, "TESTS", 15, GRAPHITE, MONO, 700, ls=2)
y += 24
flow = [("On the old versions", "4 passed", CARD), ("After the version bump", "4 passed", CARD), ("After Cutoff", "7 passed", LIME)]
fw = 376
for i, (k, v, fill) in enumerate(flow):
    fx = 96 + i * (fw + 60)
    card(fx, y, fw, 112, fill)
    text(fx + 24, y + 42, k, 17, GRAPHITE, SANS, 500)
    text(fx + 24, y + 86, v, 34, INK, SANS, 800)
    if i < 2:
        text(fx + fw + 32, y + 70, "→", 34, INK, SANS, 700, "middle")
text(96 + fw + 60 + 24 + 150, y + 86, "looks safe. It isn’t.", 20, ROSE, SERIF, italic=True)

y += 112 + 72
text(96, y, "EVERY CHANGE, CHECKED AGAINST A SOURCE", 15, GRAPHITE, MONO, 700, ls=2)
y += 24
CH = 600
card(96, y, W - 192, CH, CARD, 22, 6)
text(128, y + 50, "api/main.py:9", 20, INK, MONO, 700)
sticker(310, y + 24, "SOURCE CONFIRMED", LIME, 13, 14)
# diff panel
dy = y + 80
rect(128, dy, W - 256, 252, NIGHT, 14, INK)
lines = [("-", "def create_order(sku: str = Body(...), qty: int = Body(1)):", CORAL),
         ("+", "def create_order(sku: str = Body(...), qty: Optional[int] = Body(1)):", LIME),
         (" ", '    """Create an order. A null quantity means one unit."""', MIST),
         ("+", "    # newer FastAPI validates an explicit JSON null against the type", LIME),
         ("+", "    if qty is None:", LIME),
         ("+", "        qty = 1", LIME),
         (" ", '    order = {"id": len(ORDERS) + 1, "sku": sku, "qty": qty}', MIST)]
for i, (sign, code, col) in enumerate(lines):
    ly = dy + 42 + i * 30
    text(152, ly, sign, 17, col, MONO, 700)
    text(180, ly, code, 17, col, MONO, 500)
ry = dy + 252 + 44
text(128, ry, "An explicit JSON null for a field with a default is no longer replaced by the default.", 21, INK, SANS, 600)
text(128, ry + 32, "It is validated against the type and rejected with a 422. Found by testing the docstring’s intent in the sandbox.", 18, GRAPHITE, SANS, 400)
qy = ry + 60
rect(128, qy, W - 256, 112, LAV, 14, INK)
text(156, qy + 50, "“Clients that used null to request a default should omit the value instead.”", 28, INK, SERIF, italic=True)
text(156, qy + 86, "fastapi.tiangolo.com/release-notes  ·  quote verified word for word", 15, GRAPHITE, MONO, 500)

y += CH + 56
card(96, y, W - 192, 128, CARD, 22, 6)
text(128, y + 50, "tests/test_upgrade_null_quantity.py", 20, INK, MONO, 700)
sticker(560, y + 24, "REGRESSION TEST ADDED", SKY, 13, 14)
text(128, y + 92, "Pins the documented behaviour: tablets send null for “not filled in”, and that must mean one unit.", 18, GRAPHITE, SANS, 400)

y += 128 + 64
card(96, y, 600, 84, BUTTER, 42, 6)
text(396, y + 53, "VIEW PULL REQUEST  →", 22, INK, SANS, 800, "middle", ls=1)
text(W - 96, y + 50, "fix: Claude Opus 5.5  ·  verify: Claude Sonnet 5.5 + Linkup  ·  store: Databricks", 14, GRAPHITE, MONO, 500, "end")

H = y + 84 + 96
svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">' + "".join(o) + "</svg>"
out = Path(__file__).parent / "run-report.svg"
out.write_text(svg)
print(out, len(svg), "bytes", H, "px tall")
