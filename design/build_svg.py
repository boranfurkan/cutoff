"""Generate the Cutoff design board as one SVG (paste into Figma: every group becomes a named, editable layer).

Frames: Cover, Foundations, Report / Silent change (desktop), Report / Unverified change (desktop), Report / Mobile,
Pull request comment. Tokens come from the portfolio's design language.
"""
from html import escape as e
from pathlib import Path

NIGHT, PAPER, MIST, INK, CARD, GRAPHITE = "#0c0b10", "#ece9f5", "#bdb6ea", "#111111", "#f3f0fa", "#24222e"
LAV, BUTTER, SKY, LIME, ROSE, CORAL = "#c9c2ff", "#f7d774", "#9fd8f0", "#c9f07a", "#e4577a", "#f28b9e"
SANS, SERIF, MONO = "Bricolage Grotesque", "Instrument Serif", "JetBrains Mono"
o = []


def g(name):
    o.append(f'<g id="{e(name)}">')


def end():
    o.append("</g>")


def rect(x, y, w, h, fill, r=0, stroke=None, sw=2.5):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}"{s}/>')


def text(x, y, t, size, fill=INK, font=SANS, weight=400, anchor="start", italic=False, ls=0):
    st = ' font-style="italic"' if italic else ""
    sp = f' letter-spacing="{ls}"' if ls else ""
    o.append(f'<text xml:space="preserve" x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{st}{sp}>{e(t)}</text>')


def card(x, y, w, h, fill=CARD, r=18, shadow=5, name="Card"):
    g(name)
    rect(x + shadow, y + shadow, w, h, INK, r)
    rect(x, y, w, h, fill, r, INK)


def sticker(x, y, label, fill, size=15, pad=16, rot=0):
    w = len(label) * size * 0.62 + pad * 2
    h = size + 20
    o.append(f'<g id="Sticker / {e(label)}" transform="rotate({rot} {x + w / 2:.1f} {y + h / 2:.1f})">')
    rect(x + 4, y + 4, w, h, INK, h / 2)
    rect(x, y, w, h, fill, h / 2, INK)
    text(x + w / 2, y + h / 2 + size * 0.36, label, size, INK, MONO, 700, "middle", ls=0.5)
    end()
    return w


def frame_label(x, y, name):
    text(x, y - 24, name, 28, "#8a86a0", SANS, 600)


def wrap(t, n):
    words, lines, cur = t.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + [cur]


SILENT = dict(
    kicker="ORDERS-API · FASTAPI 0.146.0 → 0.163.0", h1="The tests passed.", h2="The behaviour didn’t.",
    pills=[("UPGRADED · 7 TESTS PASS", LIME, -1.5), ("SILENT CHANGE CAUGHT", BUTTER, 1), ("2 / 2 SOURCE-BACKED", SKY, -1)],
    stats=[("2", "code changes", CARD), ("2/2", "backed by a source", LIME), ("1", "regression test", CARD),
           ("36s", "to fix", CARD), ("46s", "with verification", CARD), ("$0.10", "model cost", BUTTER)],
    flow=[("On the old versions", "4 passed", CARD), ("After the version bump", "4 passed", CARD), ("After Cutoff", "7 passed", LIME)],
    aside="looks safe. It isn’t.", file="api/main.py:9", badge=("SOURCE CONFIRMED", LIME),
    diff=[("-", "def create_order(sku: str = Body(...), qty: int = Body(1)):", CORAL),
          ("+", "def create_order(sku: str = Body(...), qty: Optional[int] = Body(1)):", LIME),
          (" ", '    """Create an order. A null quantity means one unit."""', MIST),
          ("+", "    # newer FastAPI validates an explicit JSON null against the type", LIME),
          ("+", "    if qty is None:", LIME), ("+", "        qty = 1", LIME),
          (" ", '    order = {"id": len(ORDERS) + 1, "sku": sku, "qty": qty}', MIST)],
    why="An explicit JSON null for a field with a default is no longer replaced by the default.",
    why2="It is validated against the type and rejected with a 422. Found by testing the docstring’s intent in the sandbox.",
    quote="“Clients that used null to request a default should omit the value instead.”",
    src="fastapi.tiangolo.com/release-notes  ·  quote verified word for word", quote_fill=LAV,
    test="tests/test_upgrade_null_quantity.py",
    test_why="Pins the documented behaviour: tablets send null for “not filled in”, and that must mean one unit.")

