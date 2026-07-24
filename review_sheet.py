#!/usr/bin/env python3
"""
review_sheet.py  --  one-page HTML review per building (offline, bpy-free)
==========================================================================
Assembles everything a human reviewer needs into a single page:
  * the deterministic floor plans (build/floorplans/<name>.floor*.svg, inlined)
  * the validation gate results (build/<name>.validation.json) -- the pass/fail
    authority, incl. the enforced `layout` coherence/reachability gate
  * the advisory AI review (build/<name>.ai_review.json), if present

The plan + gates are deterministic ground truth; the AI cards are clearly
labelled advisory. Pure-Python string building -- no Blender, no deps.

    python review_sheet.py specs/deli_a01.json      # -> build/review/deli_a01.review.html
    python review_sheet.py --all
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CATC = {"tactical_balance": "#b45309", "plausibility": "#2563eb",
        "readability": "#7c3aed", "theme": "#0f766e", "cross_reference": "#be123c"}


def _load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def _json(path):
    txt = _load(path)
    return json.loads(txt) if txt else None


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _gate_section(val):
    if not val:
        return "<p class='muted'>No validation.json found.</p>"
    passed = val.get("passed")
    blk = val.get("blocking_failures") or []
    badge = ("<span class='badge pass'>PASS</span>" if passed
             else f"<span class='badge fail'>FAIL · {', '.join(blk)}</span>")
    rows = []
    for g, d in (val.get("gates") or {}).items():
        errs = d.get("errors") or []
        warns = d.get("warnings") or []
        e, w = len(errs), len(warns)
        st = ("err" if e else ("warn" if w else "ok"))
        tag = (f"{e}E " if e else "") + (f"{w}W" if w else "") or "clean"
        msgs = "".join([f"<div class='gmsg e'>{_esc(m)}</div>" for m in errs]
                       + [f"<div class='gmsg'>{_esc(m)}</div>" for m in warns])
        rows.append(f"<div class='gate {st}'><div class='grow'><b>{g}</b>"
                    f"<span class='gtag'>{tag}</span></div>{msgs}</div>")
    return f"<div class='gatehead'>Validation {badge}</div>" + "".join(rows)


def _ai_section(ai):
    if not ai:
        return "<p class='muted'>No AI review (advisory) generated.</p>"
    cards = []
    for f in ai.get("findings", []):
        col = CATC.get(f.get("category"), "#555")
        room = f"<code>{_esc(f['room'])}</code> · " if f.get("room") else ""
        gnd = (f"<div class='gnd'>grounding: {_esc(f['grounding'])}</div>"
               if f.get("grounding") else "")
        cards.append(
            f"<div class='find'><div class='fh'>"
            f"<span class='sev {f.get('severity')}'>{_esc(f.get('severity'))}</span>"
            f"<span class='chip' style='color:{col};background:{col}1a;border:1px solid {col}55'>"
            f"{_esc(f.get('category','').replace('_',' '))}</span></div>"
            f"<div class='fm'>{room}{_esc(f.get('message'))}</div>{gnd}</div>")
    note = ("<div class='advisory'>Advisory — a model reading the finished "
            "deterministic plan. Never affects pass/fail.</div>")
    return note + "".join(cards) if cards else note + "<p class='muted'>No findings.</p>"


def build_html(name, plans, val, ai):
    plan_blocks = "".join(
        f"<div class='plan'><div class='plabel'>{_esc(os.path.basename(p))}</div>{svg}</div>"
        for p, svg in plans)
    return f"""<!doctype html><html><head><meta charset=utf-8>
