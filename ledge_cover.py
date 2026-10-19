"""How much of a vault ledge stands inside furniture -- and so whether it draws a box of its own (0.227.0).

A vault ledge (`spec_types.VaultLedge`) is a waist-height box the game marks vaultable. Where a spec puts one at a
piece of furniture -- a register counter, a reception desk -- the ledge is that furniture's vault tag, and the
furniture's own box (a `Volume`, which the art pass dresses as a Zoo prop) is its look. Drawing the ledge as well
stood a second box inside the first: the office's reception desk is 1.0 m tall and its ledge 1.1 m, so a 0.2 m
strip stood 10 cm proud of the desk along its 5 m, and the two boxes' ends z-fought (the factory's cold run 9322:
`base:VAULTLEDGE_0 / reception_desk`). Measured across the spec library on 2026-10-19: 228 ledges; 111 stand clear
of every volume; 98 cross one in part; 19 stand at least half inside one (14 wholly in a register counter, 5 mostly
in a reception desk).

THE RULE, a call made 2026-10-19 and meant to be changed: a ledge at least HIDDEN_BY of whose box lies inside one
visible volume draws no box; its collision and VAULTLEDGE tag stay, so the vault is unchanged. The share is by
volume, of the ledge's own box, against the one volume that covers most of it. A volume with `visual` False hides
nothing: it draws nothing either, so the ledge's box is the only look there is.

Frame: Deli Counter's spec frame, metres, Z up; a box is a centre and a size, a volume's `z` its centre.
"""

#: The share of a ledge's box inside one visible volume at which the volume is its look. The dial.
HIDDEN_BY = 0.5


def _overlap(c0, s0, c1, s1) -> float:
    """The volume two axis-aligned boxes share."""
    shared = 1.0
    for k in range(3):
        lo = max(c0[k] - s0[k] / 2, c1[k] - s1[k] / 2)
        hi = min(c0[k] + s0[k] / 2, c1[k] + s1[k] / 2)
        if hi <= lo:
            return 0.0
        shared *= hi - lo
    return shared


def cover(center, size, volumes):
    """``(fraction, name)``: the share of the box ``(center, size)`` inside the one visible volume covering most of
    it, and that volume's name -- ``(0.0, None)`` when none does. ``volumes`` are ``spec_types.Volume``s, or
    anything with name, x, y, z, size_x, size_y, size_z and, optionally, visual."""
    own = size[0] * size[1] * size[2]
    if own <= 0:
        return 0.0, None
    best, name = 0.0, None
    for v in volumes:
        if not getattr(v, "visual", True):
            continue
        f = _overlap(center, size, (v.x, v.y, v.z), (v.size_x, v.size_y, v.size_z)) / own
        if f > best:
            best, name = f, v.name
    return best, name
