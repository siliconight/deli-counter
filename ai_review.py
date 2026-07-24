#!/usr/bin/env python3
"""
ai_review.py  --  ADVISORY AI review of a generated building (never blocks)
===========================================================================
The deterministic gates (validate.py / evidence.py / layout_lint.py) own the
pass/fail decision. This step adds a human-style second read on top: it feeds
the already-computed deterministic artifacts -- the rendered floor plan(s), the
spec facts, and the validation report -- to a model and asks for design/gameplay
observations the geometric rules can't make.

BRIGHT LINE: this tool only READS the finished plan and COMMENTS. It never
generates plan geometry and never affects the pass/fail gate. Output is
advisory, and `main()` always exits 0.

v2 improvements:
  * MULTIMODAL   -- attaches the rendered plan image(s), so the model reasons
                    over real space (cover placement, sightlines) not a room list.
  * DETERMINISTIC-- temperature 0, pinned model, and a content-hash cache so a
                    building is only re-reviewed (and re-billed) when it changes.
  * GROUNDED     -- each finding must cite the packet fact / plan it rests on;
                    the model is told to use only given facts (anti-hallucination).
  * VERSIONED    -- PROMPT_VERSION is part of the cache key and the output.
  * GUARDRAILS   -- a findings cap, "don't repeat a deterministic WARN, frame it",
                    and an `--eval` mode that asserts known issues still surface.

    python ai_review.py specs/deli_a01.json            # write build/deli_a01.ai_review.json
    python ai_review.py specs/deli_a01.json --dry-run  # packet + image manifest, no API call
    python ai_review.py --all
    python ai_review.py --eval                          # regression: known issues still caught
"""
import argparse
import base64
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODEL = os.environ.get("DC_AI_REVIEW_MODEL", "claude-sonnet-4-5-20250929")
PROMPT_VERSION = "2"
MAX_FINDINGS = 6
CATEGORIES = ["tactical_balance", "plausibility", "readability", "theme",
              "cross_reference"]
CACHE_DIR = os.path.join(HERE, "build", ".ai_review_cache")