<title>Review — {_esc(name)}</title><style>
body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#eef1f4;margin:0;color:#1f2933}}
header{{background:#fff;border-bottom:1px solid #d2dae2;padding:14px 22px;display:flex;align-items:center;gap:14px}}
header h1{{margin:0;font-size:20px}}
.badge{{padding:4px 12px;border-radius:999px;font-weight:700;font-size:12px}}
.badge.pass{{background:#eaf5ee;color:#2f7a46;border:1px solid #bfe3ca}}
.badge.fail{{background:#fbe6e6;color:#cf3b3b;border:1px solid #f0b9b9}}
main{{display:grid;grid-template-columns:1.4fr 1fr;gap:18px;padding:18px 22px}}
.col h2{{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:#52606d;margin:0 0 10px}}
.plan{{background:#fff;border:1px solid #d2dae2;border-radius:10px;padding:10px;margin-bottom:14px}}
.plan svg{{max-width:100%;height:auto}}
.plabel{{font-size:11px;color:#7b8794;margin-bottom:6px}}
.card{{background:#fff;border:1px solid #d2dae2;border-radius:10px;padding:4px 0;margin-bottom:16px}}
.gatehead{{padding:10px 14px;font-weight:700;border-bottom:1px solid #eef2f6;display:flex;align-items:center;gap:8px}}
.gate{{padding:8px 14px;border-bottom:1px solid #f2f5f8}}
.grow{{display:flex;align-items:center;gap:8px}} .gtag{{margin-left:auto;font-size:11px;font-weight:700;color:#7b8794}}
.gate.err .gtag{{color:#cf3b3b}} .gate.warn .gtag{{color:#a86a12}} .gate.ok .gtag{{color:#2f7a46}}
.gmsg{{font-size:12px;color:#52606d;margin:4px 0 0 4px}} .gmsg.e{{color:#cf3b3b}}
.advisory{{background:#fff7ed;border:1px solid #fdba74;color:#9a3412;font-size:12px;padding:7px 12px;border-radius:8px;margin:8px 14px}}
.find{{padding:9px 14px;border-bottom:1px solid #f2f5f8}}
.fh{{display:flex;gap:8px;align-items:center;margin-bottom:4px}}
.chip{{font-size:11px;font-weight:700;padding:1px 8px;border-radius:999px}}
.sev{{font-size:10px;font-weight:800;text-transform:uppercase;padding:1px 7px;border-radius:5px}}
.sev.concern{{background:#fbe6e6;color:#cf3b3b}} .sev.suggestion{{background:#eef2f7;color:#52606d}}
.fm{{font-size:13px;line-height:1.45}} .gnd{{font-size:11px;color:#90a0ad;margin-top:3px;font-style:italic}}
code{{background:#eef2f7;padding:0 4px;border-radius:4px;font-size:12px}} .muted{{color:#90a0ad;font-size:13px;padding:0 14px}}
</style></head><body>
<header><h1>{_esc(name)}</h1>
{"<span class='badge pass'>PASS</span>" if (val or {}).get("passed") else "<span class='badge fail'>FAIL</span>" if val else ""}
<span style='color:#7b8794;font-size:13px'>Review sheet · plans + gates (authoritative) + AI notes (advisory)</span></header>
<main>
<div class=col><h2>Floor plans</h2>{plan_blocks or "<p class='muted'>No plans found.</p>"}</div>
<div class=col>
<h2>Validation gates</h2><div class=card>{_gate_section(val)}</div>
<h2>AI review · advisory</h2><div class=card>{_ai_section(ai)}</div>
</div></main></body></html>"""


def run(spec_path, build_dir, out_dir):
    name = os.path.splitext(os.path.basename(spec_path))[0]
    s = _json(spec_path)
    if s and s.get("name"):
        name = s["name"]
    plans = [(p, _load(p)) for p in
             sorted(glob.glob(os.path.join(build_dir, "floorplans", f"{name}.floor*.svg")))]
    plans = [(p, svg) for p, svg in plans if svg]
    val = _json(os.path.join(build_dir, f"{name}.validation.json"))
    ai = _json(os.path.join(build_dir, f"{name}.ai_review.json"))
    html = build_html(name, plans, val, ai)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{name}.review.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[review-sheet] {name}: {len(plans)} plan(s), "
          f"gates={'yes' if val else 'no'}, ai={'yes' if ai else 'no'} -> {out}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--build-dir", default=os.path.join(HERE, "build"))
    ap.add_argument("--out", default=os.path.join(HERE, "build", "review"))
    args = ap.parse_args(argv)
    targets = (sorted(glob.glob(os.path.join(HERE, "specs", "*.json")))
               if args.all else [args.spec] if args.spec else None)
    if not targets:
        ap.error("give a spec path or --all")
    for t in targets:
        run(t, args.build_dir, args.out)


if __name__ == "__main__":
    main()
