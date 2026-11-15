"""Build the logo and the Devpost thumbnail/gallery images as PNGs (rendered with headless Chrome so web fonts load)."""
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "assets"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FONTS = ("<link href='https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800"
         "&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500;700&display=swap' rel='stylesheet'>")
NIGHT, PAPER, MIST, INK, CARD, LAV, BUTTER, SKY, LIME, CORAL = ("#0c0b10", "#ece9f5", "#bdb6ea", "#111", "#f3f0fa", "#c9c2ff",
                                                              "#f7d774", "#9fd8f0", "#c9f07a", "#f28b9e")
CSS = f"""*{{box-sizing:border-box;margin:0}}body{{background:{NIGHT};color:{PAPER};font-family:'Bricolage Grotesque',sans-serif;overflow:hidden}}
.serif{{font-family:'Instrument Serif',serif}}.mono{{font-family:'JetBrains Mono',monospace}}
.pill{{display:inline-block;padding:.55em 1em;border:3px solid {INK};border-radius:999px;box-shadow:5px 5px 0 {INK};font:700 1em 'JetBrains Mono',monospace;color:{INK};letter-spacing:.04em;white-space:nowrap}}
.card{{background:{CARD};color:{INK};border:3px solid {INK};border-radius:22px;box-shadow:7px 7px 0 {INK}}}"""

LOGO = f"""<div style="width:512px;height:512px;background:{NIGHT};border-radius:112px;position:relative;overflow:hidden">
<div class=serif style="position:absolute;left:0;right:40px;top:-6px;text-align:center;font-size:470px;font-style:italic;line-height:1;color:{PAPER}">c</div>
<div style="position:absolute;right:74px;bottom:92px;width:132px;height:132px;border-radius:50%;background:{LIME};border:6px solid {INK};box-shadow:7px 7px 0 {INK};display:grid;place-items:center;font:800 78px 'Bricolage Grotesque';color:{INK}">✓</div></div>"""

THUMB = f"""<div style="width:1500px;height:1000px;padding:84px 96px;position:relative">
<div style="display:flex;justify-content:space-between;align-items:baseline"><span class=serif style="font-size:64px;font-style:italic">cutoff</span>
<span class=mono style="font-size:19px;letter-spacing:.14em;color:{MIST}">IMPERIAL AI HACK 2026 · AUTONOMOUS AGENTS</span></div>
<div class=serif style="font-size:148px;line-height:1.0;margin-top:92px">Dependency upgrades<br><i style="color:{LAV}">you can merge.</i></div>
<div style="font-size:31px;line-height:1.4;color:{MIST};margin-top:38px;max-width:1050px">Bumps your pins, fixes what breaks, finds what silently changed, and backs every change with a source.</div>
<div style="margin-top:56px;font-size:22px;display:flex;gap:26px">
<span class=pill style="background:{LIME};transform:rotate(-1.5deg)">19 / 19 REPOS UPGRADED</span>
<span class=pill style="background:{BUTTER};transform:rotate(1deg)">8 / 8 SILENT CHANGES CAUGHT</span>
<span class=pill style="background:{SKY};transform:rotate(-1deg)">53 / 58 CHANGES CITED</span></div>
<div class=mono style="position:absolute;left:96px;bottom:84px;font-size:18px;color:{MIST};letter-spacing:.08em;line-height:1.7">CLAUDE · LINKUP · DATABRICKS · ADAPTION</div></div>"""


def shot(name, body, w, h, transparent=False):
    page = OUT / f"_{name}.html"
    bg = "transparent" if transparent else NIGHT
    page.write_text(f"<!doctype html><meta charset=utf-8>{FONTS}<style>{CSS}body{{background:{bg}}}</style>{body}")
    args = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{h}",
            "--virtual-time-budget=8000", f"--screenshot={OUT / (name + '.png')}"]
    if transparent:
        args.append("--default-background-color=00000000")
    subprocess.run(args + [f"file://{page}"], capture_output=True)
    page.unlink()
    print(OUT / f"{name}.png")


OUT.mkdir(exist_ok=True)
shot("logo", LOGO, 512, 512, transparent=True)
shot("thumbnail", THUMB, 1500, 1000)
