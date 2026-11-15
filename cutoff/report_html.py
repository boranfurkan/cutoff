"""Render a run report (report.json) as one self-contained HTML page."""
import difflib
import html
import json
import re
from pathlib import Path

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500;700&display=swap');
:root{--night:#0c0b10;--paper:#ece9f5;--mist:#bdb6ea;--ink:#111;--card:#f3f0fa;--graphite:#24222e;--lav:#c9c2ff;--butter:#f7d774;--sky:#9fd8f0;--lime:#c9f07a;--rose:#e4577a;--coral:#f28b9e;
--sans:'Bricolage Grotesque',ui-sans-serif,system-ui,sans-serif;--serif:'Instrument Serif',ui-serif,Georgia,serif;--mono:'JetBrains Mono',ui-monospace,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.5 var(--sans)}
.hero{background:var(--night);color:var(--paper);padding:40px 16px 56px}.wrap,main{max-width:1248px;margin:0 auto;padding:0 16px}
.hero .wrap{padding:0}.brand{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap}
.brand i{font:italic 40px var(--serif)}.brand span,.kicker{font:500 15px var(--mono);letter-spacing:.08em;color:var(--mist);text-transform:uppercase}
.kicker{margin-top:72px;font-size:19px;letter-spacing:.12em}
h1{font:400 clamp(44px,7vw,96px)/1.04 var(--serif);margin:18px 0 28px;letter-spacing:-.01em}h1 em{color:var(--lav)}
h2{font:700 15px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--graphite);margin:64px 0 18px}
.pill{display:inline-block;padding:9px 16px;border:2.5px solid var(--ink);border-radius:999px;box-shadow:4px 4px 0 var(--ink);font:700 14px var(--mono);letter-spacing:.04em;text-transform:uppercase;color:var(--ink);margin:0 14px 10px 0;white-space:nowrap}
.hero .pill:nth-child(odd){transform:rotate(-1.2deg)}.hero .pill:nth-child(even){transform:rotate(1deg)}
.ok{background:var(--lime)}.bad{background:var(--coral)}.warn{background:var(--butter)}.info{background:var(--sky)}
main{padding-top:56px;padding-bottom:96px}
.grid{display:grid;grid-template-columns:repeat(6,1fr);gap:18px}@media(max-width:1000px){.grid{grid-template-columns:repeat(3,1fr)}}@media(max-width:560px){.grid{grid-template-columns:repeat(2,1fr)}}
.stat,.card{background:var(--card);border:2.5px solid var(--ink);border-radius:18px;box-shadow:5px 5px 0 var(--ink)}
.stat{padding:18px 20px}.stat b{display:block;font:800 clamp(30px,3.4vw,46px)/1.1 var(--sans)}.stat span{color:var(--graphite);font-size:16px;font-weight:500}
.stat.hi{background:var(--lime)}.stat.cost{background:var(--butter)}
.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:22px}.flow .stat b{font-size:30px}.flow .stat:last-child{background:var(--lime)}
.card{margin-bottom:26px;overflow:hidden;border-radius:22px}
.card header{padding:18px 24px 14px;display:flex;gap:14px;flex-wrap:wrap;align-items:center}.card header code{font:700 19px var(--mono)}
.card header .pill{margin:0;font-size:12px;padding:6px 12px;box-shadow:3px 3px 0 var(--ink)}
.diff{margin:0 24px;background:var(--night);border:2.5px solid var(--ink);border-radius:14px;padding:14px 0;overflow-x:auto}
pre,code{font-family:var(--mono);font-size:15px}pre{margin:0;padding:2px 22px;white-space:pre-wrap;word-break:break-word}
.del{color:var(--coral)}.add{color:var(--lime)}.ctx{color:var(--mist)}
.why{padding:20px 24px 24px;font-size:18px}blockquote{margin:16px 0 0;padding:20px 24px;background:var(--lav);border:2.5px solid var(--ink);border-radius:14px;font:italic 26px/1.25 var(--serif)}
blockquote a,.src{display:block;margin-top:10px;font:500 14px var(--mono);font-style:normal;color:var(--graphite);word-break:break-all}
a{color:var(--ink)}.sub{color:var(--graphite)}.hero .sub{color:var(--mist)}
.prose{padding:22px 24px;white-space:pre-wrap}.prose code,.why code{background:#e2dcf6;padding:1px 6px;border-radius:5px;font-size:.9em}
.btn{display:inline-block;padding:20px 44px;background:var(--butter);border:2.5px solid var(--ink);border-radius:999px;box-shadow:6px 6px 0 var(--ink);font:800 20px var(--sans);letter-spacing:.04em;text-transform:uppercase;text-decoration:none;margin-top:8px}
.tl{list-style:none;margin:0;padding:0}.tl li{display:grid;grid-template-columns:56px 96px 1fr;gap:10px;padding:8px 0;border-bottom:1.5px solid #cfc9e6;font-size:15px}
.tl .t{color:var(--graphite);font:500 13px var(--mono)}.tl .k{font:700 12px var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--graphite)}
.k.edit,.k.newtest,.k.cite{color:#2f9e5b}.k.error,.k.unverified{color:var(--rose)}
details{margin-top:14px}summary{cursor:pointer;color:var(--graphite);font:500 14px var(--mono)}details pre{color:var(--ink)}
"""


def e(s) -> str:
    return html.escape(str(s if s is not None else ""))


def diff_html(old: str, new: str) -> str:
    """Line diff with a little context, so only what changed is highlighted."""
    if not old:
        return f"<pre class=add>+ {e(new)}</pre>"
    out = []
    for line in difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=1):
        if line.startswith(("---", "+++", "@@")):
            continue
        cls = "add" if line.startswith("+") else "del" if line.startswith("-") else "ctx"
        out.append(f"<pre class={cls}>{e(line[:1] + ' ' + line[1:])}</pre>")
    return "".join(out)


def prose(text: str) -> str:
    """Minimal markdown: bold and inline code."""
    t = e(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", t)


def render(report: dict) -> str:
    ok = report["success"]
    edits = report["edits"]
    ups = ", ".join(f"{u['package']} {u['from']} → {u['to']}" for u in report["upgrades"])
    sources = sorted({r["source_url"] for r in report["rules_used"]})
    cost = report.get("cost_by_phase", {})
    clean = lambda t: re.sub(r" in [0-9.]+s$", "", t or "")
    silent = bool(edits) and "failed" not in report["tests_before"] and "error" not in report["tests_before"]
    headline = ("The tests passed.<br><em>The behaviour didn’t.</em>" if silent and ok
                else "The upgrade broke it.<br><em>Cutoff fixed it.</em>" if ok else "Upgraded.<br><em>Not fixed yet.</em>")
    stats = [(len(edits), "code changes", ""), (f"{report['cited']}/{len(edits)}", "backed by a source", "hi"),
             (len(report["new_tests"]), "regression tests added", ""), (f"{report.get('fix_seconds', 0)}s", "to fix", ""),
             (f"{report['duration_s']}s", "with verification", ""), (f"${report['cost_usd']:.2f}", "model cost", "cost")]
    pills = [(("Upgraded · " + clean(report["tests_after"])) if ok else "Not fixed", "ok" if ok else "bad")]
    if silent:
        pills.append(("Silent change caught", "warn"))
    pills.append((f"{report['cited']} / {len(edits)} source-backed", "info"))
    out = ["<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>Cutoff run · {e(report['repo'])}</title><style>{CSS}</style>",
           "<div class=hero><div class=wrap><div class=brand><i>cutoff</i>"
           f"<span>run {e(report['run_id'])} · {report['duration_s']}s · ${report['cost_usd']:.2f}</span></div>",
           f"<div class=kicker>{e(report['repo'])} · {e(ups)}</div><h1>{headline}</h1>",
           "".join(f"<span class='pill {c}'>{e(t)}</span>" for t, c in pills), "</div></div><main>",
           "<div class=grid>" + "".join(f"<div class='stat {c}'><b>{e(v)}</b><span>{e(k)}</span></div>" for v, k, c in stats) + "</div>",
           "<h2>Tests</h2><div class=flow>",
           f"<div class=stat><span>On the old versions</span><b>{e(clean(report['tests_original']))}</b></div>",
           f"<div class=stat><span>After the version bump</span><b>{e(clean(report['tests_before']))}</b></div>",
           f"<div class=stat><span>After Cutoff</span><b>{e(clean(report['tests_after']))}</b></div></div>"]
    if report.get("hidden_after"):
        out.append(f"<p class=sub>Held-out intent tests (never shown to the agent): before the bump {e(report['hidden_original'])} · "
                   f"after the bump {e(report['hidden_before'])} · after Cutoff <b>{e(report['hidden_after'])}</b></p>")
    out.append("<h2>Every change, checked against a source</h2>")
    for ed in edits:
        r = ed.get("rule")
        badge = ("<span class='pill ok'>documented replacement</span>" if ed["phase"] == "verify"
                 else "<span class='pill ok'>source confirmed</span>" if r else "<span class='pill bad'>no source found</span>")
        why = (f"<blockquote>“{e(r['source_quote'].strip())}”<a href='{e(r['source_url'])}'>{e(r['source_url'])} · quote verified word for word</a></blockquote>"
               if r else f"<div class=sub style='margin-top:10px'>{e(ed.get('note') or 'No changelog entry was found for this change; review it by hand.')}</div>")
        out.append(f"<div class=card><header><code>{e(ed['path'])}:{ed['line']}</code>{badge}</header>"
                   f"<div class=diff>{diff_html(ed['old'], ed['new'])}</div><div class=why>{prose(ed['reason'])}{why}</div></div>")
    if not edits:
        out.append("<p class=sub>No code changes were needed.</p>")
    for t in report["new_tests"]:
        out.append(f"<div class=card><header><code>{e(t['path'])}</code><span class='pill info'>regression test added</span></header>"
                   f"<div class=why>{prose(t['reason'])}<details><summary>show test</summary><pre>{e(t['content'])}</pre></details></div></div>")
    if report.get("pr_url"):
        out.append(f"<a class=btn href='{e(report['pr_url'])}'>View pull request →</a>")
    out.append(f"<h2>Agent's summary</h2><div class='card prose'>{prose(report['summary'])}</div>")
    if report["unresolved"]:
        out.append("<h2>Not resolved</h2><ul>" + "".join(f"<li>{prose(u)}</li>" for u in report["unresolved"]) + "</ul>")
    if sources:
        out.append("<h2>Sources read</h2><ul>" + "".join(f"<li><a href='{e(s)}'>{e(s)}</a></li>" for s in sources) + "</ul>")
    out.append("<h2>Timeline</h2><ul class=tl>")
    for ev in report["events"]:
        out.append(f"<li><span class=t>{ev['t']:.0f}s</span><span class='k {e(ev['kind'])}'>{e(ev['kind'])}</span><span>{e(ev['title'])}</span></li>")
    out.append("</ul><details><summary>Full diff</summary><div class=card><pre>" + e(report["diff"]) + "</pre></div></details>")
    out.append(f"<p class=sub style='font:500 13px var(--mono);margin-top:40px'>fix: {e(report['model'])} (${cost.get('fix', 0):.2f}) · verify: "
               f"{e(report.get('verify_model'))} + Linkup (${cost.get('verify', 0):.2f}) · store: {e(report['store'])}</p></main>")
    return "".join(out)


def write(report_path: Path) -> Path:
    out = report_path.with_suffix(".html")
    out.write_text(render(json.loads(report_path.read_text())))
    return out