UNVERIFIED = dict(SILENT,
    kicker="CHART-GRID · PILLOW 12.2.0 → 13.0.0", h1="Fixed and tested.", h2="One change has no source.",
    pills=[("UPGRADED · 5 TESTS PASS", LIME, -1.5), ("SILENT CHANGE CAUGHT", BUTTER, 1), ("0 / 1 SOURCE-BACKED", CORAL, -1)],
    stats=[("1", "code change", CARD), ("0/1", "backed by a source", CORAL), ("1", "regression test", CARD),
           ("23s", "to fix", CARD), ("48s", "with verification", CARD), ("$0.18", "model cost", BUTTER)],
    flow=[("On the old versions", "3 passed", CARD), ("After the version bump", "3 passed", CARD), ("After Cutoff", "5 passed", LIME)],
    file="charts/grid.py:12", badge=("NO SOURCE FOUND", CORAL),
    diff=[(" ", "    for x in range(0, img.width, step):", MIST),
          ("-", "        draw.line([(x, 0), (x, img.height - 1)], fill=255, width=0)", CORAL),
          ("+", "        draw.line([(x, 0), (x, img.height - 1)], fill=255, width=1)", LIME),
          (" ", "    for y in range(0, img.height, step):", MIST),
          ("-", "        draw.line([(0, y), (img.width - 1, y)], fill=255, width=0)", CORAL),
          ("+", "        draw.line([(0, y), (img.width - 1, y)], fill=255, width=1)", LIME),
          (" ", "    return img", MIST)],
    why="Lines with width 0 are no longer drawn, so the hairline grid disappeared.",
    why2="Observed in the sandbox. Cutoff searched the release notes and found no entry it could quote.",
    quote="Review this one by hand.", src="no changelog line supports this change  ·  flagged, not hidden", quote_fill=BUTTER,
    test="tests/test_upgrade_grid_visible.py", test_why="Pins the documented behaviour: grid lines must be visible on the chart.")


