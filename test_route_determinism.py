"""A stair's discharge route does not depend on the interpreter's hash seed.

0.131.1's library rebuild changed the `destination` of one route in
deli_a01, mansion_a03 and warehouse_a02 against a worktree build of the same
code and specs. `_bfs_path` visited a set of room ids, whose order is
PYTHONHASHSEED's, drawn per process: two equally short routes to two exterior
doors were chosen by the interpreter. Run: python -m pytest test_route_determinism.py
"""
import stairwell


def _adj(order):
    # hall reaches two exterior rooms in one hop each; both are destinations
    return {"hall": list(order), "east_door": ["hall"], "west_door": ["hall"]}


def test_equal_routes_pick_the_same_room_whatever_the_neighbour_order():
    dests = {"east_door", "west_door"}
    a = stairwell._bfs_path(_adj(("west_door", "east_door")), "hall", dests)
    b = stairwell._bfs_path(_adj(("east_door", "west_door")), "hall", dests)
    assert a == b == ["hall", "east_door"]


def test_a_shorter_route_still_wins_over_the_alphabetical_one():
    adj = {"hall": ["zed", "annex"], "annex": ["hall", "aa_door"],
           "zed": ["hall"], "aa_door": ["annex"]}
    assert stairwell._bfs_path(adj, "hall", {"zed", "aa_door"}) == ["hall", "zed"]