REVIEW_INSTRUCTIONS = f"""You are a senior level designer reviewing ONE generated \
building for a heist/assault shooter. You get a factual PACKET plus the rendered \
FLOOR PLAN image(s). The geometry already passed hard checks (walls close, rooms \
connect, everything is reachable) -- do NOT re-report geometry, and do NOT repeat \
the deterministic warnings listed in the packet; you may FRAME them but not restate \
them.

Give only observations a geometric rule cannot make -- design/gameplay JUDGEMENT \
grounded in the plan and packet: tactical balance, plausibility, readability, theme \
fit. Use ONLY facts present in the packet or visible in the plan image; never invent \
rooms, distances, or objects. Prefer a few high-signal notes over many obvious ones \
(at most {MAX_FINDINGS}). Use American spelling.

Each finding:
  category  : tactical_balance | plausibility | readability | theme | cross_reference
  severity  : "concern" (worth a designer's attention) or "suggestion"
  room      : the room id it concerns, or null
  grounding : the packet field or plan feature the note rests on (e.g. "vertical: 1 stair",
              "plan: floor_1 has no interior walls", "sightlines story-1 death_lane 37m")
  message   : one or two concrete, actionable sentences

You are advisory; you never decide pass/fail. If the building is good, say so with \
few findings rather than inventing problems."""


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def build_packet(spec, validation, navigation):
    """Distil the deterministic artifacts into a compact, model-ready packet.
    Includes COORDINATES + cover + sightlines so the model can reason spatially
    alongside the plan image. Pure data -- no judgement."""
    def dims(b):
        return round(b[2] - b[0], 1), round(b[3] - b[1], 1)
    rooms = spec.get("rooms", [])
    cover = ([{"type": m.get("type"), "xy": [m.get("x"), m.get("y")], "room": m.get("room")}
              for m in spec.get("markers", []) if "cover" in (m.get("type") or "")]
             + [{"type": "prop", "name": v.get("name"),
                 "xy": [v.get("x"), v.get("y")], "size": [v.get("size_x"), v.get("size_y")]}
                for v in spec.get("volumes", [])])
    packet = {
        "name": spec.get("name"), "mode": spec.get("mode"),
        "footprint": [spec.get("footprint_x"), spec.get("footprint_y")],
        "stories": spec.get("n_stories"), "has_basement": spec.get("has_basement"),
        "rooms": [{"id": r["id"], "story": r.get("story"), "role": r.get("role"),
                   "size_m": dims(r["bounds"]),
                   "objective": bool(r.get("objective") or r.get("role") == "objective_room")}
                  for r in rooms],
        "objectives": [{"id": o.get("id"), "kind": o.get("kind"), "room": o.get("room"),
                        "xy": [o.get("x"), o.get("y")], "required": o.get("required")}
                       for o in spec.get("objectives", [])],
        "loot": [{"id": l.get("id"), "value": l.get("value"), "room": l.get("room"),
                  "xy": [l.get("x"), l.get("y")]} for l in spec.get("loot", [])],
        "spawns": [{"type": m.get("type"), "id": m.get("id"), "room": m.get("room"),
                    "xy": [m.get("x"), m.get("y")]}
                   for m in spec.get("markers", []) if "spawn" in (m.get("type") or "")],
        "cover": cover,
        "vertical": ([{"kind": "stair", "from": s.get("from_story"), "to": s.get("to_story"),
                       "role": s.get("role")} for s in spec.get("stairs", [])]
                     + [{"kind": "ladder", "from": l.get("from_story"), "to": l.get("to_story"),
                         "role": l.get("role")} for l in spec.get("ladders", [])]),
        "connectivity": (navigation or {}).get("adjacency"),
        "entry_rooms": (navigation or {}).get("entry_rooms"),
    }
    if validation:
        packet["deterministic_warnings"] = {
            g: v.get("warnings", []) for g, v in (validation.get("gates") or {}).items()
            if v.get("warnings")}
        intel = (validation.get("intel") or {}).get("sightlines")
        if intel:
            packet["sightlines"] = [
                {"story": s.get("story"), "death_lane_m": s.get("death_lane_m"),
                 "long_rooms": [r["id"] for r in s.get("rooms", [])
                                if r.get("computed") == "long"]}
                for s in intel]
    return packet


def plan_images(name, build_dir, max_px=1100):
    """Rasterize the rendered floor-plan SVGs to PNG bytes (one per story).
    Returns list of (label, png_bytes). Empty if none / no rasterizer."""
    out = []
    fp = os.path.join(build_dir, "floorplans")
    svgs = sorted(glob.glob(os.path.join(fp, f"{name}.floor*.svg")))
    if not svgs:
        return out
    try:
        import cairosvg
    except ImportError:
        return out
    for s in svgs:
        try:
            png = cairosvg.svg2png(url=s, output_width=max_px)
            out.append((os.path.basename(s), png))
        except Exception:
            continue
    return out


def _cache_key(packet, images, model):
    h = hashlib.sha256()
    h.update(PROMPT_VERSION.encode())
    h.update(model.encode())
    h.update(json.dumps(packet, sort_keys=True).encode())
    for _lbl, png in images:
        h.update(png)
    return h.hexdigest()


