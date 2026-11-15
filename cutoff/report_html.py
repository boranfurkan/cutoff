"""Render a run report (report.json) as one self-contained HTML page."""
import difflib
import html
import json
import re
from pathlib import Path

CSS = """
:root{--bg:#f6f5f1;--card:#fff;--ink:#1c1b19;--mute:#6b6862;--line:#e2dfd7;--ok:#1a7f4b;--okbg:#e3f4ea;--bad:#b3261e;--badbg:#fbe7e5;--acc:#3b4cca;--add:#e6f6ea;--del:#fdecea;--code:#f1efe9}
@media(prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1d1b;--ink:#ecebe6;--mute:#9a968d;--line:#33312d;--ok:#5fd08f;--okbg:#17301f;--bad:#ff8a80;--badbg:#3a1917;--acc:#9aa5ff;--add:#15301d;--del:#3a1b19;--code:#262522}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
main{max-width:980px;margin:0 auto;padding:32px 16px 80px}
h1{font-size:28px;margin:0 0 4px;letter-spacing:-.02em}h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--mute);margin:40px 0 12px}
.sub{color:var(--mute)}.pill{display:inline-block;padding:3px 12px;border-radius:999px;font-weight:600;font-size:13px}
.ok{background:var(--okbg);color:var(--ok)}.bad{background:var(--badbg);color:var(--bad)}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:20px}@media(max-width:560px){.grid{grid-template-columns:repeat(2,1fr)}}
.warn{background:#fdf0d5;color:#8a5a00}@media(prefers-color-scheme:dark){.warn{background:#3a2c0a;color:#ffcf70}}
.ctx{color:var(--mute)}pre.add,pre.del,pre.ctx{padding:2px 16px}header+pre{padding-top:10px}.prose{padding:14px 16px;white-space:pre-wrap}.prose code{background:var(--code);padding:1px 5px;border-radius:4px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}.stat b{display:block;font-size:22px;letter-spacing:-.01em}.stat span{color:var(--mute);font-size:13px}
.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}.flow .stat b{font-size:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:14px;overflow:hidden}
.card header{padding:12px 16px;border-bottom:1px solid var(--line);display:flex;gap:10px;flex-wrap:wrap;align-items:baseline}
.card header code{font-weight:600}.kind{font-size:12px;color:var(--mute);border:1px solid var(--line);border-radius:6px;padding:1px 7px}
pre,code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px}pre{margin:0;padding:10px 16px;overflow-x:auto;white-space:pre-wrap;word-break:break-word}
.del{background:var(--del)}.add{background:var(--add)}
.why{padding:12px 16px;border-top:1px solid var(--line)}blockquote{margin:8px 0 6px;padding:6px 12px;border-left:3px solid var(--acc);background:var(--code);border-radius:0 6px 6px 0}
a{color:var(--acc);word-break:break-all}
.tl{list-style:none;margin:0;padding:0}.tl li{display:grid;grid-template-columns:56px 84px 1fr;gap:10px;padding:7px 0;border-bottom:1px solid var(--line);font-size:14px}
.tl .t{color:var(--mute);font-variant-numeric:tabular-nums}.tl .k{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute)}
.k.search,.k.read,.k.cite{color:var(--acc)}.k.edit,.k.newtest{color:var(--ok)}.k.unverified{color:var(--bad)}.k.error{color:var(--bad)}
details{margin-top:14px}summary{cursor:pointer;color:var(--mute)}
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
    stats = [(len(edits), "code changes"), (f"{report['cited']}/{len(edits)}", "backed by a source"),
             (len(report["new_tests"]), "regression tests added"), (f"{report.get('fix_seconds', 0)}s", "to fix"),
             (f"{report['duration_s']}s", "total with verification"), (f"${report['cost_usd']:.2f}", "model cost")]
    silent = report["tests_before"] and "failed" not in report["tests_before"] and "error" not in report["tests_before"] and edits
    out = [f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>Cutoff run · {e(report['repo'])}</title><style>{CSS}</style><main>",
           f"<span class='pill {'ok' if ok else 'bad'}'>{'Upgraded, tests pass' if ok else 'Not fixed'}</span> "
           + ("<span class='pill warn'>silent behaviour change caught</span>" if silent else ""),
           f"<h1>{e(report['repo'])}</h1><div class=sub>{e(ups)}</div>",
           "<div class=grid>" + "".join(f"<div class=stat><b>{e(v)}</b><span>{e(k)}</span></div>" for v, k in stats) + "</div>",
           "<h2>Tests</h2><div class=flow>",
           f"<div class=stat><span>On the old versions</span><b>{e(report['tests_original'])}</b></div>",
           f"<div class=stat><span>After the version bump</span><b>{e(report['tests_before'])}</b></div>",
           f"<div class=stat><span>After Cutoff</span><b>{e(report['tests_after'])}</b></div></div>"]
    if report.get("hidden_after"):
        out.append(f"<p class=sub>Held-out intent tests (never shown to the agent): before the bump {e(report['hidden_original'])} · "
                   f"after the bump {e(report['hidden_before'])} · after Cutoff <b>{e(report['hidden_after'])}</b></p>")
    if report.get("pr_url"):
        out.append(f"<p>Pull request: <a href='{e(report['pr_url'])}'>{e(report['pr_url'])}</a></p>")
    out.append("<h2>Every change, checked against a source</h2>")
    for ed in edits:
        r = ed.get("rule")
        badge = ("<span class='pill ok'>documented replacement</span>" if ed["phase"] == "verify"
                 else "<span class='pill ok'>source confirmed</span>" if r else "<span class='pill bad'>no source found</span>")
        why = (f"<blockquote>{e(r['source_quote'])}</blockquote><a href='{e(r['source_url'])}'>{e(r['source_url'])}</a>" if r
               else f"<span class=sub>{e(ed.get('note') or 'No changelog entry was found for this change; review it by hand.')}</span>")
        out.append(f"<div class=card><header><code>{e(ed['path'])}:{ed['line']}</code>{badge}</header>"
                   + diff_html(ed["old"], ed["new"]) +
                   f"<div class=why>{prose(ed['reason'])}{why}</div></div>")
    if not edits:
        out.append("<p class=sub>No code changes were needed.</p>")
    if report["new_tests"]:
        out.append("<h2>Regression tests added</h2>")
        for t in report["new_tests"]:
            out.append(f"<div class=card><header><code>{e(t['path'])}</code></header><div class=why>{e(t['reason'])}</div>"
                       f"<details style='margin:0 16px 12px'><summary>show test</summary><pre>{e(t['content'])}</pre></details></div>")
    out.append(f"<h2>Agent's summary</h2><div class='card prose'>{prose(report['summary'])}</div>")
    if report["unresolved"]:
        out.append("<h2>Not resolved</h2><ul>" + "".join(f"<li>{e(u)}</li>" for u in report["unresolved"]) + "</ul>")
    if sources:
        out.append("<h2>Sources read</h2><ul>" + "".join(f"<li><a href='{e(s)}'>{e(s)}</a></li>" for s in sources) + "</ul>")
    out.append("<h2>Timeline</h2><ul class=tl>")
    for ev in report["events"]:
        out.append(f"<li><span class=t>{ev['t']:.0f}s</span><span class='k {e(ev['kind'])}'>{e(ev['kind'])}</span><span>{e(ev['title'])}</span></li>")
    out.append("</ul><details><summary>Full diff</summary><div class=card><pre>" + e(report["diff"]) + "</pre></div></details>")
    out.append(f"<p class=sub>Run {e(report['run_id'])} · fix {e(report['model'])} (${cost.get('fix', 0):.2f}) · verify "
               f"{e(report.get('verify_model'))} (${cost.get('verify', 0):.2f}) · store {e(report['store'])}</p></main>")
    return "".join(out)


def write(report_path: Path) -> Path:
    out = report_path.with_suffix(".html")
    out.write_text(render(json.loads(report_path.read_text())))
    return out