def report(x0, y0, name, d, W=1440):
    m = W < 600
    P = 24 if m else 96
    inner = W - 2 * P
    g(name)
    frame_label(x0, y0, name)
    # hero
    g("Hero")
    hh = 470 if m else 520
    rect(x0, y0, W, hh, NIGHT)
    text(x0 + P, y0 + (56 if m else 84), "cutoff", 30 if m else 40, PAPER, SERIF, italic=True)
    if not m:
        text(x0 + W - P, y0 + 78, "RUN 1114-223529 · 46s · $0.10", 15, MIST, MONO, 500, "end", ls=1)
    text(x0 + P, y0 + (116 if m else 190), d["kicker"] if not m else d["kicker"].split(" · ")[1], 13 if m else 20, MIST, MONO, 500, ls=1 if m else 2)
    hs = 44 if m else 96
    text(x0 + P, y0 + (176 if m else 290), d["h1"], hs, PAPER, SERIF)
    text(x0 + P, y0 + (226 if m else 392), d["h2"], hs, LAV, SERIF, italic=True)
    px, py = x0 + P, y0 + (270 if m else 440)
    for label, fill, rot in d["pills"]:
        w = sticker(px, py, label, fill, 12 if m else 15, 12 if m else 16, rot)
        if m:
            py += 46
        else:
            px += w + 22
    end()
    # body
    g("Body")
    y = y0 + hh
    body_y = y
    rect(x0, y, W, 10, PAPER)  # resized at the end via a second rect
    body_idx = len(o) - 1
    y += 40 if m else 64
    g("Stats")
    cols = 2 if m else 6
    gap = 14 if m else 19.2
    cw = (inner - gap * (cols - 1)) / cols
    chh = 104 if m else 128
    for i, (v, k, fill) in enumerate(d["stats"]):
        cx = x0 + P + (i % cols) * (cw + gap)
        cy = y + (i // cols) * (chh + gap)
        card(cx, cy, cw, chh, fill, 16 if m else 18, 4 if m else 5, f"Stat / {k}")
        text(cx + (16 if m else 22), cy + (52 if m else 66), v, 34 if m else 46, INK, SANS, 800)
        text(cx + (16 if m else 22), cy + (80 if m else 100), k, 13 if m else 16, GRAPHITE, SANS, 500)
        end()
    end()
    y += ((len(d["stats"]) + cols - 1) // cols) * (chh + gap) - gap + (48 if m else 72)
    g("Tests")
    text(x0 + P, y, "TESTS", 13 if m else 15, GRAPHITE, MONO, 700, ls=2)
    y += 24
    if m:
        for k, v, fill in d["flow"]:
            card(x0 + P, y, inner, 84, fill, 16, 4, f"Test / {k}")
            text(x0 + P + 18, y + 34, k, 14, GRAPHITE, SANS, 500)
            text(x0 + P + 18, y + 66, v, 24, INK, SANS, 800)
            end()
            y += 84 + 14
        y += 34
    else:
        fw = (inner - 120) / 3
        for i, (k, v, fill) in enumerate(d["flow"]):
            fx = x0 + P + i * (fw + 60)
            card(fx, y, fw, 112, fill, name=f"Test / {k}")
            text(fx + 24, y + 42, k, 17, GRAPHITE, SANS, 500)
            text(fx + 24, y + 86, v, 34, INK, SANS, 800)
            if i == 1:
                text(fx + 190, y + 86, d["aside"], 20, ROSE, SERIF, italic=True)
            end()
            if i < 2:
                text(fx + fw + 32, y + 70, "→", 34, INK, SANS, 700, "middle")
        y += 112 + 72
    end()
    g("Change")
    text(x0 + P, y, "EVERY CHANGE, CHECKED AGAINST A SOURCE", 13 if m else 15, GRAPHITE, MONO, 700, ls=1 if m else 2)
    y += 24
    ip = 18 if m else 32
    lh = 22 if m else 30
    fs = 10.5 if m else 17
    code = d["diff"] if not m else [(s, c[:46] + ("…" if len(c) > 46 else ""), col) for s, c, col in d["diff"]]
    dh = len(code) * lh + 42
    why1 = wrap(d["why"], 40 if m else 200)
    why2 = wrap(d["why2"], 48 if m else 200)
    qlines = wrap(d["quote"], 30 if m else 200)
    qh = len(qlines) * (30 if m else 36) + (62 if m else 76)
    CH = 80 + dh + 36 + len(why1) * (24 if m else 30) + len(why2) * (22 if m else 28) + 22 + qh + ip
    card(x0 + P, y, inner, CH, CARD, 22, 5 if m else 6, "Change card")
    text(x0 + P + ip, y + 48, d["file"], 15 if m else 20, INK, MONO, 700)
    if m:
        sticker(x0 + P + ip, y + 62, d["badge"][0], d["badge"][1], 10, 10)
    else:
        sticker(x0 + P + ip + 190, y + 22, d["badge"][0], d["badge"][1], 13, 14)
    dy = y + (104 if m else 80)
    if m:
        CH += 24
    g("Diff")
    rect(x0 + P + ip, dy, inner - 2 * ip, dh, NIGHT, 14, INK)
    for i, (sign, c, col) in enumerate(code):
        ly = dy + 36 + i * lh
        text(x0 + P + ip + (12 if m else 24), ly, sign, fs, col, MONO, 700)
        text(x0 + P + ip + (26 if m else 52), ly, c, fs, col, MONO, 500)
    end()
    ry = dy + dh + 40
    for ln in why1:
        text(x0 + P + ip, ry, ln, 16 if m else 21, INK, SANS, 600)
        ry += 24 if m else 30
    for ln in why2:
        text(x0 + P + ip, ry, ln, 14 if m else 18, GRAPHITE, SANS, 400)
        ry += 22 if m else 28
    qy = ry + 6
    g("Citation")
    rect(x0 + P + ip, qy, inner - 2 * ip, qh, d["quote_fill"], 14, INK)
    ty = qy + (38 if m else 48)
    for ln in qlines:
        text(x0 + P + ip + (16 if m else 28), ty, ln, 22 if m else 28, INK, SERIF, italic=True)
        ty += 30 if m else 36
    text(x0 + P + ip + (16 if m else 28), ty + 2, d["src"] if not m else d["src"].split("  ·  ")[0], 11 if m else 15, GRAPHITE, MONO, 500)
    end()
    end()  # change card
    if m:
        # redraw is not possible, so the card height was computed with the mobile extra above
        pass
    end()  # Change
    y += CH + (40 if m else 56)
    th = 150 if m else 128
    card(x0 + P, y, inner, th, CARD, 22, 5 if m else 6, "Regression test card")
    text(x0 + P + ip, y + 46, d["test"] if not m else d["test"].replace("tests/", ""), 13 if m else 20, INK, MONO, 700)
    if m:
        sticker(x0 + P + ip, y + 60, "REGRESSION TEST ADDED", SKY, 10, 10)
        for i, ln in enumerate(wrap(d["test_why"], 46)[:2]):
            text(x0 + P + ip, y + 118 + i * 20, ln, 13, GRAPHITE, SANS, 400)
    else:
        sticker(x0 + P + ip + 470, y + 22, "REGRESSION TEST ADDED", SKY, 13, 14)
        text(x0 + P + ip, y + 92, d["test_why"], 18, GRAPHITE, SANS, 400)
    end()
    y += th + (40 if m else 64)
    bw = inner if m else 600
    card(x0 + P, y, bw, 72 if m else 84, BUTTER, 42, 5 if m else 6, "Button / View pull request")
    text(x0 + P + bw / 2, y + (45 if m else 53), "VIEW PULL REQUEST  →", 17 if m else 22, INK, SANS, 800, "middle", ls=1)
    end()
    if not m:
        text(x0 + W - P, y + 50, "fix: Claude Opus 5.5  ·  verify: Claude Sonnet 5.5 + Linkup  ·  store: Databricks", 14, GRAPHITE, MONO, 500, "end")
    y += (72 if m else 84) + (56 if m else 96)
    o[body_idx] = f'<rect x="{x0}" y="{body_y}" width="{W}" height="{y - body_y}" fill="{PAPER}"/>'
    end()
    end()
    return y - y0


def cover(x0, y0, W=1440, H=900):
    g("Cover")
    frame_label(x0, y0, "Cover")
    rect(x0, y0, W, H, NIGHT)
    text(x0 + 96, y0 + 120, "cutoff", 56, PAPER, SERIF, italic=True)
    text(x0 + 96, y0 + 360, "Dependency upgrades", 124, PAPER, SERIF)
    text(x0 + 96, y0 + 490, "you can merge.", 124, LAV, SERIF, italic=True)
    for i, ln in enumerate(["Cutoff bumps your pins, fixes what breaks, finds what silently changed,",
                            "and backs every change with a source a reviewer can check."]):
        text(x0 + 96, y0 + 590 + i * 40, ln, 28, MIST, SANS, 400)
    px = x0 + 96
    for label, fill, rot in [("19 / 19 REPOS UPGRADED", LIME, -1.5), ("8 / 8 SILENT CHANGES CAUGHT", BUTTER, 1), ("53 / 58 CHANGES CITED", SKY, -1)]:
        px += sticker(px, y0 + 720, label, fill, 17, 20, rot) + 26
    text(x0 + W - 96, y0 + H - 60, "IMPERIAL AI HACK · 15 NOV 2026 · FURKAN BORAN", 15, MIST, MONO, 500, "end", ls=2)
    end()


def foundations(x0, y0, W=1440, H=1500):
    g("Foundations")
    frame_label(x0, y0, "Foundations")
    rect(x0, y0, W, H, PAPER)
    text(x0 + 96, y0 + 130, "Foundations", 84, INK, SERIF)
    text(x0 + 96, y0 + 178, "One loud idea per screen. Ink borders, hard shadows, and colour only where it carries meaning.", 22, GRAPHITE, SANS)
    y = y0 + 270
    text(x0 + 96, y, "COLOUR", 15, GRAPHITE, MONO, 700, ls=2)
    sw = [("Night", NIGHT, "hero, code"), ("Paper", PAPER, "page"), ("Card", CARD, "surfaces"), ("Ink", INK, "text, borders"),
          ("Lime", LIME, "passed, confirmed"), ("Butter", BUTTER, "caught, cost, action"), ("Sky", SKY, "evidence, tests"),
          ("Coral", CORAL, "removed, unverified"), ("Lavender", LAV, "citation, accent"), ("Mist", MIST, "quiet text on night")]
    for i, (n, c, use) in enumerate(sw):
        cx = x0 + 96 + (i % 5) * 252
        cy = y + 28 + (i // 5) * 200
        card(cx, cy, 228, 104, c, 16, 5, f"Colour / {n}")
        end()
        text(cx, cy + 138, n, 20, INK, SANS, 700)
        text(cx + 228, cy + 138, c.upper(), 14, GRAPHITE, MONO, 500, "end")
        text(cx, cy + 162, use, 15, GRAPHITE, SANS)
    y += 28 + 400 + 56
    text(x0 + 96, y, "TYPE", 15, GRAPHITE, MONO, 700, ls=2)
    text(x0 + 96, y + 96, "The tests passed.", 84, INK, SERIF)
    text(x0 + 760, y + 60, "Instrument Serif", 20, INK, SANS, 700)
    text(x0 + 760, y + 88, "Headlines and quotes. Italic for the turn of the sentence.", 17, GRAPHITE, SANS)
    text(x0 + 96, y + 190, "7 passed", 56, INK, SANS, 800)
    text(x0 + 760, y + 160, "Bricolage Grotesque", 20, INK, SANS, 700)
    text(x0 + 760, y + 188, "Numbers at 800, body at 400–600.", 17, GRAPHITE, SANS)
    text(x0 + 96, y + 262, "api/main.py:9  ·  SOURCE CONFIRMED", 24, INK, MONO, 700)
    text(x0 + 760, y + 240, "JetBrains Mono", 20, INK, SANS, 700)
    text(x0 + 760, y + 268, "Code, paths, labels and stickers. Uppercase, tracked out.", 17, GRAPHITE, SANS)
    y += 340
    text(x0 + 96, y, "COMPONENTS", 15, GRAPHITE, MONO, 700, ls=2)
    px = x0 + 96
    for label, fill in [("SOURCE CONFIRMED", LIME), ("SILENT CHANGE CAUGHT", BUTTER), ("REGRESSION TEST ADDED", SKY), ("NO SOURCE FOUND", CORAL)]:
        px += sticker(px, y + 30, label, fill, 14, 16) + 24
    text(x0 + 96, y + 108, "Sticker: one per fact. Lime means verified, coral means look closer.", 16, GRAPHITE, SANS)
    card(x0 + 96, y + 150, 228, 128, CARD, 18, 5, "Stat card")
    text(x0 + 118, y + 216, "2/2", 46, INK, SANS, 800)
    text(x0 + 118, y + 250, "backed by a source", 16, GRAPHITE, SANS, 500)
    end()
    card(x0 + 372, y + 150, 420, 84, BUTTER, 42, 6, "Button")
    text(x0 + 582, y + 203, "VIEW PULL REQUEST  →", 20, INK, SANS, 800, "middle", ls=1)
    end()
    g("Citation block")
    rect(x0 + 840, y + 150, 504, 128, LAV, 14, INK)
    text(x0 + 866, y + 200, "“Quote from the changelog.”", 30, INK, SERIF, italic=True)
    text(x0 + 866, y + 240, "source.url  ·  verified word for word", 14, GRAPHITE, MONO, 500)
    end()
    text(x0 + 96, y + 320, "Card: 2.5px ink border, 5px hard shadow, 18px radius.     Button: pill, butter, 6px shadow.     Citation: lavender, serif italic.", 16, GRAPHITE, SANS)
    end()


def pr_comment(x0, y0, W=1040):
    g("Pull request comment")
    frame_label(x0, y0, "Pull request comment")
    H = 900
    rect(x0, y0, W, H, "#ffffff")
    rect(x0 + 40, y0 + 40, W - 80, H - 80, "#ffffff", 10, "#d0d7de", 1.5)
    rect(x0 + 40, y0 + 40, W - 80, 56, "#f6f8fa", 10, "#d0d7de", 1.5)
    text(x0 + 64, y0 + 76, "cutoff opened this pull request", 17, "#1f2328", SANS, 600)
    text(x0 + 64, y0 + 150, "Upgrade fastapi to 0.163.0 and migrate code", 30, "#1f2328", SANS, 700)
    y = y0 + 196
    for i, (k, v) in enumerate([("Before the upgrade", "4 passed"), ("After the bump, before any change", "4 passed"), ("After this PR", "7 passed")]):
        rect(x0 + 64, y + i * 44, W - 128, 44, "#ffffff" if i % 2 else "#f6f8fa", 0, "#d0d7de", 1)
        text(x0 + 84, y + i * 44 + 28, k, 16, "#1f2328", SANS, 400)
        text(x0 + 520, y + i * 44 + 28, v, 16, "#1f2328", SANS, 700 if i == 2 else 400)
    y += 132 + 44
    text(x0 + 64, y, "2 of 2 changes are backed by a cited source.", 18, "#1f2328", SANS, 700)
    y += 48
    text(x0 + 64, y, "Changes and their sources", 22, "#1f2328", SANS, 700)
    y += 40
    text(x0 + 64, y, "api/main.py:9", 16, "#1f2328", MONO, 700)
    for i, ln in enumerate(wrap("fastapi: an explicit JSON null for a field with a default is no longer replaced by the default; it is validated against the type and rejected with 422. Accept Optional[int] and map None to the documented default of 1.", 104)):
        text(x0 + 64, y + 30 + i * 24, ln, 16, "#1f2328", SANS)
    y += 30 + 72
    rect(x0 + 64, y, 4, 76, "#d0d7de")
    text(x0 + 84, y + 26, "Clients that used null to request a default should omit the value instead.", 16, "#59636e", SANS)
    text(x0 + 84, y + 60, "Source: https://fastapi.tiangolo.com/release-notes/", 16, "#0969da", SANS)
    y += 116
    text(x0 + 64, y, "Regression tests added", 22, "#1f2328", SANS, 700)
    text(x0 + 64, y + 36, "•  tests/test_upgrade_null_quantity.py: null quantity must mean one unit", 16, "#1f2328", SANS)
    text(x0 + 64, y0 + H - 70, "Opened by Cutoff in 46s. Tests were run in an isolated container; review before merging.", 14, "#59636e", SANS)
    end()


X = 0
cover(X, 0)
foundations(X, 1060)
X += 1440 + 160
report(X, 0, "Report / Silent change caught", SILENT)
X += 1440 + 160
report(X, 0, "Report / Change with no source", UNVERIFIED)
X += 1440 + 160
report(X, 0, "Report / Mobile", SILENT, 390)
pr_comment(X + 390 + 160, 0)
TW, TH = X + 390 + 160 + 1040, 2700
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{TW}" height="{TH}" viewBox="0 -80 {TW} {TH}">' + "".join(o) + "</svg>")
out = Path(__file__).parent / "cutoff-board.svg"
out.write_text(svg)
print(out, len(svg), "bytes", TW, "x", TH)