def review(packet, images, api_key, model=MODEL):
    """Call the model (temperature 0, multimodal) for advisory findings."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    tool = {"name": "record_review",
            "description": "Record advisory design/gameplay findings.",
            "input_schema": {"type": "object", "properties": {"findings": {
                "type": "array", "maxItems": MAX_FINDINGS, "items": {"type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": CATEGORIES},
                        "severity": {"type": "string", "enum": ["concern", "suggestion"]},
                        "room": {"type": ["string", "null"]},
                        "grounding": {"type": "string"},
                        "message": {"type": "string"}},
                    "required": ["category", "severity", "grounding", "message"]}}},
                "required": ["findings"]}}
    content = [{"type": "text", "text": REVIEW_INSTRUCTIONS
                + "\n\nPACKET:\n" + json.dumps(packet, indent=1)}]
    for lbl, png in images:
        content.append({"type": "text", "text": f"Plan: {lbl}"})
        content.append({"type": "image", "source": {"type": "base64",
                        "media_type": "image/png",
                        "data": base64.b64encode(png).decode()}})
    msg = client.messages.create(
        model=model, max_tokens=1500, temperature=0, tools=[tool],
        tool_choice={"type": "tool", "name": "record_review"},
        messages=[{"role": "user", "content": content}])
    for block in msg.content:
        if getattr(block, "type", None) == "tool_use":
            return block.input.get("findings", [])
    return []


def run(spec_path, build_dir, out_dir, dry_run=False, model=MODEL, use_cache=True):
    spec = _load_json(spec_path)
    name = spec.get("name") or os.path.splitext(os.path.basename(spec_path))[0]
    validation = _load_json(os.path.join(build_dir, f"{name}.validation.json"))
    navigation = _load_json(os.path.join(build_dir, f"{name}.navigation.json"))
    packet = build_packet(spec, validation, navigation)
    images = plan_images(name, build_dir)
    if dry_run:
        print(json.dumps(packet, indent=1))
        print(f"\n[images] {len(images)} plan(s): "
              + ", ".join(f"{l} ({len(p)//1024} KB)" for l, p in images))
        print(f"[cache-key] {_cache_key(packet, images, model)[:16]}…")
        return None
    key = _cache_key(packet, images, model)
    cache_path = os.path.join(CACHE_DIR, f"{name}.{key[:16]}.json")
    if use_cache and os.path.exists(cache_path):
        report = _load_json(cache_path)
        print(f"[ai-review] {name}: {len(report['findings'])} findings (cached)")
        _write(out_dir, name, report)
        return report
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(f"[ai-review] {name}: SKIP (no ANTHROPIC_API_KEY; try --dry-run)")
        return None
    findings = review(packet, images, api_key, model)[:MAX_FINDINGS]
    report = {"schema_version": 2, "tool": "deli_counter/ai_review.py",
              "name": name, "advisory": True, "model": model,
              "prompt_version": PROMPT_VERSION, "content_key": key,
              "n_plans_reviewed": len(images), "findings": findings}
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    _write(out_dir, name, report)
    n_con = sum(1 for x in findings if x.get("severity") == "concern")
    print(f"[ai-review] {name}: {len(findings)} findings ({n_con} concern) -> "
          f"build/{name}.ai_review.json  (advisory)")
    return report


def _write(out_dir, name, report):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{name}.ai_review.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)


# --- eval: a tiny regression so a prompt change can't silently degrade quality --
EVAL_EXPECT = {
    # spec name -> a substring that MUST appear in some finding's message/grounding
    "office": "floor_1",          # the empty 816 m2 middle floor must be flagged
    "bank_branch_a02": "defender",  # defender-on-objective must be flagged
}


def evaluate(build_dir, model):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("[eval] needs ANTHROPIC_API_KEY"); return
    ok = True
    for name, needle in EVAL_EXPECT.items():
        p = os.path.join(HERE, "specs", f"{name}.json")
        rep = run(p, build_dir, build_dir, model=model, use_cache=False)
        hay = json.dumps(rep or {}).lower()
        hit = needle.lower() in hay
        ok &= hit
        print(f"[eval] {name}: {'PASS' if hit else 'FAIL'} (expected mention of '{needle}')")
    print("[eval] all passed" if ok else "[eval] FAILURES — review the prompt")
    sys.exit(0 if ok else 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--build-dir", default=os.path.join(HERE, "build"))
    ap.add_argument("--out", default=os.path.join(HERE, "build"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args(argv)
    if args.eval:
        evaluate(args.build_dir, args.model); return
    targets = (sorted(glob.glob(os.path.join(HERE, "specs", "*.json")))
               if args.all else [args.spec] if args.spec else None)
    if not targets:
        ap.error("give a spec path, --all, or --eval")
    for t in targets:
        run(t, args.build_dir, args.out, args.dry_run, args.model, not args.no_cache)
    sys.exit(0)   # advisory: never fails the build


if __name__ == "__main__":
    main()
