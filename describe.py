#!/usr/bin/env python3
"""
describe.py  --  guided interview: describe a building, get a usable level
==========================================================================
The on-ramp between "I want a two-story bank with a vault" and
`new_level.py --preset bank --floors 2`. Fully offline, no AI: a short series
of questions whose answers map deterministically to a preset + parameters via
a decision tree. Picks the best-fit recipe from the nine, then hands off to the
same generation path as new_level.py.

    python describe.py                 # interactive interview
    python describe.py --name my_lvl   # interactive, pre-set the output name

This is an OPTIONAL convenience layer — one of three independent ways to make a
level (describe / `new_level.py --preset` / hand-authored JSON). Nothing else
depends on it; you can ignore or delete it and every other path still works.

The interview narrows the preset space with each answer rather than asking
everything and guessing. It also explains *why* it chose a preset, and lets you
override the auto-picked parameters before generating.

This is deliberately a recommender, not a generator: it always lands on one of
the existing presets (which are validated, budgeted, guarded). It never invents
geometry — it routes a human's description to the closest proven recipe.
"""

import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import presets  # noqa: E402


# ---------------------------------------------------------------------------
# Preset knowledge: the axes that distinguish the nine recipes. Each entry is
# what the interview reasons over. (size: footprint feel; setting: vibe;
# default_mode: native playstyle; vertical: how tall/stacked.)
# ---------------------------------------------------------------------------
PRESET_INFO = {
    "suburban_safehouse": {
        "setting": "residential", "size": "small", "default_mode": "assault",
        "blurb": "a compact suburban house — tight rooms, central stair, attic, basement",
        "modes": ["assault", "heist"], "has_basement_opt": True, "fixed_floors": 2},
    "rowhome": {
        "setting": "residential", "size": "small", "default_mode": "assault",
        "blurb": "a narrow deep 3-floor terraced house — stacked front-to-back clears",
        "modes": ["assault", "heist"], "has_basement_opt": True, "fixed_floors": 3},
    "corner_deli": {
        "setting": "retail", "size": "medium", "default_mode": "heist",
        "blurb": "a corner deli/market over a basement — deli counter, aisles, stockroom, vault",
        "modes": ["heist", "assault"], "has_basement_opt": True, "fixed_floors": 2},
    "bank": {
        "setting": "retail", "size": "medium", "default_mode": "assault",
        "blurb": "a bank branch — glass-front lobby, teller line, basement vault",
        "modes": ["assault", "heist"], "has_basement_opt": True, "fixed_floors": None},
    "casino_tower": {
        "setting": "retail", "size": "large", "default_mode": "heist",
        "blurb": "a casino — open gaming floor, cashier cage, count room, basement vault",
        "modes": ["heist", "assault"], "has_basement_opt": True, "fixed_floors": 2},
    "police_station": {
        "setting": "institutional", "size": "large", "default_mode": "assault",
        "blurb": "a precinct — lobby, holding cells, booking, reinforced armory",
        "modes": ["assault", "heist"], "has_basement_opt": False, "fixed_floors": None},
    "hospital": {
        "setting": "institutional", "size": "large", "default_mode": "survival",
        "blurb": "a multi-story hospital — lobby start, wards, rooftop helipad holdout",
        "modes": ["survival", "assault"], "has_basement_opt": False, "fixed_floors": None},
    "warehouse": {
        "setting": "industrial", "size": "large", "default_mode": "assault",
        "blurb": "a big open warehouse — loading docks, crate cover, long sightlines",
        "modes": ["assault", "heist"], "has_basement_opt": False, "fixed_floors": 1},
    "compound": {
        "setting": "institutional", "size": "large", "default_mode": "assault",
        "blurb": "a fortified multi-story compound — central atrium, dual stairs, top-floor objective",
        "modes": ["assault", "heist"], "has_basement_opt": False, "fixed_floors": None},
}


