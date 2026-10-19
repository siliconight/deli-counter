"""Every module a shell build reaches is a geometry source or is named as kept out (0.229.0, the factory's
roadmap 259).

`build_freshness.GEOMETRY_SOURCES` is the whole idea, for this repo's commit hook and for Level Factory's guard
that parses the same tuple, of what a built shell is made of. Until 0.228.0 it named 23 sources while a build
reached 54 of this repo's modules, 21 of the unlisted ones shaping what a build writes, so a change to one of
them passed the hook with every shell older than the code that makes it. This walks the build's imports the way
the factory's `docs/findings/build_freshness_259/freshness_imports.py` measured them -- AST imports, top-level
and inside functions, followed from build.py and deli_counter.py through this repo's modules -- and fails on a
module in neither `GEOMETRY_SOURCES` nor `NOT_BAKED`. Both are read the way Level Factory reads the tuple: parsed
with `ast`, never imported.

Run: python -m pytest -q test_freshness_sources.py
"""
import ast
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRIES = ("build", "deli_counter")


def _literal(name):
    tree = ast.parse(open(os.path.join(HERE, "build_freshness.py"), encoding="utf-8").read())
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else []
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            return ast.literal_eval(node.value)
    raise AssertionError("build_freshness.py assigns no literal %s" % name)


def _reached():
    local = {f[:-3] for f in os.listdir(HERE) if f.endswith(".py")}
    seen, todo = set(), list(ENTRIES)
    while todo:
        mod = todo.pop()
        if mod in seen:
            continue
        seen.add(mod)
        tree = ast.parse(open(os.path.join(HERE, mod + ".py"), encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module.split(".")[0]]
            else:
                continue
            todo.extend(n for n in names if n in local)
    return seen


def test_the_sources_are_a_literal_that_names_files():
    sources = _literal("GEOMETRY_SOURCES")
    assert isinstance(sources, tuple) and sources
    missing = [s for s in sources if not os.path.isfile(os.path.join(HERE, s))]
    assert not missing, missing


def test_every_module_a_build_reaches_is_classified():
    sources = set(_literal("GEOMETRY_SOURCES"))
    kept_out = {name for name, _why in _literal("NOT_BAKED")}
    reached = _reached()
    assert len(reached) > 20, reached        # the walk found the build, not an empty graph
    unclassified = sorted(m + ".py" for m in reached if m + ".py" not in sources | kept_out)
    assert not unclassified, "reached by a build, in neither GEOMETRY_SOURCES nor NOT_BAKED: %s" % unclassified


def test_no_module_is_in_both():
    both = sorted(set(_literal("GEOMETRY_SOURCES")) & {name for name, _why in _literal("NOT_BAKED")})
    assert not both, both


def test_each_module_kept_out_says_why():
    for name, why in _literal("NOT_BAKED"):
        assert name.endswith(".py") and os.path.isfile(os.path.join(HERE, name)), name
        assert isinstance(why, str) and len(why) > 10, name


def test_the_agent_contract_is_a_source():
    # the one data file a build reads: body sizes and every clearance derived from them
    assert "agent_contract.json" in _literal("GEOMETRY_SOURCES")