def ask(prompt, options):
    """Present numbered options, return the chosen key. options: list of
    (key, label)."""
    print("\n" + prompt)
    for i, (_, label) in enumerate(options, 1):
        print(f"  {i}. {label}")
    while True:
        raw = input("  > ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        # also accept the key text directly
        for k, _ in options:
            if raw.lower() == k.lower():
                return k
        print("  (enter a number from the list)")


def score_presets(playstyle, setting, size):
    """Deterministic scoring: rank presets by how well they match the answers.
    Returns sorted [(preset, score, reasons)]."""
    ranked = []
    for name, info in PRESET_INFO.items():
        score = 0
        reasons = []
        if playstyle and playstyle in info["modes"]:
            # native mode is a strong match; supported-but-not-native is weaker
            if playstyle == info["default_mode"]:
                score += 3
                reasons.append(f"native {playstyle}")
            else:
                score += 1
                reasons.append(f"supports {playstyle}")
        if setting and setting == info["setting"]:
            score += 3
            reasons.append(f"{setting} setting")
        if size and size == info["size"]:
            score += 2
            reasons.append(f"{size} footprint")
        ranked.append((name, score, reasons))
    ranked.sort(key=lambda x: -x[1])
    # if everything tied at 0 (caller gave no signal), prefer a versatile,
    # broadly-useful default over the alphabetical first entry.
    if ranked and ranked[0][1] == 0:
        default = "corner_deli"
        ranked = ([(default, 0, ["default pick"])]
                  + [r for r in ranked if r[0] != default])
    return ranked


def interview():
    print("=" * 64)
    print(" Deli Counter — describe a building")
    print(" Answer a few questions; I'll pick the closest proven recipe.")
    print("=" * 64)

    playstyle = ask(
        "What kind of gameplay is this level for?",
        [("assault", "Assault — attackers vs defenders, breach and clear"),
         ("heist", "Heist — a crew grabs loot and extracts"),
         ("survival", "Survival — co-op team holds out against waves"),
         ("", "Not sure / any")])

    setting = ask(
        "What kind of place is it?",
        [("residential", "Residential — a house or apartment"),
         ("retail", "Retail / commercial — shop, bank, casino"),
         ("institutional", "Institutional — precinct, hospital, compound"),
         ("industrial", "Industrial — warehouse, depot"),
         ("", "Not sure / any")])

    size = ask(
        "How big is it?",
        [("small", "Small — a single house, tight quarters"),
         ("medium", "Medium — a shop or branch building"),
         ("large", "Large — a multi-wing or multi-story building"),
         ("", "Not sure / any")])

    ranked = score_presets(playstyle, setting, size)
    top = ranked[0]
    # if everything tied at 0 (all "any"), fall back to a sensible default
    if top[1] == 0:
        top = ("corner_deli", 0, ["default pick"])

    name, score, reasons = top
    info = PRESET_INFO[name]
    print("\n" + "-" * 64)
    print(f" Best fit: {name}")
    print(f"   {info['blurb']}")
    if reasons:
        print(f"   why: {', '.join(reasons)}")
    # show runners-up so the human can redirect
    alts = [r for r in ranked[1:4] if r[1] > 0]
    if alts:
        print("   other options: " + ", ".join(f"{n} ({s})" for n, s, _ in alts))
    print("-" * 64)

    chosen = ask(
        "Use this preset?",
        [(name, f"Yes — use {name}")]
        + [(n, f"No, use {n} instead ({PRESET_INFO[n]['blurb'][:40]}…)")
           for n, s, _ in alts]
        + [("__list", "Show me all nine presets")])
    if chosen == "__list":
        print("\nAll presets:")
        for n, i in PRESET_INFO.items():
            print(f"  {n:20s} {i['blurb']}")
        chosen = ask("Which one?", [(n, n) for n in PRESET_INFO])

    info = PRESET_INFO[chosen]

    # --- parameters -------------------------------------------------------
    # mode: default to the playstyle if supported, else the preset's native
    mode = playstyle if (playstyle and playstyle in info["modes"]) else info["default_mode"]

    kwargs = {"mode": mode}

    # floors (only if the preset allows it)
    if info["fixed_floors"] is None:
        floors = ask(
            "How many above-ground floors?",
            [("2", "2"), ("3", "3"), ("4", "4")])
        kwargs["floors"] = int(floors)

    # basement (only if the preset supports toggling)
    if info["has_basement_opt"]:
        b = ask("Include a basement?",
                [("yes", "Yes"), ("no", "No")])
        kwargs["basement"] = (b == "yes")

    sref = ask("Add 1.8 m human-scale proxies (for a Blender scale check)?",
               [("no", "No"), ("yes", "Yes")])
    kwargs["scale_ref"] = (sref == "yes")

    return chosen, kwargs


def main():
    args = sys.argv[1:]
    name = None
    if "--name" in args:
        i = args.index("--name")
        if i + 1 < len(args):
            name = args[i + 1]

    try:
        preset, kwargs = interview()
    except (KeyboardInterrupt, EOFError):
        print("\n(cancelled)")
        return 1

    if not name:
        name = input("\nName this level (-> specs/<name>.json): ").strip()
    if not name:
        name = f"{preset}_level"

    print("\n" + "=" * 64)
    print(" Generating with:")
    flagstr = f"--preset {preset} --name {name}"
    flagstr += f" --mode {kwargs['mode']}"
    if "floors" in kwargs:
        flagstr += f" --floors {kwargs['floors']}"
    if "basement" in kwargs:
        flagstr += "" if kwargs["basement"] else " --no-basement"
    if kwargs.get("scale_ref"):
        flagstr += " --scale-ref"
    print(f"   python new_level.py {flagstr}")
    print("=" * 64)

    # generate directly (same path as new_level.py)
    spec = presets.make(preset, name=name, **kwargs)
    import json
    out = os.path.join(HERE, "specs", f"{name}.json")
    with open(out, "w") as f:
        json.dump(spec, f, indent=2)
    print(f"\nwrote {out}")

    # validate + refresh catalog, same as new_level.py
    import subprocess
    subprocess.run([sys.executable, "validate.py", out], cwd=HERE)
    cat = os.path.join(HERE, "catalog.py")
    if os.path.exists(cat):
        subprocess.run([sys.executable, cat], cwd=HERE,
                       capture_output=True, text=True)
        print("refreshed specs/CATALOG.md")
    print(f"\nNext: build it ->  python build.py specs/{name}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
