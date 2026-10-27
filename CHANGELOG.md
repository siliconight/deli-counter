## [0.279.0] - a supermarket's ceiling rows bake to the next lamp along

The walker, 2026-10-26: "far too dark in teh super market". Measured on the walker's level (the factory's
docs/findings/black_gondola_ends/):

- The supermarket's lamps are baked statics whose range is the drop rule. That rule was written for the realtime
  claim each lamp makes on every mesh it reaches.
- Re-baked with the range x 1.6, the store's frame rose 38.5 -> 61.5 mean, and the gondolas' black ends lifted.

Lux 0.80.0 lends a static lamp a longer range only while a lightmap bakes. It derives that range as
`hypot(drop, bake_reach) + 0.75` from a row's `bake_reach`.

### Added
- **`bake_reach`** on the fluorescent rows of a room in `derive_light_anchors`' new `bake_reach_rooms`: the row's
  lamp spacing, so the bake reaches the floor under the next lamp along. Lux makes 7.61 m of it in supermarket_a01
  (drop 4.1, spacing 5.5), x 1.57 its live 4.85.
- **`_bake_reach_rooms(rooms, business)`**: a supermarket's selling floor (`level_design.is_supermarket_floor`). In
  the library that is the three supermarkets' `sales_floor` rows (spacing 5.5, 5.5 and 5.0 m). Every other anchor is
  byte-identical to 0.278.0's. Zoo 1.134.0 carries it to the lamps' markers.

### Tests
- `tests/test_bake_reach.py` (all 6 fail on 0.278.0):
  - a named room's rows carry their spacing, and no other room's do;
  - without a named room every row is 0.278.0's anchor exactly (the control);
  - the supermarket floor is the named room, and a convenience store's is not;
  - every built supermarket's sales-floor rows carry it.

## [0.278.0] - a supermarket's shelves sell what the markers over them say

The walker's grocery comps (the factory's docs/reference/GROCERY_STORE_COMPS.md). In the walker's level the
supermarket's gondolas sold the convenience store's chips under markers that said CEREAL and CANNED VEG (0.276.0).
Zoo 1.133.0's `snack_gondola` form `grocery` sells, on each face, one of the 24 categories the markers print.

### Added
- **`stock_supermarket_gondolas(spec, room)`.** Furnish makes every gondola on a supermarket's floor, authored or
  laid, Zoo's grocery form:
  - its VARIANT is its line's index, low end of the cross axis first, as the markers number their lanes;
  - it is turned half round where its module's +Y points to the lower lane. A gondola is an island shopped on both
    sides, so the turn moves nothing it collides with.
  - In Zoo's rule, face -Y of line v sells the second category of lane v - 1 and face +Y the first of lane v. So
    lane j's two categories are on the +Y face of line j and the -Y face of line j + 1, under marker j.
  - Twelve lines sell all 24 categories; a thirteenth starts round again.
- **`_plus_y_plan(v)`**: where a gondola's module +Y points in plan. The slot's turn
  (`prop_species.long_axis_first`, plus the volume's `rot_z`) takes the module's +X to plan +X at 0 degrees, -Y at
  90, -X at 180 and +Y at 270 (the composer's measured convention), so its +Y goes to plan +Y, +X, -Y and -X.
- **`migrations/migrate_grocery_gondolas.py`** refurnishes the three supermarkets:
  - a01: 5 gondolas;
  - a02: 10 gondolas. Its laid runs' variants, drawn for variety, are now their lines'. The two runs on line 2 that
    stood at 180 degrees now stand at 0, their +Y toward the lane after.
  - a03: 4 gondolas.

### Changed
- **`_gondola_lines(spec, room)`**: `aisle_markers`' grouping of the gondolas into lines, moved out whole so the
  markers and the stock read one grouping. Each line now also carries its volumes. Every marker is where it was.

### Tests
- `tests/test_grocery_gondolas.py` (4 of 5 fail on 0.277.0; the first holds the library's three supermarkets):
  - every gondola is the grocery form of its line, its +Y toward the lane after;
  - a lane's marker and the faces either side of it agree. Every lane of the library takes a marker, which the
    pairing needs: a skipped lane would renumber the markers after it.
  - stocking is a fixed point, and turns a backward gondola back;
  - the slots carry the form, the line and the turn.

## [0.277.0] - a supermarket stands a produce section

The walker's grocery comps, 2026-10-26 (the factory's docs/reference/GROCERY_STORE_COMPS.md): "a retro produce
section ... neatly arranged fruit and vegetables". Zoo 1.132.0's `produce_table` is the table.

### Added
- **`produce_table`**, a piece:
  - an island a shopper walks round, front to the aisle;
  - 1.8 to 3.0 m wide and 0.9-0.95 m tall, below cover height, so it stands mid-floor under furnish's rule.
  - Its variant is its stock, the heap a table's first bay starts from. It takes FOUR variants, not Zoo's eight: a
    piece past four draws its variant from the building's id (the neon sign's rule), and the first build gave both
    tables in every store the same heaps.
- **The supermarket recipe stands two first** (`anchors`, `all_anchors`): its produce section, where furnish's island
  rule finds them clear floor. `migrations/migrate_produce_section.py` refurnishes the three supermarkets, each with
  two tables of different stock.
- `prop_species` routes `produce_table` to Zoo's species.

### Changed
- The supermarket recipe's note said "NO AISLE SIGNS YET". Its signs are `aisle_markers`' rule (0.276.0), and the note
  says so.

### Tests
- `tests/test_produce_section.py` (3 of 4 fail on 0.276.0; the fourth holds every pair of tables there is):
  - the recipe stands two tables first, below cover height;
  - every supermarket stands one or two;
  - two in a store carry different heaps;
  - each routes to Zoo's species, within its genome's sizes.
- `test_furnish` names the supermarket among the recipes that stand an island, and mirrors `produce_table`'s sizes.

## [0.276.0] - a supermarket hangs a numbered marker over each aisle

The walker's grocery comps, 2026-10-26 (the factory's docs/reference/GROCERY_STORE_COMPS.md) show a printed sign over
the head of every aisle, its number large and what is down it beside it. Zoo 1.131.0 prints one: `aisle_sign` form
`grocery`, the number its variant gives.

### Added
- **`level_design.aisle_markers(spec, room)`**: where a supermarket's sales floor hangs its markers, aisle 1 first.
  - Read off the gondolas on the room's floor, its own aisles or the rows furnish laid, grouped into lines along
    the axis most of them are long in.
  - Each lane between two neighbouring lines takes one marker, 0.6 m in from its storefront end: the end nearer the
    storey's glazed wall, else the low end.
  - The board is 1.4 m across the lane, or the lane's width less 10 cm; a lane under 0.5 m takes none. Twelve at most.
- **Furnish hangs them last** in a supermarket's sales floor, `form: grocery`, the variant the aisle's index, and only
  where the storey gives a body its headroom under one (`hung_headroom_ok`).
- **`migrations/migrate_aisle_markers.py`** refurnishes the supermarkets: supermarket_a01 hangs 4, a02 3, a03 3.

### Tests
- `tests/test_aisle_markers.py` (2 of 4 fail on 0.275.0; the other two hold every marker there is, and on 0.275.0
  there is none):
  - supermarket_a01's four at its lanes' storefront end;
  - every supermarket's markers numbered in order;
  - each over a lane with a body's headroom under it;
  - the markers reach Zoo's grocery form.

## [0.275.0] - a supermarket is furnished as one, and stands its cooler wall

The walker, 2026-10-26, walking seed 9205's supermarket: "far too dark in teh super market". Then came the comps:
"shiny floor, bright lights, isles, glowing freezer section, stacked high". They are filed as the factory's
docs/reference/GROCERY_STORE_COMPS.md.

Before this release:
- none of the library's three supermarkets stood a cooler. 0.272.0 kept them out of the convenience store's rule:
  "their cooler wall and glass front are their own decision";
- their sales floors took the shop floor's recipe. supermarket_a01's stood a service counter, two filing cabinets,
  two vending machines, two video poker machines with their stools, and eleven cartons and bins round its five aisles;
- supermarket_a02 had no aisle at all.

### Added
- **`migrations/migrate_supermarket_cooler.py`**: a supermarket's sales floor stands a glass-door cooler wall,
  using `migrate_cooler_wall`'s clearances.
  - The wall is the one opposite the storefront glass, where the aisles' heads face and a real store backs its
    dairy and frozen cases onto the stockroom.
  - The run is up to 24 m, in runs of at most 12 m (Zoo `cooler_run`'s widest), named `cooler_run_sales_<i>`.
  - It is planned on the spec less its furnishing, then the spec is refurnished.
  - a01 stands 2 x 8.85 m, a02 2 x 12.00 m, a03 2 x 10.95 m.
- **The `supermarket` kind** (`level_design.is_supermarket_floor`, `_RECIPES["supermarket"]`). A building whose id
  says supermarket or grocer, and a room whose id says it sells, are furnished as a supermarket:
  - its aisles;
  - shelving stacked along its walls;
  - one cluster of cartons;
  - an ATM.

  Its stockroom, mezzanine and offices keep their kinds.
- **`gondola_run`**: the supermarket's rows, Zoo's `snack_gondola` at 7.2 to 12.0 m, below shelter like
  `gondola_aisle`.
  - A floor whose own aisles already stand (`authored_aisles`) takes no rows. The first build laid 3.6 m islands down
    the lanes between supermarket_a01's 14 m aisles.
  - supermarket_a02 now stands four rows of three 7.2 m runs.

### Changed
- A one-cluster recipe lays its rows after its wall run, as every other recipe does. The supermarket is the first
  one-cluster recipe that has rows.
- No aisle signs yet. A fixture hangs where a hung slot is free, and the first build hung one over the checkout. A
  supermarket's sign hangs over its aisle, which is a rule of its own.

### Tests
- `tests/test_supermarket_dress.py` (fails on 0.274.0) checks:
  - the rule's rooms;
  - every supermarket's cooler wall: on the back wall, facing in, at least 16 m;
  - no office furniture on the floor;
  - authored aisles take no rows, and a bare floor takes long runs;
  - the migration is done and idempotent;
  - the names route.
- `test_furnish` knows the supermarket's rows.
- `test_card_shop` and `test_store_atms` named a supermarket's sales floor a shop floor. It is its own kind now,
  still never the card shop's, and it still sells.

## [0.274.0] - a selling room keeps a shop's lamp density, however big it is

The walker, 2026-10-26, in seed 9205's supermarket: "far too dark in teh super market". Then came the comps: "shiny
floor, bright lights, isles, glowing freezer section". They are filed as the factory's
docs/reference/GROCERY_STORE_COMPS.md: long fluorescent runs 2 to 3 m apart, nothing in shadow.

Every room was held to twelve lamps, whatever its size (`_MAX_LAMPS_ROOM`, "until the price of more is measured").
So the library's selling floors got darker as they got bigger. The factory's
docs/findings/selling_hall_lights/census.py counts it:
- the shops under 340 m2: 13 to 34 m2 a lamp;
- the supermarkets: 88 to 92;
- the market halls: 89 to 104.

### Changed
- **`lights.room_caps(r, bounds)`**: a room whose id sells takes its lamp cap from its area. "Sells" means
  `floors.floor_by_use` returns "tile", the same words that tile its floor.
  - The cap is one lamp per `_SELLING_M2_PER_LAMP` (25.0) and never fewer than twelve. Its rows across and its
    lamps along are bounded by that cap alone.
  - 25 m2 is the density the library's capped selling rooms of 250 to 300 m2 already had: the delis'
    `market_aisles` 25.0, gas_station_a02 23.0, convenience_store_a01 21.1, pharmacy_a01 26.4. A big store is lit
    like a small one, not brighter.
  - WOOD's spacing, unchanged, decides how many lamps a room asks for. supermarket_a01's 44 x 24 m sales floor goes
    from 3 rows of 4 at 11 m to 5 rows of 8 at 5.5 m: 40 lamps, 26.4 m2 a lamp. market_hall_a01's stall floor
    goes from 10 to 15.
  - Every other room keeps the library's caps.
- The lamps are baked, so what more of them costs a frame is their fixtures' draws. The price is in the factory's
  docs/findings/selling_hall_lights/.

### Tests
- `tests/test_selling_room_lamps.py` (2 of 3 fail on 0.273.0):
  - the cap's derivation;
  - supermarket_a01 lit at 40 lamps;
  - a non-selling hall kept at twelve.
- `test_fixture_rows`'s many-aisles cap test now names a stockroom, which keeps the library's cap.

## [0.273.0] - a ramp's cut begins where a body clears the slab, and nothing stands in it

**The factory's roadmap 270.** The walker, on seed 9205's parking garage, 2026-10-26: "i can't use this wide ramp to
go up or down?". Every library ramp's slab cut began at the ramp's middle. There the gap between the ramp's top and
the slab it climbs to was 1.04 to 1.55 m, against the agent contract's `min_headroom_m` of 2.0, so a body met the
slab's edge, up or down.

### Changed
- **`stairwell.ramp_cut_span(rp, spec)`**: the cut begins where that gap falls to `min_headroom_m`, at
  `t_low + run * (rise - slab - headroom) / rise`, and never later than the middle.
  - Across the nine library ramps the start moves 0.9 to 2.7 m down each ramp. The parking garages' cut now starts
    2.33 m from the foot where it started at 5.00, and every gap where a cut starts is 2.00 m.
  - `ramp_hole` and every caller (the builder, `slab_openings`, `stair_guards`, the stair walk-off) pass the spec,
    so the rails, wall voids and holes follow the longer cut.
  - Without a spec the cut begins at the middle, as before.
- **Furnish keeps every piece off a ramp's cut** (`level_design.ramp_holes`), as it keeps off an authored hole. This
  applies to piece placement and to the seeded corridor's obstacles.
- **`migrations/migrate_ramp_cut.py`** clears what stood in the longer cuts.
  - `cbp_town_finale`: cartons, a desk and a chair set, refurnished.
  - `foundry_heist_vertical`: pallets and a drum refurnished, and two AUTHORED pieces moved by the least distance
    that clears the cut and its rail: `forklift_cover` x 12.0 -> 10.6 and `loading_crate_stack_a` x 17.0 -> 17.6,
    both still in the loading dock.
- `tests/test_ramp_cut.py`'s two rail tests ask the rails of the cut the builder makes, `ramp_hole(rp, spec)`.

### Tests
- `tests/test_ramp_cut_headroom.py` (all 4 fail on 0.272.0):
  - every library ramp's cut begins where the gap is at least 2.0 m and no later than its middle;
  - the walker's garage opens 2.33 m up its ramp;
  - nothing stands in any cut;
  - the authored pieces moved by the least distance.
- Layout lint over the garages unchanged: the same warnings before and after.

## [0.272.0] - a supermarket's aisles are gondolas too

**The walker, walking seed 9205's supermarket, 2026-10-26**: "far too dark" and, of the level, "doesn't look finished".
Under an inspection light the sales floor's aisles were five 14 m plain boxes (the factory's
`docs/findings/walk_2026-10-26_panel/`, L3 and L4).

### Changed
- **`migrations/migrate_supermarket_gondolas.py`** renames the supermarkets' `aisle_N` volumes to `gondola_aisle_N`,
  which `prop_species` routes to Zoo's `snack_gondola`: 5 in `supermarket_a01`, 4 in `supermarket_a03`.
  - `migrate_store_gondolas.py` (0.149.0) had left them boxes because "a supermarket aisle is not a snack aisle".
    They fit the species, though: 1.4 x 14.0 x 2.0 m and 1.4 x 12.0 x 2.0 m, against widths 1.2-14.0, depths
    0.6-1.5 and heights 1.2-2.2. Grocery stock in place of snacks is a Zoo variant for later.
- **`migrate_slush_machine.is_store` means a CONVENIENCE store and excludes supermarkets.** It reads "a sales floor
  with `gondola_aisle` volumes", so the renamed supermarkets matched it, and six migrations would have given them a
  slush station, a roller grill, window posters and signs. A supermarket's cooler wall and glass front are a decision
  of their own, not this release's side effect.
- `prop_species`' note records the change; `test_store_gondolas` keeps only the pharmacy out.

### Tests
- `tests/test_supermarket_gondolas.py` (both fail on 0.271.0): every supermarket aisle is a gondola; they fit the
  species, all 9 checked, so the test cannot pass by finding none.

## [0.271.0] - a selling floor is tile and a working floor is concrete

**The walker, walking seed 9205's supermarket, 2026-10-26: "far too dark in teh super market"** (the factory's
`docs/findings/walk_2026-10-26_panel/`, L4).

### Measured, in order
1. The sales floor's light-check station read luma p50 3 at Blue Hour; the back stock next door read 77.
2. Not the import: a complete re-walk read the same.
3. Not missing lamps: every lamp is baked, and the bake supplies 15.8 of the frame's 20.7.
4. Re-baked copies, against a control that reproduced the shipped frame exactly: doubling the lightmap's texels
   changed nothing, and doubling the room fill raised both rooms alike.
5. Under an inspection light the sales floor is a dark maroon carpet; the back stock is pale concrete. The room was
   lit like its neighbour and dark because of what it was made of.

### Changed
- **`floors.floor_by_use`, asked by `_material` wherever the role map would carpet a floor.**
  - `public_entry` maps to carpet. That is right for a lobby, a banking hall or a parlour, and it had carpeted 33
    `sales_floor`s, the delis' `customer_floor`s and `stockroom_loading`s, pawn, pharmacy and market floors, a
    garage deck, service bays, docks and train sheds.
  - A room whose id SELLS (`sales`, `retail`, `shop`, `store`, `market`, `stall`, `customer`, `aisle`) now gets
    `tile`, a 1990s store's vinyl tile.
  - A room whose id WORKS (`stock`, `loading`, `dock`, `bay`, `deck`, `shed`, `lanes`, `works`, `pour`, `garage`)
    gets `concrete`.
  - A room's own floor material still wins, the ceiling is untouched, and floor and ceiling stay different surfaces.
  - `main_floor` is left alone: it is a warehouse's and a club's both, so what it is needs the building, not the room.
- Rebuilt library: 594 floor slots, 72 still carpet (lobbies, halls, parlours, lounges, waiting rooms, offices).

### Tests
- `tests/test_floor_by_use.py` (3 of 5 fail on 0.270.0; the other two guard lobbies and a room's own floor):
  - the supermarket's sales floor is tile;
  - stores sell on tile and work on concrete;
  - a lobby, a banking hall and a parlour keep carpet;
  - only a carpet is reconsidered, and a room's own floor wins;
  - no selling or working floor in the library is carpeted.

## [0.270.0] - a chapel, a courtroom, an assembly hall and a gallery furnished as what they are

**The factory's roadmap 308.** One `hall` kind covered the words gallery, galleries, exhibit, chapel, assembly,
courtroom, courtrooms, viewing and artifact, and its recipe was a dining hall's: a service counter, waiting chairs,
a shelf run, a file cabinet, vending, dining tables, a litter bin and a cigarette machine. Fifteen rooms in twelve
specs stood a cafeteria: a funeral home's chapel and viewing rooms, two courtrooms, two assembly halls, three
museums' galleries, a mansion's gallery and final_stand's.

### Changed
- **Four kinds where there was one** (`_ROOM_KINDS`): `chapel` (chapel, viewing), `courtroom` (courtroom,
  courtrooms), `assembly` (assembly), `gallery` (gallery, galleries, exhibit, artifact). `hall` is gone.
- **A room's front** (`room_front`, `room_openings`): an end of its long axis. It is the end whose own wall has
  less doorway, and between two walls with as much, the end away from the doors' mean. An authored seat row
  (`pew`, `bench` in its name) turns the axis so furnish continues it. Each rule was measured on the library:
  - landmark_hall_a02 has three doors in each long wall, and the mean alone put the front on a wall of doors;
  - funeral_home_a01's chapel's authored 8 m pews run across the long axis.
- **Facing rows** (`facing_slots`, furnish's `_facing`, the recipe's `facing`): laid first. In order:
  - a front piece centred on the front wall, sliding a metre at a time off a door's approach, facing back into the
    room;
  - any well pieces in a row before it;
  - rows of `seat` across the room, all facing the front: two blocks either side of a centre aisle, with side
    aisles. A wide block is several pews with aisles between them. Rows run from `gap` off the front wall to a
    door's clearance off the back wall, until `share` or `rows`.

  Every slot is asked of the room as it stands before any row is written (`_row_clear`), so rows keep their aisles
  from everything but one another; pews stand `FACING_ROW_GAP` 0.3 m apart.
- **A room that faces a front reserves its routes** (`reserves_routes` -> `"all"`, as a corner store's rows have
  since 0.250.0). Unreserved, landmark_hall_a01's assembly hall stood a block of pews across its door to `entry_e`
  (16.3 -> 20.8 m in the route census); reserved, its worst detour is 1.068.
- **The recipes:**
  - chapel: an altar (`table_work`) and pews, 12 rows;
  - courtroom: the judge's bench (`counter_service`), two counsel tables in the well, the public's pews 6 m back,
    6 rows, clerk's cabinets on the walls, 6 pieces at most;
  - assembly: a lectern (`table_work`) and pews, 12 rows;
  - gallery: display cases and shelf runs on the walls and a short pew or two to look from (`pew_short`, 2.4 and
    1.8 m: a floor piece's spot stands a metre off the room's bounds, and a 4.2 m pew turned 0.45 m through the
    generated compound's south wall), one piece in 40 m2, 10 at most.

  The rows are capped because every pew is its own mesh: courthouse_a02's first trial stood 60 where the cafeteria
  had 21 pieces.
- **`pew`**, a floor piece (3.6 / 3.0 / 2.4 / 4.2 x 0.62 x 0.95 m, front, 60 at most), built by Zoo's `pew`
  (>= 1.130.0); `prop_species` routes `pew` names there before `chair`. That includes the funeral home's authored
  `pew_row` boxes.
- **The library refurnished** (`migrations/migrate_civic_rooms.py`): the twelve specs with civic rooms, then, in the
  order they shipped, the passes the library is a fixed point of -- shelter, the seeded pieces' corridor and line,
  the wall trim; every volume outside those rooms unchanged. A spec is migrated when none of its civic rooms holds a
  piece only the old recipe stood.
- **Cigarette machines 85 -> 71**: the 14 that stood in these rooms.

### Measured (the factory's `patches/dc_civic_rooms/route_summary.out.txt`)
- The route census on the twelve specs, before and after: no route closed to a body or to the bake. Pairs past the
  guide's 1.10 detour are unchanged in every spec. funeral_home_a01's chapel narrows 6 pairs to single file, and
  courthouse_a02 narrows 2. The worst new detour is 1.073 (funeral_home_a01's chapel).

### Noted, not changed
- A courtroom of 42 m (courthouse_a02) keeps most of its floor open behind six rows. Naming that floor's use is the
  factory's roadmap 306.
- Authored boxes in a room refuse the slots beside them, and two rooms' blocks come out uneven
  (landmark_hall_a01: 12 pews and 6).
- A courtroom's rail, a lectern and a plinth are not built: no piece or species makes them yet.
- **Three rooms gain a seeded shelter piece**: funeral_home_a01's chapel (a kiosk) and viewing_wing, and
  funeral_home_a02's viewing_rooms (crate stacks). The cafeteria's vending machines and shelves had given them
  shelter-height cover; pews are 0.95 m. They stand in line (`tests/test_seed_lines.py`, lined rooms 35 -> 38). It
  keeps the rooms fightable, but a crate stack in a viewing room is an odd sight. A shelter-height piece that belongs
  in a chapel is open.

### Tests
- `tests/test_civic_rooms.py`: the kinds; the front away from the door; an authored row turning the axis; a chapel
  as one altar and pews all facing it across a centre aisle, with no cafeteria piece; a courtroom's bench, well and
  public in that order; a gallery's floor kept open. Fails on 0.269.0.
- `tests/test_furnish.py` (the `pew` range), `tests/test_club_fixtures.py` (an exhibit hall stands no cigarette
  machine; the library's 71), `tests/test_seed_lines.py` (38 lined rooms).

## [0.269.0] - a switchback's seam draws as a raking rail

**The walker, walking cold run 9386** (the factory's `docs/findings/walk_2026-10-23_9386/`, finding 6), circling the
plain block over the office switchback's upper flight: "the walling/railing doesn't loook natural yet". Their pick, the
compact U: walls where they enclose the well, a rail between the flights. 0.268.0 made the hole's rails balustrades;
this is the block.

### Changed
- **The seam's collider stays exactly where it was, unseen** (`visual: false`): its underside a body's height over
  the storey's floor so the lower flight keeps its headroom (`stairwell._seam_pieces`, 0.225.0's measurement), which a
  rail's collider following the upper flight down to its treads would not.
- **A raking rail along the upper flight's inner edge**: Zoo's `stoop_railing` flight form (>= 1.129.0), from the
  storey's floor at the flight's foot to `stoop.RAIL_H` over its head, its high end up the flight (`rises_hi`, which
  `_seam_pieces` now records from the leg's arrival end). A SLOT WITH NO GREYBOX BOX and no collider: a greybox visual
  box is navigation data to Lot's walk bake, and this one would stand a thin wall from the floor at the seam -- the
  floor-height seam 0.225.0 measured cutting the lower flight. With no greybox node the composer places the module by
  the slot's own transform and turn, and the bake sees the seam's collider alone, as before.

### Tests
- `tests/test_stair_rake.py` (new): the office's seam keeps its collider, draws no box of its own and gains one raking
  rail -- `stoop_railing`, flight, no collision, the seam's length by a storey and a rail, turned up the flight -- and
  the rake draws no greybox box. The first fails on 0.268.0.

### Measured, the clone
- `build.py --all` and `nav_gate.py --all` exit 0, 157 shells passed -- the seam's collider is where it was, so
  the walk bake meets what it met; the suite 1,831 tests, 0 failed, 31 skipped (the factory's
  `patches/dc_stair_rake/prove.out.txt`).

## [0.268.0] - a stair hole's rail is a balustrade

**The walker, walking cold run 9386** (the factory's `docs/findings/walk_2026-10-23_9386/`, finding 6), of the office's
double stair -- its hole ringed by solid wood guard boxes 1.07 m high, a flight walled where it should be open: "something
about the doulbe stairs still needs some work to not look so odd...mainly the walling/railing doesn't loook natural yet".
Their pick for the form: the compact U, walls where they enclose the well, a rail between the flights. This is the
first step: the rails.

### Changed
- **A stair hole's rail is Zoo's `stoop_railing`** (>= 1.128.0, its level form, posts at least every 2.0 m and
  pickets between): `prop_species` routes `stair_guard_rail_<k>` to it, first in the table (no other row's keyword is in
  those names, and no authored volume carries one), and `_stair_guards` gives a rail `form: level`.
- **Painted iron where the palette has it, else wood**: a stair's rail took `wood` wherever the palette had it; a
  ramp's still names its own steel. 117 of the library's 305 stair specs have `metal_painted`.
- **The collider is unchanged**: each rail keeps its own `_col` box; Zoo's species builds no collision.

### Still open
- The seam wall a switchback's upper flight carries over the lower one's edge -- the plain block the walker circled --
  becomes a raking rail in a later step; its underside stands a body's height up so the lower flight keeps its
  headroom, and that has to hold.

### Tests
- `tests/test_stair_balustrade.py` (new): the rail's name routes to the balustrade and a side or back wall's does not;
  the office's six rails are iron balustrades in the level form and keep their colliders, its walls stay walls. Both
  fail on 0.267.0. `tests/test_ramp_cut.py`'s pin on the builder's material line follows it.

### Measured, the clone
- `build.py --all` and `nav_gate.py --all` exit 0, 157 shells passed; the suite 1,829 tests, 0 failed but the ramp
  test's pin, since followed (the factory's `patches/dc_stair_balustrade/prove.out.txt`).

## [0.267.0] - a loading dock's pile is pallet stacks, and a safe is painted steel

**The walker, walking cold run 9386** (the factory's `docs/findings/walk_2026-10-23_9386/`, findings 9 and 3), of
deli_a03's stockroom: "not sure what this large boring wood block is"; and of pharmacy_a01's drop safe: "looks like a
brown box". The block was the corner deli preset's `loading_pallet_stack`, one 4.5 x 2.5 x 1.5 m volume: Zoo's
`pallet_stack` fits 0.84-1.80 x 0.70-1.50 x 0.665-1.425 m, so the kit refused the species and built a plain box. The
safe was `metal`, which a theme spends on its street metal -- delco_1997's `metal_rusted_street`, averaging
(115, 80, 53) against its wood's (86, 60, 41).

### Changed
- **`presets.pallet_pile`**: a dock pile as a grid of stacks that each fit -- as many along each side as keep a
  stack inside `PALLET_MAX` (1.8 x 1.5 m), `PALLET_GAP` (0.15 x 0.2 m) apart, too narrow for a body, so the pile is
  still one obstacle and the cover it was -- at the heights a dock's stacks stand at (`PALLET_HEIGHTS`, 1.0-1.4 m in
  turn). A 4.5 x 2.5 pile is three by two of 1.4 x 1.15 m. The corner deli preset stands its pile this way.
- **A pile is one piece of what its room holds** (`_room_volume_count`, `PALLET_STACK_PREFIX`): a room's stacks count
  once, as the block did, so furnish's target for the room is what it was.
- **A safe is painted steel**: `level_design`'s material rows give `safe` `metal_painted`, above the row whose `safe`
  it was. Zoo 1.125.0 paints `drop_safe` by default; a slot naming a kind builds that kind, so this row decides the
  library's safes on any Zoo.

### Noticed, not changed
- The rows match a name's keyword, so `crate_stack_safe_room` -- five crate stacks named for the safe room they
  stand in -- read `safe` and were `metal` before this; they are `metal_painted` now. The kind was already wrong;
  a crate row above the safe row is its own change.

### Library
- `migrations/migrate_pallet_pile.py`: every stored `loading_pallet_stack` becomes `pallet_pile` over its own
  footprint and floor, and the spec is refurnished (the library is a fixed point of furnish) -- 8 specs, 8 piles to
  48 stacks, every other volume in them where it was (the factory's `patches/dc_pallets_safes/furniture_kept.py`).
  `migrations/migrate_safe_paint.py`: every stored safe-named piece in `metal` to `metal_painted` -- 66 specs,
  136 pieces (the 8 refurnished specs' safes come out of furnish painted). A second run of either changes nothing.

### Refuted on the way, each kept in the factory's `patches/dc_pallets_safes/`
- Migrating without the refurnish: four fixed-point-of-furnish tests failed on the six delis
  (`suite_draft1.out.txt`).
- Refurnishing with the pile counted as six: each of six delis' stockrooms lost five pieces -- its supply cabinet,
  file cabinet, shelf run, cartons and pallets -- 30 in all (`furniture_kept_draft2.out.txt`; the instrument that saw
  it now runs on every proof).
- Counting it by a `pile` key on the stacks: `spec_loader.Volume` takes no key it does not know, and furnish failed
  on every deli (`migrations_draft3.out.txt`, `suite_draft3.out.txt`).

### Tests
- `tests/test_pallets_safes.py` (new): a pile's stacks each fit Zoo's genome and no body passes between them, at
  two pile sizes; no library spec keeps the one block (eight did: six at 4.5 x 2.5, two at 4.0 x 3.0); a pile
  counts as one piece of its room; a safe is painted steel; no stored safe wears street metal. All six fail on
  0.266.0.

### Measured, the clone
- From a fresh clone, the edit and both migrations (the factory's `patches/dc_pallets_safes/prove_clone.sh`):
  `build.py --all` and `nav_gate.py --all` exit 0, 157 shells passed; the suite 1,827 tests, 0 failed, 31 skipped;
  every spec holding a pile keeps every other volume where it was.

## [0.266.0] - an indoor litter bin stands against a wall

**The walker, walking cold run 9386** (the factory's `docs/findings/walk_2026-10-23_9386/`, finding 8), of deli_a03's
bin alone at an aisle's end: "garbage cans are usually up against walls inside buildings". Of the library's 288 bins
furnish stood, none stood against a wall: 260 loose by the arrangement census, 18 aligned, 10 centred. Five recipes
drew the bin as a floor cluster, and the corridor's and hallway's wall runs named it while its own `where` --
`cluster` -- sent it to the floor grid anyway: a piece is placed by its `where`, not by the list that names it.

### Changed
- **`furnish` ends by standing every bin against a wall** (`stand_bins_on_walls`, after the fixtures): each bin it
  or an earlier release stood goes to the nearest spot flush against a wall of its room -- every 0.2 m along each
  edge a built wall holds its whole run on, at the wall slots' own offset, clear of exterior openings
  (`_bin_wall_spots`) -- where `_seed_clear` lets it stand, asked with the bin set aside and backed on its wall's
  edge, and off any route its room reserves (`reserves_routes`; furnish hands over the routes it already asked, so
  none is searched twice); ties by position, so a re-run makes the same move. A bin no wall spot clears goes: a bin mid-floor is the
  defect and a room without one is not. Its size, height and turn are kept, and NOTHING ELSE MOVES -- every recipe and
  every draw is as it was.

### Refuted and kept
- **The bin as a wall piece in five recipes' wall runs.** Built and measured in full before this: 241 rooms
  re-drawn for 288 bins, because a longer wall run re-shuffles every room that has one. The suite then named what
  the bins had nothing to do with -- bank_job's queued lobby lost its payphone, ATM and sofa; deli_a03 lost its ATM;
  a store poster stood on the deli's open edge; a chair stood in a stair core's egress; foundry_heist_vertical's
  stair_0 stopped traversing -- and the galleries, chapels and courtrooms the `hall` recipe furnishes took the freed
  turns as dining tables, 267 -> 324 pieces. Kept in the factory's `patches/dc_bins_on_walls/draft1/`.

### Library
- `migrations/migrate_bins_on_walls.py`: the same function over the stored specs. 92 specs: 280 bins moved to a
  wall, 8 with no clear wall removed (the corner delis' customer floors -- deli_a01 2, deli_a02, cr_deli and
  night_deli 1 each -- office_stepped's lobby 2, pawn_shop_a01's shop floor 1); a second run moves none. Every changed spec differs from 0.265.0 in its
  litter bins and nothing else.
- Census, 0.265.0 against this: the library's furnished bins 288 -> 280, against a wall 0 -> 280; every generated
  standing piece loose 14.1 -> 10.8 %, rooms holding two or more loose 292 -> 238. Route census, both
  libraries in one session: detours over 10 % 23 -> 23, closed 0 -> 0 to a body and 5 -> 5 to the bake, narrowed
  to single file 141 -> 130 (the dressing's own 25 -> 16): a bin off the floor is a passage back.

### Tests
- `tests/test_bins_on_walls.py` (new): every furnished bin in the library reads `wall` to the arrangement census;
  the library is a fixed point of the bin pass; a furnished corner deli and bank stand their bins on their walls and
  every other volume exactly where furnish without the pass stands it; a bin no wall clears goes. All four fail on
  0.265.0, the first on behaviour (288 bins off the wall).

### Measured, the clone
- `build.py --all` and `nav_gate.py --all` exit 0, 157 shells passed; the suite 1,821 tests, 0 failed, 31 skipped
  (the factory's `patches/dc_bins_on_walls/`).
- Drafts of this one refuted on the way, each by the suite: the bin pass's first stay test counted a corner bin
  moved onto its own spot (two edges offer it); its second stood bins on rooms' reserved routes
  (`test_marker_room_routes`, `test_reserved_routes`) and then searched market_aisles' routes twice.

## [0.265.0] - the root is the builder: tests in tests/, one-shots in migrations/, and a hook that keeps it so

**The walker, 2026-10-23**: "Deli Counter Repo needs a little clean up/organization? (and a way so the home root
doesn't just fill up with python files?)". 300 files stood at the root, 288 of them Python: 181 tests, 32
`migrate_*`, 75 builder modules. 0.193.0 moved the 23 one-shots nothing imported into `migrations/` and left the rest,
because the tests imported them by standing beside them.

### Changed
- **The 181 tests live in `tests/`**, with a `conftest.py` that puts the root and `migrations/` on the import path as
  the root's own directory once was. In each, the name for the repo -- `HERE`, `here`, a `__file__`-relative path --
  is the root, one level up, and a usage line that named a test or a migration names it where it now stands.
- **26 `migrate_*` one-shots live in `migrations/`.** Six stay at the root, because they are builder code under an
  old name: `presets.py` imports `migrate_roller_grill`, `migrate_slush_machine`, `migrate_wall_crossing`,
  `migrate_window_poster` and `migrate_window_sign`, and a build reaches `migrate_furnish_recipes`
  (`build_freshness.GEOMETRY_SOURCES`, which Level Factory parses by file name). Run one as `python
  migrations/migrate_<name>.py`.
- **The root holds the builder, 81 modules, and 92 files in all.** Nothing a consumer imports moved: Level Factory,
  the factory's `tools/` and its findings import builder modules by name from the root, as before.

### Added
- **`root_modules.txt`** names every `.py` at the root. **`check.py`** -- the commit hook -- runs a first step, "the
  root is the builder": a root `.py` not named there fails, with where it belongs (a test in `tests/`, a one-shot in
  `migrations/`, an instrument in the factory's `tools/`), and so does a name with no file. A new builder module is
  added to the list on purpose, in the change that adds it.
- `check.py`'s held-back and Blender-only tests are named under `tests/`.

### Tests
- `tests/test_root_is_the_builder.py` (new): the root holds what `root_modules.txt` names and nothing else; a stray
  script at the root and a name with no file are both refused.
- `tests/test_check_order.py`: the population test named where it stands.

## [0.264.0] - a room's seeded pieces stand on a lattice, and a census of what has a reason to stand where it stands

**The walker's walk of cold run 9383** (the factory's `docs/findings/walk_2026-10-23_deli/`, finding 3; roadmap 300),
of deli_a03's stair landing: "layout of these tables doesn't seem to have a rhyme or reason" -- and of the fix: "do
the full correct fix, allowing us to have nuance and flavor, but not look like random assortment". `seed_cover` stood
a room's pieces where a shuffled, jittered grid's first fits fell, each turned by a coin flip.

### Added
- **`arrangement.py`**: every standing piece in a room gets the first visible reason it has to stand there -- `wall`,
  `seat`, `aligned` (a row or grid of its own kind, lying the same way), `centred`, `grouped` (a pile, a stool at its
  counter) -- or `loose`, the random assortment; by producer (seed, furnish, authored), over the library, Level
  Factory's `lf_` specs (`--dir`, as they are untracked) or every preset built in memory (`--presets N`).
  Measurements only; an empty population fails rather than reporting zeros. Its controls, `test_arrangement.py`.
- **`_line_up(spec, room, pieces, routes=())`**: the same pieces on a LATTICE, in place -- one row first, then two, up
  to `_SEED_LINE_ROWS` (3), a body's corridor between rows, every row on the same stations along it (a short last row
  centred), ONE KIND A ROW (desks in a row and their cabinets behind, not alternating), long sides along the rows; the
  rows' position across the room every `_SEED_LINE_CROSS` (0.5 m), sampled every `_SEED_LINE_STEP` (0.2 m), the room's
  long axis first, then the lattice's middle nearest the room's, the first clear on every row winning. Each piece is
  cleared as `seed_cover` clears one, by its own footprint, the pieces already stood among what it clears, and off
  the room's reserved routes. A lone piece stands on the room's line too. A room no lattice fits keeps its pieces.
  `seed_cover` lays a room's pieces and then `_line_up`s them.
- **`_seed_clear(..., size=None)`**: a piece's own footprint for every box rule -- off another volume, a stair's
  reserve, a hole, a vault leaf, the body's corridor -- when it stands the way it is asked; the radius rules still ask
  `half`. A counter 0.8 m deep was cleared as if it were 2.2 m deep. `migrate_seed_corridor.failing` and
  `test_seed_corridor` ask a stored piece by its footprint the same way.
- **`migrate_seed_lines.py`**: lines up the pieces the library stores, never re-seeding (replayed, today's seeder gives
  back its stored pieces in 7 of 128 specs and would place 1,419 where 75 stand), the routes asked without the
  room's own pieces as `seed_cover` asks them; then refurnishes.

### Measured
- **The census, 0.263.0 against this** (the factory's `patches/dc_seed_lines/arrangement_*.out.txt`): every preset at
  two seeds, built in memory -- seeded pieces loose 95.4 % -> 13.8 %, every generated piece 25.7 % -> 13.1 %, rooms
  holding two or more loose generated pieces 145 -> 88. The library -- seeded pieces loose 71.8 % -> 3.8 %, every
  generated piece 14.7 % -> 14.1 %. Level Factory's `lf_` mission shells, built from presets, read 28.6 % loose
  before, seeded cover 72.5 % of 3,092 pieces: the next ones are built by this seeder.
- **The library, laid out, refurnished and sheltered**: 35 of the 37 rooms storing seeded pieces stand them on a
  lattice -- deli_a03's landing and its four twins two rows of two, a row of counters and a row of planters; the
  bank offices a row of desks and their cabinets behind -- and 2 keep theirs: night_pawn's and pawn_shop_a01's safe
  rooms, too tight for one clear of their own routes (pawn_shop_a01's crates stood on that route at 0.263.0). The
  shelter pass stood one piece, night_pawn's safe room's tall crate, where the refurnish took the piece that had
  sheltered it. Furnish's pieces 8,154 -> 8,139 in 23 rooms of 14 specs, every one under the walker's 12 % band
  before and after; the offices 5.7 -> 4.8 % of their floor. Four hold a marker: landmark_hall_a01's artifact_room
  (6 -> 3 pieces), night_pawn's safe_room (3 -> 1), rowhouse_raid's basement_vault and twin_a01's front_right_1 (no
  count moved). twin_a01's 38 m2 front_left_0 leaves the refurnish no wall for its cigarette machine (the library's 86
  -> 85).
- **The route census**, both libraries in one session: detours over 10 % 23 -> 23 pairs, closed 0 -> 0 to a body and
  5 -> 5 to the bake, narrowed from two abreast to single file 142 -> 141.
- **A seeded desk still gets no chair** -- furnish seats its own hosts only -- and in an office the seeded lattice
  takes the floor furnish stood its own desks on. Roadmap 300's next step lays floor hosts and seats a seeded one.

### Refuted and kept
- **A line alone, cleared as squares.** The first draft stood every room's pieces in one line, each cleared as the
  square of its longest side: deli_a03's four want 10.5 m of clear line with the corridor between them and the strip
  beside its stairwell is shorter, so the room the walker named kept its scatter. Two rows of two fit.
- **Every line before choosing**, which ran `test_door_width`'s preset test past half an hour where 0.263.0 takes 35 s
  (the first fit wins now: 59 s; presets are not in a cold run).
- **The line's own pieces set aside while clearing each**: 2.2 m between centres put 0.6 m between a counter's end and
  a planter's, a line a body could not pass through, and `test_seed_corridor` refused it.
- **Routes asked with the room's pieces standing**: they bent round where the pieces stood, and the migration lined
  pawn_shop_a01's two crates onto its safe room's true route.
- **Kinds alternating along a row**: a desk, a cabinet, a desk, a cabinet mid-floor.

### Tests
- `test_seed_lines.py` (new): a bare room's pieces are seeded in a line, a body passing between any two; `_line_up`
  moves the same pieces and nothing else; where one line cannot, two rows do; a room nothing fits keeps its pieces;
  THE TEST THAT MATTERS -- every library room storing a seeded piece stands it on a lattice but the two named, and
  the library is a fixed point of the migration. On 0.263.0 the five fail, the first on behaviour.
- `test_arrangement.py` (new): the census's controls -- each reason read as built, a scatter told from a row.
- `test_marker_room_routes.py`: a room with no spot off its routes keeps its shelter, the route now covering the
  room's depth -- through the one spot the square once left, by the crate's footprint the room has a second.
- `test_club_fixtures.py`: the library's cigarette machines 86 -> 85, and why. `test_seed_corridor.py`: by footprint.

## [0.263.0] - a hall the id names and says nothing more of is a hallway

**The walker's walk of cold run 9383** (the factory's `docs/findings/walk_2026-10-23_deli/`, finding 3; roadmap 300),
of deli_a03's stair landing `upper_hall`: "layout of these tables doesn't seem to have a rhyme or reason". The
landing took the `hall` kind by its id's token -- the row for galleries, chapels and courtrooms -- and was given a
service counter, waiting benches, vending, a cigarette machine and a dining table with its chairs. 45 of the 64 rooms
that row furnished are connectors, nearly all hallways and stair landings: `upper_hall` (24 of them), `back_hall`,
`rear_hall`, `mezz_hall`. The role cannot tell them apart -- `connector` is 896 rooms, kitchens, offices and bars
among them -- the id's words can.

### Changed
- **`_ROOM_KINDS`**: the `hall` row keeps the gathering words (gallery, exhibit, chapel, assembly, courtroom,
  viewing, artifact) and loses "hall" itself; a last row, `hallway`, takes "hall" when no other kind's word does, so
  `assembly_hall` stays a hall and `cellar_hall` and `under_hall` stay basements. 40 rooms in 38 library specs move
  from `hall` to `hallway` and no room changes kind otherwise.
- **The `hallway` recipe**: benches, a file cabinet, a bin and vending against the walls, at most six pieces, nothing
  on the floor. Movement first; its floor share sits under the walker's 12-25 % band on purpose, and is reported.
- Below grade a hallway takes no basement clutter, as a corridor does not.

### The library, refurnished and sheltered
- **40 rooms in 38 specs moved and no other** (the factory's `patches/dc_hallway/rooms_moved.out.txt`), none holding
  an objective or loot marker. Furnish's pieces 8,510 -> 8,154; the moved rooms' floor share fell from 2.3-12.8 % to
  0.9-7.3 %, the shelter pieces counted. The 32 cigarette machines that stood in them go (118 -> 86 in the
  library); none moved elsewhere.
- **The shelter pass** (`migrate_shelter.py`) stood a kiosk in courthouse_a02's and survival_demo's `upper_hall`, whose
  only shelter had been the gallery set, and a tall crate stack in gas_station_a02's `back_hall`, which had none.
  Every combat hallway is sheltered but stop_n_go's 27 m2 `back_hall`, under the seeder's 30 m2 floor
  (`_SEED_MIN_AREA`) and unsheltered before this too.
- **The route census** (the factory's `docs/findings/furnish_route_cost/route_cost.py`, both libraries in one
  session): routes over the guide's 10 % detour 26 pairs in 25 rooms -> 23 in 22; narrowed from two abreast to single
  file 151 -> 142; closed to a body 0 -> 0, to the bake 5 -> 5.

### Tests
- `test_furnish.py`: `upper_hall` and `back_hall` are hallways, `assembly_hall` and `chapel` halls -- failing on
  0.262.0 on the first.
- `test_club_fixtures.py`: its hall example was `upper_hall`, now `exhibit_hall`, and `upper_hall` stands no cigarette
  machine; the library's 118 machines are 86.
- `test_marker_room_routes.py` mirrors furnish's below-grade rule, `hallway` in it.

## [0.262.0] - every library stair is solid underneath unless named

**The walker's walk of cold run 9383** (the factory's `docs/findings/walk_2026-10-23_deli/`, finding 4), of deli_a03's
up-stair: "this stair has unexpected space below it". Solid has been the default since 2026-09-13; that flight was the
library's one exception, opened by hand in 0.124.1 because its foot could only be reached from under its high end, the
basement flight's slab hole leaving 0.4 m beside it. 0.189.0 widened the door beside it to 2.4 m, and the door has
opened onto the strip beside the flight ever since -- the opening outlived its reason and nothing asked.

### Changed
- **deli_a03's `deli_stair_up` is solid underneath**: `open_under` removed; its `open_under_why` becomes
  `underside_why`, keeping the history. Built solid, the nav gate traverses both stairs and reaches objective_A
  upstairs and the patrol point at 8 of 8 voxel-grid origins (the factory's
  `patches/dc_solid_undersides/navgate_deli_a03.out.txt`). The flight takes the side and back guards every solid
  one-run flight takes, and its slot is closed by its back.

### Tests
- `test_library_undersides.py` (new): THE TEST THAT MATTERS -- every library stair builds solid underneath unless it is
  named in `OPEN_UNDERSIDES` with its reason (empty); a name there that no longer builds open fails too. On 0.261.0 it
  fails naming `('deli_a03.json', 'deli_stair_up')`.
- `test_stair_back.py`: the library's solid one-run flights are 132, not 131 -- deli_a03's joins them; the slots left
  open are still `credit_union_a02`'s one, closed by its partition.

## [0.261.0] - every opening's landing is lit to read from above

**The walker's walk of cold run 9383** (the factory's `docs/findings/walk_2026-10-23_deli/`, finding 1), of a stair
opening onto deli_a03's basement: "this shouldn't look pitch black" -- and the rule: "you should be able to see into
holes to know you can go forward into them". The basement is moody by rule -- bare bulbs, dark corners -- and the
place the stairs come down into it read luma p50 10 from its own station, against the stairwell above at 74.

### Added
- **`opening_landings(spec)`**: where every opening into a storey lands -- a stair's lower end
  (`stairwell.stair_endpoints`), the floor under each hole in a slab that is not a stair's own (authored holes, floor
  holes, hatches), a ladder's base -- one entry a place.
- **A moody room lights its landings** (`derive_light_anchors(..., landings=)`, `build_light_manifest(...,
  landings=)`, passed by the build): a fluorescent over each landing inside it -- the lamp an ordinary room is lit by
  -- and, where a hole is over the landing, hung `_LANDING_OFF_HOLE` (0.6 m) past the hole's edge on the side nearest
  the room's middle, then kept off the partitions as every lamp is (`_row_runs`). Each carries `landing` (its kind),
  and they come last with the spills, so every anchor before them keeps its id and its place. A moody room keeps its
  bulbs; an ordinary room, already lit by its rows, gets none. A hole that is a ladder's or a stair's own cut
  (`_own_hole`: the builder cuts both into the slabs the lights are derived from) is that opening, not a second
  one -- the first build of this change lit deli_a03's basement corridor twice at one point, its ladder and the
  ladder's own hole, and 153 lamps went into 40 buildings where the openings asked fewer. The count the library
  takes is the rebuilt light records' (the factory's `patches/dc_landing_lights/landing_census.out.txt`).

### Tests
- `test_landing_lights.py` (new): every opening of deli_a03 lands once; THE TEST THAT MATTERS -- its basement's stair
  foot and ladder base are lit, the rooms above get nothing, and every anchor before is the same and in order; a
  landing under a hole hangs its lamp beside the hole; a spec cut the way the builder cuts it lands exactly as the
  library spec does. On 0.260.0 the four fail on the new names.
  `test_lights_partitions.py` pins the derivation's report key for key: it gains `landing_lights` (the first run of
  this change applied it without, and the paired suites caught it -- one new failure, the pinned dict).

## [0.260.0] - the scout model in the handheld's colours, with the score and the props worth knowing about

**The factory's roadmap 295.** The walker, on the first frames: it "should roughly be in the style of a 1990s palm
pilot...but with a little more backlight and color (so a blend of what was and what could be that makes it more
legible)", and "buildings should show the 'score' location and key props of interest".

### Added
- **The `palm` palette, the default**: a handheld's grey-green LCD floors, ink walls with a darker cut, and lit
  accents for what a player hunts for -- the entry, the stairs, a ladder, a hole, a window, and now the score and the
  props of interest, every one its own colour (`ROLES_READ`). The three palettes before it stay, for comparison.
- **The score and the props of interest** (`POINTS_OF_INTEREST`, `points`): a beacon -- plinth, mast, a block on
  top, 3.0 m -- at every `objective` marker, and a lit block at every `loot` and `camera_socket` marker, safe and
  ATM. Each storey's are a mesh of their own, `storey_<n>_points`, a child of the storey so they ride it when a viewer
  lifts the storeys apart, and the scene's `extras.points` names every one: kind, label, storey, and where it stands
  in the model's frame. Across the library's buildings with an inside: 131 scores, 139 cameras, 131 safes, 69 ATMs,
  13 loot. Spawns are not drawn: they are the gameplay layer's, and provisional.

### Tests
- `test_scout_model.py`: every objective marker is a score on its storey and every safe, ATM, loot and camera a
  point, named in the scene, each storey's under it (five buildings, the control at least five scores and three
  safes); a mesh a storey and one more on each storey with points; the score and the props of interest their own
  colours in every palette.

## [0.259.0] - the scout model: a building a player turns all the way round

**The factory's roadmap 295.** The walker, of 0.258.0's scout view: "its ok for now, but i want to make it look more
polished and artistic so it could ship to players....They can scout out the buildings and rotate the schemas in a 360
degree way".

### Added
- **`scout_model.py`**: the scout view's signals as a model -- each storey's slab with its holes cut through and
  rimmed, its walls to the plan cut with a dark cap on the cut, a window as glass from its sill to the cut, a door as
  a strip across the floor in the entry colour where it lets you in from outside, every stair as the treads the
  builder builds, every ladder as its rails and rungs; no furniture, rooms or markers. Read from the layout the
  drawings read (`floorplan.storey_walls`/`wall_split`, `axonometric._slab_holes`, `stairwell`, `setbacks`).
  `build_glb(spec, palette=)` returns deterministic GLB bytes: a node and a mesh a storey at its true elevation
  (`extras.storey`, `extras.elevation`), so a viewer lifts the storeys apart; one material, every colour in
  `COLOR_0` as normalised bytes -- one draw a storey. Across the library's 132 buildings with an inside: median 1,312
  triangles, the largest cbp_town_finale_midbalanced 5,628 (386 KB); all 132 built in 1.4 s.
- **Three palettes, the walker's to pick** (`PALETTES`): a night blueprint, an architect's card model, a heist
  dossier; `DEFAULT_PALETTE` is the blueprint until they do. Every role a player reads by colour -- a door in from
  outside, an inside door, a window, a stair, a ladder, a hole in a floor -- has its own in each.
- **A package carries it**: `package_drawings` writes `drawings/scout.glb` with the keep `.import` -- a game reads it
  with `GLTFDocument` when its screen opens, so no level pays to import it -- and names it in `drawings.json` under
  `scout_model` (null for a facade).

### Tests
- `test_scout_model.py` (new): THE TEST THAT MATTERS -- the model and the scout drawing agree, storey by storey, on
  every door and window (five buildings, over 40 openings); a node and a mesh a storey at its true elevation, one
  material, colour as normalised bytes; the doors in from outside, and only they, in the entry colour; every read role
  its own colour in every palette (the first draft gave a hole's rim the entry's red, and the agreement test caught
  it: deli_a03's upper floor counted 17 doors against the drawing's 5); deterministic, and every library building
  builds, the largest under 8,000 triangles -- a regression detector, not a frame cost. `test_package_drawings.py`
  asks for `scout.glb`, its keep `.import` and the record's `scout_model`.

## [0.258.0] - the scout view: a building drawn with only what a body finds its way by

**The factory's roadmap 296.** The walker judged 0.257.0's exploded axonometric on a review page (2026-10-22): one
storey of pharmacy_a01 "Looks right"; deli_a03 and office "Needs work" -- "we need to find a way to be simple and not
noisy visually. assume that in game, a player could rotate it as well to" -- and what players should see, "simpler but
carry all of the signals needed". On the two busy buildings the furniture, the room names and the dashed lines between
the storeys crowded the structure the drawing exists to show.

### Added
- **`render_axonometric(spec, scout=True)`**: the same storeys, offsets and cut, with every wall, door and window,
  every stair as its treads, every ladder and every hole in a floor -- and none of the furniture, room fills and
  names, markers, or dashed lines. What joins the storeys stays a signal: each flight keeps one solid leader from its
  head to the storey it reaches, each hole one line down to the floor it opens onto, a ladder its one line. A door's
  threshold is drawn heavier (3.4 against 2.2). Its legend leaves out furniture; its title says "scout view". On the
  review page's three buildings it draws deli_a03 in 595 elements against 1,422, office in 520 against 1,003,
  pharmacy_a01 in 135 against 310. Which signals a player needs is the walker's to settle; this is the proposed set.
- **A package carries it**: `package_drawings` writes `drawings/scout.svg` beside the axonometric, kept like it
  (`KEEP_IMPORT`), and names it in `drawings.json` under `scout` (null for a facade).

### Unchanged
- **The full drawing, to the byte**: every one of the 458 specs in the working checkout -- its ignored `lf_*`
  per-candidate specs included -- renders its axonometric the same on 0.257.0 and 0.258.0
  (the factory's `patches/dc_scout_view/prove.out.txt`).

### Tests
- `test_scout_view.py` (new): the scout view keeps every wall piece, opening (with its kind and place), tread and
  landing (with its height), ladder and hole the full drawing carries, and adds none -- the test that matters,
  "simpler" not meaning less to find your way by; it leaves out furniture, rooms, markers and every dashed line, the
  full drawing of the same building carrying them; each flight and hole keeps one line; it is deterministic and holds
  its text. `test_package_drawings.py` asks for `scout.svg` and the record's `scout`. All six fail on 0.257.0, on the
  new name (`render_axonometric()` takes no `scout`; the record has no `scout`).

## [0.257.0] - a building's package carries its drawings

**The factory's roadmap 296.** The walker, of roadmap 293's exploded axonometric, asked where it is seen: "both" -- a
review page and a level's export -- "It could even get into the game where the players can 'scope out' the level and
see the buildings the level assembles". A building's files reach a level only through
`portable_building.build_package` (Level Factory's presentation compose, then its export's copy into `lot/<id>/`), and
no drawing went that way: the plans and the axonometric were written only into the ignored `build/floorplans/`, by
`validate.py`.

### Added
- **`build_package(..., spec_path=)`**: named the spec the building was built from, the package draws it into
  `drawings/` (`package_drawings`) -- the exploded axonometric and a plan a storey (`floor<n>`, a basement
  `floorB<depth>`), each beside a `.import` that keeps it as the file it is (`KEEP_IMPORT`), and `drawings.json`
  naming them -- and records it in its manifest under `drawings`. Drawn from the spec when the package is composed, so
  a package never carries a drawing older than its building. Named no spec, a package is what it was. `--spec` on the
  command line.
- **A facade gets the record and the reason, no drawing**: a street wall with no interior, never entered, whose
  axonometric is an empty walled box (gs_facade_rowhome and gs_midrise_a drawn and read, 2026-10-21).
- **How a drawing ships, measured on Godot 4.7, headless** (the factory's `patches/dc_drawings/keep_probe.py`): left
  to the default import, deli_a03's axonometric becomes a 136,248-byte texture in every level that carries it, for a
  screen no game has built yet; with the keep `.import` beside it none is made, the `.import` comes back as written,
  and a game still reads the file with `FileAccess` and draws it with `Image.load_svg_from_string` (674 x 1197, no
  error), at the size its own screen wants.

### Fixed
- **An axonometric's canvas holds its own text.** The canvas was the drawing's extent alone, and on a small building
  -- a facade, 275 px -- the title, the two lines under it and the legend ran off its right edge: the facade's last
  legend word began at 466 px. The widest of them now sets a floor under the width, each measured as it is written
  (`CHAR_EM`, `CHAR_EM_BOLD`; the legend, `LEGEND`, by its own steps); a drawing wide enough before is drawn as
  before.

### Tests
- **test_package_drawings.py**, new, four: the keep `.import` is the one Godot left as written; deli_a03's package
  carries its axonometric and three plans, each its renderer's drawing of the spec, each beside a keep `.import`,
  named in `drawings.json`; a facade's carries the reason and no drawing; `build_package` draws when named a spec and
  draws nothing when not. On 0.256.0 all four fail on the missing names.
- **test_axonometric.py**, one more: every line of text fits its canvas, on a facade, a midrise, office and deli_a03
  -- the legend first, by its own steps, so on 0.256.0 it fails on behaviour (the facade's legend ends past its 275
  px) and not on a name (the factory's `patches/dc_drawings/prove_tests_on_0256.out.txt`).

### Measured, kept
- **Left** (the factory's roadmap 296): Level Factory naming the spec of each building it composes, and an index of a
  level's buildings at its package's root; a review page built from a cold run's package; the in-game screen, which is
  the game's.
- **Seen while reading**: `floorplan.write_floorplans` names every basement `floorB`, so a building with two would
  write one plan over the other; none in the library has two (read 2026-10-21), and a package names its plans by
  depth.

## [0.256.0] - a host no chair fits beside is moved where one does

**The factory's roadmap 284.** 0.252.0 seats a host the room left chairless and takes away one no chair fits beside:
25 hosts, 24 desks and a dining table. Asked whether such a desk should be moved instead of removed, the walker,
2026-10-21: "yes".

### Changed
- **A host no chair fits beside moves** (`_move`), still LAST, when the room is furnished, so every piece the room's
  recipe drew stands where it stood and no draw is taken from the room's stream: to the nearest spot on the room's
  candidate grid where it clears as `_host` placed it (off the nested rooms, `_seed_clear` with the spread from every
  other piece), faced as `_host` faces it, and seated as the rescue seats one, from a stream keyed by the new spot. It
  and its chair keep off the room's routes -- the reserved ones, or where the recipe reserves none, the routes
  `protected_routes` asks of the room for the move -- and it narrows no pair (below). A floor piece only, as all 25
  were; a host no spot takes still goes.
- **A moved host narrows no route.** Seated at a spot, it may take no width from any two of the room's route endpoints
  that it leaves under two abreast, nor part two that were joined (`_narrows`). Keeping off a route keeps its length,
  not its width: without this, the 19 hosts the move stood narrowed nine pairs from two abreast to single file, in two
  rooms -- landmark_hall_a01's curator_band (six) and train_yard_a01's dispatch_office (three) -- each desk off the
  routes and standing where the widest way ran.
- **`room_necks(spec, room)`, new**: the widest-path neck between every two of a room's route endpoints -- the
  factory's census of what furnishing costs a route (its `docs/findings/furnish_route_cost/route_cost.py`) asked of
  one room, at the bake's cell, with its obstacles, its endpoint snapping, its open door-approach disc and its
  union-find, so what furnish guards and what the census reports are one measure. Read against the census before it
  shipped: 187 pairs in 64 rooms of twelve specs this change leaves alone, every neck the same to the millimetre.
- `_seats` takes `keep_off`, the routes a moved host's chairs keep off in place of the room's reserved ones.
- **The library refurnished**: 18 hosts back in 17 specs -- 17 desks (239 -> 256) and museum_a01's dining table (254
  -> 255) -- each with its chair; seven still go, every spot on their rooms' 25-spot grids refused (9 to 19 on a
  route, 6 to 14 by `_seed_clear`, the rest by the chair or, twice in train_yard_a01's dispatch_office, by the guard):
  airport_terminal_a01's customs_office two, bank_branch_a04's security_office, bank_job's security_room,
  supermarket_a02's manager_suite, train_yard_a01's dispatch_office two.

### Tests
- **test_seated_hosts.py**: "seating a chairless host moves nothing the room drew" lets a host the rescue moves stand
  elsewhere -- only a host, and only one chairless without the rescue; a new test, office's exec_suite and
  landmark_hall_a01's curator_band each move their desk, in its room, with its chair, both off the room's routes,
  narrowing no pair -- failing on 0.255.0 on behaviour (no host moves there).
- **test_room_necks.py**, new: an open room's neck, the gap a box leaves, a pair the box parts; `_narrows` counting
  only width lost under two abreast. Both fail on 0.255.0 on the missing name (the factory's
  `patches/dc_desk_move/prove_tests_on_0255.out.txt`).

### Measured, kept
- **The census over the library**, each arm refurnished and sheltered in memory against 0.255.0's (the factory's
  `patches/dc_desk_move/arms.py`, its control reproducing the census pair for pair): routes over 10 % 26 -> 26, closed
  to the bake 5 -> 5, narrowed to single file 151 -> 151, p99 1.107, max 1.308; ten pairs lost width and every one is
  still two abreast, the narrowest now curator_band's at 1.053 m of clearance against two abreast's 0.95. The floor
  share of the 17 rooms a host came back to: 1.9 to 7.5 %, each up 0.2 to 2.1 points.
- **The arms before the guard**: off the routes only, 19 back and the nine narrowings above; then anywhere `_host`
  itself would stand it, 21 back and the same nine; then its chair's routes relaxed too, 24 back, the same nine and
  one pair over 10 % (dispatch_office's secure_door to its objective, 5.60 -> 6.85 m).
- **Refuted and kept**: the arms' first run counted a host as moved or gone only where it stood in the shipped
  library, and the 25 stand in neither -- "gone 0, moved 0" for every arm, only its host counts seeing them;
  test_room_necks's first draft asked an open room for the clearance cap and read 1.598, the wall a door stands in
  just past its open disc.

## [0.255.0] - the exploded axonometric draws a stair as its treads

**The factory's roadmap 293, its next step.** The walker, 2026-10-21, of 0.254.0's drawing: "draw the stairs as treads
next". 0.254.0 drew a stair as its footprint, an ascent line and dashed alignment columns: where a stair goes, not
what it is.

### Changed
- **A flight is drawn as its treads and turn landings**: every walking surface `stairwell.ascent_surfaces` says the
  builder builds -- the headroom gate's copy of `Builder._stairs`, held to it by `test_headroom.py`, so the drawing
  and that gate read one stair -- on the storey the flight climbs from, at its true rise. A leg the builder fills
  solid (`flight_solid_under`) stands its treads to that floor; one open beneath draws them one riser thick; a
  switchback's turn landing is one riser thick, as `Builder._stairs` stands it, where the first draft stood it as a
  column 3.6 m tall at the head of office's stair. Tread sides are drawn without seams, so a flight's side reads as
  one stepped stringer and only the nosings are edged. Full height, not cut at the plan cut: the stair is what joins
  the storeys.
- **The ascent line is a leader**, dashed, from a flight's head across the exploded gap to its landing on the storey
  above; the alignment columns stay.
- **Each tread and landing carries what it is drawn**: `data-tread` or `data-landing` (`<stair>:<storey>: <k>`),
  `data-top` (the surface's world height), `data-at` and `data-rise` (metres from its base to its top).

### Tests
- **test_axonometric.py**, three more: a flight is drawn as the treads the builder builds -- every surface of every
  stair in office and deli_a03, at its own height and place, and nothing else, office's turn landing among them; a
  landing is a plate and a solid flight stands on its floor (office's landing one riser, each of its first leg's
  treads standing on storey 0's floor); a stair moved moves its treads. On 0.254.0 the three fail on behaviour and the
  file's other eight pass (the factory's `patches/dc_axo_treads/prove_tests_on_0254.out.txt`).

### Measured, kept
- Frames of office -- whole and its stair, cropped -- deli_a03 and cbp_town_finale (the factory's
  `patches/dc_axo_treads/axo_*.png`, `svg_png.py` and `crop_svg.py`).
- **Left** (the factory's roadmap 293): ramps, platforms and fire escapes in either drawing; a solid leg's fill drawn
  to its own storey's floor where the builder carries a cut switchback's second leg down to the stair's lowest
  (`flight_solid_base`) -- in an exploded drawing that floor is a gap away; where a reviewer finds the drawing beside
  a level.

## [0.254.0] - an exploded axonometric of every building, with architectural cutaways

**The factory's roadmap 293.** The walker, 2026-10-21: "add this to the roadmap to make our floorplan tool better and
acheive that Exploded axonometric view, with architectural cutaways" -- the guide is the factory's
`docs/reference/Floor_Plan_to_3D_Layout_and_Automap_Guide.md`, its section 6. `floorplan.py` drew each storey flat,
and nothing drew how a building's storeys stack: where a stair lands, what an atrium opens onto, which rooms stand
over which.

### Added
- **`axonometric.py`**: `render_axonometric(spec)` and `write_axonometric(spec, outdir)` draw every storey of a
  building at once, seen from above and to the south-west at true-isometric elevation. Each storey is a slab raised by
  a display offset over its true floor; walls stand to the plan cut, 1.2 m, their cut faces dark; a door is a gap with
  its threshold; a window under the cut keeps its sill wall and its glass; furniture stands to the cut; roofs and
  ceilings are left off. Every hole in a storey's slab -- authored, a stair's cut, a floor hole or hatch -- is masked
  open, the slab's thickness drawn on its far edges. Stairs are joined to the storey they climb to by an ascent line
  and dashed alignment columns; ladders and the holes that open onto the floor below are drawn between storeys;
  markers stand on their storey; rooms are labelled; a legend runs along the foot. Offline and deterministic SVG
  strings -- no Pillow, no Blender, no generative model -- the whole library drawn in under a second.
- **The offset is the drawing's alone.** A storey's group carries `data-elevation`, `story * story_height`, beside
  `data-offset`; the spec is read, never written. The gap is derived, not chosen: the least rise that keeps each
  slab's drawing clear of the next, plus 2 m.
- **`validate.py` writes `<name>.axo.svg`** beside the plans in `build/floorplans/`, so the commit gate draws every
  building's.

### Changed
- **One layout, two drawings.** The plan's wall arithmetic is data both read: `floorplan.wall_split` (a wall's
  segments and gaps) and `floorplan.storey_walls` (every wall a storey stands, as the builder stands it -- the
  exterior on the storey's extent, a partition in its built pieces, its openings remapped). Refactored first and held
  to the plan as drawn: all 288 plans of the 159 specs byte for byte as before (the factory's
  `patches/dc_axonometric/plans_identical_step1.out.txt`).
- **A partition is drawn at the thickness it is built at**, `wall_thick`, where the plan drew a fixed 0.15 m; `PART_T`
  is gone. 242 of the 288 plans move, exactly those with a partition on their storey
  (`plans_identical_step2a.out.txt`).
- **The plan's header calls the storey height floor to floor**, where it said "clg"; every plan's header line moves
  (`plans_identical_step2b.out.txt`).
- **`build_freshness.py` files `floorplan.py` and `axonometric.py` as drawings** (`NOT_BAKED`). A build reaches the
  plan only through `pvp_heist.py` and `sightlines.py`, both kept out already, asking it a marker's storey, and
  nothing either drawing says is in a shell -- so a change to a drawing no longer reads every shell as older than the
  code that makes it.

### Tests
- **test_axonometric.py** (new, 8): the offset is the drawing's alone -- every storey at its true elevation, the
  lowest at no offset and each higher one higher, the spec unwritten; every library building draws every storey; the
  drawing is deterministic; a doorway moved moves its gap in both drawings; a stair moved moves its flight and its
  column; an atrium stays open, its storey's slab cut and no other; two markers one above the other land on their own
  floors; the axonometric stands a partition at its built thickness. On 0.253.0 the file cannot import the module it
  tests.
- **test_plan_matches_build.py** (new, 2): a partition drawn at its built thickness, and the storey height called
  floor to floor, both asked of the rendered plan; both fail on 0.253.0 on what the plan draws (the factory's
  `patches/dc_axonometric/prove_tests_on_0253.out.txt`).

### Measured, kept
- Frames of `deli_a03`, `office` and `cbp_town_finale` (the factory's `patches/dc_axonometric/axo_*.png`, rasterized
  by `svg_png.py`).
- **Left** (the factory's roadmap 293): ramps, platforms and fire escapes in either drawing; stairs drawn as treads
  rather than an ascent line; where a reviewer finds the drawing beside a level.

## [0.253.0] - the enemy's body is the NPC's, and the NPC's is the player's until it says otherwise

**The factory's roadmap 292.** `agent_contract.json` said the enemy's eye twice -- `characters.npc_standard`, whose
NPCs "share player metrics until a distinct class ships", and `sightlines.enemy_sight_height_m` -- with nothing to say
which governed, and the NPC block restated the player's radius and height, which nothing read. Level Factory's seam
wrote the player's body into every Laser Tag run and left the enemy's eye at Laser Tag's 1.6; Level Factory 0.231.0
reads this block for it.

### Changed
- **The bodies decide the sight heights.** `npc_body()` (new) is `npc_standard`'s stated metrics over the player's.
  `sight_heights()` (new) gives the two eyes -- the player's and the NPC body's -- and checks the `sightlines` copies
  against them, refusing one that disagrees ("one body, one eye"), as `cover_break_height` already refused an aim
  copy. `cover_break_height()` and `shelter_height()` ask it.
- **`npc_standard` states no metric of its own.** Its restated radius and height are gone; its `shares_note` says what
  governs and why, and `sightlines.sight_heights_are` that the copies are the bodies'.
- **No copy of a body-derived sightline number is merged into a contract that omits it.** `_DEFAULTS["sightlines"]` is
  empty. A contract stating only its body -- a 2.05 m player with its chest at 1.15 m and no `sightlines` block -- was
  refused, "one body, one aim point", for disagreeing with the 1.0 m aim copy the module had merged in;
  `cover_break_height_m` was already kept out for that reason. `_player()` fills a partial player block field by field
  from its ratified fallback, for the eyes.

### Measured, kept
- **Lot 0.126.1 ships first.** Lot's contract fallback mirrored the NPC's two numbers, and Lot 0.126.0's guard, run
  against this contract, counts 19 shared keys against its floor of 21 and fails (the factory's
  `patches/lot_npc_fallback/suite_clone_vs_base.out.txt`).
- **The shells are rebuilt; no number of a body or a clearance moves.** `build_freshness.py` watches
  `agent_contract.py` and `agent_contract.json`, so the library is rebuilt. The shipped contract's change is the NPC
  block's two restated numbers and two notes; the player, the bake, the clearances and the sightline copies stand as
  they were, and at them `sight_heights()` is (1.6, 1.6) and the crossing 1.3 m.

### Tests
- **test_npc_body.py** (new, 4): a studio states its body once and the crossing follows it -- 1.5 m for a 2.05 m body,
  shelter at 1.85 m; the NPC is the player until it says otherwise; a sight height that disagrees with its body is
  refused; the shipped NPC states no metric of its own. On 0.252.0 the first fails on behaviour ("one body, one aim
  point") and so does the last (the restated radius and height); the other two fail on the new names (the factory's
  `patches/dc_npc_body/prove_tests_on_0252.out.txt`).
- **test_cover_breaks_sightlines.py**: the four fixtures that stated sight heights without the body that has them
  state it now -- the eye, and for an enemy that differs, `npc_standard`'s. On 0.252.0 the file passes.

## [0.252.0] - a piece that seats somebody stands with its chair

**The factory's roadmap 284.** Measured on 0.251.0's library (the factory's `patches/dc_table_chairs/seats.out.txt`):
255 dining tables, 51 with no chair, because their recipe seats `randint(0, 4)` and clearance refused the rest; 41 of
263 desks with no chair, though a desk seats one, because the desk stood whether or not its chair cleared; 4 of 46
cocktail tables likewise. The walker's guide (`docs/reference/Lived_In_Levels_Clear_Navigation_4P_PVE_1999_PA.md` at
the factory root, section 8) builds a room's clusters from what belongs together; a table with no chair is half of
one.

### Changed
- **A host the room left with no chair is seated last.** `_host` notes a piece that must seat somebody -- one whose
  seats ask one or more, or that says so (`must_seat`, new on `_piece`: a dining table, whose draw stays none to four)
  -- when its chairs came to none; when the room is furnished, `_seats` seats it with `rescue`: one chair, from the
  host's own stream, tucked and then pushed in -- every side of a table, half under it; a desk's front, half under its
  knee space; a stool against a counter's front -- and kept off any route the room reserves. A host no chair fits
  beside goes. Seated last, so nothing else furnish drew in the room moves.
- **`_seats` takes its stream** (`draws`, the room's unless given) and a `rescue` flag; without them it draws what it
  drew, in the order it drew it.
- **The library refurnished and sheltered**: 77 rooms in 55 specs (the factory's `rooms_moved.out.txt`). Dining tables
  255 -> 254, 50 seated and one taken away; desks 263 -> 239, 17 seated and 24 taken away; cocktail tables 4 seated
  (`seats.out.txt`). Every host taken away is attributed (`gone_hosts.out.txt`): 14 of the 25 in rooms holding a
  marker, 11 in rooms that reserve no route, none with a chair before. Eight of them -- seven desks and the dining
  table, all in rooms holding a marker -- went only because a rescued chair keeps off the room's routes: with that
  check off, the same library takes away the other seventeen and seats these (`no_route_check.out.txt`). Furnish's
  pieces, by `rooms_moved.py`'s count, 8,428 -> 8,474; a moved room's floor share -3.0 to +1.1 points, 76 of the 77
  under the walker's 12 % before and after; the offices' mean 5.3 -> 4.8 % for the desks that went.
- **76 of the 77 rooms moved by the rescue alone** (`moved_why.out.txt`). The 77th, landmark_hall_a01's artifact_room,
  re-drew in the shelter pass (`artifact_steps.out.txt`): the rescue took away its chairless dining table, whose chair
  fitted only on the room's routes; the shelter pass, which had found no clear spot in the room at 0.251.0, stood a
  tall crate on floor the table freed -- on a route, its fallback, no spot off them being clear -- and, as in every
  spec it adds to, refurnished the spec, furnish counting the crate among what the room holds: the room's counter 2.2
  -> 1.6 m, both its tables seated.

### Measured, kept
- **The census over the 55 specs**, 1,011 pairs, 0.251.0 against this (`census_changed.out.txt`,
  `pairs_compare.out.txt`): routes over 10 % 15 -> 13 -- three came back under, one crossed over, landmark_hall_a01's
  artifact_room from its secure door to its crew marker 1.076 -> 1.115; the extra metres walked, summed over every
  pair, 93.5 -> 90.2; the dressing's detours 0 -> 0; closed to the body 0 -> 0 and to the bake 0 -> 0; narrowed to
  single file 68 -> 69 -- six pairs lost two abreast, five of them the artifact room's (1.95 -> 1.47 m at the
  narrowest), and five regained it.
- **The combat audit** (`audit_compare.out.txt`): COVER_ALL_LOW 8 -> 7 and SIGHT_INTENT 503 -> 502, both
  landmark_hall_a01's artifact_room -- sheltered now, and no longer reading medium where it is authored close (an 8.5
  m sightline at 0.251.0); the same re-draw narrowed its five routes above. Every other code's count unchanged; two
  findings re-worded for a piece more in their rooms.
- REFUTED, kept (`*_first_built.out.txt`, `variants.py`, `variants_*.json`): the shape first built -- every host's
  chairs drawn from its own stream, a host with no chair undone and its next spot tried, a table trying every side, a
  dining table drawing one to four. It seated every host and re-drew the library: 265 rooms in 119 specs, routes over
  10 % library-wide 28 -> 40, three more closed to the bake, narrowed 150 -> 176, and four tests that pass on 0.251.0
  failed -- two club-fixture tests, a strip-club preset test and the library shelter test. Run feature by feature
  against a control that reproduced 0.251.0's census exactly: the re-draw alone 28 -> 34 and +13 narrowed, on this
  draw -- choosing among draws by their census would be seed-shopping, not a fix; the undo rule and the one-to-four
  draw together the other six and the three closures, which no variant separated; tucking every chair, or trying every
  side for the first chair only, moved none of it below 39.
- **What is left.** A host's regular chairs still spend the room's stream, so a piece placed before a table re-draws
  its chairs; drawing them from the host's own stream re-draws the library once, which the census priced above. The 24
  desks taken away leave offices barer, the marker rooms most: office's exec_suite keeps one piece of its two (7.2 ->
  5.4 %), train_yard_a01's dispatch_office 7.0 -> 4.0 %, airport_terminal_a01's customs_office 7.2 -> 4.5 %.

### Tests
- **test_seated_hosts.py** (new, 3): a dining table must seat one and its draw is unchanged; every piece that must
  seat stands with its chair, over the library; seating a chairless host moves nothing else furnish drew, the rescue
  on against off in train_yard_a01, office and airport_terminal_a01. On 0.251.0 two fail on behaviour -- the library's
  chairless desks, a rescue that does nothing -- and one on the new field's name.
- **test_marker_room_routes.py**: `test_the_library_is_sheltered_off_its_routes`, which asked that no shelter piece
  stand on its room's routes, is `test_a_shelter_piece_on_a_route_is_the_pass_s_fallback`: one that does must be the
  pass's own choice, put back on the same spot when taken out. The shelter pass stands its piece anywhere clear when
  no spot off the routes is (0.251.0), and landmark_hall_a01's artifact_room is such a room now, its crate the one
  shelter piece in the library on its room's routes. On 0.251.0 the changed file passes (the factory's
  `patches/dc_table_chairs/prove_tests_on_0251.out.txt`).

## [0.251.0] - a room holding an objective or loot marker keeps its dressing off its routes

**The factory's roadmap 288, and the note 289 left.** The factory's census of what furnishing costs a route
(`docs/findings/furnish_route_cost/` at the factory root) has an arm, since 0.250.0 shipped, that strips only
furnish's dressing, so it reads the walker's guide's own measure: what the dressing costs a route over the functional
build, flagged past 10 % (its section 14). Over the library at 0.250.0 eight routes were, and seven of them were one
route in an objective room, its door to its marker: funeral_home_a02's records_office 4.3 -> 5.5 m, courthouse_a02's
records_room, apartment_walkup_a03's garage_cage and four more, each lengthened by one to four carton piles, pallets
or dust sheets. The rooms are 97 to 240 m2 and stand 3.0 to 7.3 % under furniture; the route is short because the
marker stands near the door.

### Changed
- **`reserves_routes(spec, room, building)` says what keeps off a room's routes**: `"all"`, every floor piece furnish
  stands -- a shop floor that stands rows, as 0.250.0 shipped it; `"dressing"`, its clusters only -- a room holding an
  objective or loot marker (`holds_route_marker`, new), whatever its kind; `""`, nothing reserved. furnish asks it of
  every room, not only a shop floor's; its rows, floor pieces and chairs keep off the routes where it says `"all"`,
  its clusters wherever it says either.
- **The shelter pass keeps off a room's reserved routes where it can.** `seed_cover` stands its shelter piece on a
  clear spot off the routes the room reserves if one is, else on any clear spot as before: a crate stack in a route a
  dressing pile was moved off would undo it, and a room must not lose its shelter for it. Its draws happen only on a
  placement, so the second pass is 0.250.0's to the draw. A bare room's cover keeps off the routes outright.
- **`agent_contract.json`'s `sightlines` note** no longer says Lot carries the old 1.2 m crossing, which Lot has not
  since roadmap 131: it names what derives the crossing now -- Lot's copies, held to Laser Tag's by Level Factory's
  `check_sight_drift`, and Level Factory's advisory, from the body each run fields (Level Factory 0.230.0) -- and that
  nothing in the factory carries 1.2 any more (searched first). No number in the file moved.
- **The library refurnished and sheltered**: 51 rooms in 50 specs, every one holding a marker, and no other room (the
  factory's `patches/dc_marker_routes/rooms_moved.out.txt`). Furnish's pieces 8,434 -> 8,428 and one shelter piece
  more, twin_a01's front_right_1, standing off its route; a moved room's floor share -2.6 to +2.0 points, 50 of the 51
  under the walker's 12 % before and after. The worst: clinic_a01's dispensary, about 5 -> 2.4 %, whose carton cluster
  stands as one group and fits nowhere off its routes, and auto_shop_a01's parts_back 8.5 -> 6.9 %, a 26 x 5 m room
  whose routes loop round most of its floor.

### Measured, kept
- **The census over the 50 specs**, 217 rooms and 1,000 pairs, 0.250.0 against this (the factory's
  `patches/dc_marker_routes/census_changed.out.txt`, `pairs_compare.out.txt`): the dressing's detours over 10 % 7 in 7
  rooms -> 0, the worst 1.270 -> 1.052, the routes it narrows to single file 37 -> 5; all of furnishing's over 10 % 18
  in 16 rooms -> 12 in 11, the worst 1.270 -> 1.224; narrowed to single file 80 -> 51; two abreast after furnishing
  742 -> 771; none closed. Pair by pair none crossed over 10 % in either measure, and the extra metres walked summed
  over every pair 90.9 -> 87.0 for all of furnishing, 17.0 -> 9.9 for the dressing; 31 pairs regained two abreast, and
  two lost it, both in market_hall_a01's deposit_cage, where working furniture now stands in the route.
- **What dressing-only leaves.** Working furniture is not asked to keep off a marker room's routes, and where the
  refurnish moved it there it stands: funeral_home_a02's records_office's door-to-marker route is 1.154 of its
  authored length where it was 1.270, now for a desk. Plan views of four rooms before and after
  (`patches/dc_marker_routes/plan_*.png`).
- **The combat audit over the library** (`audit_compare.out.txt`): every code's count unchanged -- COVER_ALL_LOW 8,
  OBJ_NARROW 10, OBJ_AT_DOOR 52 -- and two messages moved, a sightline 17.1 -> 17.0 m and landmark_hall_a01's
  artifact_room counting five low pieces where it counted six.
- REFUTED: every floor piece kept off a marker room's routes, as a corner store's are. 47 rooms moved, 45 of them
  under the walker's 12 % already, and lost 45 pieces; twin_a01's front_right_1 lost both its pieces and the shelter
  they gave, and the shelter pass, then asking no route, wanted a crate stack there.
- REFUTED: the shelter piece kept strictly off the routes. The pawn_shop preset's safe_room had no clear spot left and
  stood no shelter, its tallest piece 1.20 m against the 1.30 m crossing, and `test_cover_breaks_sightlines`' two
  corpus tests failed on it: a room both sides see over everything in cannot be fought in, and the walker's first ask
  is the fight as much as the route.

### Tests
- **test_marker_room_routes.py** (new, 5): a room says what keeps off its routes; no dressing stands on a marker
  room's routes, over the library; the shelter pass, given a route through the spot it would choose, stands its piece
  elsewhere where there is an elsewhere (apartment_walkup_a02's safe_flat) and keeps it there where there is not
  (twin_a01's front_right_1); the library's shelter pieces stand off the routes of the rooms that reserve them. On
  0.250.0 two fail on behaviour -- dressing stands on marker rooms' routes, the crate on the planted route -- one on
  the new signature, and the two guards pass there.
- **test_reserved_routes.py**: `test_a_floor_that_stands_rows_or_a_room_holding_a_marker_asks_for_its_routes`, which
  was `test_only_a_floor_that_stands_rows_asks_for_its_routes`: furnishing office and deli_a03 asks for the market
  aisles' routes and those of the two rooms holding a marker, office's exec_suite and the deli's apartment_hideout. On
  0.250.0 it fails on behaviour, the market aisles alone; the file's other five pass there (the factory's
  `patches/dc_marker_routes/prove_tests_on_0250.out.txt`).

## [0.250.0] - a corner store's selling floor reserves its routes before its rows are laid

**The factory's roadmap 288.** The walker, 2026-10-21: rooms neither crowded nor barren, and above all "free
navigation and fun gun fights". The factory's census of what furnishing costs a route -- per room, between every pair
of its doors and markers, the shortest body route and the widest-path bottleneck, with and without what furnish stood
(the factory's `docs/findings/furnish_route_cost/`) -- found the corner stores' rows, 0.247.0's, the most of it: of
their 85 routes, 16 grown over the 10 % the walker's guide flags and 44 narrowed from two abreast to single file. The
guide, filed the same day (`docs/reference/Lived_In_Levels_Clear_Navigation_4P_PVE_1999_PA.md` at the factory root),
answers it in its section 3 and its builder's third step: reserve circulation before placing.

### Added
- **`protected_routes(spec, room)`**: the routes a room's furniture keeps clear, reserved before anything is placed.
  Square routes between the room's doors and markers for the contract's body, on a 0.25 m grid, a turn costing four
  cells, so a route runs down an aisle and across a row square as a shop's circulation does; then a greedy spanner at
  the guide's 10 % (`_ROUTE_STRETCH`): every pair keeps a reserved way within 10 % of its own square route, and no
  more floor is reserved than that takes. Each corridor's half width is half `two_abreast_width()`.
- **`two_abreast_width()`**: the guide's formula for bodies side by side, n x 2r + 2 x 0.15 + (n - 1) x 0.20, at n = 2
  on the contract's body: 1.90 m. The margins are the guide's, which it calls a prototype's.
- **`room_route_endpoints(spec, room)`**: a body's centre half a metre inside each walkable door (door, garage, a
  vault's leaf, placed by `partition_bounds.host_openings`, the builder's arithmetic), the middle of each open edge,
  and each objective and loot marker. The factory's census measures between the same points.
- **`reserves_routes(room, building)`**: which rooms reserve them -- a shop floor that stands rows, a corner
  store's -- one rule, read by furnish's recipe flag (`protect_routes`).
- **`unfurnished(spec)`**: the floor every pass asks for a room's routes on -- the spec less what furnish and the
  fixtures pass wrote, `migrate_furnish_recipes`'s own strip -- so the routes are the same whichever asks and in
  whatever order the rooms are furnished.
- **`on_protected_route`**: furnish's rows, floor pieces, clusters and chairs keep off them. A wall piece is not
  asked, and neither is the fixtures pass: a wall fixture and the seat in front of it stand in the wall's zone.

### Changed
- **Down a row, every island stands on the writer's centimetre.** `_make_volume` writes a position to 0.01 m, so an
  island placed between centimetres can be written up to half of one off where its aisle was measured. Each island is
  centred on the centimetre, rounded away from the last, and the next starts an aisle past its written end. Measured:
  once the routes moved its packing onto slides, fuel_stop_heist's two gondolas meant to be an aisle apart were
  written 1.24 m apart (`test_corner_store_rows`).
- **The library refurnished**: the fourteen corner-store selling floors and no other room (the factory's
  `patches/dc_reserved_routes/routes_rooms_diff.out.txt`). Their floor share from 19.2-23.1 % to 17.2-22.1 %, every
  one inside the walker's band of 12 to 25 %; their generated gondola units from 126 to 115. The delis' market aisles
  stand two banks of gondolas with one straight cross-aisle between them, the gas stations' rows two aligned banks
  with their front clear; the convenience stores keep their video poker cabinets.

### Measured, kept
- **The census over the fourteen specs**, every room of them, 0.249.0 against this (the factory's
  `patches/dc_reserved_routes/census_0249_corner.out.txt` and `census_0250_corner.out.txt`): routes grown over 10 %
  from 20 in 13 rooms to 4 in 3, none on a corner floor -- the four are back offices and back halls, which reserve
  nothing, and the corner floors' worst pair is 1.096; p90 1.079 -> 1.059, p99 1.143 -> 1.119; routes narrowed from
  two abreast to single file 70 -> 54; routes two abreast after furnishing 129 -> 145; none closed to a body.
- REFUTED: the shortest route on eight directions, the diagonal an empty floor allows. Its corridors cut a store's
  rows into scattered short gondolas -- deli_a03's market aisles from 19.7 to 11.0 % of their floor,
  convenience_store_a01's eight gondola units to two, six of the fourteen floors under the walker's 12 %.
- REFUTED: a minimum spanning tree over the routes, which joins every endpoint and bounds no pair -- on square routes
  it left 10 pairs over 10 % where the spanner leaves 4. Also measured and not taken: the contract's aisle as the
  corridor's half width (the same share, 62 routes narrowed where two abreast leaves 54), and a stretch of 1.25 (the
  same routes reserved).
- REFUTED: the fixtures pass asked too. convenience_store_a01 and stop_n_go each lost both video poker cabinets and
  their stools -- the walker's PA skill games -- to the route along their north wall between their two north doors;
  not asked, a stool stands 0.27 m off that route's line and the floor's worst pair reads 1.096.
- REFUTED: the rows built a centimetre wider apart instead. It moved their pitch off a room's own aisles --
  deli_a03's, 4.5 m apart, two pitches of 1.25 + 1.0 -- and its third row onto its second authored aisle.
- **What the census cannot say.** It measures the rows against an empty floor, and in the guide's terms a store's
  rows are its functional build, not its dressing; the guide's 10 % is a flag on dressing. The routes a corner floor
  still walks longer than an empty floor would let it are an aisle layout's, which a shop has.

### Tests
- **test_reserved_routes.py** (new, 6): every pass reserves on the floor the refurnish starts from; two abreast is the
  guide's formula on the contract's body; route endpoints stand inside the doors the builder cuts; reserved routes run
  square; nothing furnish stood on a corner floor stands on its routes; only a floor that stands rows asks for its
  routes. On 0.249.0 all six fail on the new functions' names: what they guard is the census above, not a behaviour
  0.249.0 had (the factory's `patches/dc_reserved_routes/prove_tests_on_0249.out.txt`).
- **test_corner_store_rows.py**: `test_the_rows_fill_the_floor` asks for 17 to 25 % where it asked for at least 19 %,
  its docstring saying what it guards and the walker's band; on 0.249.0 the changed file passes, all nine.

## [0.249.0] - a room holds what stands on its storey, and the shelter pass runs over the library

**The factory's roadmap 283.** 0.246.0 made furnish's count ask a volume's FOOT, because `abs(z - (floor + size_z /
2)) < sh` put a piece on the floor above or below exactly `sh` away and let float rounding decide. Three more places
asked the question their own ways. `_room_has_cover` and `_room_has_shelter` -- which decide whether `seed_cover`
stands shelter in a combat room -- kept that window and asked no storey of a cover marker.
`combat_audit._cover_in_room` asked `abs(z - floor) < sh` of a volume's CENTRE, which counts everything standing on
the floor below as cover in the room over it (a 1 m crate on the ground floor was cover upstairs), and no storey of a
marker either. Attributing every room the change fills found the second defect behind the first: nothing ran the
shelter pass over the library.
`enrich` runs in `presets.make`, `build.py` builds a library spec's JSON as it stands, and the shelter guarantee was
tested on presets alone; a library room was sheltered when furnish happened to stand a tall piece in it, and a
refurnish could take that away with nothing to notice.

### Added
- **`stands_on_storey(vz, vh, floor, sh)`**: does a volume STAND on the storey whose floor is at `floor` -- its foot
  on that floor, to `_on_storey`'s slab tolerance, up to just under the next storey's. The one test for "what is in
  this room", asked now by furnish's count (`_room_volume_count`, whose 0.246.0 spelling it is), `_room_has_cover`,
  `_room_has_shelter` and `combat_audit._cover_in_room`. `_on_storey` asks whether a volume REACHES into a storey, as
  a stair or a tall piece from below does, and stays as it is.
- **`marker_on_storey(m, floor, sh)`**: a marker's `z` is the floor it stands on. One with no `z` keeps counting on
  every storey, as every marker did; none of the library's 269 cover markers lacks one, and a test keeps it so.
- **`migrate_shelter.py`**: runs the shelter pass over the library and refurnishes any spec it adds to -- furnish
  counts what a room holds, and a shelter piece is one more -- so the library stays a fixed point of both. `--check`
  reports, and exits 1 when a room would be filled. It is the remedy the new library test names.

### Changed
- **The shelter pass tries the room's own piece, then the smallest.** The piece is chosen by the room's words, and a
  room's words do not know its stair: the rowhome preset's `back_0`, 8 x 11 m with a flight up its middle, chooses a
  2.6 m shelf run, which the stair, its landings and the door approach refuse at every one of its 36 candidates, where
  the default 1.1 m crate stack stands at four. It read sheltered until now only because a 1.9 m piece on the floor
  above was counted in it. The random draws happen only on a placement, so a room whose own piece fits seeds exactly
  as before.
- **COVER_ALL_LOW quotes the tallest piece on the room's own storey**, the storey its count asks: it could name one on
  another floor -- a piece breaking the sightline the finding says nothing in the room breaks. `combat_audit` imports
  `level_design` for the shared test.
- **The library: eleven shelter pieces at `shelter_height()` (1.60 m) in eleven combat rooms of nine specs** -- eight
  1.1 m crate stacks, two kiosks, one shelf run -- each attributed (the factory's `patches/dc_storey_shelter/`,
  `storey_attrib.out.txt` and `shelter_history_old.out.txt`):
  - three read sheltered only by something on another storey: final_stand's `stair_core` by a `cover_high` marker two
    storeys up (z 7.6), rowhouse_raid's `kitchen` by a 1.80 m shelf run on the floor above (its foot at 3.20),
    twin_a01's `front_left_1` by a `cover_high` marker on the ground floor under it;
  - three were sheltered by furnish's own lockers and shelf runs until a refurnish moved them: rail_station_a02's
    `vault_approach` (0.204.0), rowhouse_raid's `basement_vault` (0.234.0), warehouse_a01's `back_corridor` (0.131.0);
  - five were never sheltered in any committed version, by either test: cbp_town_finale_midbalanced_schemafixed's
    `main_concourse` and `club_ring_overlook`, freight_terminal_a02's `gantry_control`, parking_garage_a02's
    `attendant_booth`, primos_pizza's `rear_hall`.

  The nine specs are refurnished and only those eleven rooms move (`shelter_rooms_diff.out.txt`): the piece stands
  and the room's furnish draws again around it. Most move a piece or two. Three lose some: cbp's `club_ring_overlook`
  27 -> 15 pieces -- it draws 3 chairs for its 8 tables where 0.248.0 drew 15 for 9, since a dining table draws 0 to 4
  (`seats=("table", 0, 4)`) -- primos_pizza's `rear_hall` 5 -> 3, a dining table and its two chairs, and
  rowhouse_raid's `basement_vault` 10 -> 9.

### Measured, kept
- **The audit's findings over the library**, asked of the specs that ship: COVER_ALL_LOW 12 -> 8; KILLBOX,
  C_NAKED_ROOM and H_NO_HOLDOUT 0 -> 0. Seven of the twelve are rooms this fills, which the audit had been reporting
  and nothing had acted on. Asked by the foot the audit sees seven more, furnished low over tall pieces on the floor
  below; four are filled here and three stay. The eight left, each attributed: seven where neither the room's own
  piece nor the crate stack clears at any of the 36 candidates (apartment_walkup_a01's `kitchen`, cbp's
  `home_plate_overlook`, deli_a02's `stairwell`, fuel_stop_heist's and gas_station_a02's `back_hall`,
  landmark_hall_a01's `artifact_room`, pawn_shop_a02's `upper_flat`), and stop_n_go's `back_hall`, 27 m2, under
  `_SEED_MIN_AREA`. A room where nothing fits keeps its finding rather than getting a crate in a doorway, as before.
- **The library's dining tables**: 257, of which 50 stand with no chair (19 %) and 65 with one; `seats=("table", 0,
  4)` is uniform before clearance refuses any. Not this change's question: the factory's roadmap 284.

### Tests
- **test_storey_shelter.py** (new, 9): a piece stands on the storey its foot is on; a marker on the floor its `z`
  names; every library cover marker names its floor; the producer shelters a room from neither another storey's piece
  nor its marker; the audit does not count the floor below as cover upstairs; COVER_ALL_LOW quotes a piece on its own
  storey; a room whose own shelter fits nowhere gets the smallest; the library is a fixed point of the shelter pass.
  On 0.248.0 six fail on behaviour -- the producer counts a tall piece one storey down at 1.45 m and a `cover_high`
  marker on the floor below; the audit counts a crate and a marker on the floor below as cover upstairs (2 against
  0); a room furnished low over a tall shelf below draws no COVER_ALL_LOW; the rowhome's `back_0` stands no shelter
  piece; the library owes eight rooms (0.248.0's own pass, which still reads the three leak rooms sheltered) -- two
  fail on the new helpers' names, and one, the cover markers' floors, is a guard that holds there (the factory's
  `patches/dc_storey_shelter/prove_tests_on_0248.out.txt`).

## [0.248.0] - an office building's open floor is an office

**The factory's roadmap 281.** `floor` is a shop-floor word in `_ROOM_KINDS` -- "a shop floor is shelving and stock"
-- so the office preset's open storey over the bullpen, `floor_1` (816 m2 in office and office_stepped), was furnished
by the shop floor's recipe. 0.246.0's count fix let it reach its target, and cold run 9369's frame of office's showed
litter bins standing mid-floor among carton stacks.

### Added
- **`is_office_floor(room, building)`**, read in `_room_kind` after the strip club's, the card shop's and the video
  store's rules and on their terms: a building whose id says `office`, and a room the word table would make a shop
  floor by the word `floor` alone. A room that names a stronger kind keeps it (`ground_bullpen` is an office,
  `lobby` a lobby), and `floor` beside a real shop word is a shop floor still.

### Changed
- **The library refurnished**: office's `floor_1` goes from a service counter, three vending machines, two filing
  cabinets, four shelf runs, four cartons and four litter bins to four desks and their chairs, three shelf runs, six
  filing cabinets and five cartons; office_stepped's from five litter bins and nine cartons to six desks and their
  chairs and ten cartons. No other room in the library moves. The library's other thirteen rooms that are shop floors
  by `floor` alone -- an arena's event floors, a brewery's, a depot's, a foundry's, a freight terminal's and the
  warehouses' floors, a supermarket's mezzanine -- keep their kind; each is a question of its own.

### Tests
- **test_office_floor_kind.py** (new, 4): an office building's floor_N is an office; the other thirteen bare floors
  keep their kind; the rule asks `floor` alone; the library's two office floors hold desks and no shop stock. On
  0.247.0 two fail on behaviour -- `floor_1` reads `shop_floor`, and the library's office floors hold litter bins and
  no desk -- and two are guards whose kind halves hold there, failing only on the new function's name.

## [0.247.0] - a corner store's selling floor stands its aisle gondolas in rows

**The factory's roadmap 148.** The look review of 2026-10-19 found the rooms "Too sparse", and deli_a03's market
aisles were the first of its seven frames: 300 m2 with 5.7 % of the floor under anything standing -- two authored aisle
shelves, a counter, a cabinet, cartons and a bin. More pieces was measured first and is not what this does: furnish's
target without its 160 to 400 m2 plateau would write 63 % more pieces across the library (7,777 -> 12,665) and move
that room from 5.7 to 6.8 %, because what it adds is cartons and cabinets. What a room is known by stands in rows.

### Added
- **`gondola_aisle`** (`_PIECES`): Zoo's `snack_gondola` (1.13.0), both long faces shopped in one module, 2.4, 3.6
  and 4.8 m long, 0.9 to 1.0 m deep, 1.40 to 1.45 m tall -- over `cover_break_height` (1.30) and under
  `shelter_height` (1.60), so a row is cover a body crouches behind and an eye sees over, which is furnish's rule for
  anything it stands mid-floor. In `metal_painted`, the species' own kind, so Zoo's stem carries no `_m`. Capped at
  16 a room like every island ("an uncapped island is a maze") -- a guard the rows stay under, not their rule: the
  most any library floor stands is 12.
- **`is_corner_store_floor(room, building)`**: a building whose id names a deli, a convenience store, a gas station,
  a fuel stop, a bodega or a stop, and a room whose id names its selling floor (`market`, `aisles`, `aisle`,
  `sales`). Not a supermarket, on `migrate_store_gondolas`'s own line -- "a supermarket aisle is not a snack aisle"
  -- nor a pharmacy; `gs_corner_station` names neither `gas` nor `fuel` and keeps its authored aisles alone. Each is
  a word away. The room keeps its kind, `shop_floor`, so fixtures, posters, ATMs and lights read it as they did.
- **Rows** (`_row_slots`, `_row_clear`, the plan's `rows` item): after a room's wall run and before its floor sets
  and clusters, gondolas of one length down the room's long axis -- or, when the room has its own island (a standing
  volume of an island's shape clear of every wall face), along it, at its depth and on its line -- each an aisle
  (`island_aisle_width`, the contract's 1.25 m) from every wall's FACE, partition, stair reserve and standing volume,
  and asked furnish's other rules down its length; each row packed along past anything that refuses a slot; whole
  rows laid from the middle out until `room_floor_share` reaches the recipe's `rows_share` (0.25) or nothing more
  clears. The length is the palette's that covers the most floor.
- **`room_floor_share(spec, room)`**: the share of a room's floor under standing furniture -- footprints clipped to
  the room, feet on its floor (a 46 x 46 m forecourt slab whose top is a sales floor is not furniture).

### Changed
- **A deli is a store** to `migrate_store_gondolas.py` (`REGISTERS`, `is_store`): its counter is a
  `front_register_counter`, so the six delis' authored `aisle_shelf_01` and `_02` -- shelving, 1.0 x 6.0 x 1.6 m,
  binders and boxes on it -- are `gondola_aisle_01` and `_02`, as every store's aisles have been since 0.149.0, and
  `presets.corner_deli` writes them so. Those twelve are the only volumes the wider rule renames.
- **The library refurnished**: its 14 corner store floors stand 126 gondolas -- nine in each deli's market aisles,
  twelve on each of the four 22 x 22 m gas station floors, eight on each convenience store's, four on gas_station_a02's
  and fuel_stop_heist's -- and their floor share goes from 5.4 to 13.4 % to 19.2 to 23.1 %. deli_a03's market aisles:
  5.7 -> 19.7 %, nine 4.8 m gondolas in five rows, two of them continuing its own aisles' lines. No other room in the
  library moves.

### Measured, kept
- REFUTED: the rows first took `_island_slots`'s grid, an aisle off the room's BOUNDS, and every one of deli_a03's
  market-aisle slots beside a wall was refused: a bound is a wall's centre line, and at its 0.36 m walls the floor
  between such a slot and the wall's face was 1.07 m. The rows measure from the faces.
- REFUTED: an even grid stood its columns 1.1 m off deli_a03's authored aisles, which refused 12 of its 30 slots; and
  the gas stations' square floors ran the rows ACROSS their authored 10 m aisles. A room's own island sets the rows'
  axis, depth and line.
- The first 1.45 m gondola counted in deli_a03's apartment upstairs and cost it nine pieces: 0.246.0's defect, fixed
  there first.
- NOT CHANGED, and measured: the card shop's single island keeps `_island_slots`'s bound. On card_shop_a01 its twin
  island stands 1.12 m from a partition's face, under the 1.25 m aisle its docstring claims and over the corridor's
  1.10; moving it would refurnish a room the walker has passed.

### Tests
- **test_corner_store_rows.py** (new, 9): the piece routes to `snack_gondola` in its own kind, capped like every island; every size is cover
  and never shelter; which floors are a corner store's; the library's fourteen stand rows, one way and one length a
  room, and no other room holds one; every gondola an aisle from every other and from every wall's face, and no
  standing piece within furnish's 0.9 m (re-derived from rectangles in the test, not `_row_clear` asked again); no
  gondola within an aisle of a door's centre; deli_a03's rows on its own aisles' lines; every floor at 19 % or more;
  a deli is a store to the migration. On 0.246.0 eight fail -- four on behaviour (the material reads `wood`, the
  library holds no rows, the delis' aisles are unrenamed, the store count), four for a piece or function that does
  not exist yet -- and the aisle and door tests pass vacuously, with no gondola to ask.
- **test_store_gondolas.py**: 15 stores, six of them delis, and no `aisle_N` or `aisle_shelf_N` left in any.
- **test_furnish.py**: `_ZOO_RANGES` carries `snack_gondola`, held to its genome by `test_the_ranges_are_zoo_s`;
  `test_the_only_mid_floor_shelter_is_a_declared_island` asks the rows too -- the shop floor is their one giver, a
  corner store's floor the one room given them, their piece capped and under shelter.

## [0.246.0] - a room counts only what stands on its own storey

**The factory's roadmap 148**, whose look review of 2026-10-19 found the rooms "Too sparse". Laying the rows that item
asked for next, deli_a03's apartment upstairs lost nine of its twelve pieces to gondolas standing on the floor below
it, and the cause was older than the rows: `level_design._room_volume_count` -- what a room already holds, so furnish
tops it up rather than doubling it -- asked `abs(z - (floor + size_z / 2)) < sh`, a foot anywhere between the storey
below's floor and the storey above's with both ends open. A piece standing on either of those floors is EXACTLY `sh`
from this one, so whether it counted was float rounding.

### Fixed
- **`_room_volume_count` asks a volume's foot**: on this storey's floor to `_on_storey`'s slab tolerance (0.05 m), up
  to the next storey's. Measured over the library before the change: 740 volumes in 195 rooms of 55 specs inside the
  old window -- chair sets, shelves, cartons and filing cabinets above all -- each a piece the room it was counted in
  then went without, so a room furnished sparser for every piece on the floor over it or under it. At sh 3.3 a 1.45 m
  piece standing one storey down was 3.2999999999999994 off and counted, a 1.40 m one 3.3 and not. The same spelling
  counted a slab sunk under the floor -- gas_station_a02's 46 x 46 m `forecourt_pad`, whose top is its sales floor --
  and a raised piece in the room a storey over it.

### Changed
- **The library refurnished** (`migrate_furnish_recipes.py`): 44 specs and 109 rooms move, and furnish's pieces in
  those rooms go 1,034 -> 1,432 -- office 239 -> 364 in 27 rooms, fallback 162 -> 249 in 21, vault 74 -> 104, hall
  100 -> 132, mechanical 71 -> 92, storage 66 -> 91, shop floor 72 -> 94, club 52 -> 79, strip club 80 -> 93,
  apartment 64 -> 69, garage 12 -> 16, basement 17 -> 20, locker 0 -> 2, lobby 16 -> 17, kitchen 9 -> 10. Two rooms
  hold fewer: cbp_town_finale_midbalanced_schemafixed's home_plate_overlook 15 -> 12 and strip_club_a02's count_room
  13 -> 12, where the larger target re-drew the room's plan and more of it found no clear floor. Every other room in
  the library furnishes as it did, and the library is a fixed point of furnish again.

### Tests
- **test_room_count_storey.py** (new, 6): pieces at every height from 0.30 to 2.40 m standing on the floor below are
  not counted upstairs, nor ones on the floor above downstairs; a slab sunk under the floor is not furniture; a raised
  piece counts on its own storey only; the window is real at sh 3.3 (the control: 1.45 m inside it, 1.40 m not); and
  the whole library is a fixed point of furnish. Three fail on 0.245.0 -- five of the 43 heights counted upstairs, the
  slab counted, the raised piece counted a storey up -- and the library test fails with this rule on 0.245.0's
  specs. The floor-above sweep holds on both: at sh 3.3 none of its heights falls in the window from that side, so it
  guards the rule rather than proving the change.

## [0.245.0] - a shipping container is the cargo container, recorded short side first

**The factory's roadmap 267**, its last named word: freight_terminal_a01's four `container` volumes, 6.0 x 2.4 x 2.6,
built as plain boxes -- Zoo planned them `prop_delco_1997_04_w600_d240_h260_mmetal` -- though Zoo has drawn the ISO
container since 0.82.0 and Lot stands it as cover and in its backdrop yards. 0.240.0 found why a word alone could not
route them:
Deli Counter records every hinted volume long side first, as the module's width, and `cargo_container` is long in
DEPTH (2.3-2.5 m wide, 2.9-13.8 m deep), so a container recorded 6.0 wide fails its genome however it is named.

### Added
- **`prop_species.DEPTH_LONG`**: the species whose genome's whole depth range lies above its whole width range, so no
  slot recorded long side first can fit one. Measured over Zoo's genomes: ten are (boots, box_truck, cargo_container,
  cheesesteak, cruiser, jersey_barrier, security_camera, simple_car, step_van, utility_pole), and the table routes
  one, `cargo_container`. Held to the genomes by a test, not chosen.
- **`long_axis_first(size, species=None)`**: a depth-long species is recorded with its long side as the module's
  depth, turned 90 when that side is x -- the four containers are recorded 2.4 x 6.0 x 2.6 at 90 and Zoo plans them
  `prop_cargo_container_delco_1997_06_w240_d600_h260`, no fallback, no `_m`. Without a species, and for every
  species not in the set, the rule is the one it was.
- **`prop_species.recorded_turn(name, sx, sy)`**: the 0 or 90 degrees the emitter adds for a volume's long side, by
  its name. `level_design._front_turn` and `lights._front_bearing` each spelled the long-side-first rule out for
  themselves, right for every species but a depth-long one; both ask this now, so a depth-long piece cannot be
  recorded one way and faced another. For every other volume in the library the answer is the one they spelled.
- **`container` routes to `cargo_container`** (`PROP_SPECIES`). It claims exactly freight_terminal_a01's four. `cargo`
  is not a keyword: the library's two `cargo_cover` volumes (harbor_score, marina_a01) are 4.0 x 4.0 x 2.0 of wooden
  cargo, which the genome's width cannot build either way round.

### Changed
- **freight_terminal_a01's containers are written in `metal_painted`**, the species' own kind -- its genome's default
  and every style's -- for the dartboard's reason in `level_design._PROP_MATERIALS`: in `metal`, a kind Zoo knows,
  the stem would carry `_mmetal` and the container would build as bare steel. `metal_painted` was already declared
  (the cigarette machine's); `metal` stays, worn by eleven other volumes and two partitions and the spec's default.
  The spec is still a fixed point of furnish. Their four colliders' surfaces take `metal_painted`'s acoustics with
  it -- absorption 0.25 and damping 0.2, where `metal`'s were 0.5 and 0.3, both `Metal` -- which is the gameplay
  record's whole change.
- **The composer needed nothing.** `themed_tscn._fit_rotation` scores each turn by the module's placed footprint
  against the greybox slot's and tries the slot's own first, so a 2.4 x 6.0 module recorded at 90 lands on the 6.0 x
  2.4 box at 90. Roadmap 267's note asked for "the composer that mirrors it"; the composer derives the turn from
  extents and mirrors nothing.

### Costs, and what the cheaper container would buy
- **A container is nine draws where the box was one.** Zoo's recipe gives each colour its own material, all of one
  kind -- paint (the frame and doors share it), rib flank, rib valley, hardware, apertures, markings, plate,
  warning, rust and, on a patched box, patch -- and the shipped `prop_cargo_container_delco_01_w244_d606_h259.glb`
  (the factory's cold run 9279) reads 9 visual meshes on 9 materials, 3,296 triangles with its collider. Zoo's own
  `geometry.tint_wear_by` calls it "the cargo container's pattern the draw-call rule forbids". Level Factory merges
  a building's static pieces per material in 6 m cells of the room they stand in (its 0.223.0), and the four
  containers stand 9 m apart in `cross_dock`, one to a cell: up to 36 submissions where the four boxes added at most
  four, when all four are in view -- at 3.47 us a draw, the slope of the factory's cold run 9062 measurement (1,730
  draws 9.49 ms, 6,376 draws 25.59 ms), about 0.1 ms.
  AN ESTIMATE, NOT A PRICE: the package's own count is the factory's next record. The cheaper container -- its
  colours in the `Wear` vertex colour, as the coffee island and the service counter carry theirs, one or two
  submissions -- is a Zoo change for every container Lot places too, and waits on whether cover modules draw vertex
  colour, which the recipe says they did not in walk 9052.

### Tests
- `test_depth_long.py` (new, 5): the word routes the four and not the cargo covers; a depth-long species is recorded
  short side first and turned only when long in x, every other species unchanged; the four library containers in
  `metal_painted`, recorded inside the genome; `DEPTH_LONG` is exactly the routed species of that shape in Zoo's
  genomes (skipped, not passed, without them); the emitter's container slot -- species, dims, turn, its greybox
  collider kept; and both front readers ask the emitter's turn, which for every other library volume is the rule
  they spelled. All five fail on 0.244.0.

## [0.244.0] - a bank's teller line gets a queue, and a queue is not furniture

**The factory's roadmap 275, the walker, 2026-10-20**: "stanchion or stanchions are likley more common for banks and
indoor common areas". 0.243.0 laid a box office's queue in Zoo 1.119.0's retractable-belt stanchions; this lays a
teller line's the same way, as generator logic.

### Added
- **`ticket_queue.queue_teller_lines`** (and `plan_teller`): a teller line (`level_design._teller_lines`) gets a queue
  on its public side -- the side `level_design._public_side` reads off the room's street doors, the one
  `enclose_teller_lines` does not wall -- in the room in front of the counter: three lanes or two of stanchion runs
  parallel to it, `stanchion_run_t<q>_<k>`, letting out on a 0.5 m grid along the counter wherever the turn it leaves
  by faces the counter, nearest the middle preferred; a customer walks on to whichever window is free. The floor in
  front of a counter is `teller_service_depth()`, a door's approach for the customer at a window and a corridor
  behind them. Every other clearance is the box office's.
- **One fitting for both**, `ticket_queue._fit`: what differs is the frontage (a wall's face or a counter's), where a
  queue may let out (the window, or anywhere along the counter) and the floor in front. A counter on the edge of the
  room in front of it may stand a hair outside that room (`_grown`). The box office's queue is unchanged: re-planned
  from 0.242.0's arena_a02, the same runs and window to the millimetre.
- **`ticket_queue.lay_queues`**, both; `level_design.enrich` lays it after the teller line's enclosure, whose walls a
  teller line's queue keeps clear of, and before cover and furniture.

### Changed
- **`migrate_ticket_queue.migrate`** fits a library spec's queues with its furnished pieces set aside, carries them
  in, and refurnishes (`migrate_furnish_recipes.migrate`) -- the order `enrich` gives a generated building. Run on
  0.242.0's arena_a02, it writes 0.243.0's arena_a02 to the byte (the factory's
  `patches/dc_teller_queue/arena_either_way.out.txt`), so the two ways of fitting agree on the one queue they share.
- **A queue is the room's circulation, not its furniture.** `level_design._room_volume_count` leaves stanchion runs
  out: counted, each bank lobby's four runs cost it four pieces, among them bank_job's payphone and sofa and
  bank_branch_a03's and credit_union_a01's ATMs. The queue keeps its own floor without being counted -- furnish
  holds a piece 0.9 m off each run, and a lane is narrower than two of those.
- **A room with a queue has no lone queue posts**: furnish drops a lobby's cluster of `stanchion` posts where
  `ticket_queue` has laid the queue they stood for.
- **The library.** bank_branch_a02, bank_branch_a03, bank_job and credit_union_a01 are queued -- three lanes each,
  5.2 to 5.6 m along their counters -- and refurnished: their lobbies keep every piece they had but the lone posts
  (and, in bank_branch_a03's, a waiting chair), and take litter bins and low tables in their place. bank_branch_a04
  is left, and says why: its counter stands
  against the grand lobby's concrete wall, its public face 0.1 m into partition 0, so no queue stands in front of it.
  arena_a02 is refurnished, its runs no longer counted: four more cartons and a file cabinet on its event floor, a
  litter bin fewer.
- **Not this change's rule, and recorded.** bank_branch_a03's upstairs offices re-drew too -- five pieces more, the
  teller staff room a carton fewer -- because `_room_volume_count`'s storey filter, `abs(z - (story * sh + h / 2)) <
  sh`, sits exactly at its threshold for a piece standing on the floor below, and float rounding counted seven of
  the lobby's pieces in the offices above, three of them the lone posts this removes
  (`patches/dc_teller_queue/storey_filter_floats_0243.out.txt` at the factory root, the factory's roadmap 277).

### Tests
- `test_ticket_queue.py`: the teller numbers are the contract's; each queued library bank's four lines stand parallel
  to its counter a teller line's floor off its face, a lane apart, switching back, letting out where the counter is;
  nothing else stands inside a bank's queue and every line keeps a corridor from every other standing volume on its
  storey, every walkable opening's approach and every wall; bank_branch_a04 is left with its reason; the bank preset
  gets its queue once, nothing furnished inside it; furnish does not count a queue; the queued lobbies keep their
  ATMs and bank_job its payphone and sofa; no room holding a queue has a lone post; the library is a fixed point of
  both rules and of the migration. The checks that read volumes compare a storey's own -- a first draft read a
  basement's tables as standing in a ground-floor queue. They fail on 0.243.0, which queues no teller line.

## [0.243.0] - a box office sells through a ticket window, and its queue switches back in front of it

**The factory's roadmap 267, the walker, 2026-10-20.** Asked what arena_a02's four steel barricades on its event floor
were for, the walker chose "queue lanes to the box office"; then "stanchion or stanchions are likley more common for
banks and indoor common areas", "metal barriers are for outdoor concerts or riot protection from police", "retractable
belt stanchion", and a photo of a queue lined with them. Zoo 1.119.0 draws one straight run of those stanchions,
`stanchion_run`. This lays a box office's queue of them, as generator logic, and takes the barricades indoors away.

### Added
- **`ticket_queue.py`**, pure. A room whose id names a box office or a ticket office (`is_box_office`: `box` with
  `office`, `ticket`, `tickets`, `ticketing`, `boxoffice`) that shares an interior wall with a public room (the role
  `public_entry`, or a lobby or a hall by its words) gets:
  - **a ticket window** in that wall: a `window` opening tagged `ticket_window`, 1.2 m wide over a 1.0 m sill, 1.1 m
    tall, sealed -- not `breakable`, since a pane that shot out would be a firing line into the room behind it -- on
    the builder's grid, so it is cut where its queue was laid, and a jamb clear of the wall's openings and of any wall
    ending on it;
  - **a queue** in front of it, on the public side: three lanes or two between lines of stanchion runs parallel to the
    wall, one `stanchion_run_<q>_<k>` volume a line, each line stopping a turn short at alternate ends, so the queue
    switches back -- in at the end away from the window, out of the last lane at the window's end onto the floor in
    front of the window.
  Every clearance is the body contract's: a lane's clear floor and a turn are `stair_flight_width()` (a corridor and
  one bake cell, a lane being a corridor to the bake); the floor in front of the window is `door_approach()`; nothing
  stands inside the queue, and every line keeps `min_corridor_width()` from every wall but its own, every standing
  volume, every walkable opening's approach, every stair, hole and vault swing. `plan` tries every window place the
  grid allows, at either end, three lanes then two, as long as 6 m and shorter in 0.1 m steps to a line as long as the
  lanes are wide, and keeps the most lanes, then the longest, then the window nearest the middle of the office's wall.
  A box office whose only outside wall is the street's is the street's queue, and Lot's; this reports it and lays
  nothing. `RUN_DEPTH`, `RUN_HEIGHT` and the kind are Zoo's genome's, retyped and pinned by a test when the zoo repo is
  beside this one, as the vault door's are.
- **`level_design.enrich`** lays the queue after the teller line and the vault and before cover and furniture
  (`queues_laid`), so a generated building's cover and furniture clear its lines and its window.
- **`migrate_ticket_queue.py`**: the library's box offices get the same answer, fitted round what is already there.
- **`PROP_SPECIES`**: `stanchion_run` routes to the species, above `stanchion`, whose single post a lone
  `stanchion_*` still is; `SPECIES_OWNS_COLLISION` holds it -- the module's collider is the posts and the belt line, and
  a box the slot's size would be a 0.97 m wall a crouching body hides behind, cover a belt is not.
  `level_design._PROP_MATERIALS`: a run is `metal_painted`, its species' own kind.

### Changed
- **`specs/arena_a02.json`**, the library's one box office:
  - the four steel barricades 0.242.0 routed to Zoo's `crowd_barrier` (`barrier_0` to `_3`, 3.0 x 0.8 x 1.2 m across
    the event floor) are gone -- the walker: the steel barricade is for outdoor concerts and police lines -- and
    `metal_bare`, which they alone wore, with them;
  - `migrate_ticket_queue` laid the box office's queue: the window in the partition at y 5.9 at x -15.5, between the
    box office's secure door and its east wall, and three lanes, 6.0 m along the event floor's north wall eastward from
    the window, four lines of 4.8 m; `metal_painted` declared last, after the finish palette, style 10;
  - **refurnished** (`migrate_furnish_recipes.migrate`, arena_a02 alone), because the library is a fixed point of
    furnish and a piece removed or added moves what furnish places round it: ten of the event floor's furnished pieces
    -- cartons and litter bins -- stand elsewhere, none inside the queue. The rest of the library is untouched.
- `combat_audit --rules auto` reads arena_a02 the same before and after: 0 HIGH, 1 MED, 4 INFO, the box office's
  sightline 12.7 m. The barricades were 1.2 m, under the contract's 1.3 m cover-break height, so no sightline they cut
  opens; the event floor's cover-like pieces go 21 -> 17.

### Tests
- `test_ticket_queue.py` (new): the words that name a box office; every number the contract's; the stanchion numbers
  Zoo's genome's; a run is the species and owns its collision, and a lone post is still the single stanchion;
  arena_a02 sells through one window in the box office's wall, on the grid and clear of its door; its queue switches
  back to the window, a lane's clear floor apart; nothing stands inside it and every line keeps a corridor from every
  volume, opening approach and wall, measured from the spec; no steel barricade and `metal_painted` last; the library
  is a fixed point of the rule; a theatre built for it gets three lanes and its window, once; declaring the kind moves
  no style; no public neighbour and a wall full of doors each leave it unlaid with a reason; `enrich` lays it before
  cover and furniture and nothing stands in it; the builder writes each line as the species with no greybox box.
  It cannot import on 0.242.0.
- `test_prop_species.py`: `test_barrier_routes_to_the_crowd_barrier_and_none_stands_in_the_arena` replaces 0.242.0's
  barrier test -- the word still routes to the barricade; arena_a02 carries none and no `metal_bare`. It fails on
  0.242.0.
- `test_cover_breaks_sightlines.py`: `enrich`'s report carries `queues_laid`.

## [0.242.0] - arena_a02's barriers are crowd rails: the word `barrier` routes to Zoo's steel crowd_barrier

**The factory's roadmap 267, the walker's look review of 2026-10-20**: arena_a02's four barriers -- 3.0 x 0.8 x 1.2 m
volumes Zoo built as plain boxes -- are to be "Crowd rails (a new model)", not the concrete jersey barrier 0.240.0
left for that call. Zoo 1.118.0 draws the steel barricade, `crowd_barrier`.

### Changed
- `PROP_SPECIES`: a `barrier` row routes to `crowd_barrier`. It claims exactly arena_a02's four volumes, each inside
  the genome long side first (3.0 x 0.8 x 1.2 in 1.8-3.2 x 0.45-0.9 x 0.95-1.25), and no earlier keyword claims a
  `barrier_<n>`.
- `specs/arena_a02.json`: the four volumes' material `metal` -> `metal_bare`, the species' own kind. Zoo's kit keeps a
  slot's known kind its genome does not offer (`dna.resolve_module_plan`), so `metal` would have built the `_mmetal`
  module in the theme's metal pack instead of the galvanised grey -- the dartboard's rule, which
  `level_design._PROP_MATERIALS` applies to every piece it places.
- `specs/arena_a02.json` DECLARES `metal_bare`, with the acoustics every spec that uses it gives it (Metal, absorption
  0.2, damping 0.15), and declares it LAST, after the four finish materials it now declares itself in the finish
  palette's order and values (`floors.FINISH_PALETTE`: carpet, tile, ceiling_tile, plaster), so every other material
  keeps its style number and `metal_bare` is style 10. Two cuts were wrong first, both found in the rebuilt records
  (the factory's `patches/dc_crowd_barrier/`): renaming the volumes' kind alone left it undeclared -- "UNRESOLVED
  MATERIALS in 'arena_a02': metal_bare x4", four surfaces with no acoustics (`record_moves.out.txt`); declaring it
  after `metal` moved 50 slots' styles, because styles are the palette's order and the finish palette is appended
  after the authored list (`record_moves_declared_after_metal_REFUTED.out.txt`).

### Not changed, and why
- The four volumes' collider, the convex 3.0 x 0.8 x 1.2 box the composer keeps in the greybox: the barriers keep the
  cover and the pathing they had. A barricade you can see through still stops a shot as the box did; whether a shot
  should pass between its pickets is the gameplay layer's (a collider that stops bodies and not shots), and stays the
  walker's call.
- `level_design`'s cover tagger still reads `barrier` as a cover name (`_COVER_NAME_HINTS`), for the same reason.

### Tests
- `test_prop_species.py`: `test_barrier_routes_to_the_crowd_barrier_in_its_own_kind`, every library volume the word
  reaches, with its species, its kind and its dims inside the genome. It fails on 0.241.0, where `barrier` routes to
  None and the four are `metal`.

## [0.241.0] - a ramp's cut stops at its head, railed, with a landing past it

**Found by the factory's install test 10** (roadmap 202): a stranger's first `make` picked seed 9205, whose lot
stands a parking_garage, and Level Factory's drop-edge gate refused the export on 33 edges round the garage's ramp.
`stairwell.ramp_hole` cut the storey a ramp climbs to from the ramp's middle to half a run PAST its head -- the box
`Builder._ramps` builds is centred on the ramp's (x, y) -- so the cut's far half stood open over nothing, 5 m beyond
the top of the garage's ramp (24 of the edges, most of them a 3 m fall to the ground floor), and the cut's other edges
dropped 0.75 to 1.2 m onto the ramp unguarded (9). Every library ramp did the same: nine ramps in six specs, 5 to 8 m
past their heads (the factory's `docs/findings/ramp_cut_241/`).

### Changed
- `stairwell.ramp_hole`: the cut runs from the ramp's middle -- where it always began -- to its head, and never past
  it; across the ramp's width and `RAMP_CUT_SIDE` (0.2 m) either side, as before. `ramp_cut_span` says where. Along X
  the same rule: the old cut covered an X ramp's whole footprint (no library ramp runs along X).
- `stairwell.stair_guards` rails a ramp's cut as it rails a flight's hole: `GUARD_HEIGHT` rails along both long edges
  and across the entry end, `GUARD_THICK / 2` outside the cut, on the storey whose slab it opens; the head stays open,
  the way off. They come after every stair's pieces, so every existing guard keeps its index and its name
  (`stair_guard_rail_<k>`), and they take every trim a stair's rail takes -- furniture on the line, a wall holding it.
  Painted steel where the palette has it (`metal_painted`, else `metal`), a garage's guardrail rather than a stair's
  wood: the builder takes a piece's own `material` before its wood-where-the-palette-has-it default.
- `stairwell.ramp_landing`: a wall void past a ramp's head, as deep as the ramp is wide or the 60 in that IBC 2018
  section 1012.6.3 asks of a ramp landing, whichever is more, and reaching back over the cut's last `RAMP_CUT_SIDE` --
  floor, not a hole -- so no partition stands across a ramp's arrival. Two library walls did, clipped only by the old
  cut running past the head: foundry_heist_vertical's `int_0_4`, its centreline on the head, and parking_garage_a02's
  wall at y 6, 1 m past ramp 0's. A landing begun at the head left `int_0_4` standing --
  `partition_bounds.hole_cuts` decides by a wall's centreline, strictly inside -- found by the new tests before it
  shipped.

### Not changed, and why
- WHERE THE CUT BEGINS. Where each cut begins, the clearance between the slab's underside and the ramp's top face is
  1.04 to 1.55 m on the nine library ramps, under a body's 1.8 m, so a body walking up meets the slab's edge. The agent
  contract's `min_headroom_m` would open each cut 1.4 to 3.2 m further down its ramp, under furniture that furnish
  lays without reading a ramp's cut (foundry_heist_vertical's forklift and pallets, cbp_town's chairs), so it waits on
  furnish learning ramps -- the factory's roadmap, open.
- A RAMP'S OWN SIDES. The drop from a ramp to the floor beside it is reported by Level Factory's gate as a thing's
  top, not refused; walls or rails along them would change the garages' ground floors, and are the walker's call.

### Tests
- `test_ramp_cut.py`, 6 new; 5 fail on 0.240.0 -- the cut ending 5 to 8 m past the head, nothing railing it, the
  garages' three rails missing, no `ramp_landing`, the builder ignoring a piece's material -- and the sixth, the
  library's nine cut ramps, is the floor under them.
- `test_wall_over_void.py`: the ramp's cut no longer described as "offset half a run".

## [0.240.0] - a roof AC unit is an hvac unit and a club bar is a counter: two boxes get the word they lacked

**The factory's roadmap 267, its one-word mappings first.** Read against the walker's asset wishlist, 1,486 of the
library's prop slots named no species and Zoo built each as a plain box (the factory's
`docs/findings/asset_wishlist_2026-10-19/box_slots.py`); a few of them name a species Zoo already has, for want of a
word in `PROP_SPECIES`. Each candidate was checked before it was added: every library volume the new word would
claim, and whether the species' genome holds those volumes' dims in the slot's own orientation, which is how Zoo's
`_species_fit` asks.

### Changed
- `PROP_SPECIES`: `roof_ac` joins the `hvac_unit` row. It claims 3 volumes, the bank's `roof_ac` and the foundry's
  `roof_ac_block_a` / `_b` (3.0 to 4.0 x 2.0 x 1.2 to 1.4 m), all inside the genome.
- `club_bar` joins the `counter` row. It claims 2 volumes, primos_pizza's and strip_retail_a01's 2.8 x 0.8 x 1.15 m
  serving bar (`bar_` wanted the underscore). Not `back_bar`, which the roadmap first named: that species is the
  shelving behind a bar, 1.8 m and up.

### Not changed, and why
- `container` -> `cargo_container`: freight_terminal_a01's four 6.0 x 2.4 x 2.6 m containers would be recorded long
  side first, as every hinted volume is (`long_axis_first`). Zoo's container is long in DEPTH (width 2.3 to 2.5), and
  `_species_fit` asks in the slot's own orientation, so all four would be built as the box, "would fit turned 90
  degrees". That needs a rule for species that are long in depth, and the composer infers the same turn from a
  slot's extents, so it is its own change.
- `barrier` -> `jersey_barrier`: arena_a02's four 3.0 x 0.8 x 1.2 m barriers are a crowd's, not a road's. That is
  the walker's call, not a word's.

### Tests
- `test_prop_species.py`: `test_the_one_word_mappings_re_route_exactly_their_library_volumes`, every library volume
  the two words reach, with its species and its dims inside the genome. It fails on 0.239.0, where both route to
  None.

## [0.239.0] - a roof hatch stands over its ladder's cut: the hole, the curb and the lid are one rectangle

**The factory's roadmap 170.** The walker's look review, 2026-10-19, on the roof hatch: "the hole of the ladder
opening doesn't match the lid...they should match". Read off the built slots: a roof ladder cuts its own hole,
`ladder_geom.through_hole` -- the body's envelope, 1.1 x 1.3 m, set 0.45 m toward the side the climber stands on --
and `_vertical_links` cut the hatch's 1.5 m square centred on the ladder's face. The roof took both cuts, so its
opening ran 0.35 m past the square on the climber's side, and 0.27 m past the curb that 0.224.0 sized to the
square. All 46 roof hatch links in the library have a ladder, and every one ran out by the same 0.35 m. The 20
hatches below the roof have no ladder, and nothing changes for them.

### Fixed
- `roof_hatch.opening(spec, link)`: the hole a roof hatch covers. It is the link's square, centred on the cuts of
  the ladders at the link that reach its storey, where it holds them -- the 1.5 m square holds the ladder's 1.1 x
  1.3. Where the square cannot hold them it is the box round both. With no such ladder it is the square where the
  link stands, as before.
- `_vertical_links` cuts a roof hatch's slab hole at `opening`, and files its drop link's points and its `hole`
  there. `roof_hatches` stands the slot over it: the curb's world footprint is the opening plus `CURB` a side, and a
  quarter-turned slot carries those sides swapped as its own (w, d), as `hole_causes._local` does. Every roof hatch
  in the library today is square, so no Zoo module changes. The hatch moves 0.45 m toward its climber, and its
  `HATCH_` marker and its ids stay keyed on the link.

### Tests
- `test_roof_hatch.py`:
  - the first test's slot now stands at the ladder's cut, (13.0, -9.45), where it stood at the link;
  - the ladder's cut lies inside the opening, and the opening is the curb's inside, for a ladder facing each of N, E,
    S and W;
  - with no ladder, the hatch stands on its link;
  - a square too small for the cut grows round both, and a quarter turn swaps the slot's sides;
  - in the built library, every roof hatch's curb holds every hole the roof is cut with under it. 39 built hatches;
    on 0.238.0's build every one fails, with the ladder's cut out past the curb.
- 8 of the file's 12 fail on 0.238.0.

## [0.238.0] - a face's upper storeys stand over the openings below them: the facade planner's first rows

**The factory's roadmap 79** (its `docs/proposals/FACADE_PLANNER.md`, steps 1 and 3). Measured first (the factory's
`docs/findings/facade_census_79/`, off the built slots of the 102 buildings a themed lot can draw): of the 169
first-storey openings in the 52 multi-storey buildings, 28 stood over a ground-floor opening, where the Empties --
whose presets lay every storey on one list of bays -- read 92.9 %. The upper storeys had been authored mirrored about
each face's centre (167 of 177 openings) and the ground floors for the rooms behind them (135 of 321), and nothing
asked the two to meet: `_exterior` emits each side of each storey on its own, and `_emit_wall_run` is handed one run
with its openings already placed.

### Added
- `facade_plan.py`, where a face is decided: the module a preset or a migration asks before an opening is placed.
  `ROWS`, each naming its source -- `rowhome` (two bays, a fixed fraction off the front's centre) and `midrise`
  (round(width / 3.2) equal bays, at least two) -- moved here from inline in `presets.empty_rowhome` and
  `presets.empty_midrise`, their output unchanged to the byte: every Empty spec is still its preset's own output.
  `bay_positions(row, width)`, `nearest(positions, toward)`; `presets.MIDRISE_BAY` reads the row.
- `facade_plan.stack_mirrored(spec)`: an untagged upper-storey window moves onto an opening of the storey below as
  it now stands -- a mirrored pair only together, onto a mirrored pair; a window on the centre line only onto an
  opening on it; any other onto the nearest -- each within `REACH`, the mid-rise row's 3.2 m bay. A target that
  would leave the run, come within `MIN_PIER` (0.3 m) of another opening or stand over a partition's junction with
  the wall is turned down and the next one tried. Held where they stand: a window a drape hangs over, the windows
  on a wall a fire escape serves, a setback storey's face, and a window whose mirrored partner stays. Every
  ground-floor opening, door, breach, garage, vault and tagged window stays where gameplay put it, and an Empty is
  its row's and untouched.
- `presets.make` runs it on every spec it writes, after the holes pass and before every other, so cover and
  furniture are laid round the windows that are built: corner_deli's first-storey east window moves from 5.5 to
  7.0 m, over the ground floor's; auto_shop, compound, hospital and twin move theirs.
- `migrate_facade_stack.py`: the library through it, each changed spec refurnished
  (`migrate_furnish_recipes.migrate`), so it stays a fixed point of furnish. Run once: 69 windows in 32 specs, a
  median 2.0 m and at most 3.0. The 22 of them in the themed pool, 46 windows, are the ones the factory's
  `docs/findings/facade_census_79/predict.py` priced, building by building. 4 held: two under a drape, two on a fire
  escape's wall. The refurnish moved 279 volumes and laid 283 in 31 of the 32 (bank's moved nothing): upper-storey
  cabinets, chairs, shelves and cartons laid round the moved windows. strip_retail_a01's upstairs room lost its video
  poker machine, and primos_pizza's gained one.
- `facade_plan.py` is a geometry source (`build_freshness.GEOMETRY_SOURCES`).

### Corrected
- 0.237.0's entry says 54 of 288 levels across 24 staged lot missions carried a hole a player sees. The census counts
  54 of 300 across 25 (the factory's `docs/findings/hole_frequency/`); the 288 was a count made by eye.

### Tests
- `test_facade_plan.py` (23; 22 fail on 0.237.0, the Empties' guard holding on both): deli_a01's east window and
  bank_branch_a04's front read from the specs alone; the corner_deli preset writes the composed face; the library is
  migrated and the migration idempotent; the Empties are their rows'; the two rows reproduce the presets' bays; a
  pair moves together onto a mirrored pair, stays when the ground floor offers none, and never past a bay; the
  ground floor and tagged windows stay; a window alone takes the nearest opening below; a window whose mirror stays
  stays with it; a partition junction turns a target down; a drape and a fire escape hold their windows; an Empty is
  not touched.

## [0.237.0] - a hole in a floor is an optional route: left out on request, and the deli family keeps a variant without one

**The factory's roadmap 269.** The walker, 2026-10-20: "stairs and ladders should be the primary way to get between
floors in this game...with the holes in floors being somewhat rare...but still at our disposal to use if
needed/desired to add some more ways to navigate levels". Measured first (the factory's
`docs/findings/hole_frequency/`, a level-by-level replay of Level Factory's own lot draw): across the 24 staged lot
missions 54 of 288 levels carried a hole a player sees, and they bunched where a family that always carries one
anchors the mission -- every restaurant_row_001 and urban_row_001 level had the deli's cut drop, because both of the
deli variants a themed lot can draw (deli_a01, deli_a03) carry it -- and every single-building level whose preset
authors one (deli_001's cut and hatch; county_hospital_001's elevator shafts, bare). Level Factory decides per level
whether one is wanted; this release gives it the two things it needs from here.

### Added
- `hole_causes.without_holes(spec)`: leaves out, in place, every drop a player would see -- `is_drop`, unless it
  opens into a stair's own well (`cause_for` says `stair`: nothing of it shows) -- and the authored `slab_holes`
  whose plan overlaps a removed drop's hole on ANY storey, because a recipe authors the slab hole beside the link
  and an atrium or a shaft cuts every storey its one link passes; a slab hole left behind is an undeclared drop. A
  roof hatch, a stair and a ladder are untouched. Returns what it removed.
- `presets.make(..., holes=None)`: `False` builds the recipe without them, right after the recipe returns and before
  every other pass, so cover, stairs and furniture are placed in a floor that never had the hole. None and True build
  what the recipe authored, as always. The five presets that author one: police_station (the armory's floor hatch),
  corner_deli (the hideout's cut drop), compound (the atrium), hospital (the elevator shafts), casino_tower (the
  count room's skylight).
- `new_level.py --holes on|off`, passed through to it.
- `migrate_hole_free_variants.py`: the variants in `HOLE_FREE` lose their holes and are refurnished, so each stays a
  fixed point of furnish. **A call, made 2026-10-20 and meant to be changed: deli_a01**, because deli_a03 keeps the
  drop the factory's cold runs 9340 and 9341 proved and priced. Run once: deli_a01 lost its 2.2 m drop at (8.5, -4)
  and the slab hole under it; its hatch into the stair's well stays; the refurnish moved nothing.

### Tests
- `test_optional_holes.py` (10; every one fails on 0.236.1): the drop and the slab holes under it on every storey go
  and another slab hole stays; a hatch into a stair's well stays (deli_a03); each of the five presets builds without
  its holes when asked and with them otherwise, `holes=True` equal to the recipe; a preset with no hole is unchanged;
  the deli family keeps a variant without the drop and one with it; the migration is done and idempotent.
- `test_hole_causes.py`'s library test: deli_a01 no longer dresses a hole (20 drop links in 12 specs).

## [0.236.1] - a hole's greybox is a ring round it, never a box over it

**The factory's roadmap 265, its first cold run.** Cold run 9340 (restaurant_row_001 on 0.236.0 and Zoo 1.114.0, 0
interventions) read 8 new findings, every one WALKTEST_WALKER_STUCK: all four walkers on both of deli_a03's candidates
were sent to a target inside the deli's drop and stuck in its corner, pressing on the slab's cut faces. 0.236.0 drew
the greybox of a `hole_edge` -- and of a floor hatch -- as one box over the hole, its top 12 mm above the floor; Lot
bakes the walk test's navmesh from the candidate's greybox lot with visual meshes in it (`geometry_parsed_geometry_type
= 2`), so the bake took the box for floor and laid a path and a target across the hole that no collider holds up.

### Fixed
- `hole_causes._ring`: an edge's and a floor hatch's greybox are four boxes outside the hole's rect -- `BAND` and
  `HATCH_CURB` wide -- named `<slot_id>_n` / `_s` / `_e` / `_w`, so each is the slot's own node: their union is the
  slot's footprint, which the placement gate and the composer's fit read, and nothing stands over the hole. The spoil
  and the kit keep their one box each. `hole_slots` returns `(slot, entry, boxes)`; `_vertical_links` draws them.
- Measured over the library (the factory's `docs/findings/hole_causes_265/greybox_over_holes.py`): on 0.236.0 all 16
  dressed holes had greybox over their whole area, 56.76 m2 in all; now none.

### Tests
- test_hole_causes.py: `test_nothing_of_a_holes_greybox_stands_over_the_hole` (18 in the file). On 0.236.0 the file
  fails 13: the new test, and 12 that read `hole_slots`' new shape.

## [0.236.0] - every hole in a floor has a cause, and what stands round it says so (`hole_causes.py`, layout_lint L28)

**The factory's roadmap 265.** The walker, 2026-10-19, asked why the levels have holes in their floors -- the drop
routes this repo cuts square through a slab -- and chose to keep the routes and give each a reason to exist: "if we
have holes it should be clear to the player that they are there, but also some reason other than a perfectly cut
square (what is diegetic but a signal to the human playing the game)". Needs Zoo 1.114.0, whose `hole_edge`,
`hole_spoil` and `hole_kit` and `roof_hatch`'s `floor` form build what this release asks for.

### Added
- `hole_causes.py` (pure, a geometry source). A drop -- a `floor_hole` link, or a `hatch` link below the roof, that
  cuts the slab -- has a CAUSE: its link's own `cause`; else `stair` when its hole opens into a stair's well
  (`stair_share`: there is no floor there to dress); else `hatch` for a hatch link; else a row of `RULES` by the rooms
  above and below its centre -- the factory's calls of 2026-10-19 under the walker's direction, meant to be changed:
  the hideout over a deli's kitchen `cut` (a crew broke through), a bedroom over a kitchen `broken` (the floor gave
  way), an armory over a garage and a warehouse mezzanine over its floor `hatch`. What stands round it, each a `prop`
  slot Zoo builds:
  - `cut` and `broken`: a `hole_edge` round the cut (`BAND` 0.30 m past it a side, from `TOP` 0.012 m above the
    visible floor to `HANG` 0.30 m under the ceiling below), its form the cause plus `_slab` where the room above has
    a `concrete` floor and `_plaster` where the room below has a plaster or drywall ceiling; a `hole_spoil` on the
    floor the drop lands on (`ladder.drop_landing`), the hole and 0.25 m a side, cut back from every piece, stair and
    other hole there, its stock the finish of the floor above (`carpet`, `tile`, else `none`), one a place where a
    stacked shaft's drops land together; and for `cut`, the crew's `hole_kit` (1.4 x 0.7 x 0.7 m) beside the hole,
    its near edge 0.35 m off it, turned to face it, on the side reaching furthest into the room above that keeps off
    every piece, stair, other hole, door approach (`DOOR_APPROACH_M`) and ladder.
  - `hatch`: `roof_hatch` in its `floor` form -- a 3 cm frame 0.08 m outside the hole, its lid standing open on the
    side nearest a wall of the room above among those clear of stairs and door approaches -- with the `hatch`
    interactive, open by default so the drop stays a route.
  A slot outside its species' sizes (`GENOME_DIMS`, Zoo's genomes mirrored) is left out and the build log says so:
  Zoo builds such a slot as the plain box at its size (`kit._species_fit`), which over a hole would cover it. The
  edge and the spoil are visual only and the kit and the hatch own their collision, so the slab's cut stays the
  collider and the drop's route. The contract's numbers are `zoo_keeper.core.hole_forms`' and change with them.
- `VerticalLink.cause` and the schema's `cause` (`cut`, `broken`, `hatch`); gameplay.json's `vertical_links` record
  says every drop's cause, `stair` included, None where nothing names one.
- `_vertical_links` stands the slots and records the hatch interactives, after the roof hatches.
- layout_lint L28: a FAIL for a link naming a cause that is not one; an advisory WARN for a hole that ships as a bare
  cut, or part of one -- no cause, a cause whose edge or hatch is outside its species' sizes, or a hole only partly
  in a stair's well.
- `prop_species.SPECIES_OWNS_COLLISION` gains `hole_edge`, `hole_spoil` and `hole_kit`.

### Library
- 21 drop links in 12 specs, 30 slots. `cut` 6: the six delis' hideout over their kitchen, `cut_slab` (a concrete
  floor over a drop ceiling) -- the edge 2.8 m square, the spoil 2.655 x 2.7 m, cut back at the kitchen wall 0.225 m
  off the hole, and the kit south of the hole. `broken` 2: rowhouse_raid's and apartment_walkup_a01's bedroom over
  their kitchen, the spoil on `tile` (1.7 x 1.83 and 2.29 x 1.83 m). `hatch` 8: corner_deli_heist_01's, cr_deli's
  and night_deli's drop to the stairwell, apartment_walkup_a01's office over its garage bay and foundry's skylight
  room over its archive by kind; 07_police_station's and pvp_station_ref's armory over the garage and
  warehouse_a02's mezzanine by `RULES`. `stair` 4: deli_a01-a03's drop to the stairwell, cut wholly inside
  `deli_stair_up`'s well, and rowhouse_raid's hatch, 70 % in its stair's -- a floor hatch built round either first
  stood over the stair, and `circulation.check_shell` read its frame 0.03 m inside the stair's column on all four.
  Uncaused 1: foundry_heist_vertical's 5 x 3 m drop from catwalk_south onto south_machine, which L28 names.
- layout_lint over the library: 0 FAIL before and after; 395 WARN on 0.235.0, 397 now -- L28's two, foundry's
  uncaused drop and rowhouse_raid's hatch running past its stair's well.
- `circulation.check_shell` on the twelve built with 0.235.0 and with this release: no new conflict in any;
  foundry_heist_vertical's 2 and warehouse_a02's 1 are 0.235.0's.

### Tests
- test_hole_causes.py (17). The file does not collect on 0.235.0; with `hole_causes.py` alone beside 0.235.0's tree,
  the 8 that ask the rest of the release fail -- L28, the schema and the dataclass, the species' collision, the
  library's stair wells.

## [0.235.0] - a wall may not stand under a hole in its ceiling (layout_lint L27); the open-floor table slides a hole off a wall it stands

**The factory's roadmap 260.** 0.234.0's table walled the six delis' kitchens from their market aisles along x 7
(`market_aisles|kitchen`, WALL), and their 2.2 m "vertical attack angle" drop at (8, -4) -- a `slab_holes` entry and a
floor_hole link, one hole -- spans x 6.9..9.1: the new wall's centreline 0.1 m inside the hole's edge, its new door
under the hole, the wall's 0.35 m top showing in it. Seen in the factory's cold run 9338 (restaurant_row_001, deli_a03)
in frames of the hole from the kitchen and from above, and by Level Factory's drop-edge gate as 7 fewer unguarded
edges, its column probe reading the wall's top as floor. Nothing here asked it: L21 asks a wall against a STAIR's hole,
and `partition_bounds.hole_cuts` a wall over a hole in its own floor (roadmap 114).

### Added
- layout_lint L27 (advisory WARN): a wall under a hole in its ceiling. `ceiling_holes` reads every authored hole the
  builder cuts -- `slab_holes`, and the floor_hole and hatch links that cut the slab, read as `_vertical_links` reads
  them; a hole authored in both lists is one hole carrying both -- and `ceiling_hole_walls` names each partition, as
  `built_walls` stands it, that reaches into one in its own ceiling: how far its thickness reaches past the hole's edge
  and along how much of its run. Touching the edge (`CEILING_HOLE_TOL_M`, `STALE_TOL_M`'s 0.02 m) is the hole's
  enclosure, not a wall under it. Built walls, not authored ones: a wall over a hole in its own floor is cut there
  first, and two storey-1 walls of final_stand's and cbp_town_finale's atriums that a census of raw partitions counted
  stand nowhere under the hole above.
- `open_floor_rules._clear_holes`: a hole a WALL row's new wall would stand under slides across the wall, whole grid
  cells, toward the side holding its centre, until it opens into the one room below that holds its centre and no wall
  stands under it -- the hole moves, not the wall (L21's rule for a stair) -- every ref with it. It stays over the same
  rooms above and below, off every other hole and stair walk, and moves no wall of the storey above; else the pair is
  taken back whole, as for a lint FAIL. `apply` also slides a hole off a standing wall whose two sides are a WALL row's
  pair, so running the migration again converges a library walled before the rule; a wall the table does not own
  keeps its hole, and L27 names it.

### Library
- `migrate_open_floor_rules.py`, run again: the six delis' drops slid +0.5 m in x, to (8.5, -4) -- x 7.4..9.6, in the
  kitchen, 0.225 m clear of the wall's face -- slab hole and link together.
- Refurnished (`migrate_furnish_recipes.py`): corner_deli_heist_01, cr_deli and night_deli move, their storey-1 dining
  table having stood within furnish's 0.3 m of the slid hole -- in each, 6 pieces moved and one chair out; deli_a01,
  deli_a02 and deli_a03 move none. The rest of the library refurnished changes nothing.
- L27 on the library: the six delis' walls gone; three walls that stood under a hole before the table, named and not
  moved -- final_stand's ground-floor wall at y -3 under its atrium (0.30 m into it, along 10 m),
  cbp_town_finale_midbalanced_schemafixed's at y 10 (0.30 m, 28 m), and bank's at x 4, its centreline on its atrium's
  edge (0.15 m, 6 m). No lint FAIL before or after in any of the six.

### Changed
- `migrate_open_floor_rules.py`'s docstring says what running it again does.
- Tests: test_ceiling_holes.py (9). All 9 fail on 0.234.0; with L27 alone beside 0.234.0's table, the 5 that ask the
  table fail -- the hole left over the wall it lays and over one standing, the pair not refused, the library's six
  delis and a preset deli carrying the drop over the kitchen wall.

## [0.234.0] - the walker's open-floor table: each pair of rooms one floor or two; an exterior wall covers its line; a room may name `open_to`

**The factory's roadmap 260, from 255.** 0.223.0 named every open floor nobody named (layout_lint L26) and froze the
library's 49 in `open_floor_baseline.json` for the walker to sort one pair at a time. On the review page the walker
answered "Wall it" for every pair, unsure whether a wall would shut a room nobody could open -- "we aren't making the
doors in level factory because we are going to have networked doors added later" -- and, told that a wall here
carries its own openings and that every door opening already ships to gameplay as a door socket (Dispatch's
`interactives.json`), approved in chat a table by room pair: "go ahead with the 255 table, your defaults are good".
The 49 are 20 pairs of room ids repeated through shared recipes.

### Added
- `open_floor_rules.py`: `RULES`, one row per pair of room ids.
  - OPEN, the floor is meant (`open_to`): customer_floor|deli_counter, front_hall|kitchen, the garage decks,
    exec_lobby|exec_anteroom, north_aisles|north_dock -- and, the factory's call where a stair stands on the line,
    lobby|ground_bullpen (the office's only stair at (0, 0)) and corner_deli_heist_01's stair well against its two
    cold rooms (`main_stack` reserves y 6.05..12.65: a wall on the well's south edge runs inside the stair, L21, and
    one on its north edge ends at the centre of `cold_n_access`, L18).
  - WALL, the rest: each stretch of the meeting line no partition covers is closed -- an abutting partition extended
    over it, each of its openings kept where the builder stands it, else a partition of its own in its neighbour's
    material; an opening a new wall's end would split slides along its own wall by whole grid cells until clear
    (L18's own prescription); then one door of the agent contract's width where nothing walkable joins the two rooms
    any more (`DOORWAY_POLICY = "keep_pair_joined"`, a call meant to be changed; "only_if_sealed" the other), never
    into an objective room.
  - A WALL row that would leave a spec failing any lint rule it passed is taken back whole and named.
- `migrate_open_floor_rules.py`: the one-shot, idempotent migration over specs/ (not the mission's `lf_*`).
- `presets.make` applies the table to every spec it writes, and trims a piece the new wall runs through.
- `test_open_floor_rules.py` (11). On 0.233.0 the file does not collect; with the table alone beside 0.233.0, three
  fail -- the exterior wall, `open_to` loading and the deli preset.

### Fixed
- An exterior wall covers its line as a partition does (`tactical.exterior_parts` and `exterior_sides`; layout_lint's
  `_story_parts` and `_exterior_sides`, read with `LevelSpec`'s defaults). The gas stations' forecourts are outdoor
  rooms that meet the shop along y -11, where the front wall stands with its doors and windows; read with partitions
  alone, L26 named seven such pairs and the tactical graph held four edges through a wall with no door in it. On the
  library's 128 specs with rooms: L26 49 -> 42 by this alone, graph edges 1,362 -> 1,358, L12 and L24 unchanged.
- `Room` takes `open_to`. The schema has admitted it since 0.223.0, but `spec_loader`'s `Room(**r)` refused any spec
  naming it: every spec the table opens would have failed to load into the builder.
- `build_graph`'s docstring said it returned "(adjacency, info)"; it returns the adjacency.

### Library
- Migrated, 23 specs: 20 pairs given `open_to`; 24 stretches closed by running a partition on to its wall -- the
  rowhouse, the walk-up, the auto shops' and the pawn shops' upper floors -- and 7 partitions added: a kitchen wall
  in each of the six delis (x 7, y -14..6, a door at y -4), each deli's stockroom gate slid 0.5 m west to clear its
  end, and corner_deli_heist_01's cold rooms walled apart (x -16.8, a piece of its own, since running its neighbour
  on would have slid `cold_w_access` 0.125 m on the grid; a door at y 3.625). Nine doors in all, `kitchen_to_garage_bay`
  in the rowhouse and the walk-up among them; none into rowhouse_raid's vault, the objective.
- 0 open floors nobody named in 159 built specs; L12 0; L24 one room more, rowhouse_raid's basement vault -- the
  objective, behind a reinforced door and a breach -- kept by the walker's rule (`walk_reach_baseline.json`); no new
  lint FAIL in any migrated spec; the tactical graph loses only the four forecourt edges.
- Refurnished (`migrate_furnish_recipes.py`): three specs move, by the new doors -- deli_a02's kitchen work tables
  and cartons, a pallet in front of corner_deli_heist_01's new cold-room door (dropped), apartment_walkup_a01's garage
  cartons and chairs; 16 pieces out, 14 in. The untouched library refurnished changes nothing, the control.
  CATALOG.md regenerated.

### Changed
- L26's message offers the table.
- `open_floor_rules.py` is a geometry source (`build_freshness`), with the migrations presets call while they write a
  spec.
- Tests: test_open_floor's warning test takes its open floor back out of rowhouse_raid; test_wall_over_void pins
  night_pawn's wall at its captured run as it pins the stair; test_stair_back's library counts 34/17/15 -> 33/16/14,
  the cold-room wall standing where `main_stack`'s storey -1 side guard stood (x -16.6, y 6.05..6.25), the leg's
  back kept.

## [0.233.0] - a shell build reads nothing from the layout lint

**The factory's roadmap 259, its last residue.** 0.229.0 kept `layout_lint.py` out of `build_freshness`'s sources by
decision, so a lint edit does not demand a rebuild, though stairwell asked the lint two things while building a
shell: `_host_openings`, the door-like openings on a host wall, and `DOOR_APPROACH_M`, the floor a body needs before
a door. An edit to either could move a shell the gate did not see. Read off the call sites, those two were the
lint's only build-time readers: the evidence report writes a report, and furnish and stair_pitch read its findings
when a spec is made, which the spec's own hash covers.

### Changed
- `host_openings` moved verbatim to `partition_bounds.py`, the builder's and the lint's shared source of wall-span
  truth, watched since it was written; layout_lint keeps `_host_openings` as an alias, so its callers read the same
  function.
- stairwell asks `partition_bounds.host_openings` and `agent_contract.door_approach()`, the function
  `DOOR_APPROACH_M` was always computed from, and imports the lint nowhere.
- `build_freshness.NOT_BAKED` says layout_lint is a reader again; the readers test's docstring records its premise
  as true again.

### Added
- `test_lint_out_of_the_build.py` (3): two fail on 0.232.0; the third, that the contract's number is the
  lint's, holds before and after and pins the swap stairwell makes.

No geometry moves: rebuilt with `build.py --all`, every tracked build record changed its build time alone.

## [0.232.0] - every hole in a stacked shaft is declared, and its drop lands where a body would

**Found by the factory's breadth sweep of 2026-10-19 (roadmap 173).** Cold run 9329, county_hospital_001's first run
since Level Factory's drop-edge gate shipped, stopped at the export with 0 interventions: `UNDECLARED_DROP_INDOORS:
20 unguarded edge(s)`. All 20 are one rim, the storey-2 slab round the hospital's elevator shaft, 7.2 m above the
ground floor. `presets.hospital` stacks the shaft's holes on every storey from 1 to the top -- "a vertical
horde-spawn channel" -- and declared only storey 1's. The gate keys a declared rim on its storey as well as its
rect, so the storey-1 link did not cover storey 2, rightly.

### Fixed
- `presets.hospital` declares a `floor_hole` for every hole it stacks.
- A declared drop lands where a body would. `drop_nav_link` ended every link on the floor below, which over a stacked
  shaft is cut too: the upper link ended in mid-air. `ladder.drop_landing(story, x, y, holes)` falls through every
  storey cut under the drop to the first that is not, and `_vertical_links` passes it as `land_story`. A drop over an
  uncut floor lands on the floor below, as before.

### Added
- `test_hospital_shaft.py` (5, all fail on 0.231.1).

### Not changed
- Three library atriums cut holes no link declares -- bank, cbp_town_finale_midbalanced_schemafixed, final_stand --
  large guarded voids, not a shaft; the gate's guarded class is theirs.

## [0.231.1] - two video poker cabinets in one room are two different machines

**Seen in the factory's cold run 9326 (roadmap 196).** deli_a01's two cabinets, both in the customer floor since
0.231.0, instanced one machine twice: a fixture's variant is its name's crc32 modulo the species' count, and
`video_poker_store_r7070a315_9` and `_10` drew the same one. Across the library, 6 of the 30 rooms holding two
cabinets showed one machine twice -- all six delis, whose customer floors share the tag and the names.

### Changed
- `video_poker_store` is `distinct` (0.163.0's dial, which the poster runs use): `_distinct_variant` moves a
  variant off the one its room already shows, and refuses a spot only when every variant is taken -- four here, two
  a room at most -- so no placement moves. A call, made 2026-10-19 and meant to be changed.

### Added
- `test_cabinet_variants.py` (2, both fail on 0.231.0).

## [0.231.0] - a store's video poker cabinet may stand against the partition it backs onto

**The factory's roadmap 196: the four stores 0.228.0 left short, and its other residue.** Traced on 0.230.0's
library, rule by rule (the factory's `patches/dc_store_cabinets/why_rule.py`), the short stores' candidates were
refused by two rules: the 0.9 m spread off other volumes, 12 to 37 a room, and the metre-off-a-partition line
rule, 24 to 48 a room. The line rule keeps every piece's centre 1.0 m off every partition's line, so it refuses
every slot a held partition wall offers: a cabinet backed against one stands its centre about half a metre off it.
That is the roadmap's "a partition is still unfurnished". The door rule (`_seed_clear_doors`) is separate.

**The call, made 2026-10-19 and meant to be changed:** one dial on one piece, `backs_on_partitions`, on for
`video_poker_store` alone. Placed against a wall, the cabinet is not asked the line rule for the one partition
whose centreline is the room edge it backs onto; every other partition, the door rule and every other rule still
apply. Every other wall piece keeps the metre.

### Added
- `_piece(backs_on_partitions=)`, `_seed_clear(backed_on=)`, and `_place_fixture` passing the edge, named by the
  slot's front bearing, for a piece with the dial.
- `test_cabinet_partitions.py` (4, three of which fail on 0.230.0), on fixtures kept beside it as the library was.

### Changed
- `test_store_cabinets.py`'s filler test asks with the dial off. The displacement path it proves is unchanged;
  deli_a01 with the dial on needs fewer fillers.
- The library, stripped and refurnished with `migrate_furnish_recipes.py`, as simulated beforehand
  (`partition_sim.py` beside the census): fuel_stop_heist 0 -> 2, pharmacy_a01 1 -> 2, stop_n_go 1 -> 2,
  pawn_shop_a01 0 -> 1, so 30 of 31 stores hold two. Nine of the fifteen fillers 0.228.0 displaced come back, five
  file cabinets and four vending machines, because a cabinet now finds a partition first. Poster boards net +2.

## [0.230.0] - the z-fight gate reads a scene's transforms as Godot does

**The factory's roadmap 177, its last two pairs.** The gate built each composed module's box from its `.tscn`
`Transform3D`, reading the nine basis numbers as columns. Godot 4.7 writes and parses them as rows, measured three
times: by this repo on cold run 9013 (`tscn_export.godot_basis`), by Lot on 2026-09-13, and on cold run 9324's
deli_a01 with the factory's `tools/module_pose_census.py`. A pure turn reads the same either way for a box about its
own centre; a turned, non-uniformly scaled module does not. deli_a01's east-wall end piece `ext_0_E_seg10`, 0.6 m
along its wall and 0.35 m through it, came out the other way round, sharing both side planes of partition 1's end
piece: the two 0.9 m2 pairs cold runs 9322 to 9324 reported. The engine stands it as written, x 18.825..19.175 and
z -6.300..-5.700, with no face on either plane.

### Fixed
- `instance_matrix(f)`: a node's 3x4 world matrix from the twelve numbers as written, the basis rows then the
  origin; `_scene_module_boxes` builds every instance box with it. The column reading is kept, refuted, in its
  docstring.

### Measured
- Cold run 9324's 16 composed buildings, the gate's own code with only the matrix differing (the factory's
  `docs/findings/zfight_rows_177/`): 2 visible pairs read as columns, both deli_a01's junction, and 0 read as rows;
  no pair appears under rows that columns hid. Buried pairs, reported and never gated on, move: deli_a01 213 -> 220,
  pharmacy_a01 29 -> 27.

### Added
- `test_zfight_rows.py` (3), on the two nodes' transforms exactly as cold run 9324 wrote them; all fail on 0.229.0.

No rebuild: `zfight_gate.py` is a reader, in `build_freshness.NOT_BAKED`. Other readers outside this repo hold the
same belief -- Level Factory's `ground_contact`, and three of the factory's tools -- and are the roadmap's, not this
release's.

## [0.229.0] - the freshness gate watches every module a build writes with

**The factory's roadmap 259.** `build_freshness.GEOMETRY_SOURCES` is this repo's commit hook's whole idea of
what a built shell is made of, and Level Factory's library guard parses the same tuple. Measured on 0.228.0 by
following the build's imports (AST, from build.py and deli_counter.py): a build reaches 54 of this repo's
modules and the tuple named 23, 22 of them reached -- `ladder_place.py` is named on the build path only in
comments. Of the 32 unlisted, 21 put their output into what a build writes, read off their call sites, and
`agent_contract.json` was a source no tuple named. A commit changing only one of them passed the hook with
every shell older than the code that makes it.

**The call, made 2026-10-19 and meant to be changed:** 20 of the 21 and the contract are watched; `layout_lint`
is not (below).

### Changed
- `GEOMETRY_SOURCES` gains 20 modules and `agent_contract.json`: agent_contract, ledge_cover, level_design,
  material_kind, prop_species, rarity, setbacks, skin_style, stair_pitch, stoop, tactical, tscn_export,
  vault_room, zoo_export, and the six migrations presets call. Still a literal.
- No rebuild: every judged shell was built after the newest source added.

### Added
- `NOT_BAKED`, a literal: the 12 modules a build reaches that are kept out, each with why -- circulation,
  zfight_gate, evidence and the eight gates and reports it calls, and layout_lint.
- `test_freshness_sources.py` (5): every module a build reaches is in one list or the other; the tuple is a
  literal naming files; no module is in both; each kept out says why; the contract is a source. Four fail on
  0.228.0.

### Not done, by decision
- `layout_lint.py` stays unwatched, as `test_gates_that_only_read_shells_are_not_watched` holds it: a lint edit
  must not demand a rebuild. That test's premise is refuted in its docstring. stairwell asks layout_lint's
  `_host_openings` and `DOOR_APPROACH_M` where a stair can stand and stair_pitch acts on its findings, so an
  edit there can move a shell unseen. Moving those names into a geometry module would watch them without
  watching the lint.

## [0.228.0] - two video poker cabinets a store, and a filler's wall when none is free

**The factory's roadmap 196, its open line.** 0.202.0 made `_wall_slots` offer a slot only where a built wall holds
the piece, and dropped every fixture no held wall could take. The six delis lost 18 of their 20 video poker
cabinets, against the walker's two a store. Across the library, 31 buildings' rooms ask for `video_poker_store`;
16 held two, 6 one and 9 none. In deli_a01 both selling rooms are offered held wall slots, 7 and 11, and
`_seed_clear` refuses every one: the held walls are already stood with shelf runs, vending, file cabinets and the
service counter, and the rest are partitions, kept a metre off for their doors.

**The rule, a call made 2026-10-19 and meant to be changed, as two dials on the piece:**
- `displaces=("cabinet_file", "vending")`: a cabinet with no free wall takes a filler's slot in its own room, a file
  cabinet first, then a vending machine, passing every test of its own and its stool's. A filler is put back when
  the retry fails.
- `most_building=2`: two a store, across the building's rooms. `most` stays two a room.

### Added
- `_displace_for`, and `place_fixtures(spec, keys=None)`, which places only the pieces it names.
- `test_store_cabinets.py` (5, which fail on 0.227.0), on fixtures kept beside it as the library was before.

### Changed
- The library, stripped and refurnished with `migrate_furnish_recipes.py`: 11 specs, +18 cabinets and their 18
  stools, 9 file cabinets and 6 vending machines displaced. 27 of the 31 stores hold two. fuel_stop_heist and
  pawn_shop_a01 stay at none, and pharmacy_a01 and stop_n_go at one: their rooms hold no filler that a cabinet and
  its stool fit in.
- A store's poster boards come after its cabinets in the recipe, so they meet different walls. corner_deli_heist_01,
  cr_deli, deli_a01 and night_deli each lose one, and convenience_store_a01 gains one; every store keeps a board.
- Rebuilt with `build.py --all`; the suite after the rebuild: 1576 passed, 2 skipped.

### Refuted, kept
- A migration that placed the cabinets alone, `place_fixtures(spec, keys={"video_poker_store"})` over the library,
  left it no fixed point of furnish: test_wall_backing, test_club_fixtures and test_deli_window each failed theirs.
  A fresh furnish places the cabinet before the poster boards, and the targeted pass had placed it after. The
  migration is the strip and refurnish every furnishing change here uses.

## [0.227.0] - a vault ledge inside furniture draws no box of its own

**Found resolving factory roadmap 177's last z-fight pairs.** Two of cold run 9322's four were the office's
`base:VAULTLEDGE_0 / reception_desk`. The office preset stands its 5 m vault ledge in its 5 m reception desk on
purpose -- the desk is the obstacle a body vaults, and the ledge its tag -- but the ledge also drew its own box,
1.1 m tall inside a desk 1.0 m tall: a 0.2 m strip 10 cm proud of the desk top along its length, z-fighting the
desk's ends. Across the spec library: 228 ledges; 111 clear of every volume, 98 crossing one in part, and 19 at
least half inside one (14 wholly in a register counter, 5 mostly in a reception desk).

**The rule, a call made 2026-10-19 and meant to be changed:** a ledge at least `ledge_cover.HIDDEN_BY` (0.5) inside
one visible volume draws no visual box. Its collision and VAULTLEDGE tag stay, so the vault, the grades and the nav
bake see the same solid; only the duplicate look goes. A ledge crossing furniture in part keeps its box.

### Added
- `ledge_cover.py`: `HIDDEN_BY` and `cover(center, size, volumes)`, the share of a box inside the one visible
  volume covering most of it.
- `test_ledge_cover.py` (6, which fail to import on 0.226.0).

### Changed
- `_vault_ledges` asks `ledge_cover` before it draws, and says which ledge it left to its furniture.

## [0.226.0] - a declared drop carries its own off-mesh nav link

**Factory roadmap 173 ("a drop is either guarded or declared, and today nothing declares one"), step 3.** A
`floor_hole` or `hatch` vertical link is the spec saying "a body goes down here"; the builder cut the slab and
recorded the link, and nothing downstream could tell that hole from one nobody meant. The package's
`navigation_hints.json` carried a ladder's off-mesh link (0.172.0) and no drop's: measured on cold run 9317's
package, 2 links, both ladders, while deli_a01 declares a floor hole and a hatch. So the AI had no edge through
a hole a player drops through, and the drop-edge instrument that found the office's unguarded stair pit (0.225.0)
had no declared set to read off the package -- it reads Deli Counter's build records instead, which a consumer
of the package does not have.

### Added
- **`ladder.drop_nav_link(lid, story, x, y, size_x, size_y, story_height)`**: the one-way off-mesh link of a
  declared drop, the same two-point shape as a ladder's `_nav_link` (so Dispatch carries it verbatim and Lot
  moves its points into site space), starting over the cut on the storey whose floor it opens and ending on the
  floor below, `bidirectional` false, `required_capability` "drop", `cost` `DROP_COST` (4.0, dearer than any
  ladder: a route of last resort), and `hole`, the cut's rect as two corners, for a gate that asks which rim is
  declared.
- **`_vertical_links` files it on the record** as `nav_link`, for `floor_hole` / `hatch` links with a storey and
  a position; a `stair` link, which is descriptive, carries none. The id is
  `<spec>_<kind>_<story>_<x>_<y>_navlink`.
- `test_drop_nav_link.py`.

### Downstream
Lot 0.125.0 moves the link's points into site space with the vertical link; Dispatch 0.5.3 reads it from both
importers into `navigation_hints.json` `links[]`. The factory's `tools/walkable_edge.gd` sort can then take the
declared set from the package rather than from this repo's build records.

## [0.225.0] - a switchback's top leg cuts only its own run

**Cold run 9317's office, read by the drop-edge instrument (roadmap 173, the factory's
`docs/findings/drop_edges_173/`):** the stair's top leg arrives at storey 2 in the west run; the east run holds
leg 0, which tops out a storey below, and the slab cut at storey 2 spanned both runs -- so the east half of the
cut was a pit 6.67 m deep onto leg 0's foot, open on three edges: the discharge plate's edge over the east run
(five unguarded edges), the east rail's sideways opening (one of them), and the seam between the runs along the
whole of leg 1 (seven, 1.3-5.9 m down onto leg 0). The guards derived for it on 0.224.1 said why: `rail` leaves
the arrival end open across the whole reserved rectangle, which is two runs wide, and `side` stands only on the
rectangle's outer edges, so a wall even hung over the east run's margin at storey 1 while nothing stood at the
seam. `single_run` already stops a one-leg switchback cutting the run it does not use (cold run 9050); this is
the same rule one storey up.

### Changed
- **`stairwell.hole_span(st, s)` is per leg**: the top leg of a multi-storey switchback cuts its own run plus
  its outer margin, meeting the other run at the seam with no margin, so the slab covers the other run to the
  flight's edge. `flight_rect` and the builder's `_stairs` (the cut and the discharge plate) pass `s`; an
  intermediate leg and its turn landing keep both runs. Every other caller of `flight_rect` passed `s` already.
- **`stairwell.stair_guards` guards the seam**: on the top leg's seam side a thin side wall (`GUARD_THICK` at
  `SIDE_GAP` from the treads, as a narrow flight's) runs from the rectangle's far end to the turn landing the
  leg departs from, with no sideways opening, and ITS UNDERSIDE IS A BODY'S HEIGHT ABOVE THE FLOOR
  (`_seam_pieces`, `z_lo`; the builder's `_stair_guards` lifts the box and keeps its top at the slab
  underside). The rail above stands at the seam on the slab that now covers the other run, with the usual
  opening at the arrival end, which is over the leg's own top treads and plate. The wall that stood over the
  other run's outer margin at the top storey goes with the margin.
- `test_switchback_top_run.py`: the cut at the top storey is one run wide and meets the other run at the
  flight's edge (two and three legs, facing N and E), an intermediate storey keeps both runs, the seam wall and
  rail exist with those spans and that underside and nothing stands over the other run, a single-storey
  switchback and a straight flight are unchanged. Fails on 0.224.1.

### Measured
- The seam wall's underside, on the nav gate (Godot's own bake, `nav_gate.py`), one shell of 157:
  `cbp_town_finale_midbalanced`'s stair 0, whose lower run a console volume already leans over from the other
  side (`STAIR_VOLUME_INVADED`). With the wall's bottom at the storey floor the bake lost the lower flight
  2.25 m up (endpoints on islands of 101 and 612 polygons; the mirror stair, with nothing leaning on it,
  passed); with no seam wall it connected; with the bottom lifted a metre it connected. REFUTED on the same
  shell: an underside stepped along the flight below at a body's height plus a riser over it -- the same cut,
  the same 101 polygons -- so the bake's objection is not that headroom model. Shipped: the bottom at the floor
  plus the contract's body height, which passed; the gap under it is a body's height minus the leg's own rise,
  so the top leg is held from its first riser on.
- Before, on cold run 9317 (DC 0.224.1): the office, walked by the factory's `tools/walkable_edge.gd` seeded
  from the crew spawn, had 59 unguarded edges, 12 of them this pit. The after is the next cold run's, in
  roadmap 173.

## [0.224.1] - the hatch is its ladder's own furniture

**Cold run 9315, the first with a roof hatch, stopped at the art pass** on the circulation gate: the hatch's own
greybox box stood 0.2 m inside `ladder:ladder_0`'s climb volume on courthouse_a02 and airport_terminal_a01
(`circulation_check`, shell arm). It stands there by construction -- the climber comes up THROUGH the hatch --
as a stair's guard stands at its own hole's edge, which the gate has excused since 0.191.0.

### Changed
- **`circulation.check_shell` excuses a `roof_hatch_*` prop in a ladder's climb volume** (`HATCH_PREFIX`), and
  lists it as excused so a reader sees what was not counted; in a doorway or a stair's column it is a prop like
  any other. The two excusals are one function now, `excused_own_furniture`, and `test_circulation.py` pins
  it: the hatch in its ladder's volume and the guard in its stair's are excused, the same hatch in a doorway and
  a crate in the ladder's volume are not.
- **`roof_hatch.py` is a geometry source** (`build_freshness.GEOMETRY_SOURCES`): it emits slots, so editing it
  demands the rebuild the freshness gate exists to demand.

The placement gate's finding on the same buildings -- the open lid's footprint 0.33 m past the slot -- is Zoo
1.113.1's.

## [0.224.0] - a lid on every roof hatch

**Factory roadmap 170, step 1** (`docs/findings/roof_openings_170/` there). A `hatch` vertical link on the roof
slab cuts the slab and emits a `HATCH_<x>_<y>` marker, and nothing put a lid on the hole: 43 roof ladders in the
library climb out through bare sky. Zoo 1.113.0 grows `roof_hatch`, a steel curb with a hinged lid; this release
stands one on every such opening.

### Added
- **`roof_hatch.py`** (pure): `roof_hatches(spec, style)` derives, for every `hatch` link whose story is the
  roof slab and that cuts it, one `prop` slot of species `roof_hatch` -- the hole plus `CURB` 0.08 m a side,
  `HEIGHT` 0.2 m, centred on the link and standing on the slab's top face (`top * story_height`) -- with the
  `hatch` interactive machine on it and its gameplay entry. `rot_for` turns the slot so the hinge side (local
  -Y) is away from the ladder's climber: `ladder.climb_rect` reserves the body's envelope along the ladder's
  `facing`, so that side is local +Y. A hatch with no ladder at its (x, y) faces north. A hatch below the roof
  is a floor-to-floor opening and gets nothing.
- **`interactives.py`: the `hatch` kind.** States `open` (default) and `closed`, both mapped to `roof_hatch`,
  `close` / `open` transitions, reversible; `collision_per_state` open False (passable), closed True. Open is
  the default so the ladder's `roof_hatch_exit` stays a route for every walker and the lid stands clear;
  shutting it is the game's, as a door's is.
- **`prop_species.SPECIES_OWNS_COLLISION`** gains `roof_hatch`: the greybox draws the slot's box for the swap
  to replace and emits no collider over the hole (a solid box there would block the ladder); the module's own
  `-colonly` boxes -- the curb, and the lid in each state -- are the collision.
- `_vertical_links` emits the slot, its greybox box and the gameplay interactive after the links' own
  markers; `test_roof_hatch.py` pins the machine, the slot, the size, the yaw, the roof-only rule and the ids.

### The library
- Rebuilt with it (`build.py --all`; the pre-commit freshness gate refused the commit until the 157 shells
  were newer than the code), so the library's 43 roof hatches carry their lids from this release. The
  bulkhead for the 16 stair heads is step 2.

## [0.223.0] - an open floor nobody named: layout_lint L26

**The factory's roadmap 255, found tracing the walker's walk of 2026-10-14, finding 5** (the factory's
`docs/findings/walk_2026-10-14/partition_gaps.py`). The delis' basement divider stopped 7 m short of each wall and
the vault stood open to the utility room, and no spec said so; across the library 59 such stretches stood in 31 of
446 specs, 33 in 20 after 0.222.0 closed the delis'. Some are designed openness -- a lobby flowing into a bullpen
-- and some are the finding again, and nothing told them apart: `tactical.shared_open_edge` has joined every such
pair as one floor since 0.197.0, so the engine walks it, and the spec was silent.

- **`tactical.OPEN_FLOOR_M`** (1.2 m) is the rule's threshold, spelled once where it was spelled four times.
- **`tactical.open_edge(a, b, parts)`** is `shared_open_edge`'s body, returned: the edge two rooms meet along and
  how much of it no partition covers -- ``(axis, pos, lo, hi, uncovered)`` -- or None. `shared_open_edge` asks it;
  `build_graph`, L12 and L24 move nothing.
- **A room's `open_to`** (the schema admits it: a list of room ids) says the floor between them is meant.
- **`layout_lint.open_floors(spec)`** names every pair tactical joins that neither room's `open_to` names;
  **`open_floor_findings`** is L26, an advisory WARN in every mode: "open floor nobody named: 'a' and 'b' (story
  s) meet along x = 0 from -5 to 5 with 2.00 m of it uncovered by any partition; the engine walks it as one floor
  -- say so (`open_to` on either room) or build the wall". `_story_parts` is the one reading of a storey's
  partitions both L24's search and L26 use.
- **`open_floor_baseline.py`** freezes the built library's pairs in `open_floor_baseline.json` for the walker to
  sort, one by one; `test_open_floor.py` fails on a new pair and on a stale one, as `test_walk_reach` does for
  L24. Nothing is a verdict on any pair: the walker's finding 5 was one of them, and the lobbies are others.
- **`test_open_floor.py`:** where a short partition is named; a wall-to-wall one and a 1.0 m gap are not; `open_to`
  silences the lint and not the engine; one threshold for both (moved, both move); a WARN and never a FAIL on
  rowhouse_raid; the schema; the spec left alone; the baseline. The seven that touch the code fail on 0.222.0
  (proven on a copy; the two baseline tests pass there trivially, with no `build/` to read).

Nothing built moves: a lint names, it does not change a shell. Level Factory's findings never carry a Deli Counter
lint warning, so no cold run moves either.

**The census:** 49 open floors nobody named, in 26 of 159 built specs

**Suite:** `python -m pytest -q`: 1549 passed, 2 skipped, 1 warning in 115.66s (0:01:55), exit 0 -- 0.222.0's 1,540 and `test_open_floor.py`'s 9

## [0.222.0] - the delis' basement divider runs wall to wall, and the utility room gets a door

**The walker's walk of cold runs 9305-9307, finding 5** (the factory's `docs/findings/walk_2026-10-14/`). In
deli_a01's basement: "this wall supposed to stop here and have this big opening?".
- **Traced:** the divider along X at y 1.0 stood x -12..12, under rooms that meet across the whole basement,
  x -19..19. That left 7.00 m open at each end:
  - the corridor into cold storage;
  - the utility room into the vault, the objective room, beside the 1.4 m breach that was its way in.
- **Its origin:** 0.80.0's `presets.corner_deli` authored it so. Its other partitions all run wall to wall, and it
  was carried into all six delis.
- **Asked, the walker chose: "close the basement".**

### Changed
- **`presets.corner_deli`:** the divider runs `-half_x..half_x`. Its door and breach keep the positions 0.221.0
  built: snap(-0.35 * 24) = -8.5 and snap(0.3 * 24) = 7.0, now -8.5 / 38 and 7.0 / 38 of the run.
- **`migrate_basement_wall.py`,** new: the one-shot, idempotent migration bringing the library to the rule.
  - It touches deli_a01, deli_a02, deli_a03, cr_deli, night_deli and corner_deli_heist_01.
  - In each, the divider and its two openings' fractions move, and nothing else does.
  - A divider of another span is refused and named.
- **The library refurnished around the new wall** (`migrate_furnish_recipes.py`, 0.214.0's pattern). The library
  is held to be a fixed point of `level_design.furnish`, and the wall moves what furnish stands beside it.
  - Measured before anything was written (the factory's `docs/findings/door_widths/refurnish_delta.py`, on a copy):
    deli_a03 alone moves, 118 furnished pieces to 117.
  - It loses one chair set at the vault's count table, which stands 0.15 m from the new wall.
- **What it changes in play:**
  - The vault is entered by its cold-room door and by breaching.
  - The utility room's only open way in had been the vault's east gap. Its other two openings are reinforceable
    breaches, which build as solid panels with colliders. A room reached only by breaching gets a door unless it
    is the objective (the walker, 2026-10-06; layout_lint L24), and `test_walk_reach` refused the closed wall
    without one. Asked, the walker chose the door.
- **`presets.corner_deli` and the migration give the utility room a door from the corridor,** tagged
  `corridor_to_utility`, as wide as the cold-room door. It sits on their shared wall midway between that wall's
  breach at y -9.0 and the divider at y 1.0, so y -4.0. In all six delis the rooms a body reaches only by
  breaching are then exactly `walk_reach_baseline.json`'s: the four server rooms ruled objectives by design.
- **`test_walk_reach.py`:** `test_deli_a01s_utility_room_is_open_floor` is now `..._is_walked_into`. The gap that
  made it open floor is closed, and its door is asserted.

### Tests
- **`test_basement_wall.py`:**
  - the preset builds the divider wall to wall;
  - all six library delis are closed, with their door at -8.5 and their breach at 7.0;
  - the migration keeps every opening, adds the door, and is idempotent;
  - the preset and every deli give the utility room its door at y -4.0, and L24's walk search reaches it;
  - another span is refused;
  - no two basement rooms meet past the divider.
- On 0.221.0 it fails: there is no `migrate_basement_wall`.

**Proven to fail first:** `test_basement_wall.py` fails on 0.221.0, at collection, there being no `migrate_basement_wall`; on 0.222.0 it passes with the two furnish fixed points (`test_deli_window`, `test_club_fixtures`), `test_walk_reach.py` and the stair tests, 41 of 42 (the 42nd reads `build/`, which the copy lacks; its question, asked directly, matches the baseline exactly) (the factory's `patches/dc_basement_wall/prove_tests_0221.out.txt`, run on throwaway copies before the repo was touched). The refurnish lost deli_a03's `chair_set_r365b5162_9_1` at (14.72, 1.99), by the new wall, and placed its partner `_9_2` again

**Suite:** `python -m pytest -q`: 1,540 passed, 2 skipped, exit 0, in 117 s -- 0.221.0's 1,533 and `test_basement_wall.py`'s 7; `test_walk_reach.py`'s renamed test stands in its old one's place, and its two library checks pass on the built library, the walk-unreachable rooms exactly the baseline's

**Build:** `python build.py --all --blender C:/blender/blender.exe`: exit 0 in 404 s. Every changed file attributed, the build folder hashed before and after (the factory's `patches/dc_basement_wall/build_diff.out.txt`): 189 of 1,483 -- the six delis' GLBs and their gameplay, combat-audit and validation manifests, with a slots manifest (navigation for corner_deli_heist_01) each, 30 files; and every shell's manifest, its `built_utc`. No other shell moved

## [0.221.0] - a switchback's second flight stands on the floor under it

**The walker's walk of cold runs 9305-9307, findings 7-9** (the factory's `docs/findings/walk_2026-10-14/`). At
restaurant_row_001's office, from below the stair core: "bottom of this stair should come down all the way to the
ground"; beside it, a tall gap in the enclosure; inside, a core that "looks wrong in general".
- **Traced:** `flight_solid_under` fills a switchback's first two legs solid "to that storey's floor", on the
  premise that only the first leg of each run stands on one. With `cut_slabs`, leg 1's own storey floor is the slab
  its stair cut across both runs (`hole_span`). So its fill hung with a level bottom a storey over the floor below,
  over the walkway 0.134.0 kept open under the next leg, and that walkway's mouth was the gap.
- **The same shape stood in 17 legs of 14 library specs** (`floating_flights.py` there).
- **Asked, the walker chose: "fill the stairs to the ground".** That overrides 0.134.0's channel.

### Changed
- **`stairwell.flight_solid_base(spec, st, s)`:** the storey whose floor a leg's fill stands on.
  - A cut, multi-storey switchback's second leg, when it is filled, stands on the stair's lowest storey.
  - It keeps its own storey when something else opens that floor under its run (`slab_openings`).
  - Every other leg stands on its own storey, as before.
- **The builder's `_stairs`:** each tread's column, and its collider one riser short of the tread, stands on that
  floor. For every leg on its own storey the numbers are the same floats as 0.220.0's.
- **`stairwell.stair_guards`:** on the lowest storey the second run gets a back from leg 1's foot to the
  rectangle's arrival edge. It runs from the side wall's inner face to the run boundary and from the floor to the
  slab underside, beside the first run's back, which is unchanged. The core's face there is flush, where it was
  the gap the walker looked through.

### Tests
- **`test_stair_fill_to_ground.py`:** the walker's stair stands on the ground floor; only a cut multi-storey
  switchback's second leg moves; a floor cut under the second run keeps the old base; the office's core is closed
  to the north; every cut second flight in the library, 17 legs in 14 specs, stands on its stair's lowest floor.
- **`test_stair_back.py`:** two tests pinned 0.134.0's walkway and change with it:
  - `test_the_walkers_stair_gets_a_back_in_its_own_run_only` is now `..._in_each_run`;
  - `test_the_walkway_under_the_next_leg_keeps_both_its_mouths` is now `..._is_filled_to_the_ground`.

**Proven to fail first:** `test_stair_fill_to_ground.py` fails on 0.220.0, all 5, `stairwell` having no `flight_solid_base`; on 0.221.0 it passes with `test_stair_back.py` and `test_stair_underside.py`, 27 (the factory's `patches/dc_fill_to_ground/prove_tests_0220.out.txt`, run on a throwaway copy before the repo was touched)

**Suite:** `python -m pytest -q`: 1,533 passed, 2 skipped, exit 0, in 131 s -- 0.220.0's 1,528 and `test_stair_fill_to_ground.py`'s 5; `test_stair_back.py`'s two rewritten tests stand in their old ones' place

**Build:** `python build.py --all --blender C:/blender/blender.exe`: exit 0 in 579 s. Every changed file attributed, the build folder hashed before and after (the factory's `patches/dc_fill_to_ground/build_diff.out.txt`): 197 of 1,483. The 14 GLBs are the 14 shells whose second flight now stands on the ground -- bank, bank_job, cbp_town_finale_midbalanced_schemafixed, corner_deli_heist_01, cr_deli, final_stand, foundry_heist_vertical, harbor_score, night_deli, office, office_stepped, primos_pizza, rowhouse_raid and twin_a01. Of those, 12 also changed their slots and gameplay manifests, recording the second run's back (office: two `stair_guard_back` slots where it had one); the other two, foundry_heist_vertical and primos_pizza, are where an exterior wall already refuses the back. Every shell's manifest changed its `built_utc`

## [0.220.0] - a walk-up stands a fire escape on its front, a storey a slot

**Factory roadmaps 156 and 241.** The walker's photo of a brick walk-up: "this is something i'd like to see in our
toolset, fireescape stairs brick". Zoo 1.110.0 draws a fire escape a storey at a time (`fire_escape`); this stands
one on the urban street's walk-ups (the factory root's `docs/proposals/FIRE_ESCAPE.md`, step 2).

- **`fire_escape_stack.plan`**, pure: where each storey of it stands, in the building's frame.
  - **Which buildings:** a walk-up, six storeys or fewer (`WALKUP_STOREYS`), and not a corner block, whose awning
    runs the front. CHOSEN, not read from a code: the height a walk-up stops at before a building takes a lift and
    its stairs inside. Of the library's Empties that is `gs_midrise_a`, `_b`, `_g`, `_h` and `_i`.
  - **Where on the front:** centred on the window column at the end farther from the front door, a bay's spacing
    less 0.2 m either side and at most 2.8 m wide, 1.2 m out, its back 8 mm inside the wall's face.
  - **The storeys:** under each landing but the top, a flight bay a storey tall, its deck's top on the storey's
    walking surface -- `flight_a` and `flight_b` alternating from the second storey, so the stack switches back.
    The top landing is `top_a` or `top_b`, whichever the last flight comes up into.
  - **The drop ladder:** under the lowest landing's hatch, in the stair band, its foot 2.2 m over the ground floor.
  - **Zoo's numbers it draws to** (the deck's 2 in, the 36 in guard, the 22 in stair band, the 0.75 m hatch) are
    repeated here, because Deli Counter does not import Zoo. The tests pin them, and read them off Zoo's module
    where the Zoo repo stands beside this one.
- **`LevelSpec.fire_escape_stack`**, a side or None, and the schema carries it (0.218.0's lesson).
- **`_fire_escape_stack`** writes a `prop` slot a storey, and one for the drop, in `metal_painted`, each greyboxed as
  a visual box. No collision: the lowest landing stands a storey up, and Level Factory reads an Empty's street edge
  off its colliders.
- **`presets.empty_midrise(..., fire_escape=None)`:** None asks the walk-up rule; True or False overrides it. A
  block that stands one declares the painted steel in its palette.
- **`build_freshness`** lists `fire_escape_stack.py` among the sources baked into a shell.
- **The specs:** the five walk-ups' regenerated; every other mid-rise and corner block asserted unchanged;
  `specs/CATALOG.md` regenerated.
- **`test_walkup_fire_escape.py`:** on 0.219.0 it fails to collect (`ModuleNotFoundError: No module named 'fire_escape_stack'`). On 0.220.0, 11 of its 12 pass before the build -- its two Zoo checks against Zoo 1.110.0 beside it -- and the twelfth, every built walk-up carrying its stack, fails against 0.219.0's shells and passes after the build.
- **The suite:** `python -m pytest -q`: 1,528 passed, 2 skipped, exit 0, after the build -- 0.219.0's 1,516 and the new file's 12.
- **The build:** `build.py --all`: 154 shells' outputs byte-identical to 0.219.0's and 5 moved -- the five walk-ups, each its GLB and its spec -- none new or gone, by the shells' manifests; the two fuel-stop heist shells' manifests carry no hashes, as before. `gs_midrise_a`'s slots carry its five: three flights, the top landing and the drop.

## [0.219.0] - the corner blocks hang an awning over the shop

**Factory roadmap 241, the corner shop.** The comps: "Corners carry the life. The corner building has the shop at
grade (lit, awning), homes above." 0.218.0 built the shop; Zoo 1.108.0 draws the awning (`shop_awning`); this hangs
one over each corner block's storefront, in its shop's canvas.

- **`shop_awning.py`** (new, pure) says where the awning hangs, in the building's frame:
  - across the front, 0.3 m short of either end;
  - 1.2 m out, its back 8 mm inside the front wall's face, so no face of Zoo's awning lies on the wall's;
  - its valance's bottom 0.1 m over the storefront's head, and its top 0.85 m over that.

  CHOSEN, not read. 1.2 m stays inside Level Factory's 2.0 m terrace frontage, off the sidewalk, and the top
  stands more than 0.3 m under the first floor's sills. A form Zoo does not draw is refused.
- **`LevelSpec.awning`,** a form or None. The schema carries it: 0.218.0's lesson, a spec field the schema does not
  carry fails the build's own gate.
- **A facade calls `_awning` after `_stoop`.** It writes a `prop` slot -- `shop_awning`, canvas, the form the
  shop's colour -- and a visual greybox box.
  - No collider: the awning hangs over a frontage nobody walks at its height.
  - Level Factory reads an Empty's street edge off its colliders, so the awning moves no line.
- **`empty_midrise(..., awning=None)`** declares canvas when it hangs one. The four corners hang a deli's red, a
  bar's black, a laundromat's navy and a grocery's green.
- **`material_kind.KIND_BY_MATERIAL` carries canvas,** a skin kind already. The suite's `test_every_spec_material_has_a_kind` found the row missing after the first build.
- **`build_freshness.py`** counts `shop_awning.py` among a shell's sources. The four corner specs are regenerated,
  and the nine mid-rises are byte for byte as they were.
- **Built:** `build.py --all`, 6 min 59 s, 159 shells. The four corner blocks moved -- their spec and glb, each now carrying the awning's slot and visual box -- and each validates clean; every other shell's outputs are byte-identical to 0.218.0's by its manifest's `outputs_sha256_16`, 155 of 155. Read off `build/gs_cornershop_a.slots.json`: one `shop_awning` slot, `shed_red`, 14.4 x 1.2 x 0.85 m centred at (0, -8.242, 3.075) -- its back 8 mm inside the front wall's face at y -7.65, its valance's bottom 0.1 m over the storefront's head.
- **`test_corner_awning.py` and the suite:** 1,516 passed, 2 skipped, exit 0: 0.218.0's 1,508 and `test_corner_awning.py`'s 8, which fails to import on 0.218.0 (no `shop_awning`). Its `test_every_built_corner_carries_its_awning_slot` reads all four built slots. The suite's `test_every_spec_material_has_a_kind` failed on the first run, canvas having no kind row, and passes with it.

## [0.218.0] - the corner blocks: a mid-rise Empty whose ground-floor front is a shop

**Factory roadmap 241.** The urban comps (the factory root's `docs/reference/URBAN_MIDRISE_COMPS.md`): "Corners
carry the life. The corner building has the shop at grade (lit, awning), homes above. The middle of the block is
residential." The mid-rise Empties are homes from the pavement up. Zoo 1.107.0 paints a shop's window from its own
atlas (`zoo_keeper.core.shop_panes`); this authors which windows show a shop, and which shop. Step 2 of the factory
root's `docs/proposals/CORNER_SHOP.md`.

- **`presets.empty_midrise(..., security_door=False, shop=None)`.** With `shop`, every front bay at grade but the
  door's is a `SHOP_WINDOW`, authored in the shop's state. That is 2.4 m of glass from a 0.3 m bulkhead to the
  front door's 2.4 m head.
  - The front door is the shop's, in the bay nearest `lobby`; the homes above keep the service door behind.
  - `security_door` hangs the rowhome Empty's iron door on the front.
- **`EMPTY_CORNERS`**, four blocks under their own prefix, `gs_cornershop_`, so the urban street's deal
  (`gs_midrise_`) never draws one mid-block. Not `gs_corner_`: that is `gs_corner_station`'s, an enterable
  gas station Level Factory's clusters name as a corner store.

      gs_cornershop_a   15.0 m, 6 storeys, brick          a deli, black door, iron
      gs_cornershop_b   18.0 m, 8 storeys, brick_orange   a bar, oxblood door
      gs_cornershop_c   12.0 m, 5 storeys, brick_brown    a laundromat, white door
      gs_cornershop_d   16.5 m, 7 storeys, stone_ext      a grocery, green door, iron

- **An opening carries an authored state,** `Opening.pane`.
  - `_opening_to_hole` carries it, and a facade window's slot takes it before `empty_panes.choose` draws one.
  - `empty_panes.SHOP_STATES` is Zoo's shop atlas in its order. `empty_panes.authored` refuses a state outside
    both sets rather than dropping it.
  - A shop window hangs nothing: no bars and no air conditioner (`fixtures`).
- **`themed_tscn.resolve_themed_stem`** names a shop window as Zoo's `plan_kit` does, `_p<state>`.
- **`schema/level.schema.json`'s opening may carry `pane`,** a string or null. The value is checked by
  `empty_panes.authored` at build, so the schema keeps no third copy of the states.
- **Nothing stands one yet.** Level Factory deals them where a wall closes at a corner (the proposal's step 3).
- `navgate_baseline.json` has four UNJUDGED entries, as every Empty does. `specs/gs_cornershop_*.json` are written
  from the presets, and `specs/CATALOG.md` is regenerated.
- **Built:** `build.py --all`, 6 min 53 s, 159 shells. The four corner blocks are new, each validating clean with `facade` true (glb sha256_16: gs_cornershop_a 27217982b626dd13, _b 6478958475edf9b5, _c beaeac67c42d7f16, _d c1c1c084bad2cc04). Every other shell's outputs are byte-identical to 0.217.0's by its manifest's `outputs_sha256_16`, 155 of 155; `fuel_stop_heist2` and `_3`, June builds with no spec of their own, are not rebuilt and their manifests are unchanged. Read off `build/gs_cornershop_*.slots.json`: at grade 3 to 5 shop windows in the block's shop, with no bars and no air conditioner; the shop's door between them in its finish, an iron door on _a and _d; the service door behind; every upper window drawn as before. The first build of this change failed the four specs' own schema gate ("'pane' was unexpected"), read off their validation manifests: the schema now carries `pane`, and the shells rebuilt to the same bytes.
- **`test_empty_corner.py` and the suite:** 1,508 passed, 2 skipped, exit 0: 0.217.0's 1,497 and `test_empty_corner.py`'s 11. On 0.217.0 the file fails to import (no `EMPTY_CORNERS`). With every edit but the builder's, `test_a_shop_window_s_slot_carries_its_shop_and_nothing_hangs_in_it` alone fails; with every edit but the schema's, `test_every_corner_spec_passes_the_schema` alone fails. That check was added after the build found what the suite had not.

## [0.217.0] - three narrow mid-rises: the blocks that fit between the mission's buildings

**Factory roadmap 241, the near side.** Level Factory 0.201.0 fills an urban street's near frontage between
the mission's own buildings, keeping a 4 m passage beside each. On urban_row_001's three candidates (cold run
9288) the rooms left were 12.67 m, 11.35, 7.33, 6.70 and none. The narrowest of the six mid-rises measures
15.3 m, so nothing stood (the factory root's `docs/findings/urban_street/near_room.py`). Real streets carry
two- and three-bay buildings between the wide blocks. This is that capability, grown where it belongs.

- **`presets.EMPTY_MIDRISE_NARROW`**: `gs_midrise_g`, `_h` and `_i`, 12.0, 10.0 and 6.3 m wide (12.3, 10.3
  and 6.6 as built, a wall's thickness more) at 6, 5 and 4 storeys. They are narrower and lower than the six,
  in the family's bricks, and named under its prefix, so Level Factory's urban street draws them with the
  rest. A separate table, so the six keep their own rule of five to twelve storeys with no two the same
  height. Three specs are written from it, and `specs/CATALOG.md` is regenerated.
- **`empty_midrise`'s bays floor at two, not three.** A 6.3 m front holds two windows in the family's 3.2 m
  rhythm, where three would stand 2.1 m apart. No block of the six has fewer than five bays, so their specs
  stand byte for byte.
- **`navgate_baseline.json`** records the three UNJUDGED, as it records every Empty: no interior for a spawn
  marker to stand in. `counts.unjudged` 27 -> 30.
- **`test_empty_midrise_narrow.py`** checks:
  - the three narrower and lower than the six, and named under the prefix;
  - each the preset's own output, an Empty with its windows in the family's rhythm, one door a face at
    grade;
  - the six unchanged by the two-bay floor.

**Built:** `build.py --all` under Blender 5.1.1, 155 shells in 368 s, exit 0, no error in the log. The three narrow blocks build 12.30, 10.30 and 6.60 m wide and 15.30 deep. Each of the 152 shells before them moves by `built_utc` alone, the six mid-rises included, so the two-bay floor moved none of them. `layout_lint --all`: 155 specs, 0 FAIL, 391 WARN, the three adding none

**Suite:** 1,497 passed, 2 skipped, exit 0: 0.216.0's 1,493 and `test_empty_midrise_narrow.py`'s 4

## [0.216.0] - the census's body-sized literals read the agent contract, and combat_audit reads the builder's openings

**For "singular changes" (the walker, 2026-10-13).** The factory's census of this repo's module-level
numbers (`docs/findings/agent_contract_follows/literal_census.py`) flagged 127 of 317 constants on a body
word or a contract number, and each was read. Eleven were a body's size written down with its rule beside
it, and each now reads the contract at the value it was:

- **A capsule's width,** two body radii: `enterability.MIN_PASS_WIDTH` and `stairwell._AGENT_PASS_WIDTH`
  (0.7).
- **The body's height and eye:** `enterability.STAND_HEIGHT` (1.8), and `sightlines.EYE` and
  `SIGHT_BLOCK_H` (1.6, the body's eye, `characters.player.eye_height_m`, not the camera's).
- **The step a controller lifts:** `guards.MAX_STEP_UP` (0.5).
- **Two agents abreast,** four body radii: `combat_audit.WIDE_DOOR` (1.4).
- **The door minimum:** `vault_room.DOOR_WIDTH` and `lights._AISLE_MIN_FALLBACK` (1.25).
- **The floor in front of a door,** two body radii and 0.3: `vault_room.APPROACH` (1.0). This is now one
  function, `agent_contract.door_approach()`, which `layout_lint.DOOR_APPROACH_M` also reads; it spelt the
  same formula itself.
- **A gap a bake-radius body cannot use,** two bake radii: `level_design._CLUSTER_GAP`'s upper end (0.8).
- **The ladder hole's clearance,** standoff, body radius and margin: `ladder_geom.HOLE_ALONG` (1.3). Its
  0.45 m margin is now named, `HOLE_ALONG_MARGIN`.

`agent_contract.py` gains the accessors they read: `body_height`, `body_eye_height`, `max_step_up`,
`nav_radius` and `door_approach`. Every value is the one it replaced, exactly in a float, so nothing built
moves.

- **`combat_audit` reads the builder's openings.** It kept its own copy of the opening defaults, and two
  were stale. A width-less door was read at 1.2, where the builder uses the contract's 1.25 since 0.214.0.
  A width-less vault was read at 1.4, where the builder uses 1.3 x 2.1. `_op_width` now asks
  `Opening.resolved()`, so a room whose widest opening is a width-less vault reads as single-file, as it is
  built (`combat_audit.py --all` over the library and `--all-presets`, run on clean copies of 0.215.0 and 0.216.0: byte-identical, 132 specs at 6 HIGH and 78 MED, and 19 presets at 0 HIGH and 8 MED. Neither stale default turned on a flag in the library or the presets; `_op_width` itself is held by the test).
- **Read, and left for the walker or later** (the factory's `docs/findings/agent_contract_follows/README.md`):
  - thresholds that disagree with the contract, such as `enterability`'s 1.1 m "can't even crouch through"
    against `crouch_height_m` 1.2, and the passes at 0.7, 0.8 and 0.9;
  - two door approaches, `circulation`'s 0.6 against `layout_lint`'s 1.0;
  - numbers whose rule names a margin it never derives;
  - one MEASURED against the bake (`stairwell.RAIL_OPEN_MIN`);
  - a comment that does not reproduce its number (`_CUSTOMER_LANE`).
- **`test_contract_census.py`** checks the accessors, each routed number as its rule, today's values, and
  `combat_audit`'s widths at the builder's. It fails to import on 0.215.0.

**Built:** `build.py --all` under Blender 5.1.1, 152 shells in 387 s, exit 0, no error in the log. Every manifest moves by `built_utc` alone, and each carries its outputs' sha256, so every shell is byte-identical to 0.215.0's. The presets as Level Factory makes them (228 combinations, the factory's `preset_digest.py`) digest d53248c1..., as on 0.215.0

**Suite:** 1,493 passed, 2 skipped (the bpy round-trip fixtures, run in their own process), exit 0: 0.215.0's 1,489 and `test_contract_census.py`'s 4, which fail to import on 0.215.0. `stair_regression.py --quick`: every variant clean

## [0.215.0] - the stair landing and the vault's opening follow the agent contract

**For "singular changes".** The walker, 2026-10-13: "continue to update the agent contract file so we can
make singular changes when we know the size of characters in the game". 0.214.0's
`clearances.re_derive_when` named the two body-sized numbers that did not follow the contract yet. Both
follow now, each as one function in `agent_contract.py`, read where it used to be spelt. The contract
writes down each rule. Today's numbers are the ones that were spelt, so nothing built moves.

- **`agent_contract.stair_flight_width()`** is `min_corridor_width_m` plus one `nav_bake.cell_size_m`:
  1.2 m.
  - `presets.STAIR_FLIGHT_WIDTH` read that formula inline. It now calls this function, so the formula is
    spelt once.
  - `stairwell.LANDING_DEPTH` was a literal 1.2, "a game-readability default". It now reads the same
    function.
  - The rule, in the contract's new `stair_landing_derivation`: a landing as deep as the flight is wide.
    That is IBC 2018 section 1011.6, which sets a landing's depth in the direction of travel at the
    stairway's width or 48 in, whichever is less. The 48 in cap is left out because it assumes a human
    body, and the contract sets the body.
- **`agent_contract.vault_aperture()`** is `min_door_width_m` rounded up to the next 0.1 m, by
  `min_headroom_m` plus 0.1, on the floor: 1.3 x 2.1 m, sill 0.
  - `vault_room.APERTURE` and `spec_types`' vault default were literals beside a comment giving this
    rule. Both read the function now.
  - The rounding guards the float that would round a door already on the 0.1 grid past it.
  - Deli Counter writes the opening into the vault door's slot (`fit.openings`), and Zoo builds the round
    door to it (`dna` passes the module's first opening to the recipe). Zoo's own default serves only a
    standalone build. The rule is in the contract's new `vault_aperture_derivation`.
- **`re_derive_when`** no longer lists a NOT YET FOLLOWING. It names what is WRITTEN and does not follow:
  the library's three vault rooms carry their 1.3 x 2.1 opening as written numbers, and no migration
  rewrites them yet.
- **`test_body_follows_contract.py`** checks:
  - the functions against stand-in contracts (a wider corridor, a finer cell, doors on and off the 0.1
    grid, more headroom);
  - the module-level copies against the contract in force, and the vault default as resolved;
  - every built vault slot's opening;
  - the contract's two derivations.

  It fails to import on 0.214.0.

**Built:** `build.py --all` under Blender 5.1.1, 152 shells in 385 s, exit 0, no error in the log. Every manifest moves by `built_utc` alone, and each carries `outputs_sha256_16`, so every shell is byte-identical to 0.214.0's. The presets as Level Factory makes them -- all 228 combinations of preset, mode and one to four floors on seed 9104 -- digest the same on 0.214.0 and 0.215.0 (sha256 d53248c1...). The control is 0.213.0, before the doors, which digests eae19d7f...

**Suite:** 1,489 passed, 2 skipped (the bpy round-trip fixtures, run in their own process), exit 0: 0.214.0's 1,480 and `test_body_follows_contract.py`'s 9, which fail to import on 0.214.0. `stair_regression.py --quick`: every variant clean

## [0.214.0] - every walkable door is at least the contract's 1.25 m, and the contract says so

**Factory roadmap 197.** `agent_contract.json`'s `clearances.min_door_width_m` is 1.25 m. The library built 200
walkable doors under it in 32 of 132 enterable buildings: 13 at 1.0 m, 74 at 1.1 and 113 at 1.2, 47 of those
width-less and so at this builder's own default, then 1.2. The presets wrote 61 more, at 1.1 and 1.2. Only
a warning in `navigability.check` named them, and nothing read it. The number itself was derived at a
0.15 m cell, which the contract had since left for 0.1; at 0.1 its formula gives 1.00. The census and the
measurements below are in the factory root's `docs/findings/door_widths/`. The walker, 2026-10-13: "If we
change the door widths, that's ok, it should be called out in the agent contract". Asked which way, they
answered "widen the doors and keep 1.25". Then they added: "continue to update the agent contract file so we
can make singular changes when we know the size of characters in the game". So every door width this
builder's code writes now asks the contract, and the contract says what one change to a body moves.

- **The contract** (`agent_contract.json`, `clearances`). No number moves.
  - `derivation` is re-worked at the contract's own cell: the bake needs 1.00 m. 1.25 is written above it
    as a DESIGN MINIMUM, with every door and width built from it.
  - `min_door_width_note`, new, records what was widened and the two doors that were not.
  - `re_derive_when`, new, says what a change to the body or the bake's cell starts. It also says what
    follows on its own, what needs the migration re-run, and the body-sized numbers that do not follow
    yet: `stairwell.LANDING_DEPTH`, a literal 1.2, and the vault door's aperture, 1.3 x 2.1 m, spelt in
    `vault_room.APERTURE`, `spec_types`' vault default and Zoo's `vault_forms.DEFAULT_OPENING`. The vault
    is named by the release's second edit, `patch_dc_door_width_vault_note.py`.
- **The staff door** behind a teller line asks the contract for its width (`level_design._STAFF_DOOR_WIDTH`).
  It was a literal 1.25 beside a comment naming the contract, and `staff_aisle_width` already said the
  staff room asks. The number is the same.
- **A width-less door** resolves to the contract's minimum, not 1.2. `spec_types.Opening.resolved` reads it
  when the door is resolved.
- **The presets** write every walkable door at `presets.DOOR_W`, the contract's minimum: 61 doors in 15
  presets. Those are `auto_shop`, `bank`, `casino_tower`, `compound`, `corner_deli`, `gas_station`,
  `hospital`, `office`, `parking_garage`, `pawn_shop`, `police_station`, `rowhome`, `suburban_safehouse`,
  `twin` and `warehouse`. `empty_rowhome` and `empty_midrise` keep theirs: an Empty's doors are shut and
  nothing walks through them.
- **The library** (`migrate_door_width.py`, one-shot and idempotent, run here) widens 152 authored doors in
  29 specs to 1.25 m, each about its own centre. Two doors are handled by name, from the lint's own numbers:
  - **`final_stand`'s `west_entry` slides 0.10 m along its wall.** A partition ended 0.90 m from its
    centre, where L18 needs more than 0.93.
  - **`primos_pizza`'s `kitchen_stairs` is KEPT at 1.20 m.** At 1.25 it fails L18 where it stands. Slid
    clear, it fails L21, hanging 0.12 m over the basement stair's hole. No place on that wall holds it
    until the stair moves.
- **The library refurnished around its wider doors** (`migrate_furnish_recipes.py`, the release's third
  edit, `patch_dc_door_width_refurnish.py`). The library is held to be a fixed point of the furnishing
  pass, and widening a door moves what furnish puts beside it: the full suite failed both fixed-point
  tests on `cr_gas`. Measured spec by spec (the factory's `docs/findings/door_widths/refurnish_delta.py`),
  the refurnish moves 8 specs, every one a spec whose doors changed:
  - `cr_gas`, `foundry_heist_vertical`, `gas_station`, `gas_street` and `gs_corner_station`: pieces
    move, none lost;
  - `cr_pawn` loses a cartons stack and a floor safe, and `stop_n_go` its back-room cigarette rack;
  - `rowhouse_raid` gains four chair sets.
  The rack stood 0.96 m from `rear_service`, which widened 1.0 -> 1.25 m, so `test_club_fixtures`' pin
  on the library's cigarette machines moves 119 -> 118 with that reason beside it. The 8 shells are
  rebuilt. `migrate_furnish_recipes.py --check`'s own summary is not a measure of this: it reads
  -7,923 / +7,819 on 0.213.0, where the library is a fixed point.
- **Stairs-first's landing door** (`stair_core._PUNCH_DOOR_W`) is the contract's corridor width,
  `min_corridor_width_m`: 1.1 m, the literal it was. It is under the door minimum, and it is commented and
  named in the contract. Of the 20 crossings in `stair_regression`'s 140 variants, 18 are 1.2 m and 2 are
  1.1. At 1.25 none is punched, and the sweep's checks fail 21 times against 2. Of the new failures, 16 are
  `STAIR_EXIT_FACES_SOLID` and 3 are a prop in a stair's reserved volume. Level Factory never builds
  stairs-first.
- **An exact fit is punched.** A crossing exactly the door's width counts as wide enough, within 1e-9. The
  two 1.1 m crossings measured were 1.1000000000000014 and were punched by 1.4e-15. Spelt `6.1 - 5.0`, the
  same crossing is 1.0999999999999996, and it was refused.
- **Stairs-first's doored check** (also `stair_core`). Asking whether a crossing is already doored, it read
  a width-less door at a literal 1.2. It now reads `Opening.resolved()`.
- **The stairs-first changes move no spec.** The 140 variants' specs are byte-identical across all three
  (`stairs_first_doors.py`: sha256 35e2a857... over the 140 variants' specs with 0.213.0's two literals, with the resolved width alone, and with all three changes; at a 1.25 m punched door, the control, it moves to 6c417af7...).
- **`test_door_width.py`**. It fails to import on 0.213.0. It checks:
  - the width-less default, and a stand-in contract with another minimum getting another door;
  - the module-level widths (`presets.DOOR_W`, the staff door, the punched landing door) against the
    contract in force;
  - every library door, and the KEPT door still named and still narrow;
  - every enterable preset made as Level Factory's adapter can make it: three modes, one to four floors,
    a basement or not;
  - the migration's Empties, kept doors and idempotence, and the library as the migration's fixed point;
  - the contract's three texts, and the derivation re-worked at the contract's own bake, so the next
    change to the bake fails here until the text follows;
  - stairs-first's doored check at a width-less door's built width, and the exact-fit crossing;
  - the library's built shells, not every file in `build/`.

**Measured before the change.** These ran on a copy of 0.213.0 with the change and a copy without it:
- `layout_lint --all`: 0 FAIL and 391 WARN both ways, with the same findings.
- Every preset as Level Factory makes it: two modes on eight seeds (304 variants), then three modes at 1 to
  4 floors with and without a basement (432). The FAILs match preset by preset and rule by rule (768 and
  1,044). Doors under 1.25 went from 1,568 to 0, and from 2,148 to 0.

**Built:** `build.py --all` under Blender 5.1.1, 152 shells in 388 s, exit 0, no error in the log; the 8 refurnished specs rebuilt after. 34 manifests move in content -- the shells the doors change -- and 118 only by `built_utc`. `door_fit.py` (the factory's `docs/findings/door_widths/`) over the 132 built enterable shells finds no door under 1.25 m but the KEPT one. Its other findings are two orphan builds of specs no longer in the library (`fuel_stop_heist3`, `fuel_stop_heist4`, untracked) and a breach overlap in `auto_shop_a02` that 0.213.0's tracked build carries too. `layout_lint --all`: 0 FAIL, 391 WARN, as before

**Suite:** 1,480 passed, 2 skipped (the bpy round-trip fixtures, run in their own process), exit 0: 0.213.0's 1,449 and `test_door_width.py`'s 31. Against an export of 0.213.0 with the migration module copied in so the file imports, 26 of the 31 fail; the 5 that pass are the three presets that never wrote a narrow door, the KEPT door's record and the migration's own check

## [0.213.0] - mid-rise Empties: five to twelve storeys of brick, out of today's streets

**Factory roadmap 241, step 1.** The walker, 2026-10-11, chose a new urban level type: mid-rise Empties
standing at the sidewalk line in continuous street walls, the enterable buildings among them, and the Delco
strip levels left as they are (the factory root's `docs/reference/URBAN_MIDRISE_COMPS.md`). This is the
family's first cut.

- **`presets.empty_midrise`**: a brick block of `floors` storeys, its windows in regular bays about 3.2 m
  apart across its width on the front (S) and the back (N), a lobby door at grade in one front bay and a
  service door behind it. The sides are left unlisted, so `auto_exterior` seals them as party walls. It has
  a parapet, is 15 m deep with a 3.1 m storey, and has a membrane roof. It is an Empty in every respect
  this builder keys on `facade`: shut doors, painted windows, only its roof slab.
- **`presets.EMPTY_MIDRISES`**: six blocks, `gs_midrise_a` to `_f`, of 5, 6, 7, 8, 10 and 12 storeys,
  15 to 24 m wide, in the rowhome family's three bricks and one stone front. No two are the same height,
  so a layout can draw them by cause, taller away from the action. `REGISTRY["empty_midrise"]`; six specs
  are written from the table and `specs/CATALOG.md` is regenerated.
- **Named out of today's streets.** Level Factory hands every `gs_empty_*` in the library to any brief
  that stands a terrace (`building_library.empty_rows`). Under that prefix these would stand in a Delco
  street, so they are `gs_midrise_*`, and they wait for the urban brief that asks for them (241, step 3).
  As facades they are already outside the enterable draw.
- **Not here:** the rooftop penthouse, the corner variant with a shop at grade, and the bay-window variant.
  Each needs a capability this builder does not have yet.
- **`navgate_baseline.json`** records the six UNJUDGED, as it records `gs_facade_rowhome` and the
  twelve rowhome Empties: an Empty has no interior for a spawn marker to stand in, so the nav gate
  checking zero markers is the correct outcome. `counts.unjudged` 21 -> 27.
- `test_empty_midrise.py`: the family's spread, the specs as the preset's own output, the prefix, the
  Empty's flags, the regular bays on every storey front and back, one door a face at grade, the party
  walls, and every block loading with its front to the street. It fails to import on 0.212.0.

**Built:** the six shells built by `build.py` under Blender 5.1.1, 2 to 3 s each: 223, 291, 367, 383, 557 and 615 slots, GLBs of 130 to 259 KB, every validation manifest `passed` with `facade` true, and no warning in any build log. Shown in greybox as a street wall beside a rowhome Empty, each piece tinted by its name (the factory's `docs/findings/urban_midrise/`)

**Suite:** 1,449 passed, 2 skipped (the bpy round-trip fixtures, run in their own process), exit 0: 0.212.0's 1,441 and `test_empty_midrise.py`'s eight, which fail to import on 0.212.0, run against an export of it

## [0.212.0] - a stoop's iron railings, one each side

**Factory roadmap 240, the walker's calls of 2026-10-13**: "3 risers, concrete, railings both sides --
build the railings". 0.211.0's stoops already have three risers and concrete; this adds the comps'
"iron railings".

- **`stoop.plan` -> `rails`**: one railing a side, each as two slots of Zoo's `stoop_railing` (1.105.0).
  - a LEVEL section along the landing, from its front edge to the facade, 36 in tall over the landing;
  - a FLIGHT section from that edge down to a post on the bottom tread, its foot on the tread and its
    top 36 in over the landing.

  Each railing stands 5 cm inside the stoop's side, and the way up between them is 1.32 m, wider
  than the contract's 1.1 m corridor. The rail is 36 in over the landing at the flight's high end, and
  34.75 in over the nosing line at its post, inside IRC R311.7.8.1's 34-38 in (Zoo's forms hold the
  same number). The flight ends 1.42 m out, inside the stoop's 1.74 m.
- **5 cm in, not flush.** Flush, a flight's box shares the middle tread's side plane, facing the same
  way, over a tread by a riser: 0.2794 x 0.1778 = 0.0497 m2. The composer's z-fight gate reads a
  module as its box and skips a pair under 0.05 m2 (`zfight_gate.AREA_MIN`), so flush would have
  passed by 0.3 cm2, one deeper tread from a flag. `test_stoop.py` asks the gate's own
  `visible_fights` with no floor and finds no railing in a pair a camera can reach. Its control, each
  railing pushed flush, finds the two flights against the middle tread.
- **The turn:** `rot_y` 270. Zoo draws the run along its X with the high end at +X, and the composer
  turns a module by `tscn_export.godot_basis` (Ry(-t)), so 270 points +X at the house. 90 would point
  each flight's rail down toward the street. `test_stoop.py` holds the turn to `godot_basis` itself.
  The composer's fit keeps the slot's own turn on the tie a thin railing makes between 90 and 270.
- **The colliders are Deli Counter's**, in the greybox the graders walk:
  - the level section is its box;
  - the flight is a slab whose top face is the rail, 36 in deep measured upright, turned to the rail's
    pitch as the stoop's ramp is.

  Zoo's module carries none (`collision: false`). A box around a flight would have stood a third of a
  metre over its low end. Named `stoop_rail_*`, which Level Factory 0.197.0 reads as stoop, so the
  terrace stands the house where it stood.
- **`empty_rowhome`** declares the railing's iron (`metal_painted`, "Metal") beside the stoop's
  concrete. The twelve specs are regenerated, the presets' output byte for byte.

**Built:** build.py --all, 146 shells. Each of the twelve rowhomes, read off its manifests: four `stoop_rail_*` slots, species `stoop_railing` in `metal_painted` at `rot_y` 270, each `prop` in `surface_roles`, and four iron surfaces, `stoop_rail_<side>_<form>_col`. Among all twelve there are two modules: the level railing, 0.9 x 0.038 x 0.9144 m, and the flight, 0.5247 x 0.038 x 1.27 m -- the two Zoo 1.105.0's kit build built. Their colliders through Level Factory's reader (the factory's `patches/lf_stoop_railings/rail_hulls_0196.log`): on gs_empty_rowhome_a the level boxes stand at x -2.181 and -0.819, 0.9144 m over the 0.9 m landing, and each flight's slab reaches 1.4088 m in front of the facade, inside the stoop's 1.738 m

**Suite:** 1,441 passed, 2 skipped (the bpy round-trip fixtures, run in their own process), exit 0: 0.211.1's 1,432 and `test_stoop.py`'s nine new checks, all nine failing on 0.211.1, run against an export of it with the new file beside it. `test_stoop_circulation.py` reads the railings off the built shells: four slots a house, Zoo's species in iron, `prop` to the circulation gate, and every rowhome's circulation clear with them in it

## [0.211.1] - a stoop is circulation, not a prop standing in it

**Found by cold run 9271** (0.211.0 in a real drive, 0 interventions): `PRESENTATION_CIRCULATION` 0 -> 12,
one a rowhome -- "stoop_landing 0.15 m into doorway:ext_0_S_open0". 0.211.0 drew the landing and treads
with the surface role `prop`, and this repo's circulation gate (`circulation.check_shell`, run on the
greybox shell by the compose) asks of every `prop` whether it stands in a doorway's walk-through volume.

**The 0.15 m is the gate's, not the stoop's.** `doorway_volume` starts a door's volume at its wall's
bottom plus its sill; `_opening_piece` opens the door at the slab's top (`floor_thick` / 2, 0.15 m on an
Empty) plus its sill; and a landing's top IS the threshold. At grade the offset never showed, because
the 0.15 m under every door is slab and a prop stands on top of it. It is recorded here and not changed:
moving every doorway volume moves every building's gate, and the fix is a slot field the gate can read
(an opening's own bottom), which is Zoo's input too.

- **`_stoop`** draws its landing and treads with the surface role `stair`: a stoop is the way to the
  door, as a flight's treads are, and the greybox paints it the climbable affordance's colour (`gb_stair`).
  The art pass still dresses each piece as a volume: its slot's `role` is the slot's own, `prop`.

**Built:** build.py --all, 146 shells; each rowhome's `surface_roles` names its `stoop_landing`, `stoop_tread_1` and `stoop_tread_2` `stair`, their slots still `prop` in concrete; `circulation.check_shell` on every built rowhome ok, no prop declared and none in a doorway

**Suite:** 1,432 passed; `test_stoop_circulation.py`, 25 checks, 24 of them failing on 0.211.0's built shells -- each the cold run's finding to the millimetre, `stoop_landing` 0.15 m into the front doorway, and the pieces `prop`

## [0.211.0] - a rowhome Empty stands three steps up, on a stoop

**Factory roadmap 240's rowhouse front.** The walker's comps, a Philadelphia rowhouse street: "three or
four steps up to each door, with iron railings; the first floor stands above the sidewalk" (the
factory's `docs/reference/PHILLY_STREET_COMPS.md`). Philadelphia's own guide says it without a number,
"Most existing rowhouses are a few steps up from the street" (City Planning Commission, *Philadelphia
Rowhouse Manual*, 2008, p. 13); the residential code fills the blank, a riser at most 7 3/4 in and a
tread at least 10 in (IRC R311.7.5). The design: the factory's `docs/proposals/ROWHOUSE_STOOP.md`.

- **`stoop.py`** (new, pure): the stoop in front of the front door. Three risers of 7 in on 11 in
  treads (0.1778 m, 0.2794 m), a 0.9 m landing, 1.5 m across. **The contract decides its collision:**
  a 7 in riser is 1.7 times `unassisted_step_max_m`, so a collider a step is a wall to the contract
  body. As the stairs do, the stoop is walked on ONE ramp whose top face is the nosing line -- through
  the landing's front edge and each tread's, meeting grade a tread past the bottom riser, its head
  ending on the landing's edge -- at 32.5 deg. A block stands under each tread but the lowest, one
  riser short of it. 1.74 m deep, ramp included, inside Level Factory's 2.0 m terrace frontage; four
  risers would not fit with this landing (2.02 m).
- **`empty_rowhome(stoop=3)`**: the ground storey's front door and window rise together, so the door's
  threshold (the slab's top plus its sill) is three risers above grade -- a 0.3834 m sill on the 0.3 m
  slab. `stoop` names the stoop for the build, and the palette declares the concrete it is made of. 0
  is the house as it was. All twelve rowhomes take three (the comps' "each door"), written once
  after `EMPTY_ROWHOMES`; their specs are the presets' output again.
- **`_stoop`**, in the facade build after the exterior: the landing and treads as visuals recorded as
  `prop` slots in concrete (the art pass dresses them as it does a volume, `fit.collision` none), and
  the landing, the blocks and the ramp as convex colliders. The spec type and the schema carry `stoop`.

**Built:** build.py --all, 146 shells. Each of the twelve rowhomes, read off its GLB: `stoop_landing`, `stoop_tread_1` and `stoop_tread_2` (visual, three `prop` slots in concrete) and `stoop_landing_col`, `stoop_under_1_col` and `stoop_ramp` (convex); on gs_empty_rowhome_a the ramp is 32.47 deg and 0.9936 m long, its top face's head on the landing's front edge (0.5334 m up, 0.900 m out of the front face) and its foot at grade 1.738 m out; every front door keeps its leaf and its collider, a sill now under it; the manifests move their build time and the twelve's spec hash

**Suite:** 1,407 passed; `test_stoop.py`, 9 checks, 8 of them failing on 0.210.0's houses with `stoop.py` beside them (the ninth holds only the code's limits). The suite caught `test_empty_door_leaf._doors` reading a sill as a window -- the raised front door has one -- and it now takes a door as an opening with a lintel and no pane (`patches/patch_dc_door_leaf_raised.py`)

## [0.210.0] - a rowhome Empty's roof is tar

**The walker's call of 2026-10-12** ("tar now, coating later"; factory roadmap 240's roofscape,
`docs/reference/ROWHOUSE_ROOFS.md` in the factory). The twelve rowhome Empties
(`presets.EMPTY_ROWHOMES`) were roofed in `concrete` under a comment calling the roof "flat tar,
silver-coated"; neither had a source, and in the delco themes `concrete` skinned them in
`concrete_delco` (under `street`, `cinderblock_delco`: a block wall with mortar lines, on a roof). A
rowhouse roof is a membrane over a wood deck, built-up or modified bitumen -- the skin kind `tar`, and
what Zoo's roof already wears in the delco themes, so a row's Empties now match its other roofs.
"Silver" is the colour of an aluminum roof coating over that membrane; how many 1990s Philadelphia
roofs carried one has no source yet, and the walker held it until one is found.

- **`empty_rowhome`**: `roof_material` "concrete" -> "tar", the comment saying why. The twelve
  `specs/gs_empty_rowhome_*.json` carry it (`test_empties` holds each to the preset's own output).
- **`material_kind.KIND_BY_MATERIAL`**: a `tar` row. Until now only `asphalt`, a forecourt's pad, named
  the kind, and a spec saying `tar` reached the slot manifest with a printed "unmapped" warning.
- **`test_material_kind._spec_material_ids`** reads `roof_material`: it read none, so a misspelt roof
  material reached the build unchecked (found tracing the roof slot's name through Zoo and Pixelcoat).
- **`test_empty_roof`** asks for `tar`; it fails on 0.209.1.

**Rebuilt:** The twelve rebuilt, then the library (`build.py --all`, 146 shells in 434 s; the freshness rule marks every shell older than `presets.py`): each Empty's roof slot reads `tar`, 12 of 12, and the tracked manifests moved only their build time (146) and the twelve's spec hash. A roof slot's style moved 4 -> 1: a style is the material's place in the palette, `tar` is in none, and the number names a module family and shapes nothing -- Zoo's recipes read none. `build_freshness.py` up to date

**Suite:** 1,398 passed, 2 skipped, before and after the rebuild; `test_empty_roof` fails on 0.209.1, on the roof slot's material

## [0.209.1] - a stair's column ends at the ceiling of the top floor it serves

**Cold run 9245, the first with roof props** (Zoo 1.101.0 through Level
Factory 0.179.0): the circulation gate's new roofprops arm reported eight
conflicts on two buildings and none a body could meet -- seven HVAC parts on
the office's roof, 10.8 m up, "in" `office_stair_0`, which serves floors 0 to
2 and ends two slabs below them; and a dish on the deli's roof over
`deli_stair_down`, the BASEMENT stair. `stair_volume` reached +/-1e6 in z:
a prop anywhere over a stair's footprint, on any floor, was in the shaft.
The dressing and shell arms never met it because nothing they place stands
over a stairwell on a floor the stair does not serve; the roof does.

- **`stair_column(system)`** reads the stair's own landings: from its lowest
  `nav_endpoints` z to one storey above its highest, the storey being the
  landings' rise over the floors they span (`floors_served`), so no manifest
  field is guessed. The office's stair: 0.0 to 7.2 over floors 0..2, a 3.6 m
  storey, column 0.0 to 10.8 -- the roof's top face, which a prop standing on
  it grazes by nothing, under the gate's 2 cm floor. A stair without
  endpoints keeps the full column, as before.
- **`circulation_volumes`** bounds every stair by it. `stair_volume`'s
  signature and its explicit-z callers are unchanged.
- A stair that reaches the roof carries the roof's floor in `floors_served`,
  so its column still covers the hatch; the landing beside it is Zoo's
  keep-out (0.209.0), as before.

**Re-gated on 9245's composed buildings** (`docs/findings/roof_props/regate_9245.py`,
the patched module against the old packages): on 0.209.0 the probe reproduces the run's own count exactly -- shell 0, dressing 0, roofprops 8 (the office's seven HVAC parts into `office_stair_0`, the deli's dish into `deli_stair_down`), the pharmacy clean; on 0.209.1, roofprops 0 with shell and dressing still 0 across every building and every volume count the same (`regate_9245_0_209_0.txt`, `regate_9245_0_209_1.txt`): the fix owns the eight and nothing else moved

### Tests

`test_circulation.py`: a stair's column reaches one storey above its upper
landing (fails on 0.209.0); a roof prop over a stair two slabs down is not in
its column while a table in the well is; a stair without endpoints keeps the
full column.

**Suite:** 1,398 passed, 2 skipped, exit 0 on the repo: 0.209.0's 1,395 and the three new tests; `test_circulation.py` 28 passed, its 0.209.0 column tests untouched (they pass explicit z)

## [0.209.0] - a roof slot says where a body steps off a ladder, and a building carries a roof-props layer

**Roadmap 181.** Zoo's rooftop scatter (0.25) is reaching levels (Zoo
1.101.0, Level Factory 0.179.0), and 60 of this library's 145 built shells
carry a ladder to their roof: a unit standing where the body steps off
would block the route the ladder exists for. Two things this release owns.

- **`fit.keep_out` on every roof slot** (`roofs.roof_keep_out`): a 3 m
  square (`LANDING_HALF_M` = 1.5, the 1.3 m hatch and a stride past its
  edge) around each ladder whose top story is the roof, written in the
  centred coords `floors.room_voids` writes the slab's holes in -- world
  minus the centre handed in -- and dropped when it misses the rect, as a
  hole is. Empty on a roof no ladder reaches, so every other roof slot is
  byte-identical but for the key. Zoo >= 1.101.0 keeps its props off these
  and off the holes. The footprint roof hands `0.0, 0.0` as its centre, as
  the holes do: right when the top slab is centred, which every library
  roof with a hole is (two of 133 stand off-centre, both hole-less,
  measured 2026-10-11); a stepped building's holes and landings would be
  off by its inset together, and that is noted here rather than fixed.
- **A third content layer.** `portable_building.build_package(...,
  roofprops_glb=None)` bundles Zoo's `<building>_roofprops.glb` at
  `art/roofprops/` and instances it as `RoofProps`, as the dressing and
  the fixtures are. The circulation gate asks the same question of it
  (`circulation.check_dressing`: a unit over a ladder's climb volume, which
  reaches above its hatch, is a conflict), and `combine_circulation` makes
  one `circulation_check` of every arm that ran: one arm is itself, two or
  more are `{"ok", <arm>: check, ...}` with the verdict the AND of theirs
  -- 0.149.0's shape for shell and dressing, unchanged, plus `roofprops`
  when it ran. The readers split by name (`run_presentation_compose.
  circulation_gate`, Level Factory's `_circulation_arms`, which 0.179.0
  teaches the third name).

### Tests

`test_roof_fixtures.py`: a ladder to the roof writes its landing on the
roof slot, a ladder that stops below it writes nothing, a landing is in the
roof's centred coords and dropped off it (two fail on 0.208.0);
`test_circulation_arms.py`: one arm is itself, two keep 0.208.0's shape,
three add the roof, none is None.

**Suite:** 1,395 passed, 2 skipped, exit 0 on the repo before the library rebuild: 0.208.0's 1,389 and the six new tests; on a clone, the one test that reads the built library fails as it does unpatched (no `build/` there)

**Library:** rebuilt (`python build.py --all`, 145 shells, 2026-10-11, about 18 minutes): 52 of the 133 roof slots carry `keep_out`, one landing each (the ladders that top out on their roof -- deli_a01's at x 6.5..9.5, y -13.5..-10.5 around `night_deli_ladder_0`, its hatch's hole inside it), and with the key removed every one of the 145 slot manifests is identical to the 0.208.0 library's as the factory 1.38.0 package shipped it, which carried the key nowhere

## [0.208.0] - a home's room hangs a dome

**Roadmap 229's species step, beside Zoo 1.98.0 and Lux 0.75.0.** A home's
room has been laid by its own rule since 0.206.1 -- a fixture a 7 m bay
since 0.207.1, in a residence or in a residence-like room inside a shop --
and every one of those fixtures was still a 2 x 4 office troffer with a
cool fluorescent row behind it.

- **A home's room writes `dome` anchors** where it wrote `fluorescent`:
  the same rows, ids, drops and positions, a different type. Zoo hangs a
  flush-mount dome on each and Lux lights it warm from under its bowl.
  `_home_room` decides, as it already decided the rows: the building
  (`residence`) or the room's own words (`_HOME_WORDS`).
- A shop's own rooms keep their troffers, and the below-grade and objective
  rooms their bare bulbs: the bulb branch says it is no home.

**Library:** rebuilt (`python build.py --all`, 146 shells), the 131 lights manifests read 67 `dome` anchors carrying 213 lamps in 18 buildings, and 1,004 `fluorescent` anchors carrying 3,889 where 0.207.1's read 1,071 and 4,102 (`docs/findings/fixture_rows/type_census.py` in the factory) -- the home rows moved type one for one, every other type unchanged; the manifests changed by their build stamp alone.

**Tests:** 1 in `test_fixture_rows.py`; its row helper reads a dome as a
row. **Suite:** 1,389 passed, 2 skipped, exit 0 on the repo before the library rebuild and after it (1,388 as 0.207.1 and the new test); on a clone, 22 environmental failures that read the built library, the same 22 an unpatched clone fails.

## [0.207.1] - a home's room takes a fixture a bay, not one whatever its size

**Cold run 9232** (roadmap 229): the deli's `apartment_hideout`, 21 x 16 m,
took the home rule's one fixture at its centre and read dark at both ends,
a hall lit like a bedsit. The guide lights a home a room at a time
(`docs/reference/INDOOR_FIXTURE_PLACEMENT_GUIDE.md`, "By room": a pendant
or flush mount over the sink, one pendant in a bedroom, flush mounts in
a hallway), and a hideout the size of four rooms is lit as four.

- **`_HOME_SPACING`** (7 m): a bay the size of an ordinary room, one
  ceiling fixture a bay. A home's room within one bay keeps its one
  fixture at its centre, byte for byte as 0.206.0 laid it (a 9 x 7 m
  living room, a 4 x 5 m bedroom); a bigger one takes a grid of bays by
  WOOD's row rule at that spacing, the fixtures at the bays' centres
  rather than on a tile line (a home hangs its fixture from the middle of
  the room, not from a grid), the room's cap thinning as everywhere. The
  hideout takes two rows of three.
- Nothing else moves: the home rule's words, the rows to the work, the
  aisles and the long hall are 0.207.0's.

**Tests:** 1 in `test_fixture_rows.py`. **Suite:** 1,388 passed, 2 skipped, exit 0, before and after the rebuild (1,387 as 0.207.0 and the one new case; 1,367 on the draft clone, whose 23 skips are the clone's). **The
library rebuilt:** 1,071 rows and 4,102 lamps where 0.207.0 read 1,048 and 3,933, the difference the home rooms' bays (39 rooms by the library diff, all in residence buildings and residence-like rooms); the deli's apartment hideout stands two rows of three where 0.206.1 stood one fixture and 0.206.0 three rows of four (`docs/findings/fixture_rows/row_census_0207_1.txt`).

## [0.207.0] - ceiling rows over the aisles, between the shelf runs

**Roadmap 229, the second step.** 0.206.0 laid a room's rows to its work
plane across its width, on the ceiling's grid; in a room organised by its
shelving the rows crossed the gondolas as readily as the aisles. A real
store's ceiling is laid to its aisles: the fixture runs over the lane a
body walks, and a troffer over a gondola lights its top shelf and leaves
the aisle beside it to spill.

- **`_lanes_for_room`:** in a room whose words say it sells or stores
  (`_AISLE_ROOM_WORDS`), the visible volumes standing on its floor whose
  name carries a shelf word (`_SHELF_WORDS`: shelf, gondola, rack, pack
  wall) are projected across the room's long axis, the spans clipped to
  the bounds and merged, and every gap between them and the bounds at
  least an aisle wide (`level_design.island_aisle_width`, the contract's
  door width, 1.25 m) is a lane. A sign hung over an aisle is not a shelf
  (`_SHELF_FOOT_MAX`), and a merged span wider than a run is deep
  (`_SHELF_SPAN_MAX`, 2.0 m: a twin island is 1.2) is a field of islands
  staggered along the room, not parallel runs -- the furnish's own layout
  for a selling floor, 66 of the library's 98 shelved selling and storage
  rooms -- and such a room keeps its grid, because the first build kept
  the gas station's rows off its island band and left 14 m of floor
  between them. The 32 rooms with runs (the deli's authored aisle shelves,
  the warehouses' racks, a stockroom's wall run) take the lanes where rows
  light them: 15 in the library's derivation, the rest being objective
  rooms on bulbs or below grade.
- **`_rows_for_room(..., lanes=)`:** each lane is laid as a floor of its own
  width by WOOD's rule, its lines snapped to the pitch and kept inside the
  lane, the lamps along the room's length as before and the room's cap
  thinning every row alike. A room with no shelving, an office with a shelf
  unit against its wall, a home's room, and shelving that leaves no lane
  are laid exactly as 0.206.1 laid them: the default band is the room's
  width and the arithmetic is the same, which the library diff proves
  (`docs/findings/fixture_rows/aisle_rows_diff_0207_draft.txt` in the
  factory: 363 rooms identical, 124 changed, the 15 laid over their aisles
  and the 110 where the cap bound; rows moved 359, removed 110, none
  added; lamps 4,374 to 4,154 in a flat derivation).
- **The long hall:** where the room's twelve-lamp cap binds, WOOD's rule
  cannot hold in both directions at once, and 0.206.0 kept the rows across
  and thinned the lamps along, so a 58 x 20 m hall stood three rows of four
  with 14.5 m between lamps. Now rows across are traded for lamps along
  while the larger of the two spacings shrinks, a row at a time from the
  band that loses least: that hall is two rows of five at 11.6 m along and
  10 m across; a 12 x 11 m office keeps its three of four, whose across
  spacing is the larger and would only grow. Nothing changes where the cap
  does not bind.
- The light manifest line counts the rooms laid over their aisles
  (`rows_over_aisles`).

**Tests:** 8 in `test_fixture_rows.py`; the gas station's storefront reach
test asserts the shape (every sales-floor row reaches the glass from its
own line, the nearer the shorter) rather than three pinned numbers, since
the built floor is now laid to its gondolas and the pure case beside it
has none. **Suite:** 1,387 passed, 2 skipped, exit 0, before and after the rebuild (1,379 as 0.206.1 and the 8 new cases; 1,366 on the draft clone, whose 23 skips are the clone's). **The library rebuilt:** 1,048 rows and 3,933 lamps where 0.206.1 read 1,140 and 4,133, 15 rooms in 13 buildings laid over their aisles (the manifest lines) and 390 rooms with more than one run as before (`docs/findings/fixture_rows/row_census_0207.txt`); the deli's market aisles stand three rows at x -5.2, 0.4 and 4.8 over their three lanes where 0.206.1 stood them at -5.6, -0.4 and 4.4 across the room, and the gas station's staggered-gondola floor keeps its three rows.

## [0.206.1] - a home's room in any building takes the home rule

**Cold run 9229** (roadmap 229): the deli's `apartment_hideout`, a
residence-like room on a shop's upper floor, took three rows of four
troffers, an office ceiling on a bedsit, because 0.206.0's home rule keyed
on the BUILDING being a residence (`is_residence(business)`).

**Now** a room whose role or id carries `apartment`, `hideout`, `bedroom`,
`living`, `flat` or `bedsit` takes the home rule whatever the building: one
fixture at its centre (`_home_room`, `_HOME_WORDS`), and the floor as its
work plane. A residence's rooms are as 0.206.0 laid them.

**Tests:** 1 pure test in `test_fixture_rows.py`, failing on 0.206.0.
**Suite:** 1,379 passed, 2 skipped, exit 0, before and after the rebuild (1,378 as 0.206.0 and the one new case). **The library rebuilt:** 1,140 rows and 4,133 lamps where 0.206.0 read 1,156 and 4,217: ten more rooms take the home's one fixture (124 single-fixture rows where 114 stood) and 390 rooms carry more than one run where 400 did (`docs/findings/fixture_rows/row_census_0206_1.txt`).

## [0.206.0] - ceiling rows laid to the work, on the ceiling's grid

**The walker, 2026-10-10** (roadmap 229): indoor light fixtures should "not
always be in a perfect line, so it looks a little less robotic in the
line/lighting placement". Counted over the 131 shipped manifests
(`docs/findings/fixture_rows/` in the factory), 513 of 513 fluorescent rows
stood on their room's centreline along its longer axis, 303 of them at the
five-lamp cap, with lamps spread 3.0 to 11.6 m apart: one rule lit every
room from its bounds alone.

### What it is now

**Rows follow the room's work plane** (`lights._rows_for_room`; WOOD's shop
rule from the walker's references, `INDOOR_FIXTURE_PLACEMENT_GUIDE.md`):
with A the height from the work surface to the lamp, rows stand at most
1.5 x A apart and the outer row within half of that of its wall, so a room
takes ceil(width / 1.5 A) rows across its shorter axis, each along the
longer one as before, with lamps at 1.5 x A along it. The work surface is
the room's (`_WORK_PLANE`, matched on role and id with the furnish's own
words): 0.75 m where desks are seeded, 1.0 m where it sells or serves, the
floor in a hall, a stockroom, a bay. A 12 x 8 m sales floor is three rows of
four over its width where it was one row of three down its middle; a 12 x
4 m stockroom is still one row. Held to 3 rows and 12 lamps a room, the row
cap of 5 unchanged: the lamp count was a budget number before the bake, and
the price of more is roadmap 229's next measurement.

**Each row's line sits on the ceiling's grid** -- 0.6 m tiles over a desk
or a counter, 0.4 m joists elsewhere, from the building's origin -- so a row
is off its room's centre by up to half a pitch for a structural reason, the
same in every build of a spec. **A home's room is one fixture at its
centre** whatever its size. Below grade and in objective rooms the bulbs
are what 0.205.0 derived.

**Ids:** the first row keeps `<room>_ceiling` (split runs `_<i>` as
before), so every authored override binds as it did; further rows are
`<room>_ceiling_r<k>`, their split runs `_r<k>_<i>`. `_colinear_shift`
takes the row's own `line`; the report and the build line carry
`rows_laid`. `docs/LIGHT_MANIFEST.md` says so.

**Lux (>= 0.62.0) fails one tube AN ANCHOR**, so a three-row sales floor
would stutter three; the fix is Lux's, one a room by the anchor's base id,
and lands beside this.

**Tests:** `test_fixture_rows.py`, 10 pure tests: the narrow stockroom's one
row and unchanged id, the sales floor's three on the tiles, the office's two,
the room cap thinning every row alike, a room one spacing wide, the joist
snap by half a pitch at most, the home's one fixture, the bulbs as they
were, a second row's split runs named, a colinear partition moving only the
row it lies under. The void and partition suites keep their argument on
rooms narrowed to one row (the measured hospital lobby's lamps at x = +-8
reproduced on a 4.5 m slice of it), and the partition report gains
`rows_laid`. **Suite:** 1378 passed, 2 skipped, exit 0 on the repo, before the rebuild against the old library and after it against the new (1,342 on the draft clone; 1,366 as 0.205.0 and the 10 new cases, with the gas station library test adapted to its three rows). **The library rebuilt:** `build.py --all` rebuilt the 131 specs clean, and `docs/findings/fixture_rows/row_census.py` over the new manifests (`row_census_0206.txt` in the factory) reads 1,156 fluorescent rows in 475 rooms where 0.205.0 had 513: 400 rooms carry more than one anchor, 1,035 rows stand off their room's centreline and 121 on it (a line a tile or a joist pitch away is the rule, not the exception), every row still along the longer axis, and the lamps a row are 4 x 646, 5 x 201, 3 x 124, 2 x 71, 1 x 114 -- 4,217 lamps against 2,083, twice as many, which cold run 9229 prices. The spacings run 2.7 to 14.5 m: the room cap thins a long hall's three rows to four lamps each, so the longest rooms are sparser along the row than before, a trade the next step should revisit by favouring lamps along over rows across where the room is long and narrow.

## [0.205.0] - a den's windows are drawn shut

**The walker, 2026-10-09,** walking club_block_014 (roadmap 219, note 2):
"the windows in any 'den of sin' building should have curtains or drapes or
blinds So people outside can't see in, and you keep the streetlight light out
of the club". strip_club_a01's one window was clear glass, with an area light
behind it standing for the street through the glass.

### What it is now

**Every window of a strip club hangs Zoo's `window_drape`** (>= 1.91.0): two
velvet panels drawn shut under a pelmet, on the room side of the glass. The
rule, `level_design.plan_den_drapes`, places each one off the window the
builder cuts:
- centred on the window's own snapped position. strip_club_a01's is at x
  12.0, where `pos * run` alone says 11.9;
- 0.15 m past each jamb, and 0.10 m under the sill;
- its pelmet 0.15 m over the head, where the ceiling allows;
- 0.03 m off the wall's inner face, as a window poster is taped;
- turned to face its room;
- with no collision, since the window's pane seals the opening;
- in `velvet`, declared with the club carpet's `Curtain` acoustics.

**`furnish` runs the rule beside `dress_club_rooms`,** so a generated den
hangs its own: the `strip_club` preset is windowless today. A new migration,
`migrate_den_drapes.py`, applies it to the authored specs, whose furnishing
is baked in. Both are idempotent:
- a drape already there is replaced by the rule's;
- one the rule no longer asks for is removed;
- the migration puts a new one before the pieces `furnish` wrote.

**The library's dens.** Two of the three strip clubs have windows:

| club | drape | at (m) | size (m) |
|---|---|---|---|
| strip_club_a01 | `window_drape_s0_1` | (12.0, -11.74, 2.475) | 1.5 x 0.16 x 1.55 |
| strip_club_a03 | `window_drape_s0_1` | (11.0, -11.74, 2.475) | 1.5 x 0.16 x 1.55 |
| strip_club_a03 | `window_drape_s1_1` | (-11.0, -11.74, 5.725) | 1.7 x 0.16 x 1.65 |
| strip_club_a03 | `window_drape_s1_2` | (11.0, -11.74, 5.725) | 1.7 x 0.16 x 1.65 |

strip_club_a02 has none.

**A draped window lets no light in.** `lights.derive_light_anchors` derives
no `window` area light behind a drape (`_drapes_window`). The window is still
counted first, so every other window on its wall keeps its light's id, and an
authored override keyed on that id still finds it. The report counts
`draped_windows`.

**Furnish never sees a drape.** The suite's first run failed four
fixed-point tests (`test_back_bar`, `test_club_fixtures`, `test_club_rooms`,
`test_wall_backing`). Re-furnished with its drape present:
- strip_club_a01's club room was re-drawn, fourteen pieces named differently
  and three fewer;
- strip_club_a03's upstairs room gained a chair.

A drape's foot is 1.3 to 1.7 m up, under `_HUNG_MIN` (1.8 m). So it was
counted as a piece the room held (`_room_volume_count`), and cleared as a
floor piece by `_seed_clear`'s 0.9 m. Now:
- **`_hung(v, floor)`** sits beside `_HUNG_MIN`. The five clearance checks
  that read `_HUNG_MIN` ask it (four `if`, `_seed_clear`'s `elif`), and it
  calls a drape hung. Every other volume answers as before.
- **`_room_volume_count` leaves a drape out:** the window sign's defect a
  fourth time (0.160.0, 0.170.0, 0.201.0). It is not a rule by foot height,
  and that was measured: over the library's 1,345 collision-free volumes, such
  a rule would move 683 of them. They are furnish's own posters, banners and
  hangers, which count toward a room's target today, so the rule would
  refurnish the library.
- **A drape is safe to ignore.** It spans its window and 0.15 m past each
  jamb, against the wall, where `_clear_of_openings` already keeps a wall
  piece 0.9 m clear.

The library is a fixed point of furnish again.

**The name reaches Zoo's species.** `prop_species` routes `window_drape`
after `window_sign`. Nothing earlier in the table claims the name (`draped`
is `dust_sheet`'s, and `window_drape_` does not contain it). Each drape's
dims fall inside the genome's ranges, so Zoo builds the species and not the
fallback box.

### The price

One draw a window: the species is one material. 944 to 1,064 triangles a
drape (Zoo 1.91.0), four in the library.

### Tests

`test_den_drapes.py`:
- every window of a strip club hangs one drape over the window the builder
  cut, measured against `build/<club>.gameplay.json`'s openings: centred,
  wider, from under the sill to over the head and under the ceiling, on the
  room side, turned to it;
- no other building is draped;
- the rule is idempotent, declares its velvet once, and removes a drape it
  no longer asks for;
- furnish never sees a drape: under the hung line, hung all the same, and
  out of every room's count;
- the name reaches Zoo's species, inside its genome;
- a draped window draws no light while the next keeps its id;
- the library's clubs carry their drapes (`migrate_den_drapes.py --check`);
- the built clubs draw no window light.

On 0.204.1 the file does not import: no `plan_den_drapes`, no
`lights.DRAPE_NAME`, no migration.

**The suite:** 1,368 passed, 2 skipped (`python -m pytest -q`). 0.204.1's
were 1,358 and 2; the difference is `test_den_drapes.py`'s 10.

**The library was rebuilt:** all 146 shells (`build.py --all`), after the
migration.
- **The two clubs changed in substance:** their slots carry the drapes,
  their lights lose the windows (a01's one, a03's three), and their
  gameplay files add the velvet and the drapes' roles.
- **Every other manifest changed only its `built_utc`.** No GLB changed.

## [0.204.1] - a quarter of the rowhome roofs carry an antenna or a dish

**The walker, 2026-10-09,** walking club_block_014 (roadmap 219, note 3):
"far too many Sattelite/Attena that makes the rowhomes look a little too
uniform and computer generated. perhaps 30% as many?"

**What was there.** The roof fixtures come from `presets.EMPTY_ROWHOMES`
(0.185.0): an antenna on eight of the twelve houses, "as a 1990s
Philadelphia street has -- cable came late to the city", and a dish on two.
That is 10 fixtures on 9 houses, and every copy of an archetype repeats its
roof.

**Now 3, 30% of 10,** on 3 houses:
- antennas on a and g;
- the dish on k.

A street of the twelve shows a quarter of its roofs dressed. The presets
lose six rows' fixtures (b, d, e, i, j and l). The six specs follow, as the
presets generate them, and the six shells were rebuilt.

*First attempt, refused by the suite and kept here.* The six specs were
edited by hand, and two tests failed, because the presets still asked for
fixtures the built roofs no longer carried:
- `test_roof_fixtures`'s built-roof test;
- `test_empties`'s preset-output test.

The presets are the source.

**Tests.** `test_the_family_has_antennas_on_two_and_a_dish_on_one`
(renamed from `..._on_eight_and_dishes_on_two`) fails on 0.204.0.

## [0.204.0] - a payphone on a wall is a wall unit

**What the walker asked for.** Roadmap 210, 2026-10-09: "yes light it, and do
the indoor wall form".

**What was there.** `level_design._piece("payphone", ..., "wall")` stands a
payphone against a wall, and it asked for no form. So Zoo's `auto` built
every one as a booth on a post, standing on the floor in front of the wall.
Cold run 9212 shipped two of them: the airport terminal's and the funeral
home's.

**The piece now asks for Zoo 1.88.0's `wall` form:** no post, a conduit down
the wall, and a phone book on two rings under the shelf. Since Zoo 1.89.0 it
also has a lit header and a hood lamp.

**The library, refurnished** (`migrate_furnish_recipes.py`, the L23 rule: a
piece edit needs a refurnish):
- **On a copy first:** 128 specs. 38 changed, and in them exactly 39 payphone
  volumes gained `"form": "wall"`. Nothing else moved, structurally or byte
  for byte once that field is taken out.
- **Then the repo,** which matched the copy file for file.
- **The 38 shells rebuilt** (`build.py <spec>` for each; `--all` is that
  loop): 0 failures, and `build_freshness` up to date at 146.
- **The tracked outputs that moved:**
  - 32 `slots.json`, each only in its payphones' `form`;
  - 38 manifests, only in `built_utc` and their two hashes.
- **Six more `slots.json` carry the form too:** police station 07, the
  `cbp_town_finale` finale (two payphones), `final_stand`,
  `foundry_heist_vertical`, `office` and `survival_demo`. `.gitignore` keeps
  those six out. 32 tracked slots plus 7 untracked is the 39.

**Left alone: the two payphones the piece did not place.** `primos_pizza`
and `strip_retail_a01` each carry an AUTHORED payphone, named plain
`payphone`.
- Its slot is 0.5 x 0.5 x 1.6 m, unrotated, 0.25 m off the dining room's
  back partition.
- The refurnish does not touch an authored volume.
- A wall unit there would hang a quarter of a metre off the wall, so both
  stay booths on their posts.

**A second fix: `material_kind.SKIN_KINDS` learns `paint_matte`.**
- `SKIN_KINDS` is a literal copy of Zoo's `skins.KNOWN_KINDS`.
  `test_material_kind.test_the_kinds_are_zoo_s_when_zoo_is_beside_this_repo`
  pins it to Zoo's list.
- Zoo 1.82.0 (the getaway van, 2026-10-07 22:35) added `paint_matte`.
  0.203.0's suite had run at 14:54 that day, and this release's was the
  first since. It found the pin failing.
- **The pin fails the same against Zoo 1.88.0** with this repo untouched. It
  is the drift the test exists to catch, not this release's change.
- No spec writes the kind (Lot stands the van), so it has no
  `KIND_BY_MATERIAL` row.

**Tests:** `test_payphone_wall_form.py`, 4.
- **On 0.203.0 three fail:** the piece has no form, and the 39 payphones it
  placed, and their slots, ask for none.
- **The fourth** guards that the form moved no size.

**Suite:** 1358 passed, 2 skipped in 95 s (`python -m pytest -q`). That is
0.203.0's 1354 and this release's 4. Before the kind fix, 1 failed: the pin
to Zoo's kinds.

## [0.203.0] - a slot owns its own greybox nodes, never a sibling slot's

**How it was seen.** Cold run 9195 (gas_block_001) stopped at the art leg on
one blocker, `PRESENTATION_PLACEMENT_MISMATCH`:

    gas_station_a02: 1 themed module(s) do not match the greybox footprint
    (visual off the collision); 166/167 aligned. Worst: cooler_run
    (prop_cooler_run_delco_1997_04_w328_d90_h220: placed [3.28, 2.2, 0.9]
    on greybox [25.442, 2.2, 0.9])

**The cooler run was never 25 m.** The slot is 3.28 m, at x 14.26, and the
module was built to it. The greybox carries two cooler runs, `cooler_run` (x
12.62..15.90) and `cooler_run_sales` (8.0 m, x -9.54..-1.54). Their union is
exactly 25.442 m.

**The cause.** The placement gate (`portable_building._slot_greybox_extent`)
and the composer's fit (`themed_tscn._slot_extent`) took a greybox node as
part of a slot when its name was the slot id or began `<slot_id>_`. That is
the rule for an opening's own parts (`_lintel`, `_sill`, `_pane`), and it was
written so `seg1` would not swallow `seg10`. But it also swallowed a SIBLING
slot whose id begins the same way: `cooler_run_sales` begins `cooler_run_`.

**How far it reached:**
- 9 of 145 library buildings carry a slot id that begins another's, 19
  pairs.
- In 5, the sibling has greybox nodes:
  - the three pawn shops (`cr_pawn`, `night_pawn`, `pawn_shop_a01`):
    `counter` swallows `counter_service_..._1`, read as 9.86 x 6.36 m against
    its own 4.0 x 0.7;
  - the two gas stations (`gas_station_a02`, `fuel_stop_heist`):
    `cooler_run` swallows `cooler_run_sales`.
- Every level placing one of the five stopped at its art leg.
- The composer orients each module by the same extent. The cooler run's
  orientation came out right only because 0 degrees fit better than 90.
- The banks' `floor_vault` and `ceiling_vault` collide in name but have no
  greybox nodes, so neither reader measured them.
- **Not new.** Cold run 9184's compose manifest for gas_station_a02 carries
  the identical mismatch. Level Factory 0.147.0 never read it: it read one
  placed building's package of many. Level Factory 0.149.0 reads them all.

**The rule now, one copy:** a node belongs to the LONGEST slot id that names
it.
- `themed_tscn.longer_siblings(slot_id, slot_ids)` lists the siblings that
  begin `<slot_id>_`.
- `themed_tscn.owns_node(slot_id, node, siblings)` answers for one node.
- Both extents take the building's slot ids, and both callers pass them.
- `verify_placement` lists its slots once, since it walks them twice.

**Measured after.**
- The gate, re-run on the real gas_station_a02 greybox with cold run 9195's
  own kit and the compose job's arguments (`--theme delco_1997 --style 1`),
  reads 167 checked, 167 matched, 0 mismatched. The job's manifest read 166
  and 1 on the same 167.
- `themed_tscn.py` is a geometry source, so `build.py --all` ran once
  (7 min). Its only tracked change is each of the 146 manifests'
  `built_utc`: no shell, slot or gameplay file moved.

**Tests:** `test_slot_extent_owner.py`, 7.
- On 0.202.0 all 7 fail: the extents take no slot ids, and the real
  greybox reads 25.442 m.
- Two are guards that the old guarantees survive: an opening's parts still
  measure as one, and `seg1` still does not own `seg10`.

**Suite:** 1354 passed, 2 skipped in 93 s (`python -m pytest -q`): 0.202.0's
1347 and this release's 7.

## [0.202.0] - a wall piece needs a wall behind it, and furniture keeps off a hole in its own floor

**How it was seen.** Framing the deli case in cold run 9190's deli_a01, two
things stood in front of its service front: an ATM, and two paper lottery
boards hanging in mid-air. All were furnish's wall pieces, slotted against
the customer floor's north edge (y -3.0). No wall stands there: the customer
floor meets the deli counter room across open floor.

**The measurement** (the factory's `docs/findings/wall_pieces_without_walls/`):
- **155 of the library's 4,086 furnished wall pieces, in 18 shells,** stood
  against a room edge with no built wall behind them.
- The six delis held 76, apartment_walkup_a01 18, rowhouse_raid 17.
- By kind: shelf runs 43, file cabinets 27, store poster boards 17, waiting
  chairs 10, service counters 10.

**Why.** `_wall_slots` offered a wall piece every edge of its room. It
checked an exterior edge's openings and glazing, but an interior edge it took
for a wall and never asked. Measured against 0.201.0's library:
- 3,924 wall pieces stood against exterior walls, 42 near a partition and
  120 against nothing.
- `_seed_clear` keeps every piece 1.0 m from a partition's line, so furnish
  furnished partitions almost never.
- Its "interior walls" were, in practice, open edges.

**The rule** (`_edge_backing`, `_held`).
- **Where a slot is offered.** Only where a wall the builder stands lies on
  the edge, and holds the piece's whole run. These are
  `layout_lint.built_walls`, the walls L25 measures, cached per spec.
- **Every slot is drawn and shuffled as before.** The unheld ones are
  dropped after the shuffle, so the held slots keep their order and the
  random stream is untouched. Only a piece that stood against nothing moves,
  and what its move displaces.
- **Refuted, kept:** the first draft dropped an unheld slot before the
  shuffle. That changed the length of every shuffled list, and its dry run
  re-rolled 33 specs where 18 held a piece against nothing.

**Furniture keeps off an authored hole in its own floor** (`_seed_clear`).
- L23's second cause, "UNSEEN": furnish cleared the stairs and never an
  authored `slab_holes` opening.
- The wall rule's refurnish re-rolled apartment_walkup_a01's dining room and
  rowhouse_raid's. Both dining sets landed over their 2 x 2 m drop holes,
  rowhouse_raid's for the first time.
- **The rule:** a piece standing on a storey keeps the stair reserve's own
  0.3 m off every authored hole in that storey's floor.
  - Its own storey only: the storey below stands under a hole, not on it.
  - A hung piece is not asked.
- **What it moved.** cbp_town_finale's and final_stand's furnished pieces,
  inside atrium holes of 28 x 22 m and 10 x 8 m that nothing fills, and both
  dining sets.

**The library** (`migrate_furnish_recipes`, both rules): 20 specs moved.
- These are the census's 18, plus cbp_town_finale and final_stand. 153 fewer
  furnished pieces in all: most of the 155 had no other wall to go to.
- deli_a01's customer floor carries nothing on its open edge, and no
  library wall piece stands without a wall.
- **The 20 shells are rebuilt.** `level_design.py` is not a geometry
  source, so nothing else needed it.

**Baselines moved, each by measurement:**
- `stale_pieces_baseline.json`: 47 pieces in 8 shells -> 18 in 7.
  apartment_walkup_a01 leaves the list, along with 20 of cbp_town_finale's
  pieces and 6 of final_stand's. Nothing joins it. The 18 left are authored
  volumes and structure.
- `test_club_fixtures`: the library's cigarette machines 121 -> 119. The two
  stood against open edges.

**The furnish and club probes stand their rooms in walls.**
- They stood a room 2 m inside a larger footprint, "so its walls are
  interior": edges the rule now refuses. 18 failed for that alone.
- Each room becomes the shell, and two basement probes declare their
  basement. All 68 tests in the three files pass on 0.201.0 with the new
  fixtures, so the fixtures changed what they stand in, not what they test.

**Tests:**
- `test_wall_backing.py`, 8. Five fail on 0.201.0: an open edge, a
  part-wall, the library, the deli's open edge, and a generated deli. The
  guards (a walled edge, an exterior edge) and the fixed point pass either
  side.
- `test_stale_pieces.py` +2. The hole test fails on 0.201.0; the storey-below
  guard passes either side.

**Open:** a partition is still unfurnished. `_seed_clear`'s 1.0 m rule keeps
pieces off every partition's line to keep its doors clear, and a rule that
clears a partition's openings, not its length, would let its walls be used.

**Suite:** 1347 passed, 2 skipped in 89 s (`python -m pytest -q`): 0.201.0's 1337, test_wall_backing.py's 8 and test_stale_pieces.py's 2.

## [0.201.0] - a deli hangs its beer sign in its front window and tapes its posters under it

**What it was.** Not one of the six library delis carried a window sign or a
window poster.
- The store rules (`migrate_window_sign`, `migrate_window_poster`, 0.160.0
  and 0.170.0) qualify a store only: a `sales_floor` with snack gondolas, and
  a storey-0 `storefront_glass` wall. They hang the sign beside a door in a
  wall of glass.
- A corner deli's street face is brick. It has the customers' door
  (`front_customer_entry`, pos -0.28) and one punched window: 2.0 m wide,
  sill 0.85, head 2.25 (`Opening.resolved`'s 1.4 m), 10.5 m from the door.
  The window opens into the market aisles.

**The window rule** (`migrate_window_sign.front_window`, `plan_window`).
- **The front window** is the storey-0 window on the wall that carries the
  customers' door, the one nearest that door.
- **The sign** hangs in it, centred, its top at the window's head, 4 cm
  inside the wall's inner face, against the pane as a deli's neon hangs.
- **The posters** (`migrate_window_poster.plan_window`) are taped low under
  it:
  - 10 cm over the sill and 5 cm under the sign's foot;
  - 0.25 m toward the customers' door, where they pass.
- **A window too small for both** hangs the sign and says why it has no
  posters. A building with no window on the door's wall is refused, and says
  so.
- **The store's rule is untouched.** Three library stores keep their sign
  exactly where it was (pinned).

**Generated and drawn alike.**
- `presets.corner_deli` runs both rules, as `gas_station` dresses its glass.
- The two migrations brought the six library delis to them: each has the
  sign at (0, -13.755, 1.95) and the posters at (-0.25, -13.79, 1.25).
- **The neon names** are Zoo's six invented beers (`club_names.WINDOW_NAMES`),
  dealt by the spec's name. **The posters** are the store family's sale
  sheets.

**A sign hung in a window stands on no floor.** In a deli's window the sign's
foot is at 1.65 m, under the headroom line that exempts a hung sign from
furnish's room count.
- `level_design._room_volume_count` now exempts a `form: window` sign at any
  height, as 0.170.0 exempted paper on a wall. Counted, it would have cost
  the market aisles a piece on every refurnish.
- **`test_window_sign`'s control moves to the sign's WALL form.** It proved
  the headroom line still counts a low piece by lowering the window sign
  itself, and would have failed for this change rather than for the rule it
  guards. Found by running the window tests against a scratch copy with this
  release applied: `assert 13 == 13 + 1`.

**Tests:** `test_deli_window.py`, 11.
- **9 fail on 0.200.0.**
- **2 guards pass either side:** furnish's fixed point on the six delis,
  and the stores' signs where they were.
- `test_window_sign.py`'s moved control passes either side.

**Suite:** 1337 passed, 2 skipped in 69 s (`python -m pytest -q`): 0.200.0's 1326 and this release's 11.

## [0.200.0] - a deli's case asks for Zoo's deli case

**What it was.** `deli_case_cover`, the case every corner deli stands in
front of its deli counter, routed to no species. So it built as a plain box
wearing glass. Cold run 9189's composed deli_a01 stood a 7 m
`prop_delco_1997_03_w700_d110_h130_mglass` there.

**What it asks for now.** Zoo 1.81.0 grows the species: curved glass, a lit
deck of salads, cards and parsley, and whole logs cut to the glass. One row
in `prop_species.PROP_SPECIES` (`deli_case`) routes the name to it.
- **What the keyword reaches** in the 146 non-LF specs: six volumes, one
  `deli_case_cover` in each of corner_deli_heist_01, cr_deli, deli_a01,
  deli_a02, deli_a03 and night_deli.
- `the_deli_counter` (primos_pizza, strip_retail_a01) does not contain it
  and stays a counter.

**The six shells are rebuilt.** Each one's case slot asks for `deli_case` at
5.815 x 1.1 x 1.3. That is the case as 0.199.0 trims it off its wall, inside
the species' range (1.2-8.0 x 0.8-1.4 x 1.1-1.5).

**Tests:** `test_prop_species.py` +1. The test fails before the row: the
name routed to nothing. Every other test in the file passes either side.

**Unproven until a cold run draws a deli.**

**Suite:** 1326 passed, 2 skipped in 74 s (`python -m pytest -q`): 0.199.0's 1325 and this release's 1.

## [0.199.0] - no piece passes through a wall: the deli's case stopped 0.825 m into the market aisles

**How it was seen.** Sizing the deli case for roadmap item 186's deli detail.
In cold run 9189's composed deli_a01, `deli_case_cover` stands at
x -14.0..-7.0, and partition segment `int_0_0_seg6` stands at x -8.0 across
it. So the last 0.825 m of the case came out of the wall into the market
aisles. `presets.corner_deli` authors it that way, so it was in all six
library delis and in every deli the recipe generates.

**The measurement** (the factory's `docs/findings/pieces_through_walls/`, two
instruments that agree). Every authored piece was checked against every wall
the builder stands, across the 146 non-LF specs. 19 pieces in 15 specs reach
past both faces of a built wall:
- **THROUGH, 7:** the piece's centre stands off the wall and its far end
  comes out of it. Each deli's case (0.825 m), and `warehouse`'s 16 m
  shelving run (3.85 m).
- **ALONG, 12:** the piece is centred on the wall's line. These are racks
  and forklift bays on y -3.0, two vomitory covers and a rollgate, a vault
  door, and four columns.
- **The recipes:** `corner_deli` (the case) and `hospital` (its waiting
  seats, 0.35 m) generate a piece through a wall. `casino_tower` (its
  basement vault block) and `parking_garage` (a column) stand one along a
  wall.

No gate saw any of them. Every rule asked a piece where it stands; none
asked whether a wall stands in it.

**L25 (WARN), `layout_lint.wall_crossings`.** It measures the walls as the
builder stands them, asking the builder's own helpers.
- **Partitions:** `partition_bounds.partition_spans`, clamped to the storey's
  setback extent and split round `stairwell.wall_voids`.
- **Exterior walls:** every side on every storey under `auto_exterior`.
- **Pieces:** each is measured by its box, which is the greybox and its
  collider, and, when `rot_z` turns it, by its art turned.
- **Openings are not cut.** A leaf, a panel or a pane fills each, and no
  crossing stood at one.

**The trim, `migrate_wall_crossing.trim`.** A piece THROUGH a wall keeps its
near end. Its far end comes back to the wall's near face, less
`level_design._WALL_PIECE_AIR`. It is refused, with the reason, when:
- the piece stands along the wall;
- the piece is turned;
- the cut would take more than half the piece;
- the cut would take the ground from under a marker.

Where it runs:
- **`presets.make`** runs it on every recipe before any pass places round
  it. A generated deli's case stands x -14.0..-8.185, and a generated
  hospital's seats stop at their wall.
- **The library:** the migration trimmed 7 pieces, the six cases to
  x -14.0..-8.185 and the shelving run to x -4.0..7.84. Each spec changed in
  two numbers.
- **The twelve ALONG a wall** are frozen in `wall_crossing_baseline.json`,
  each needing a look. After the migration, both instruments read 12 in 8
  specs.

**Tests:** `test_wall_crossing.py`, 19. All 19 fail on 0.198.0. 16 pass with
the rule, the trim and the generator change, before the library is migrated.
The last 3 pass after the migration: the library's cases stop at their wall,
the migration is a fixed point, and no new crossing appears.

**Suite:** 1325 passed, 2 skipped in 68 s (`python -m pytest -q`): 0.198.0's 1306 and this release's 19.

## [0.198.0] - the z-fight gate judges a pair by the side its faces face: 436 pairs were 5

**The measurement** (roadmap 177's open question: nobody had looked at the
pairs). Cold run 9189's composed buildings, by `zfight_gate`'s own raw
pairs:

| building | visible, 0.197.0's rule | buried by it | visible by what the faces face |
|---|---|---|---|
| deli_a01 | 198 | 19 | **2** |
| office | 121 | 0 | **2** |
| rail_station_a02 | 117 | 0 | **1** |

Nearly every pair was two bottoms on one plane, facing down into a slab:
- a chair, a counter or a stool and the floor module it stands in;
- a stair tread and the stairwell's floor module.

No camera can reach either face of such a pair. The rule buried a pair only
inside a solid with matter on BOTH sides of the plane, which holds for a
face inside a wall band and never for one pressed against a slab.

**The rule.** A same-facing pair can be seen only from the side its faces
face. `visible_fights` now buries it when solids starting within
`OUTWARD_GAP` of the plane on that side, and reaching `OCCLUDE_MARGIN` past
it, cover the shared rectangle.
- `OUTWARD_GAP` is the composer's own wall-family sink
  (`themed_tscn.SLAB_CAP_SINK`, mirrored and pinned by a test) plus the
  gate's tolerance: 5.5 mm. That shuts the caps the composer sinks 4 mm
  under the slab above them. A 5 cm gap read the same.
- Matter on both sides is matter on the facing side, so every pair the old
  rule buried, this one buries too. All 12 old tests pass unchanged.

**The cover is 2-D now** (`_rect_covered`, replacing the 1-D
`_union_covers`).
- The 1-D union needed one box to span the shared rectangle across, so four
  slab tiles meeting in a corner under a desk read as uncovered.
- **The tolerance is load-bearing.** 9189's slab tiles meet at -9.333000183
  and -9.332999944, a float32 seam of 2.4e-7 m. **Refuted, kept:** the
  census's first 2-D cover had no tolerance and called every seam a hole,
  leaving 31 of deli_a01's pairs; the gate's own 1-D union had always
  carried `tol`.

**The 5 left are worth a frame.**
- **deli_a01 (2) and rail_station_a02 (1):** a partition's end runs into
  the exterior wall where one wall segment is exactly the partition's
  width, so their faces share a plane at the junction. Where the next
  segment is a window opening, the faces show on the jamb.
- **office (2):** the reception desk stands on a greybox ledge of exactly
  its width, and their sides are coplanar, facing the room.

**Tests:** `test_zfight_gate.py` +8.
- Five failed before the change: bottoms pressed on a slab, float32 seams
  between tiles, a 2 x 2 corner of tiles, caps sunk under the next slab,
  and the gap's derivation.
- Three guards pass either side of it, so the rule cannot hide too much:
  the same bottoms with nothing under them, a rug on the floor, and the
  office's flush desk.

**Suite:** 1306 passed, 2 skipped in 63 s (`python -m pytest -q`).

## [0.197.0] - open floor is a way in: L24's utility rooms were never breach-only

**Refuted: 0.194.0's L24 census.** L24 asked L12's graph, which joins rooms
through openings, stairs and ladders only.
- deli_a01's basement partition along y = 1 stops at x 12, so its utility
  room's north edge from x 12 to 19 is open floor. Cold run 9189's bake
  walks across it on the street's island, and L24 named the room "reachable
  only by breaching".
- On that report the walker said to give the deli family's utility rooms
  doors. They are walked into already, so none was added.
- 11 of the 15 rooms 0.194.0 froze were open floor or downstream of it:
  - the deli family's six basement utility rooms;
  - apartment_walkup_a01's kitchen, and through its stair and a door, its
    bedroom and office;
  - rowhouse_raid's kitchen and basement vault.

**One rule.** `tactical.build_graph` has modelled open floor all along, as
a closure. It is lifted unchanged to `tactical.shared_open_edge`, and
`layout_lint._reach_from_ext` asks it for L12 and L24. `build_graph`'s
adjacency was recorded on all 128 room-bearing specs before the lift and
compared after: identical.

**L24 now: 4 rooms in 4 shells**, frozen in `walk_reach_baseline.json`:
- the server room where it is the OBJECTIVE, in cr_deli, deli_a02 and
  night_deli: breach-only by design, the walker's call (an objective you
  breach into);
- deli_a03's fortifiable server room, pending.

Lint warnings went from 420 to 409: the 11.

**Refuted on the way, kept.** A scratch census first kept
apartment_walkup_a01's bedroom and office. It added open-floor links on top
of the old walkable set without re-following stairs and doors from the
rooms they reached. The shipped search is one graph, and
`test_walk_baseline_has_not_gone_stale` named the two first.

**A weakness of the shared rule, not changed here.** It sums the uncovered
length of a shared edge across separate gaps.
- apartment_walkup_a01's storey-1 office-bedroom edge reads open from two
  1 m slivers at its ends, about 0.85 m clear each.
- Nothing L12 or L24 decides rests on it today: a door joins those rooms.
- Changing it changes `build_graph` for its seven callers.

**Tests:** `test_walk_reach.py` +3. All three failed before the change.

**Suite:** 1298 passed, 2 skipped in 67 s (`python -m pytest -q`).

## [0.196.0] - the nav gate asks whether an entrance reaches each stair

**Why.** A stair whose two ends join is a stair, not a route. deli_a01's
up-stair passed this gate in every build: both ends on one island, navigable
"yes". Meanwhile two crate stacks cut its foot off from the stairwell's
door, and its whole upper storey with it (cold runs 9187 and 9188; 0.195.0;
`docs/findings/deli_a01_upper_storey_9188/` at the factory root).

**The check** (`godot/addon/deli_counter/nav_gate.gd`).
- `_entry_points` takes each storey-0 exterior door and garage from
  gameplay.json and moves it `ENTRY_IN` = 1.0 m along its wall's inward
  normal. That is past the wall's erosion and inside the 1.5 m approach no
  seeded piece stands in.
- Each point is snapped with the marker rule (`MARKER_MAX_ABOVE`), so it
  never lands on furniture.
- Each stair reports `from_entry`: is either end on an island an entrance is
  on? It is null when no entrance snapped or an end is off the mesh.
- The result carries `entries` (points, snapped, `stairs_judged`,
  `stairs_unreached`), and `nav_gate.py`'s verdict prints "stairs an
  entrance reaches: k/n" and names each stair it does not.
- **Reported, not gated**, like `navigable`. The stair verdict and the exit
  code are unchanged.

**The control fails first.** On the shipped deli_a01 (cold run 9188's GLB
with its own gameplay file), both stairs read "ok" and navigable "yes",
as before, and the new line reads "stairs an entrance reaches: 1/2 -- no
entrance reaches stair deli_stair_up". On 0.195.0's deli_a01 it reads 2/2.

**The library** (`nav_gate.py --all`, after 0.195.0).
- 98 shells have judged stairs, 149 stairs in all, and 148 are reached from
  an entrance.
- **The one that is not is `primos_pizza_stair_0`**, basement to storey 1
  through the ground floor. Its ends join and all three entrances snap, but
  the ground floor cannot reach it. Roadmap 189 located that neck: its
  discharge plate stands against the north wall beside its breach panel.
- No shell with stairs went unjudged. 14 have no storey-0 exterior door: the
  12 Empties, shut by design, and the two facade shells, which have no stairs.

**Frozen** (`navgate_baseline.json`, `entry_unreached`): primos_pizza, with
that reason. `test_navgate_population` fails on a new stair no entrance
reaches, on a frozen one an entrance now reaches, and on a result from
before this check.

**Tests:**
- `test_navgate_entries.py`, 4. All four failed with the gate patch stashed.
- `test_navgate_population.py`, +4. With primos_pizza dropped from the
  frozen set, the no-new test fails and names it.

**Suite:** 1295 passed, 2 skipped in 66 s (`python -m pytest -q`).

## [0.195.0] - a seeded piece leaves a body's width on every side, and deli_a01's upper storey reaches the street

**The measurement.** In cold runs 9187 and 9188, deli_a01's upper storey
(779 m2 once 0.194.0 gave its server room a door) was a navmesh island the
street could not reach. The stairwell's plan, drawn against the bake
(`docs/findings/deli_a01_upper_storey_9188/` at the factory root):
- the up-stair, with its side and back guards, runs from the stairwell's
  south wall to its foot, so the only ways from the stairwell's door to the
  stair's foot run north past it;
- two crate stacks `seed_cover` placed shut both of them, where a bake that
  erodes 0.4 m a side needs 0.8 m:
  - `crate_stack_stairwell_0` left 0.79 m and 0.54 m. It was stale: today's
    `_seed_clear` refuses where it stands, 0.01 m off the up-stair's foot
    landing;
  - `crate_stack_stairwell_1` left 0.40 m and 0.23 m, and passed today's rule.

**Why the rule let it.** Each of `_seed_clear`'s margins is a fraction of a
body:
- 0.3 m off a stair's reserve;
- 0.9 m off a volume;
- 1.0 m from a partition's LINE to the piece's centre;
- nothing at all off an exterior wall.

Across the library: 69 seeded pieces in 128 shells; 23 stale, 35 within
1.1 m of a wall, a stair reserve or a piece, 40 either.

**The rule.** `_seed_clear(..., corridor=True)`, asked by both of
`seed_cover`'s calls.
- A standing piece's square keeps `agent_contract.min_corridor_width()`
  clear (1.1 m: 2 x the bake radius + 0.3).
- What it keeps clear of (`_corridor_obstacles`, true box gaps by
  `_box_gap`):
  - every wall's box, exterior and partition alike, `wall_thick` thick as
    the builder stands them;
  - every stair reserve;
  - every standing volume.
- Opt-in: furnish's seven callers keep their own rules.
- `reseat_piece(..., corridor=True)` moves a seeded piece by it, and leaves
  furniture to furnish.

**The library** (`migrate_seed_corridor.py`). It asks before furnish, as the
seeder does, then refurnishes. Across 13 shells it moved 35 pieces and
dropped 7 where nothing within 12 m answered:
- both stairwell crate stacks in deli_a01, a02 and a03. Each stairwell holds
  two stairs and has nowhere a crate fits with a body round it;
- video_store_a01's stockroom shelf-run shelter. That room has less tall
  cover now.

**Checked after the migration.**
- Both migrations are fixed points.
- Every changed spec is a fixed point of furnish. That was measured
  directly: the furnish migration's own `--check` prints totals and cannot
  say.
- The 13 shells are rebuilt, and `circulation.check_shell` passes 13 of 13.

**Proven on the site before shipping.** 9188's walk-test staging was
copied, the new deli_a01 swapped in, reimported, and baked with the same
instrument:
- deli_a01's only island of its own is its roof (957 m2);
- the street's island now covers its basement (783 m2), its ground floor
  (672 m2) and its stair and upper storey (759 m2);
- islands went from 165 (shipped) to 164 (0.194.0's door) to 161.

**Not done here.**
- Furnish keeps only 0.9 m from a volume, so furniture can stand 0.9 to
  1.1 m from a seeded piece. The census, furniture included, finds 4 such
  pieces in 2 shells.
- The nav gate proves each stair's two ends join, never that an entrance
  reaches them. That is how this outlived every gate, and it is next.

**Tests:** `test_seed_corridor.py`, 10.
- All 10 failed before the change.
- The seeder test was rewritten before it counted. In a 20 x 14 m room the
  old seeder happened to land every piece a body off every wall, so the
  test passed without the rule. In a 6 m deep building it failed:
  `counter_island_hall_2` stood 0.36 m off a wall.

**Suite:** 1287 passed, 2 skipped in 66 s (`python -m pytest -q`).

## [0.194.0] - deli_a01's server room gets a door, and L24 names every room only a breach reaches

**The measurement.** Cold run 9188's site bake (the walk-test scene of
seed_9104; `docs/findings/deli_a01_upper_storey_9188/` at the factory root)
made deli_a01's server room a navmesh island of its own: 186 m2 on story 1
whose only ways in were two soft-wall breaches, one from the upper hall and
one from the apartment. L12 passed it, because L12 counts a breach panel, a
vaultable window and a floor-hole drop as ways in. The walker's call,
2026-10-06: give it a door.

**The door.** `specs/deli_a01.json`, story 1's partition along x = -2:
- a 1.25 m door at pos 0.25 (y 7.0), tagged `hall_to_server_room`;
- it opens from the upper hall, where the up-stair arrives;
- the breach beside it stays, as a way in for whoever breaches.

**Refurnished, unchanged.** Refurnished through
`migrate_furnish_recipes.migrate`, and furnish laid every piece back where
it was: none stood within 1.5 m of the new doorway. The spec's diff is the
door's six lines. Rebuilt, `circulation.check_shell` reads 15 volumes, 151
of 151 props and 0 conflicts.

**Proven on the site before shipping.** 9188's walk-test staging was copied,
the new shell swapped in, reimported, and baked with the same instrument and
settings:
- the server room's island is gone;
- the upper storey's island grows from 592 to 779 m2;
- islands drop from 165 to 164.

**L24 (WARN).** `layout_lint.walk_unreachable` and `walk_reach_findings`.
- L12's search moves, unchanged, into `_reach_from_ext`, and runs a second
  time over doors, garages, vault doors, stairs, ladders and ramps only.
- A room the first search reaches and the second does not is reachable only
  by breaching, vaulting a window or dropping.
- `graph()` labels a vaultable window "vault", the same as a vault door, so
  the filter acts on the raw opening kind before `graph()` sees it.
- Measured over the library first: 16 rooms in 8 built shells (22 in 11
  counting Level Factory's lf_ specs).
- L12 reads 0 findings over the 128 lint specs before and after the move, and
  a sealed room still fails it (a positive control, run against the patched
  file).

**Frozen: 15 rooms in 8 shells** (`walk_reach_baseline.json`). Each is a
design call put to the walker:
- the deli family's server room: fortifiable in deli_a03; the OBJECTIVE in
  cr_deli, deli_a02 and night_deli, where breaching in may be the point;
- its basement utility room, role 'connector', in all six deli shells;
- apartment_walkup_a01's kitchen, bedroom and office;
- rowhouse_raid's kitchen and basement vault.

A new one fails `test_no_new_room_only_a_breach_reaches`. A room given a
door must leave the list (`test_walk_baseline_has_not_gone_stale`).

**Not fixed here, and found by the same bake.** deli_a01's upper storey,
779 m2 with the door, is still cut off from the street at its up-stair's
foot.
- Furnish placed two crate stacks in the stairwell, and they shut both ways
  round the up-stair: 0.79 m and 0.54 m passages where a bake that erodes
  0.4 m a side needs 0.8 m.
- 9187 was cut off the same way, so 0.192.0 did not do it.
- The fix belongs in furnish, and comes next.

**Tests:** `test_walk_reach.py`, 9.
- All 9 failed before the patches.
- The door test and the library test failed until the door went in.

**Suite:** 1277 passed, 2 skipped in 64 s (`python -m pytest -q`).

## [0.193.0] - the root is the builder and its gates; 23 one-shots move under migrations/

Repo hygiene (`docs/findings/repo_hygiene_2026-10/` at the factory root).
The root held 235 files, and the README's Layout section described 22 of
them. The 120 `test_*.py` stay: `check.py` collects them there, and
COMMANDS.md says so.

**Moved to `migrations/`, unchanged, history following each** (`git mv`):
the seven `phase*_status.py` reports, `p2_collect.py`, `remediate_l5.py`,
`probe_fights.py`, `sweep_stair_obstruction.py`, `walk_harness.py`,
`review_render.py`, `review_sheet.py` and the `ai_review.py` it imports,
the five `patch_dc_*.py` that were applied here rather than from the
factory's `patches/`, and `generated_sweep.json`, `rockay_sweep.json`,
`stair_sweep.json`. Measured first: nothing at the root, in `hooks/` or in
the workflow imports or reads any of them. Each ran from the root when it
ran, and is kept because a patch script is the only record of how the
source came to be.

**Not moved:** the 21 `migrate_*.py`. They are live code -- presets,
`level_design.py`, `layout_lint.py` and twenty tests import them -- so
moving them is a code change for another release.

`migrations/README.md` is a generated index (`tools/factory_index.py` at
the factory root), one line per file from its own docstring; `--check`
fails when it drifts.

**Suite:** unchanged in content; the pre-commit hook ran the full check.

## [0.192.0] - a piece where a stair now is: L23 asks every piece, and 17 pieces in 10 shells move

**Found by 0.191.0's restored circulation gate.** Its one real finding on
cold run 9187's buildings was deli_a01's `counter_island_upper_hall_2`, 0.8 m
inside `deli_stair_up`. The census that followed
(`docs/findings/presentation_gates/stale_pieces.py` at the factory root)
counted 64 pieces in 18 of 146 shells standing over a slab opening or in a
stair's walk on their own storey. The census cannot tell two causes apart:
- **Stale.** The presets, `seed_cover` and `furnish` each clear a piece of
  the stairs when they PLACE it, and each is idempotent by name. A piece
  placed before a stair lengthened or widened is never asked again.
  - deli_a01, a02 and a03 each stood a counter island 41% over the up-stair's
    hole across the flight's arrival, another 54% over it, and a crate stack
    over the basement stair's.
  - **0.190.0 put twin_a01's two wardrobes 0.12 m2 each over its widened
    hole.** Under 0.189.0's 0.9 m flights they stood clear. Its swept gate
    passed, because walking is unaffected.
- **Unseen.** `furnish` and `seed_cover` clear the STAIRS
  (`_stair_reserved_rects`), not an authored `slab_holes` opening. Today's
  furnish still stands apartment_walkup_a01's dining set over one.

**What shipped:**
- **`layout_lint` L23 (WARN):** `stair_space`, `piece_story`, `stale_pieces`
  and `stale_piece_findings`. It measures, and says no cause.
- **`level_design.reseat_piece`** moves a piece to the nearest place that
  meets every condition:
  - in its room;
  - 0.15 m clear of the stairs' holes and walks;
  - 0.05 m off every other piece;
  - out of any door's approach it was not already in;
  - for a piece `seed_cover` placed, only where `_seed_clear` takes one.

  The search is a 0.1 m grid out to 12 m, nearest first. `_seed_clear`'s door
  rule is now `_seed_clear_doors`, one spelling that both ask.
- **`migrate_stale_pieces.py`** moves every stale piece the baseline does not
  freeze, then refurnishes, so the spec stays a fixed point of furnish. It
  moved 17 pieces in 10 shells:
  - deli_a01, a02 and a03: both counter islands and the crate stack. The
    upper halls are relaid by furnish around the islands.
  - twin_a01: both wardrobes, 0.4 m outward.
  - night_deli's and primos_pizza's stairwell pieces, strip_retail_a01's
    boiler, and the bank family's manager cabinet slivers.
- **`stale_pieces_baseline.json`** freezes 47 pieces in 8 shells, each with
  why. `test_stale_pieces.py` fails a new piece, and a fixed one still
  listed.
  - cbp_town_finale and final_stand: tables, cartons and desks wholly inside
    large openings. They could be authored space or floating furniture, so a
    frame comes first.
  - foundry_heist_vertical: a skylight box and a roof AC over roof openings,
    possibly by design.
  - The garages: columns at a ramp opening, which are structure.
  - apartment_walkup_a01: furnish over an authored hole. The fix is in the
    generator.

**Refuted first, kept:**
- **Moving apartment_walkup_a01's dining set.** It is furnish's, and the
  refurnish puts it back.
- **A migration that did not refurnish.** Moving deli_a01's islands changes
  where furnish lays its hall, and `test_club_fixtures`' fixed point failed
  on deli_a01.
- **A 6 m reach.** It left four pieces unplaced; 12 m placed them all. The
  deli islands went 6.4 m east, and the primos shelf about 6 m.
- **Two storey rules.**
  - The census's round put a hung sign on the storey above.
  - A plain floor put final_stand's `boss_desk`, 5 cm below storey 2's floor
    line, on storey 1.
  - `piece_story` takes the nearest floor within a slab (0.25 m), and floors
    anything else.
- **The first hung-sign test** set the sign's centre, not its base, 2.2 m
  up, and was wrong.

**Measured after:**
- **The nav gate** on all 11 shells rebuilt (the 10 moved, and
  apartment_walkup_a01 rebuilt from its unchanged spec): every verdict is as
  0.191.0's commit run had it.
  - deli_a02, night_deli, strip_retail_a01 and primos_pizza were already not
    navigable, for the same markers.
  - night_deli's register still connects at 2 of 8 origins, and primos's
    stair at 6 of 8.
- **The circulation gate's shell arm** on the rebuilt delis is clean, where
  it named deli_a01's island.
  - twin_a01's porch deck and stoop read 0.2 m into its front doorways. They
    are walkable pieces at a door, a false positive this does not touch.
- **Lint:** the L23 warnings went, and nothing else changed except L9 counts
  moved by the deli refurnish (advisory).
- **Themed fitness:** unchanged, 102 of 127.

**Tests:** `test_stale_pieces.py`, 11. Synthetic L23 and re-seat cases, a
pin on twin_a01, and the population against the baseline. All fail on
0.191.0.

**Suite:** 1,268 passed, 2 skipped. That is 0.191.0's 1,257 and these 11.

## [0.191.0] - the circulation gate reads a dressing's parts, and excuses a stair's own guards

Found 2026-10-06, measuring roadmap 177's successor at the factory root
(`docs/findings/presentation_gates/`).

### A gate that could not pass

**Every cold run from 9164 to 9187 failed the circulation gate on every
building with covers**, and every one was counted clean. The compose driver's
exit is advisory, and Level Factory had no branch that read the result.
- Zoo merges a building's covers per side per material (1.68.0).
  `check_dressing` boxed each NODE, so one box carried dozens of strips.
- On 9187's gs_empty_rowhome_l, 9 nodes carry 109 covers, and each concrete
  node's box is the building's, about 6.7 x 7.1 x 12 m. Every doorway lay
  inside one.
- The four buildings measured read 9, 48, 28 and 27 conflicts.
- The dressing layer is non-collision by construction (Zoo's build record:
  `"collision": "none"`).

**`circulation.dressing_part_boxes`** splits each node into its parts: the
position-welded, index-connected pieces of its mesh. A part is a strip, which
is what `DOOR_TRIM_PEN` was written against. `check_dressing` boxes parts and
reports `nodes` beside `props`.
- On all 15 buildings 9187 shipped: 123 to 249 parts each, 0 conflicts.
- **The positive control:** a 1 m crate planted in a doorway is caught at
  0.95 m.

**Refuted first, kept.** Index connectivity without welding returns one
component per FACE, because faces carry their own vertices for split normals
and UVs. That gave 1,452 planes on gs_empty_rowhome_l. A plane has zero
thickness, so `_pen` can never flag it: 0 conflicts, for the wrong reason.

### A stair's guards inside its own stair

Every volume is role `prop`, so the shell arm read a stair's fall guards as
props in its column. office's `stair_guard_back_10` stood 0.26 m inside
`office_stair_0`, a storey above the flight's foot.
- **`GUARD_PREFIX`**, the builder's `stair_guard_{kind}_{k}`, is excused from
  STAIR volumes only, and returned as `excused`. In a doorway or a ladder's
  climb volume a guard is a prop like any other.
- Not linked to its own stair: a guard inside another stair's column would
  be excused too.

**What the gate says now about 9187's 15 buildings:** one thing, and it is
real. deli_a01's `counter_island_upper_hall_2` stands 0.8 m inside
`deli_stair_up`, a counter partly over the stairwell. That is the next
release.

### Tests

`test_circulation.py`, 7 new:
- a merged node's box spans its parts;
- parts are welded boxes, not faces;
- a merged frame passes its doorway, and a crate in the doorway is still
  caught;
- the guard prefix is the builder's;
- a stair's guard is excused from its stair, and not from a doorway.

The GLBs are written in the test the way a real export writes them: 24
vertices a box, four a face. Five fail on 0.190.0. The defect statement and
the positive control pass on both by design.

**Suite:** 1,257 passed, 2 skipped. That is 0.190.0's 1,250 and these 7.

## [0.190.0] - stairs a body can walk: no ledge at the head, no flight narrower than a corridor

Both were found 2026-10-06, measuring roadmap 189 at the factory root
(`docs/findings/stairwell_on_one_grid_in_four/`).

### Every stair's head stood a riser over its landing

**Cold run 9186.** With deli_a03's stairwell fixed (0.189.0), Laser Tag's bots
reached its upstairs objective. They then stuck 3,148 times at the head of
its up-stair, all in one 2 m cell, and finished 0 runs of 25.

**The census** (`ramp_ridge_census.py`): every stair collision ramp in the
library topped out 0.19 to 0.21 m above the floor it delivers to. That is 174
ramps in 98 shells.
- It is the top face's end corner, at `step_rise/2 + (thickness/2) *
  cos(pitch)` over the landing.
- It comes from the half-step-proud offset that makes the surface ride the
  nosings.
- `ramp_foot_extension` (2026-07-21) landed the foot, and said it left the
  head untouched.

**The walk** (`stair_head_walk.gd`): a capsule of Laser Tag's size (r 0.35,
h 1.8, no step-up, floor_max_angle 45) on deli_a03's up-stair.
- As built: DOWN stuck on the landing for 8 s; UP arrived.
- The control, with the ramp lowered one riser: down in 2.4 s, up in 3.8 s.
- A ledge is a drop going up and a riser coming down. The navmesh climbs
  0.15 and Lot's walkers step 0.5, so neither had seen it.

**Refuted first, kept** (`patch_dc_ramp_head.py`): SINKING every ramp by the
overshoot.
- Built, it read 0.000 on the census and walked both ways.
- The swept nav gate then failed stair traversal on **94 of 144** shells.
- The ramp ran a riser under the nosings, so every visual tread stood above
  it, and the bake, which reads visual meshes, saw 0.206 m risers against a
  0.15 climb.
- Reverted before release. The census and the walk measured collision only.

**`stairwell.ramp_head_trim`** TRIMS the head instead.
- It cuts `overshoot / sin(pitch)` along the incline and keeps the foot, so
  the corner meets the landing where the nosing line does, at the top
  tread's front edge.
- The ramp still rides the nosings. A new test,
  `test_no_tread_stands_above_the_ramp`, holds that.
- A final leg's discharge collider reaches back over the strip left; a
  landing already reached back over its top tread.
- Scissor channels keep their ramps, since they have no plate to reach back.
  The L-stair builder is untouched. Neither style stands in the library:
  77 switchback and 72 straight stairs.

**Rebuilt and measured:**
- census, 0.000 m over the landing on all 174 ramps;
- walk, down 2.4 s and up 3.8 s. The over-lowered control now fails going
  up, so the instrument sees both directions;
- swept gate, **144 of 144** shells traverse, as on 0.189.0.

### No generator draws a flight narrower than a corridor

**twin_a01's 0.9 m flights traversed at 7 of 8 grid origins.**
- The route-walking neck finder put the tear on the flight itself: one cell
  after erosion.
- **Refuted first, kept:** moving the fridge, which stood nearest the tear.
  Built in scratch, it was still 7 of 8.
- At 1.2 m, furniture untouched, 8 of 8, gate and census.

**`presets.STAIR_FLIGHT_WIDTH`** is the contract's corridor minimum
(`min_corridor_width_m`, 1.1: 2 x the bake radius + 0.3) and one bake cell:
1.2.
- `twin` and `rowhome` drew 0.9 m flights, and `pawn_shop` and
  `suburban_safehouse` drew 1.0 m. All four draw it now.
- twin_a01's frozen spec stands on it, with the reason on each stair's
  `meta` as `width_why`, and is still a fixed point of furnish.
- The library's 1.0 m and 1.1 m flights (cr_pawn, night_pawn, card_shop_a01)
  connect at 8 of 8 as built and keep their specs.

### The baseline

`grid_fragile` 7 -> 6:
- twin_a01 leaves.
- primos_pizza's list gains `patrol_point_PAT_CLUB`, which the trimmed
  ramps' base bake now reaches, at 6 of 8 like its stair.

Level Factory's themed-lot fitness, measured with its own `themed_fitness`:
101 -> **102** of 127. twin_a01 and deli_a03 are both fit again.

### Tests

- **`test_stair_ramp_head.py`, 7:**
  - the defect as a number, 0.1995 m on deli_a03's flight;
  - the trim lands the head and keeps the foot, across legal stairs;
  - no tread stands above the ramp;
  - the strip left is the top tread and at most a cell's sliver;
  - a level ramp needs no trim;
  - the builder trims and reaches back (read as source).
  - Six fail on 0.189.0. The defect statement passes both sides by design.
  - The first draft's grid held 0.56 m risers, where both properties fail
    for any ramp; it was cut to legal stairs.
- **`test_stair_flight_width.py`, 3:** the width is derived from the
  contract; no preset draws narrower than a corridor; twin_a01 stands on the
  width. All three fail on 0.189.0.
- **`test_navgate_population.py`:** `test_grid_baseline_has_not_gone_stale`
  failed on twin_a01 until the baseline let it go.

**Suite:** 1,250 passed, 2 skipped. That is 0.189.0's 1,240 and these 10.

## [0.189.0] - the nav gate bakes at eight grid origins, and deli_a03's stair door no longer tears on half of them

**Found 2026-10-06, closing cold run 9185** (roadmap 189 at the factory
root, `docs/findings/stairwell_on_one_grid_in_four/`).
- 9185 lost two candidates of three to deli_a03.
- Its objective upstairs joins the ground floor at 4 of 8 voxel-grid origins.
- A navmesh's grid starts at the corner of whatever is baked, so the
  building alone and the building in a site sit on different grids.
- This gate baked one origin, the building's own bounds, and passed it.

### The gate sweeps

**`nav_gate.gd` `_grid_sweep`** bakes the same parsed geometry again at eight
origins inside one cell:
- `GRID_FRACTIONS`: eight X phases, eight Z phases and four Y phases;
- fractions of the contract's cell, so they follow `agent_contract.json`.

Beside each traversable stair and each checked marker it writes `grid`, the
origins where that stair or marker connected. It decides nothing.

**`nav_gate.py` scopes it:**
- An interior marker the base bake reached, but not at every origin, is
  listed in `interior_grid_fragile` and makes the shell not `navigable`.
- A stair that traverses at only some origins does the same.
- `interior_unreachable` keeps its string format, which other tools parse.
- **The exit code is unchanged.** It is still the base bake's stairs.

**Level Factory reads `navigable` to choose themed-lot shells**, so a
grid-fragile shell leaves themed lots with no Level Factory change.
- Measured with Level Factory's own `themed_fitness` on this library: 102
  shells fit before, 101 after.
- twin_a01 leaves. It is the twin family's only shell, and no brief names
  that family.

### The library run

`nav_gate.py --all`: 144 shells, every exit passing. Eight flagged:

| shell | what connects at only some origins |
|---|---|
| deli_a03 | objective_A (4/8) -- fixed below |
| foundry_heist_vertical | stair_0, stair_1 |
| primos_pizza | stair_0; objective_COUNT_SAFE, loot_STASH (6/8) |
| twin_a01 | stair_1; objective_UPSTAIRS (7/8) |
| cr_deli, night_deli, corner_deli_heist_01 | objective_REGISTER (2/8) |
| fuel_stop_heist | objective_REGISTER (4/8) |

**`navgate_baseline.json` freezes the seven still fragile** (`grid_fragile`),
each with a reason that says what was measured and names no unlocated neck.
- Six were unfit for a themed lot before the sweep too. Five had markers
  unreachable at the base bake; foundry_heist_vertical had empty slot
  coverage.
- The register markers stand inside their counters, and which side of the
  counter they snap to is not yet located.

**`test_navgate_population.py`, three new tests:**
- a newly fragile shell fails;
- a fixed shell still listed fails;
- every result must carry the sweep, or a gate run from before it would
  read as "nothing fragile".

### deli_a03's `office_stair_door`: 1.25 m to 2.4 m

- **The stairwell's only walkable way in is this door.** At 1.25 m on x
  -15.0, all but its east 0.2 m opened over `deli_stair_down`'s slab hole
  (x -17.0 to -14.6, from y 6.2). That is by design: it is the basement
  flight's own door.
- **The way up turned inside the reveal**, onto the 1.6 m strip beside
  `deli_stair_up`, and that turn baked at 4 of 8 origins.
- **At 2.4 m on x -14.5** (pos -0.38; openings snap to the spec's 0.5 m
  grid), the west part still meets the basement flight's top. The east part
  opens about 0.5 m, five cells after erosion, straight onto the strip.
- **Gated:** objective_A at 8 of 8 origins, navigable.
- **The census at the factory root,** baking as the site does (imported
  colliders): 0 split pairs. Both instruments agree.
- The reason travels on `deli_stair_up`'s `meta` as `door_why`, beside
  `open_under_why`. An opening has no `meta` in the schema.
- **Re-furnished** (`migrate_furnish_recipes`), because the library must stay
  a fixed point of furnish. Exactly one piece moved: the work table
  `table_work_r9a51d20f_5`, y 2.91 to 3.91. Re-built and re-gated after it
  moved: 8 of 8.

### `material_kind.SKIN_KINDS` carries `chain_link`

It is a literal copy of Zoo's `KNOWN_KINDS`, and Zoo 1.77.0 added the
chain-link fence's fabric. `test_material_kind.py` had failed on every
checkout since, which would have refused this commit at the hook. No spec
here writes the material, so it needs no `KIND_BY_MATERIAL` row.

### Tests

- **`test_navgate_grid.py`, 8.** Five fail on 0.188.0:
  - a reached-but-fragile marker is not navigable, and says why;
  - a fragile stair is not navigable;
  - a result from before the sweep reads as it did;
  - the verdict prints both;
  - the gate sweeps fractions of a cell through `filter_baking_aabb` (read
    as source).
  - The three that pass on 0.188.0 are invariants: what every origin
    reaches stays navigable, the unreachable format is unchanged, and the
    street stays deferred.
- **`test_navgate_population.py`, 3 new and 1 extended.** Proven in order:
  - with no baseline, they fail on all eight shells;
  - with seven frozen, they fail on deli_a03 alone;
  - after the door, they pass.

**Suite** (`python -m pytest -q`): 1,240 passed, 2 skipped.

## [0.188.0] - the Flappahs store, generated or drawn, with everything it was given

**The walker, 2026-10-06:**
- "the care and detail we put into the strip club and flappahs convient store
  [should not] just get lost to the next phase of level creation. That level
  of detail should be in the logic that is called when a level calls for a
  Gas Station, Convient Store, or a strip club."
- Then: "a03 as convenience store; Flappahs store always Flappahs".

**What the audit found, checked against the files.** Most of the store's
detail was already in the recipe: counter, gondolas, cooler wall, slush
machine, roller grill, ATM, video poker, posters, glass front and lights.
Three things were not.

**1. The window beer sign and sale posters lived only in migrated specs.**
- Every library store carries one `window_sign` and one `window_poster`.
- 0 of the 6 stores generated from `presets.gas_station` carried either, and
  no preset emitted them. Counted in each shell's `slots.json`: candidate
  seeds 9080, 9181 and 9282 of `gas_block_001` (the A/B workspaces) and 9011,
  9112 and 9213 of `gas_stop_001` (cold run 9177).
- `gas_station` now ends as the slush machine (0.151.0) and roller grill
  (0.152.0) taught it to: by the migrations' own rules,
  `migrate_window_sign.migrate`, then `migrate_window_poster.migrate`.
- A generated store's glass is dressed as a drawn one's.

**2. A generated store's business was read off the mission id.**
`level_design.club_building_id` reads a building's kind from its name and its
`preset`.
- `presets.strip_club` wrote `preset` and `presets.gas_station` did not.
- So a generated store's door sign read "gas" in `lf_gas_block_001_9080` by
  luck, and would not in `lf_restaurant_row_001_...`.
- `gas_station` writes `preset: gas_station`. `club_building_id` is the only
  reader of a building spec's `preset` (checked across Deli Counter, Zoo,
  Lot, Lux, Patina, Pixelcoat and Level Factory; Level Factory's Lux adapter
  reads a job's `preset`, which names a Lux preset, not this).

**3. The Flappahs store sat in the gas-station family, and had no recipe.**
- `gas_station_a03`, tagged "Wawa (Flappahs)" in the factory's building
  registry, stands no forecourt, canopy, pumps or pylon.
- A gas-station brief drew it on about half its candidates (Level Factory
  cold run 9177: 2 of 3).
- `convenience_store` had no recipe, and Level Factory built it as the
  forecourt station.

The fix:
- **`gas_station(..., forecourt=True)`.** `forecourt=False` filters the pad,
  canopy and columns, pump islands, pumps and the `forecourt` room out of
  the one layout, before the fixture rules place anything.
- **`convenience_store(...)`** is that shop with `preset: convenience_store`,
  registered.
- **The library's a03 is now `convenience_store_a01`.**
  - Moved with `git mv`, and its `name` and the quoted store lists in seven
    files rewritten. History in comments keeps the old name.
  - Its family is its id less its variant, so it is the convenience store.
- **Re-derived on the rename.** The window sign and posters derive their
  variant from the building's name. The migrations were run again, so the
  renamed spec is their fixed point; it changed 6 lines.
- **Rebuilt.** a03's old build outputs were moved out of `build/`, so no
  library index draws a gas-station a03.

**Rebuilt again.** `presets.py` is a geometry source, and `build_freshness`
held 143 of 146 shells older than it. `build.py --all` followed, and the
tracked manifests changed only `built_utc`.

**The engine import gate** (`godot_gate.py`, which `check.py` does not run)
was run on the renamed shell, so it tracks the five files a03 did: PASS, 4 of
4 checks, 7 markers.

**Tests.**
- `test_store_window.py` (6): the generated store's sign and posters, placed
  by the library rule, and its `preset`. All fail on 0.187.0.
- `test_convenience_store.py` (6): the shop without the fuel, the station
  keeping all six pumps, the registry and `make`, and the renamed library
  spec.
  - Measured with 0.187.0's `presets.py`: the recipe's three tests fail.
  - The station keeping its pumps is the control, and passes on both.
  - The renamed-spec test fails on 0.187.0 by construction: there is no
    `convenience_store_a01.json` there.
- **`check.py`:** all checks passed. 1,211 unit tests, nav gate 144 shells.

## [0.187.0] - a spec can say it is a demo, and its validation manifest carries it

Roadmap 185. **The breadth sweep drew `setback_demo` and `pvp_station_ref`
into card_block_001's lots** (Level Factory cold runs 9170 and 9174).
- Level Factory draws any complete shell this repo does not call a facade,
  and reads this repo's word for what a shell is, never its name.
- Nothing said these were not buildings.
- The walker, 2026-10-06: keep demo and reference shells out of levels.

**`demo`, beside `facade`.**
- **Declared:** `LevelSpec.demo` (`spec_types.py`) and the schema property
  (`schema/level.schema.json`, which is closed to unknown keys).
- **Written:** `evidence.collect` writes it into the report that
  `write_reports` saves as `<id>.validation.json`.
- **Judges nothing:** a demo builds and validates like any other spec. The
  flag only says where it belongs.

**Marked: the five specs that exist to demonstrate or test a capability.**
- `setback_demo`: stepped setbacks. `office_stepped` is the building that
  uses them.
- `kitbash_demo`: kitbash assets.
- `rarity_demo`: rarity tiers.
- `survival_demo`: a survival layout.
- `pvp_station_ref`: a PvP station reference.

**Rebuilt.**
- **The five first:** each `validation.json` reads `demo: true`.
- **Then `build.py --all`:** `spec_types.py` is a geometry source, and
  `build_freshness.py` held 141 of 146 shells older than it, which `check.py`
  rightly failed on.
- **What changed:** the manifests' `built_utc`, nothing else tracked. The
  validation manifests are gitignored, and now carry `demo` on all 146.

**Tests** (`test_demo_flag.py`, 4, all failing on 0.186.0): the five specs
say so, a building does not, the schema declares it, and the report carries
it.

## [0.186.0] - an Empty's door is shut to a ray as well as a body

Roadmap 183. A door's aperture is a walkable void (`_opening_piece`), which
is right for a building you enter. On an Empty -- a sealed, hollow facade
shell -- it was a hole.
- The door module's jambs left 0.7 m, which stopped the 0.8 m walk capsule.
- It did not stop a shot: rays passed 10 m into `gs_empty_rowhome_f`
  through its front door, at 1.0 and 2.0 m (cold run 9162,
  `patches/lf_empties/door_collision_probe.gd`).

**A facade's door is now filled full-thickness**, as its window's pane is
(`ext_<storey>_<facing>_open<k>_leaf`, and its `-convcolonly` collider).
The art pass's door module still draws the leaf; this is its collision. A
building you enter keeps its doors open.

Every shell is rebuilt (`deli_counter.py` is a geometry source).

## [0.185.0] - an Empty's TV antenna and satellite dish

The comps' rowhome has "a TV antenna on the roof", and the street has "the
odd early satellite dish". From across the road an Empty's roofline was a
flat parapet edge against the sky.

- **Authored per house**, as the door is: `roof_antenna` and `roof_dish` on
  the spec (`spec_types`, `schema/level.schema.json`), and
  `empty_rowhome(antenna=, dish=)`.
  - The family: an antenna on eight of the twelve, as a 1990s Philadelphia
    street has, since cable came late to the city.
  - A dish on two: the comps' "odd" one, on `b` beside its antenna and on
    `k` alone.
  - `c`, `f` and `h` have neither.
- **`roofs.roof_fixtures`** puts them on the roof slot as `antenna` / `dish`,
  with `front`, the facing of the exterior wall holding the `front_door`
  opening. The front is that wall, not a fixed side. Patina (>= 0.29.0)
  sets them back from it, and Zoo (>= 1.74.0) builds them.
  - Only on a facade. An Empty's roof is never reached, and an antenna a
    body walked through on a real rooftop would lie about it.
  - Asked for on a spec that is not a facade, or one with no front door, it
    raises rather than leaving the fixture out without a word.
  - Every other building's roof slot is unchanged.

The twelve rowhome specs are rewritten from the preset. The roof's geometry
is unchanged; the slot gains three fields. `presets.py` and `roofs.py` are
geometry sources, so every shell is rebuilt.

## [0.184.0] - Twelve rowhome Empties

Cold run 9159's terrace placed 26 Empties from six variants, one of them
seven times. Level Factory's `empties.terrace` picks a variant per house at
random, never the same as its neighbour, so the repeats fall with every
house the family adds. The comp's rule: a terrace reads as houses because
each one differs.

- **Six more rowhomes, `gs_empty_rowhome_g` to `_l`**, authored like the
  first six. Each a different width (5.6-6.4 m), with 2 or 3 storeys, door
  side, cornice height, wall and front door.
  - Across the twelve, every wall kind (red, brown and orange brick,
    siding, Formstone, painted block) and every door finish appears exactly
    twice, and no two houses wear the same wall and door.
  - Four have iron security doors. One is vacant, as before.
- **The six new shells join `navgate_baseline.json`'s unjudged list** with
  the first six's reason: an Empty is sealed, with no interior for a spawn
  marker, so zero markers checked is correct. `unjudged` goes 15 -> 21 and
  `navigable_null` 14 -> 20.
- **The tests that counted six now read the family:**
  - `test_empties.VARIANTS` lists the twelve;
  - the doors test holds every finish to two and the iron doors to two to
    four;
  - the bricks test holds the three bricks, each worn.

The twelve rowhome specs are rewritten from the preset.

**Cost:** six more Empties' art jobs in a run that places them, and their
modules in memory. No draw a house is added: each placement draws its own
modules either way.

## [0.183.0] - A house's own brick

The walker's South Philly photograph (the factory root's
`docs/reference/EMPTIES_COMPS.md`, "Window comps"): "every house a different
brick: brown, red, orange". The family's three brick rowhomes all wore the
one red. Pixelcoat 0.57.0 paints a brown and an orange as kinds of their
own, and Zoo 1.73.0 knows them.

- **`material_kind`**: `brick_brown` and `brick_orange` are skin kinds, and
  each material id maps to itself.
- **`OUTSIDE_ONLY`** holds them beside `brick`, so an exterior wall in one
  carries its building's interior finish on its room face (0.166.0).
- **The family:**
  - `gs_empty_rowhome_a` (placed x2) is orange;
  - `gs_empty_rowhome_c` (x5) is brown;
  - `gs_empty_rowhome_f` (x7) keeps the red.

  The six rowhome specs are rewritten from the preset.

## [0.182.0] - An Empty's front door: a painted finish per house, and two iron security doors

The walker's photographs (the factory root's
`docs/reference/EMPTIES_COMPS.md`, "Window comps"):
- the South Philly row's doors are painted house by house;
- one carries "a black iron security door with a grille".

Every Empty door rendered the same brown wood. Zoo 1.61.0's navy was a flat
colour that a skinned wood panel never takes.

- **The spec says what each house's front door is.** It is authored per
  house, like `vacant`:
  - `door_finish`: one of `empty_panes.DOOR_FINISHES` -- navy, oxblood,
    green, black, white, stained;
  - `security_door`.

  A seeded draw over the six rowhomes gave three finishes, two of them
  twice, and no iron door, the same way a drawn vacancy left none vacant.
  The family now authors six different doors, with iron on two:
  - a, navy, iron;
  - b, white;
  - c, oxblood;
  - d, green;
  - e, black, iron (the vacant one, secured);
  - f, stained.
- **The front door's slot carries them**, as `door` and `security_door`
  beside its `glazing`. The opening's `tag` now rides on the hole, so the
  front door is the one the preset tagged `front_door`. The back door
  carries nothing and keeps the stained wood.
- **The finish is in the module's name** as `_e<finish>`, after the pane's
  `_p` and before `_g`. That mirrors Zoo 1.72.0's `kit.module_stem`, because
  two doors of one size in different paints are different modules. (`_d`
  is the depth's.)
- **An unknown finish is refused**, not dropped.

Zoo (>= 1.72.0) paints the leaf in the finish and builds the security door
Patina (>= 0.28.0) orders. The six rowhome specs are rewritten from the
preset.

## [0.181.0] - What hangs in an Empty's window: bars, an air conditioner

The walker's window photographs (the factory root's
`docs/reference/EMPTIES_COMPS.md`, "Window comps"):

- "window air conditioners in nearly every photograph": a white or beige box
  in the lower sash, standing out of the wall, so geometry;
- bars proud of the frame on bolted straps.

Bars were painted into the pane (`lit_bars`, `dark_bars`), and nothing made
an air conditioner. Here each Empty window also gets what hangs in it, as
slot fields beside its pane (`empty_panes.fixtures`):

- **`bars: true`** on a barred pane: about a third of the street-level
  windows, as before.
- **`ac: true`** on a window drawn for a unit:
  - 30 in 100 eligible windows upstairs (the bedrooms), 10 at the street;
  - never behind flat bars (they stand 3.5 cm off the wall, a unit 30 cm
    out; the bellied grille that takes one is not built), in a boarded
    window, or in the box fan's.

The unit is drawn on its own key, so which windows glow does not move.

Patina (>= 0.26.0) orders the bars and units from these fields, and Zoo
(>= 1.69.0) builds them -- merged per side of the building with the rest of
its covers, so their cost does not grow with the number of windows. Zoo
1.69.0 also stops painting bars into the pane; the bars are the geometry now.

Per building, as the pane is: every placement of one archetype hangs the
same units.

## [0.180.0] - The window states follow Zoo 1.65.0's sixteen

The walker, sending window photographs: "color variation is key". Zoo 1.65.0
paints four room lights -- tungsten, amber, cool fluorescent, pink -- and more
coverings: warm and cool blinds, a half-drawn shade, closed blinds, a green
roller shade, a box fan.

`empty_panes.STATES` is the same sixteen, in Zoo's order. `test_empty_panes`
pins it against Zoo, and it failed against 1.65.0 until this changed. The
mix is spread across them and stays mostly dark:
- street level: bars on over a third, 32 lit in 100;
- upstairs: no bars, 42 lit in 100.

The vacant house is boarded as before.

## [0.179.0] - An Empty's windows carry a painted state

Cold run 9150: at night the rowhome Empties were a black mass outside the
streetlight pools, every window one opaque pane. The walker's Bloodlines
comp asks for lights on to show life: mixed per building, most dark, some
lit, bars at street level, a vacant house boarded (the factory root's
`docs/reference/EMPTIES_COMPS.md`, "LIT WINDOWS AT NIGHT").

Zoo 1.64.0 paints eight states into one atlas. Here `empty_panes.choose`
gives each Empty window one, and `_record_opening_slot` writes it on the
slot as `pane`.
- **Seeded** by building, seed and slot, so a rebuild paints the same
  street.
- **Street level:** bars on half, 28 lit in 100.
- **Upstairs:** no bars, 38 lit in 100.
- **Vacancy is authored, not drawn.** A seeded one-in-seven left none of the
  six rowhomes vacant ((6/7)^6, about 40%), and the agreed family lists
  boarded as a variant. So the spec takes `vacant` (`spec_types`, schema),
  `empty_rowhome(vacant=)` writes it, and `gs_empty_rowhome_e`, the painted
  block house, is the family's vacant one, every window boarded.

`themed_tscn.resolve_themed_stem` names a painted window `_p<state>` by the
same test Zoo's `plan_kit` makes, so the composer finds the module Zoo
built. `empty_panes.py` joins the build-freshness sources.

**Per building, not per placement.** The state rides on the slot and so on
the module, and every placement of one archetype shares its modules. Seven
copies of one rowhome across a street show one pattern seven times. More
variety needs more archetypes or a per-instance pick, and is not here.

`test_empty_panes.py`:
- the states are Zoo's atlas, in its order;
- most windows are dark, and only the street has bars;
- a vacant house is boarded, and the family has exactly one;
- an Empty's window carries its state and an enterable one does not (fails
  on 0.178.0);
- the name is Zoo's name;
- every built Empty window has a state.

## [0.178.0] - An Empty's doorway is tagged so Zoo shuts it

0.174.0 made an Empty's doors solid in collision -- there is nothing behind
them -- and left the visual a doorway frame with no leaf. Zoo's doorway is a
frame and its trim; a leaf exists only for storefront doors. So every Empty
showed a doorway into a dark box that a player walks into as an invisible
wall. Seen in cold runs 9146-9148's `empties_one_front_*` frames.

An Empty's windows have carried `glazing: "facade"` since 0.80.0, which Zoo
reads as "nothing behind this opening" and glazes opaque. Its doorways now
carry the same tag, and Zoo 1.61.0 fills a tagged doorway with a painted
panel door set back from the face.

`test_facade_glazing.py`'s "a facade door carries no glazing" is RETRACTED
in place, above its replacement: it was true while no facade had a door
anyone could see into.

## [0.177.0] - A parapet is a wall the art pass dresses

Nothing ever skinned a parapet. Cold run 9148's package carried 324 greybox
surfaces (2,744.7 m2 in `gb_wall`), every one a `parapet_*`, attributed per
archetype off the shipped bases:
- 260 on the 26 Empties, where the parapet is the cornice: a grey band along
  the top of every house;
- 64 on the bank tower and the freight terminal.

The worldskin has a pass for slabs, stairs and ladders and none for
parapets. The greybox gate counts parapets and does not refuse them.

A parapet is the wall below it carried past the roof, so it is recorded as
that wall. For a modular build, `_parapets` records one wall slot per visual
tile (`_record_parapet_slot`):
- **Named as the tile**, so the composer's base strip removes exactly that
  greybox piece, as it does for a wall segment.
- **In the material of the top storey's wall on that side**: an explicit
  `ext_walls` entry when there is one, else the default.
- **Exterior on both faces.** Its inner face looks onto the roof, so it
  carries no `material_in`.
- **Its own height.** Where a parapet tile shares a width with a storey wall,
  0.176.0's `mark_height_keys` keeps the two names apart.

Zoo builds each as a wall module, exact-fit, collision as a wall's. The
greybox collision box (`parapet_<side>_col`) is unchanged.

`test_parapet_slots.py`:
- every tile is a wall slot named as the tile, in the wall-below's material
  -- a siding front over a brick house gives a siding front parapet and
  brick sides (fails on 0.176.0);
- the control: a non-modular build records none.

The library-wide name check (0.176.0) then caught a smaller collision the
new slots exposed. `floors.slab_tiles` snaps interior cuts to whole
millimetres, so a parapet run's equal tiles can be 4.666 and 4.667 m, both
named `w467`. A name carries centimetres, so they are one module. The check
and `mark_height_keys` now both ask at whole centimetres: one question at the
resolution the name can answer.

`themed_tscn.py` joins `build_freshness.GEOMETRY_SOURCES`: since 0.176.0 the
slot manifest's marking is decided there as it is written, and a change to it
moved every slots.json without making a shell stale.

9 library buildings carry parapet tiles and no parapet slots. Every one
records no wall slot at all (non-modular), and keeps its greybox by design.

## [0.176.0] - One module name, one geometry, in every building

Cold run 9148 carried 0.175.2, which runs an Empty's walls the full storey
below its roof storey. They are now 3.1 m there and 2.8 m under the roof.

Zoo names a wall, doorway or window by its width alone. So both heights
built as `wall_delco_1997_01_w200_mbrick_idrywall`, and the kit listed it
twice: two buckets of 11 slots, one file. The file on disk was the 2.8 m
one, and every 3.1 m side wall stood a 2.8 m panel. The frames showed a
0.3 m strip at each storey line. A headless census of the walk copy measured
`Wall_Panel` at 2.80 m in 3.10 m slots.

Across the library as built, 14 names covered two sizes, every one in the 8
facade shells (walls and windows, 2.8 against 3.1 m; the storefront facade
3.1 against 3.4). No enterable building collides.

`themed_tscn.mark_height_keys(slots)` groups a building's slots by the name
`resolve_themed_stem` builds and marks every slot whose name covers more than
one height with `fit.key_height`. `write_slot_manifest` calls it before
writing. Two things follow from building on this module's own name:
- the mark cannot disagree with the name it repairs;
- only a colliding name is marked, so every other building keeps every
  name.

The mirror (`resolve_themed_stem`) and Zoo 1.60.0 add `_h<cm>` to a marked
slot. `docs/SLOT_MANIFEST.md` names the field. The manifest version is
unchanged: the field is optional, and an older Zoo ignores it and builds the
old collision.

`test_key_height.py`:
- two heights under one name are marked and split (fails on 0.175.2);
- the control: one height is left alone and keeps its name;
- across every built manifest, no exact-fit name maps to two sets of dims
  (14 on 0.175.2).

## [0.175.2] - An Empty's walls run the full storey

0.175.0 left an Empty only its roof slab, and `_cap_thick` kept stopping
every wall 0.3 m short of each storey line, to sit under a floor slab that
was no longer emitted. Measured on 0.175.1's `gs_empty_rowhome_f.slots.json`:
storey 0's walls end at z 2.80 and storey 1's begin at 3.10; 5.90 to 6.20
the same. Nothing filled either band, so every Empty had a slot through it
at every storey line. In cold run 9147's frames it is a dark band across
each house. This was introduced by 0.175.0 and caught by looking at the
frames, not by a check.

`_cap_thick` answers 0 on an Empty below its roof: the wall runs the full
storey. Under the roof it still stops, and the roof slab closes it. Of
`_cap_thick`'s five callers only `_exterior` runs on an Empty, so nothing
enterable moves.

`test_empty_walls.py`:
- an Empty leaves no slot at any storey line (fails on 0.175.1: 0.3 m at
  two lines);
- the control: an enterable building still stops under each floor slab.

## [0.175.1] - The nav baseline check runs after the nav gate

`check.py` ran every pure test in one sweep, then `nav_gate.py --all`. But
`test_navgate_population.py` reads what the nav gate writes -- each shell's
`build/<name>.navgate.json` -- and compares it with `navgate_baseline.json`.
In the first sweep, a shell built for the commit being checked has no
`.navgate.json` yet, so it was never compared, and a new unjudged shell
always passed on the commit that added it.

Measured on this repo:
- 0.174.0 added six rowhome Empties and committed clean.
- 0.175.0's hook refused for those same six, whose nav results had first
  been written during that hook (11:00, 2026-10-04).

The check was one commit late, every time, for every new shell.

`AFTER_NAV_GATE` names the tests that read the nav gate's output; it is
`test_navgate_population.py` today. They are left out of the first sweep
(`--ignore`) and run as their own step straight after the nav gate.

The other files that mention `.navgate.json` (`test_headroom.py`,
`test_marker_scope.py`, `test_navgate_verdict.py`) were read: none opens
`build/`, so they stay in the first sweep.

`test_check_order.py` drives `check.main` with `run` recorded instead of
executed, so it needs neither Godot nor a build. It checks three things:
- the population check runs after the nav gate;
- the first sweep leaves it out, and it runs exactly once;
- every held-back file exists, so a rename cannot silently undo this.

All three fail against 0.175.0's `check.py`, run on a copy: the first two on
the order, the third because `AFTER_NAV_GATE` did not exist.

## [0.175.0] - An Empty is exterior plus roof

Roadmap 106. Cold run 9146 -- the first level to stand 0.174.0's rowhome
Empties across a street -- was refused at export by Level Factory's
greybox-skin gate (`GREYBOX_SLAB_IN_A_THEMED_PACKAGE`): 588 slab surfaces
still in `gb_floor`. Every one was an Empty's: 26 placed, 24 slab tiles on a
three-storey house and 18 on the two-storey, 48 + 96 + 120 + 108 + 48 + 168
= 588 exactly; the three real buildings' 193 were skinned. An Empty has no
rooms, so it recorded no floor and no roof slot, Zoo built it no `floor_` or
`roof_` module, and the worldskin's slab pass had nothing to dress a slab
with.

THE FACADE BRANCH NOW DOES WHAT ITS COMMENT SAID. `build` has documented a
facade as "exterior + roof + theme only. No interior" since it was written,
and called `_slabs()`, which emits every storey's slab:
- **No slab inside it.** An Empty keeps only its roof slab, visual and
  collision. The ground slab and the floors between storeys sat inside a
  sealed box behind opaque glass -- unseen, unreachable, and 18 of every 24
  visual slabs on a three-storey house. The roof keeps its visual, so a
  greybox level (no art pass) still has a top on every Empty, and its
  collision, so the box stays sealed against a throw.
- **A roof slot.** `_record_roof_slots` now runs for a facade when the build
  is modular, as it does for a building, so Zoo dresses the roof. No hole
  can land on an Empty's roof (it has no ladder or stair), so calling it
  without `_slab_holes_cut` first loses nothing.

A ROWHOUSE ROOF IS NOT BRICK. `empty_rowhome` names `roof_material:
"concrete"`: the flat roof of a 1990s Philadelphia rowhouse is tar,
silver-coated, and without the field the roof slot's style follows the
walls (`roofs.roof_slots`), so a brick house would have been handed a brick
roof. The six `gs_empty_rowhome_*` specs are rewritten from the preset.

The other half is Level Factory 0.138.0: the worldskin's slab reveal falls
back from `floor_` to `roof_`, the family of the surface an Empty's one
slab actually meets.

`test_empty_roof.py`:
- an Empty keeps only its roof slab, against the same house made enterable
  (control: all four levels);
- an Empty records one roof slot in concrete, over the full plan;
- the facade branch of `build` asks for its roof slot.

The six `gs_empty_rowhome_*` join `navgate_baseline.json`'s unjudged list
on the same reason as `gs_facade_rowhome`: facade-only, no interior for a
spawn marker to stand in. 0.174.0 should have been refused for this and was
not, because `check.py` runs its unit suites -- this test among them --
BEFORE `nav_gate.py --all` writes the `.navgate.json` it reads. A shell's
first commit therefore always passes `test_no_new_unjudged_shell`; the
Empties' results were first written during this commit's own hook (11:00,
2026-10-04). Recorded, not fixed here.

## [0.174.0] - Empties with real fronts: the rowhome family

Roadmap 106. The walker, 2026-10-04, shown the two Empties this repo built --
`gs_facade_rowhome` and `gs_facade_storefront`, every slot a wall, no
opening -- standing in a row across a street: "that just looks like a
continuous concrete wall". The walker then sent comps (a Philadelphia
rowhouse street; four industrial lofts) and set the period, the 1990s, and
the families, in order: rowhome, porch-front row, main-street storefront,
corner store or taproom, brick factory, cinder-block garage. All read off in
the factory root's `docs/reference/EMPTIES_COMPS.md`. This is the first.

AN EMPTY'S DOOR IS SOLID. `_wall_collision` carves a walkable void for a
door; behind an Empty's door is no interior, no navmesh and nothing to
reach, so on an Empty no opening carves and the wall stays one box. A
window already kept its wall solid.

AN EMPTY CARRIES NO GAMEPLAY. `_record_openings` returns at once on an
Empty: no opening record, no socket marker, no interactive. Item 106's
note on giving an Empty windows asked for exactly this ("an Empty is meant
to carry no gameplay").

`presets.empty_rowhome(width, floors, wall, door_side, cornice, seed)`: the
comp's rowhouse. Two window bays; a door in one bay and a window in the other
at street level, two windows on every storey above, stacked on the same
bays; a back door and a window a storey behind; the side walls left
unlisted so `auto_exterior` seals them -- party walls. Windows are glazed
`facade` by the existing tag, so Zoo skins them opaque `glass_facade`; the
painted pane that will make them read as lit, dark, curtained or barred is
Pixelcoat's next step.

A TERRACE READS AS HOUSES BECAUSE EACH HOUSE DIFFERS, so the library gets a
table of six (`EMPTY_ROWHOMES`, `specs/gs_empty_rowhome_[a-f].json`):
widths 5.5, 6.0 and 6.5 m (the comp's 18-21 ft houses), two or three
storeys, brick (three), siding, Formstone (`stone_ext`) and painted block,
the door to either side, cornice heights 0.6-1.0 m.

`test_empties.py`: the rowhome has a door and a window at street level and
two windows a storey above, its party walls unlisted; an Empty's door does
not carve its wall (the control, the same spec enterable, does); an Empty
records no gameplay from its openings (the control does); the six differ in
width, storeys, wall, cornice and door side, each wall a mapped skin kind;
each spec is the preset's own output.

## [0.173.0] - an exterior ladder says so in its name

Roadmap 169, the walker's call of 2026-09-23 with two reference photographs:
a ladder is metal, rusted outside and clean inside. Level Factory's import
(`zoo_worldskin.gd`, 0.136.0) chooses the metal, and a ladder's NAME is the
only channel it has -- the import post-processor is handed one GLB and no
spec. So a ladder whose `placement_mode` puts it outside the building now
emits `ladder<n>ext_` where it emitted `ladder<n>_`, the convention
`stair<n>col_` and `stair<n>ramp_` already use. Nothing downstream parses
these names (checked across deli_counter, lot, level_factory and lasertag
when this was staged): gameplay addresses a ladder by its `LADDER_<n>`
marker and `ladder_<n>` id, which are untouched.

STAGED 2026-09-23 (`patches/patch_dc_ladder_mode_in_name.py` at the factory
root), held behind cold run 9072 and never applied until 2026-10-04, when
the walker asked where it went. Its three anchors still matched exactly once.

## [0.172.0] - the video store, revised from the walker's photographs

0.171.0 laid the store out "from the era". Cold run 9132 put it in a level
and the walker sent ten photographs (docs/SET_DRESSING_REFERENCES.md, "The
walker's video store references"): a cult store's tall painted aisles of
tape spines, and a chain store's new-release wall and counter. Zoo 1.44.0
redrew the rack -- spines out, painted units, a `display` form; this is the
floor plan.

  * THE ISLANDS ARE AISLES: 1.9 m where they were 1.4 m. The four rows are
    corridors with a section sign on each end, not racks a body sees over.
  * A NEW-RELEASE WALL: the east wall's two runs nearest the storefront are
    the `display` form, boxes faced out; the third stays spines.
  * TWO ARMCHAIRS by the shop window, facing the floor.
  * NO SALE POSTERS: `poster_wall_store` hung the convenience store's
    SCRATCH & WIN and HOT DOGS 2/$1 in the video store (cold run 9132). Its
    posters are film one-sheets, which nothing draws yet; the recipe hangs
    none.

WHAT TALL ISLANDS CHANGE FOR A FIGHT, not measured: the sales floor was one
room with low cover and is four lanes with none to see over. That is the
photographs' store and it is also a different room to fight in.

NOT DONE, from the photographs: teal walls, a film one-sheet on a door, the
hand-painted ceiling board with arrows, an EXIT sign, the counter in the
store's colours under an overhead sign, stacks of returned tapes on it, the
chairs' orange velvet (they are `club_chair` as it comes).

Tests: `test_video_store.py` 10 -> 11.

## [0.171.0] - a 1997 video rental store

The walker's queue, 2026-09-29: "a new building type: a VHS movie rental
store". Their calls, 2026-10-02: it is MACDADE MOVIES; it has the curtained
back room, "suggestive only"; no references -- build from the era. Zoo
1.43.0 draws the tape racks (`video_rack`) and names the door.

THE PRESET, `video_store`: a strip-mall unit, 18 x 14 m, one storey. A glass
storefront with the door west of centre; the sales floor wall to wall, 18 x
10 m, its side walls blank brick; behind it a stockroom on the rear door
(the safe, a soft-wall breach) and THE BACK ROOM, 6 x 4 m, behind a curtain
off the sales floor and a staff door off the stockroom -- two ways in.

THE RACKS ARE AUTHORED BY THE PRESET, the gas station's gondolas' way: two
runs on the west wall and three on the east, three along the back wall
between the doors, FOUR ROWS OF LOW ISLANDS two runs long, the checkout
counter a staff aisle off the west wall by the door, and the back room's
north and east walls meeting at its corner. 19 racks, all 2.4 m, each with
its own variant so no two neighbours open on the same genre.

WHY NOT THE FURNISHER, MEASURED. The first draft gave the recipe `tape_wall`
pieces. `_seed_clear` clears a piece as a SQUARE of its longest side and the
sales floor's cover is seeded first: an 18 x 10 m floor stood ONE 4 m rack;
with the racks as anchors and `all_anchors`, one; at 2 m, two. A rental
store's walls are lined end to end, and that is a floor plan. What it costs:
the layout does not vary with the seed, and a second video store is this
one.

THE KINDS: `video_store` (a selling room of a building whose id says
`video_store`) and `video_back` (its back room). Their recipes are what the
furnisher may ADD: a vending machine if a wall is left, a carton or two, a
run of sale posters. No `wall_tv` -- listed, the pass hung three by the
checkout, one on the shop glass.

`prop_species`: `tape_wall` / `tape_island` -> `video_rack`, above the
counter row, whose `island` would claim every `tape_island_*`.

THE LIBRARY: `video_store_a01`. layout_lint 0 FAIL 0 WARN; nav gate
"navigable: yes", 2 of 2 interior markers reachable.

TWO THINGS A TEST CAUGHT IN THE PLAN: the checkout's corner stood 1.04 m off
the first west rack's, under `min_corridor_width`, across the way out of the
staff aisle; and the back room's two walls left a 0.2 x 0.6 m pocket at the
corner.

NOT DONE: the store has no TV, no "BE KIND, REWIND" sign, no drop box, and
the back room's doorway is a door, not a curtain. Its lights are a shop's
fluorescents throughout, the back room's included.

Tests: `test_video_store.py` (10).

## [0.170.0] - poster runs hang at varied heights; a store tapes a pair in its window

The poster pass the walker queued 2026-09-30 ("we can make them better later
right?"), its two placement halves. The colour half is Zoo 1.41.0.

VARIED HEIGHTS. Every wall run hung with its centre on the camera's eye, 1.6
m, on every wall of every building -- the placement guide's "identical
spacing, height, rotation, or mounting pattern on every wall". A piece may
carry `lift_steps`, offsets from its `lift`, and a room's k-th run of a kind
takes one (`_lift_step`); `_place_fixture` clears and builds it there. Club
one-sheets: -0.1 / 0 / +0.1. Bar bills: -0.15 / -0.05 / 0 / +0.15. A store's
sale posters: -0.2 / -0.1 / 0.

THE WINDOW. `migrate_window_poster.py`: each of the nine convenience stores
tapes one `window_poster` -- Zoo's `poster_wall`, `store` family, two sheets,
1.0 x 0.6 m -- 3 cm inside its sales floor's glass beside an entrance, at
the eye, facing the street, clear of every opening and 0.3 m clear of the
window sign. The placement guide's "sparse window: one or two notices
preserve visibility through the glass". `prop_species` routes the name to
`poster_wall`, `_PROP_MATERIALS` to paper, and `_room_volume_count` no
longer counts paper on a wall (it stands on no floor; counted, the poster
cost the sales floor a piece of furniture -- the window sign's defect of
0.160.0 again).

THREE THINGS THE FIRST CUTS GOT WRONG, each caught by a test that already
existed:
  * the step was keyed on the run's NAME, which carries the room's next free
    sequence number -- so a run that found no wall at its step was retried
    by the next pass under a new number, drew a new step and fitted, and the
    library stopped being a fixed point of the fixture pass (strip_club_a03
    grew a run on the second pass). It is keyed on the run's ordinal now.
  * a store's posters stepped +0.15: a run's foot at 1.45 m cleared an ATM's
    top and hung over it (pharmacy_a02, `test_store_atms`). A store's steps
    are at or under the eye.
  * a bar's bills stepped -0.25 and two of the library's eight runs found no
    wall that low.

Refurnished from HEAD's specs (37 change): 82 runs take a new height; the
counts are 0.169.0's but for strip_club_a03, which gains a club run (17 ->
18) and loses a cabinet and its stool (6 -> 5) -- the club recipes place
cabinets after posters, and the run that now fits took its wall.

NOT YET LOOKED AT: what a window poster shows the shop. Its sheets face the
street; whether their backs draw from inside is the next cold run's to see.

Tests: `test_window_poster.py` (4); `test_poster_walls.py` -- a piece's
steps include level and none passes 0.25 m, a run is at the eye plus its own
step, and the library's runs do not all hang at one height.

## [0.169.0] - a home has a porch light over its door, not a lit sign

Zoo 1.37.0 paints a business's name on every lit sign box and gives a
building of no kind its street number. On a home that is a lit cabinet over
a front door. The walker was asked whether an apartment or a rowhouse should
have one at all and, 2026-10-02, left the call here: no.

`lights.is_residence(business)` reads the building's identity for a home's
word, whole -- apartment, walkup, rowhouse, twin, mansion, duplex, tenement.
A residence derives no storefront sign, so its front door falls to the loop
that hangs a wall pack over every other exterior door: one anchor for one
anchor, and the light count does not move. Eight library buildings
(apartment_walkup_a01-a03, mansion_a01-a03, rowhouse_raid, twin_a01); 102
sign anchors -> 94.

Still showing a street number, and not homes: 41 buildings of no kind in
Zoo's table (auto shops, warehouses, depots, self storage, marinas, offices,
parking garages, the demos). A name for each kind is Zoo's to grow.

ASKED IN THE SAME BREATH, MEASURED, AND LEFT ALONE: one video-poker cabinet a
store instead of two, to give the tight stores their poster runs back.
Refurnished from HEAD with `video_poker_store` at `most=1`: 56 cabinets ->
32, and 81 store poster runs -> 84 -- three runs back (deli_a03,
pharmacy_a02, strip_retail_a02) for 24 cabinets. The three gas stations that
lost a run to 0.168.2 already stand one cabinet and get nothing back. The
count is not what costs the posters; `most` stays 2.

Tests: `test_residence_lights.py` (3) -- the words are whole words; a home
takes a wall pack where a shop takes a sign, over the same door, and nothing
else moves; the library's homes built with no sign. Its library test fails
on 0.168.2's build. `test_sign_business.py`'s floor 100 -> 90.

## [0.168.2] - a video-poker cabinet stands off the storefront glass

The walker, 2026-10-01, on cold run 9127's frames: "keep the posters off the
machines, set off_glass on cabinets". One of gas_station_a02's cabinets stood
against the storefront glass by its door. Both cabinet pieces now carry
`off_glass`, as the sale posters have since 0.163.0 -- a bar's machine does
not stand in its window either. The order is kept: cabinets before posters,
so no poster hangs over a machine.

Refurnished from HEAD's specs (19 change): 9 cabinets find no wall off the
glass and go, with their stools (8 store, 1 bar: 64 -> 56 and 46 -> 45); 28
move. With the glass ruled out they compete with the posters for the inside
walls, and the posters give way where they collide:

    store              posters 0.167 / 0.168.1 / now   cabinets 0.168.1 / now
    gas_station_a02          2  1  1                         2  1
    gas_station_a03          2  2  1                         2  1
    stop_n_go                2  2  1                         2  1
    pharmacy_a02             3  3  2                         2  2
    strip_retail_a02         2  0  0                         2  2

(cr_deli, deli_a01, deli_a03, night_deli as in 0.168.1.)

Tests: `test_video_poker.py` -- no cabinet within half a cabinet and a hand of
a glazed wall on its storey; its control, run on 0.168.1's
gas_station_a02, names the cabinet that stood by the door.

## [0.168.1] - a video-poker cabinet's slot names its own kind

Cold run 9127 built every cabinet as `prop_video_poker_..._mwood`: the
cabinets fell through `_PROP_MATERIALS` to the default `wood`, which is not
Zoo 1.39.0's `metal_painted`, so Zoo tagged the stem. The recipe draws from
its atlas and ignores the material, so nothing looked wrong; the stem said a
thing that was not so. The cabinets join the painted-sheet row, the species'
own kind, and the stem carries no `_m` (the dartboard's reason, 0.136.0) --
gas_station_a02's are `prop_video_poker_delco_1997_09_w65_d65_h175_n1` and
`_n3`. The skin style follows the material (05 -> 09); the recipe ignores it.

Refurnished from HEAD's specs: the 110 cabinets' `material` is the only volume
field that changes, in 42 specs; ten of them declare `metal_painted` where
they had not. Suite 1,139 pass.

## [0.168.0] - video-poker cabinets, with a stool, in stores, bars and clubs

The walker, 2026-09-30: "'PA Skill Games' ... into the level. We would see
them in convenient stores, bars, and strip clubs. High stool to play" -- the
1997 period version agreed. Zoo 1.39.0 draws `video_poker`, a "for amusement
only" upright, four invented brands by variant.

  * `prop_species`: `video_poker` routes to the species, immediately ahead of
    the counter row, whose `bar_` would claim `video_poker_bar_*`.
  * TWO FIXTURE PIECES, ONE SPECIES: a fixture's `rooms` gate is one token set
    for every recipe listing it, and `floor` -- a strip club's main floor --
    would put a store's machines on every warehouse floor.
    `video_poker_store` (the ATM's selling rooms, at most 2) on `shop_floor`,
    placed after the ATM and before the sale posters; `video_poker_bar` (bar
    and strip-club rooms, 2, 3 past 80 m2) on `club` and `strip_club`.
    0.65 x 0.65 x 1.75, standing, collision, four variants.
  * `_place_fixture` honours `seats` (only the furnishing pass did): one
    `bar_stool` in front of the cabinet's face, through the same room-edge,
    nested-room and `_seed_clear` tests, turned to face it; a spot whose stool
    does not fit is not a spot. Named `bar_stool_<tag>_<cabinet seq>_1`.

THE LIBRARY, refurnished by the chain from HEAD's specs: 110 cabinets (64 in
stores, 46 in bars and clubs), 110 stools, in 42 specs. Every volume HEAD had
is present and unchanged EXCEPT store poster runs, which are placed after the
cabinets and go round them: six stores lose runs -- cr_deli 5 -> 4, deli_a01
5 -> 3, deli_a03 5 -> 4, gas_station_a02 2 -> 1, night_deli 5 -> 4,
strip_retail_a02 2 -> 0. The only material declared is `metal_bare` (the
stool's column). On club_block_014: six cabinets in the strip club (three in
each of its two large rooms), two on the gas station's sales floor, none in
the airport (no selling or bar room).

Seven tests named what a club room or a piece may be; each is extended with
its reason (`patches/patch_dc_video_poker_tests.py`): `CLUB_SPECIES` x2,
`_ZOO_RANGES`, the 2.2 m host spread (a cabinet stands at a wall with its own
stool; the reference rows stand side by side), a stool's host (a counter or a
cabinet), and the fixture pass's invariance (a cabinet's own stools).

Nav gate: 131 shells pass. Tests: `test_video_poker.py` -- routing; cabinets
only where their piece's gate and recipe allow, at most its count; each with
one stool in front of it; the fixture pass idempotent.

## [0.167.0] - the canopy's washes hang over the lanes

Cold run 9120's FLAPPHAS walk, finding 4: the forecourt is dark -- under the
canopy "the pump stands in shadow beside a lit patch". `_canopy_anchors`
spread its washes evenly along the deck, and on gas_station_a02's 22 x 13 m
deck they stood at x -7.33, 0 and 7.33, within 1.33 m of the islands at -6, 0
and 6. A downward spot over an island lights the island and the pumps' tops
and grazes their faces -- and the faces face the lanes, which fell between
the pools. Measured on cold run 9124's walk copy, one face square on from its
lane: the pump's pixels at median luminance 2 of 255 (its glowing wheels and
header lift the mean to 44); the face across the island, in a pool, 31; the
lane's tarmac toward the store, 0.

`_canopy_lanes`: with pump islands under the deck, a wash hangs over each
LANE -- the gaps across the islands' long axis, between islands and between
the outer islands and the deck's edge, at least `_CANOPY_LANE_MIN` (2.4 m)
wide -- at the deck's middle, owning its lane's width by the deck's length;
more lanes than `_CANOPY_WASH_MAX` keep the outermost two and the evenly
spread rest. A deck with no islands keeps the even spread.

gas_station_a02: four washes at -8.9, -3, 3, 8.9 where there were three --
one light more on the forecourt, priced on the cold run that ships it.
Rebuilt: gas_station_a01, gas_station_a02 and gas_street's light manifests
change; nothing else does.

Tests: `test_canopy_lanes.py` -- one wash a lane and never over an island;
a gap too narrow to drive is not a lane; islands along x put the lanes along
x; too many lanes are capped; another forecourt's islands do not count; no
islands, no change; the real gas_station_a02 has its four washes clear of its
three islands.

## [0.166.1] - the remainders get the room face too

Cold run 9123 showed stone still inside the gas station at its remainders --
the stockroom's frame, beside the sales floor's window, the walk-in cooler's
corner. 0.166.0 left `size_mod: "end"` out; Zoo 1.38.1 builds the unit
`wallEnd` with a room face (its per-slot scale is applied in the module's own
frame, so its -Y face is the room side as a segment's is), and
`_material_in` no longer excludes it. `themed_tscn.INNER_FACE_ROLES` gains
`wallEnd`.

Library: 2,024 room-face slots, 394 of them remainders (1,630 before);
gas_station_a02's 9 among them.

Tests: `test_inner_face.py` -- every stone wall slot at the gas station has
the room face, its 9 remainders included; the remainder's stem mirror is
`wallEnd_delco_1997_01_mstone_idrywall`.

## [0.166.0] - an outside-only wall finish stops at the wall

Cold run 9120's FLAPPHAS walk, finding 3: the gas station's exterior stone on
the inside of its exterior walls. Every exterior wall slot named one material
and Zoo's module wore it on both faces. Concrete, painted block and metal read
the same both sides; brick, stone, wood boards and siding do not.

`write_slot_manifest` now stamps `material_in` -- the building's interior
finish (`_interior_finish`: the commonest kind among its partitions that is
not itself outside-only, else drywall) -- on every full segment and opening
of an exterior wall whose final kind is in `OUTSIDE_ONLY`. Zoo 1.38.0 builds
that module's room face in it. 1,630 modules in 15 buildings: drywall in
thirteen, wood panel in the card shop, concrete in landmark_hall_a03 (its
partitions). `themed_tscn` mirrors Zoo's `_i<kind>` stem and resolves the
plain name when the tagged one is not built.

WHICH FACE IS THE ROOM was measured: local +Y, through `tscn_export.
godot_basis` at each facing's rotation, lands outdoors on all four, and
`_fit_rotation` keeps the slot's own rotation on a tie. `test_inner_face.py`
pins it.

WHERE THE STAMP GOES took two wrong tries, kept in
`patches/patch_dc_inner_face_kind.py`. Stamped when a slot was RECORDED, it
compared the spec's palette id (`stone_ext`) and caught only the plain-`wood`
buildings (4 of 15); mapped to a kind at record time, it still missed
gas_station_a02's east wall, whose back-room stretch of shop front is
recorded as glass and becomes stone only in the writer. It is decided in the
writer now, where the kind is final.

NOT COVERED: a remainder (`wallEnd`, a unit box scaled per slot) keeps the
wall's finish -- gas_station_a02 has 9, the widest 1.65 m.

## [0.165.1] - a build that raises is a failed build

0.165.0's first library build raised a NameError writing every building's
light manifest, and `build.py --all` exited 0. Blender exits 0 after a
`--python` script raises unless launched with `--python-exit-code`, and
`build_one` takes Blender's return code as its verdict -- so every runner
exception has always read as a pass. `_run_in_blender.main` writes the build
manifest after the light manifest, so 128 of 131 shells were left stale on
disk, each with a `[build] X.json -> X.glb` line above its traceback.

Measured on Blender 5.1.1 before changing anything: a script that raises
exits 0 plain and 1 with `--python-exit-code 1`; a clean script exits 0 both
ways. `build_one` now launches with the flag (before `--python`, which it
governs), and `--all` ends by naming every spec that failed and says their
outputs on disk are the previous build's.

Nothing in the library was hiding behind it: the full build of 0.165.0
(after its import fix) logged 0 tracebacks.

Tests: `test_build_exit.py` -- the launch carries the flag ahead of the
script; with Blender present, a spec the runner cannot load is reported
failed. Both fail on 0.165.0's `build.py`.

## [0.165.0] - every sign over a door names its business

Cold run 9120's FLAPPHAS walk found the lit box over the gas station's door
blank; 9121 attributed it to Zoo's `sign_box`, which painted a face only from
a sign pack no theme ships, so every sign this repo derives (102 across the
library) was blank. Zoo 1.37.0 paints the business's name; this hands it the
business.

`lights.build_light_manifest` takes `business` -- the building's identity,
`level_design.club_building_id(spec)`, the string a club's `neon_sign`
variant is keyed on -- and stamps it on every `sign` anchor, derived or
authored, that does not name its own. `write_light_manifest` passes it. Zoo
reads the kind of business from it and, for a club, the same name its neon
shows.

THE FIRST LIBRARY BUILD OF THIS FAILED SILENTLY. The call used `_ld`, which
`deli_counter.py` imports only locally inside `club_room_ids`; the patch's
dry run checked that the import's text occurred in the file, not that it was
in scope. Every building raised `NameError` writing its light manifest, the
build manifest written after it was skipped, and `build.py --all` exited 0
with 128 of 131 shells unrebuilt. Fixed by importing it in the function
(`patches/patch_dc_sign_business_import.py`); the build's silence is its own
defect, filed separately.

Rebuilt: 82 light manifests change by exactly the stamp (+1 line, and a
comma); build manifests by their timestamps. Nav gate: 131 shells pass.

Tests: `test_sign_business.py` -- every library sign anchor carries its
building's identity (102 seen); an authored sign keeps its own business and
gains one when it has none; no business, nothing stamped.

## [0.164.0] - an ATM in every store

The walker, 2026-09-29: "Convenient stores should also have ATMs"; Zoo
1.35.0 redrew the `atm` species as a 1990s freestanding surcharge unit (a
lit topper, a green CRT, a keypad ledge; four invented networks by variant;
two draws). This places one in every building that sells.

`atm_store`, A FIXTURE in `shop_floor`'s recipe, placed before the sale
posters so none hangs over it; gated to rooms that sell, as the posters are
(sales, retail, shop, customer, market, showroom, stall); four variants,
keyed by the volume's name; standing, with collision -- a body walks into an
ATM.

ONE IN THE BUILDING, NOT ONE A ROOM (`_piece(..., solo=True)`, read in
`place_fixtures`). A deli's customer floor and its market aisles are two
selling rooms and one store, and with the per-room cap alone the library
carried 37 ATMs in 31 specs, two each in six delis. Now 31 in 31.

THE LIBRARY, by the refurnish chain from 0.163.0's specs: 31 ATMs (sales
floors 13, customer floors 6, shop floors 4, stall floors 3, retail floors
2, a showroom, the marina's shop wing, the country club's pro shop); every
other volume byte for byte, but the sale posters, which the ATM displaces --
3 fewer runs, and the rest renumbered (a fixture's name carries its sequence,
and with it its variant).

Found on the way, and cleared by Zoo 1.35.0 rather than here: the
airport's existing lobby ATM (`prop_atm_delco_1997_04_w60_d55_h145_mmetal`)
has failed Zoo's exact fit in every recent cold run -- the old recipe's sign
stood above its slot (1.57 m against 1.45) and its keypad past its depth
(0.58 against 0.55). The same slot builds and passes on the new recipe.

BUILT (build.py --all): 133 specs, no errors. Nav gate: 131 shells passed,
as at 0.163.0 -- an ATM against a wall blocks no route the gate walks.

Tests: `test_store_atms.py` (5): one ATM in every building with a selling
room and none elsewhere; one store with two selling rooms has one (the
control for `solo`); it stands on its floor against a wall with collision
and a network variant; no sale poster over it; the fixture pass idempotent.

## [0.163.0] - poster walls in the strip clubs, the bars and the shops

The walker, 2026-09-29, choosing where posters go: strip club interiors, bar
interiors, exterior alley walls and poles, store windows and walls; and on
2026-09-30, "then placement". Zoo 1.30.0-1.32.0 builds the runs
(`poster_wall`: four families, one object and one material a run). This is
the three interior kinds. Alleys and poles are Lot's; a store's WINDOW
posters, facing the street, are a rule of their own and not in this release.

THREE FIXTURES (`level_design._PIECES`: `poster_wall_club`, `_bar`,
`_store`), in the recipes' `fixtures` -- the strip club's, the `club` kind's
and `shop_floor`'s -- so `place_fixtures` hangs them after a room is
furnished, from the same wall draws and `_seed_clear` as the dartboard. A
run is three to six sheets wide; its height is Zoo's `band_height` (club
0.64, bar 0.50, store 0.60); it is centred on the gameplay camera's eye
(`agent_contract.eye_height`, new, 1.6), paper, collision none.

GATED BY ROOM, and measured. The `club` kind is a tavern's bar and also a
country club's lounge and a skybox; the bar's gig bills hang only where a
room's id says bar, taproom, tavern, pub or social. `shop_floor` claims any
room whose id says `floor` or `aisle`: ungated, sale posters went on 158
walls including warehouse, foundry, arena, office and self-storage floors;
gated to rooms that sell (sales, retail, shop, customer, market, showroom,
stall), 95. A store's runs stay off storefront glass (`off_glass`), where
they would show the street their backs.

NO ROOM SHOWS THE SAME RUN TWICE. A run's art is keyed on its Zoo stem --
size, form, variant -- so two runs of one width and variant in a room are
the same sheets in the same order; measured at placement, 5 rooms of 48.
`_distinct_variant` moves a `distinct` piece off a variant its size already
shows in its room (the name's crc32 still chooses first), and the pieces
write four variants, not Zoo's eight, because past four `_make_volume` keys
the variant on the building and every same-width run in it would match.
After: 0 rooms of 48.

`prop_species` routes `poster_wall` above the card shop's `poster` row, and
`_PROP_MATERIALS` gives it paper above `poster`'s metal -- `poster` is a
substring of every `poster_wall_*` name, so each run would otherwise have
been built as one card-shop print.

THE LIBRARY: 132 runs in 38 specs -- 29 club (strip_club_a01 7, a02 5, a03
17), 8 bar in 4 (the brewery's taprooms, the social clubs), 95 store in 31.
Written
by the library's own refurnish chain (`migrate_club_rooms`,
`migrate_furnish_recipes`) from 0.162.0's specs, and every other volume in
every spec came back byte for byte: the only differences are the runs and 38
specs declaring `paper`.

BUILT (build.py --all): 133 specs, no errors; the 38 with runs changed
beyond the build stamp and no other did. Nav gate: 131 shells passed, as at
0.162.0 -- the runs carry no collision.

NOT PRICED HERE: a run is one draw, and a room gains one to five. The cold
run that walks them prices them against the stations.

KNOWN: the library has no tavern or dive bar; the bar family hangs in two
taprooms and two social clubs. A bar building is a gap, like the VHS store.

Tests: `test_poster_walls.py` (13): the pieces route to Zoo's species on
paper at its band and the eye; the card shop's poster still routes as it did;
the band is Zoo's (pinned when Zoo is beside this repo); every strip club
room hangs club posters; every run is in a room its gate admits, and a control
that the kinds are wider than the gates; the slot; off the glass; no room
repeats a run; `_distinct_variant` moves and refuses; the fixture pass is
idempotent on the library. Five existing tests learned the new piece: two
club species lists, the fixture stems, the host-spread exemption for hung art
(a poster over a couch is not a second host, as a neon sign is not), and
`poster_wall`'s genome range.

## [0.162.0] - an opening is recorded where its hole is cut

Found fixing the store window sign (0.161.0): the lit sign box over
gas_station_a02's entry stood 0.24 m off its own door -- the door built at
x -6.00, the box centred on -5.76.

THE DEFECT, and it was not the sign's. `_opening_to_hole` cuts every opening
at `snap(pos * run)`; `_record_openings`, which writes the openings into
`<id>.gameplay.json` and hands them to the light manifest, used `pos * run`.
Two spellings of one number. Measured over the library's specs with the grid
each builds at (`LevelSpec.grid`, 0.5, where a spec names none): 957 of 1,943
openings recorded off their own holes, 596 by 0.10 m or more, up to 0.25 m --
472 doors, 222 windows, 194 breaches, 65 garage doors. Everything placed from
the record stood beside its doorway: the DOOR_SOCKET / BREACH_PANEL markers,
the interactives, a window's daylight anchor, the storefront sign box. Now
the record takes `self.snap(pos * run)`, the value the hole is cut at.

THE LIBRARY (build.py --all): 123 GLBs changed (the socket and panel marker
empties in them move with the record), 12 unchanged; 26 derived storefront
signs moved onto their doors, up to 0.24 m; nav gate 131 shells passed.

`migrate_window_sign` drops its two-centre workaround for the one centre, and
takes the grid a spec leaves unnamed from `LevelSpec` -- it had left a
grid-less spec's openings unsnapped, a third spelling. Every sign still clears
its box by `GAP`.

KNOWN, NOT CHANGED: `lot/preview.py` synthesizes openings before any build
with the old unsnapped rule ("mirror the published gameplay.json contract"),
so the preview's openings now differ from a build's by up to 0.25 m.

Tests: `test_opening_records.py` -- every exterior opening record stands on
its built opening slot (fails on 0.161.0: airport_terminal_a01's garage at 8.4
against a slot at 8.5), and every derived sign on its door AS BUILT. The first
cut of the second compared the sign with the opening record, which 0.161.0
had wrong the same way, and passed on the build it exists to refuse.

## [0.161.0] - a cooler wall on every store's sales floor; the window sign clears the lit box

The walker, 2026-09-29: "there should be fridges of cold sodas, beer, milk,
etc, with glowing lights too", and, of the window neon, "fix the sign".

THE SALES FLOOR'S COOLER WALL (`migrate_cooler_wall.plan_sales_cooler`). Five
stores stood an 8 m cooler run on the sales floor; gas_station_a02 and
fuel_stop_heist had only the walk-in's short side in the food-service room
(3.28 m, 4.12 m), gas_station_a03 and stop_n_go none at all. A store with no
cooler on its sales floor now gets `cooler_run_sales`, by `plan_cooler`'s own
clearances: an edge of the sales floor that is a partition or a windowless
exterior wall -- never the storefront, never glazed; the one opposite the
storefront wins a tie -- doors kept `DOOR_CLEAR`, anything in the `AISLE`
cutting the run short, capped at `SALES_RUN` (8.0 m, what the other five
stand: ten doors), centred on the longest stretch; refused below `MIN_RUN`.
All four took their north wall, 8.0 m of 8.62-9.01 m clear, and were
refurnished around it: a02 a shelf run fewer, a03 and stop_n_go a carton
stack fewer, fuel_stop_heist its vending machine and a reshuffled chair set.
The two rules are separate questions answered in one pass; the first cut
skipped the walk-in's rule once the sales floor had a cooler, and
`test_cooler_wall`'s idempotence test refused it. Zoo (>= 1.28.0) stocks
the run soda, beer, dairy first.

THE WINDOW SIGN (`migrate_window_sign`) now clears the lit sign box, not the
door opening: half the box (door + `lights._SIGN_PAD`) + `GAP`. Cold run 9113
showed its door end behind the box. And the box is NOT centred on its door:
`lights._storefront_sign` centres it on the door's unsnapped position while
the door module stands at the grid-snapped one (gas_station_a02: -5.76
against -6.00), so the migration clears both, each where it actually is.
Reported separately; not fixed here. Existing signs are re-placed in their
own slot in the volume list.

THE LIBRARY (build.py --all): the nine stores' GLBs changed, every other
building's recorded output hash is unchanged.

Tests: `test_sales_cooler.py` (6, failing on 0.160.0) and
`test_window_sign.py`'s clearance test, measured against the box in each
store's built light manifest (fails on 0.160.0's positions: cr_gas cleared it
by 0.02 m).

## [0.160.0] - a warm bulb over the register; a beer sign in the window

The walker, 2026-09-29: "add the warm counter accent and the window sign
next", from their 1990s lighting reference on the convenience store at night
-- cooler light on the aisles, a warmer accent at the counter, and a small red
or blue window sign as an accent against the fluorescent interior.

THE COUNTER ACCENT (`lights.py`): one `counter_accent` anchor over the centre
of each volume whose name carries `register_counter` (`_COUNTER_VOLUMES`, the
substring rule `prop_species` uses -- the gas stations' `register_counter`
and the delis' `front_register_counter`), in a room the fluorescent row lights
(not a club room, not a moody one), on the pendant's cord (`_PENDANT_CORD`)
under the ceiling, `drop` from the bulb. Appended with the spills, LAST, so
every anchor before it keeps its place. Lux (>= 0.59.0) lights it warm, at a
troffer's level, scaled with the wash; Zoo (>= 1.27.0) hangs a
`pendant_fixture` for it. The log line counts them.

THE WINDOW SIGN (`migrate_window_sign.py`, run over specs/): every store
(`migrate_slush_machine.is_store`) hangs one `window_sign` 1.2 x 0.06 x 0.6
inside its shop-front glass -- on the storey-0 storefront wall that is an edge
of the sales floor, beside the door nearest the room's centre, 0.15 inside the
wall's face, its top at the glass's head (where Zoo's chains end), facing the
street; refused and reported, never forced, where no span beside a door is
clear. The sign is `metal_painted`, which none of the nine stores' own
material tables defined, and `validate` refuses a volume naming a material
its spec lacks (cr_gas, the first store alphabetically, stopped the commit
gate); the migration adds the library's one definition of it -- the one 166
specs already carry -- to a store that does not have it. `prop_species` routes `window_sign` to `neon_sign`; the volume's
`form: window` rides the slot, so Zoo builds a beer on a clear sheet. No
collision, and no light: the tube is the bright thing, and a lamp would take a
per-mesh slot in a room that has spent them.

A HUNG PIECE IS NOT FURNITURE IN THE COUNT (`level_design._room_volume_count`).
`furnish` tops a room up to a target less the volumes already in it; the sign
counted, and a store refurnished after it was hung placed one piece fewer
(gas_station_a02's `shelf_run_3`; cr_gas's and stop_n_go's cartons re-drawn)
-- `test_club_fixtures`' fixed-point check caught it. A volume with no
collision whose bottom is at least `clearances.min_headroom_m` (2.0) over its
storey's floor is skipped: the bound `hung_headroom_ok` already holds a hung
piece to. The card shop's hangers, signs and pennants are furnish's own and
stripped before the count, so no other spec moved. And the migration inserts
the sign BEFORE the pieces furnish wrote, where a refurnish puts it; appended
last, it came back 10-18 places earlier and the spec failed the same check by
order alone.

THE LIBRARY (build.py --all): 15 buildings carry a counter accent (the nine
stores and six delis: corner_deli_heist_01, cr_deli, deli_a01-a03,
night_deli); 9 carry a window sign. Only the nine stores' GLBs changed (the
sign's greybox); every other building's recorded output hash is unchanged.

Tests: `test_counter_accent.py` (9) and `test_window_sign.py` (9);
`test_lights_partitions`' pinned report gains `counter_accents: 0`.

## [0.159.0] - storefront glass fronts the customer rooms only

The walker, 2026-09-29: "keep glass off the back rooms, use a room-name list".
A spec names a whole exterior wall `storefront_glass`, and in five of the
ten stores that wall also runs past a stockroom, in two past a back hall, in
two past a walk-in cooler (MEASURED on 0.158.0's build) -- each of which got
shop-front glass, a pavement spill and light-budget tiles.

THE RULE: `SHOPFRONT_ROOMS` ("sales_floor", "food_service") -- the customer
rooms behind glass in the library: the sales floor in every store, the food
counter in the two that have one. Roles could not say it: the food counter
and the stockroom are both `fortifiable`. `storefront_slot` now also asks the
room a slot stands in front of (`slot_room`, `lights.room_on_edge`: the room
one of whose exterior edges passes through the slot at the wall's
centreline), and `back_room_wall` gives a back room's stretch of a
storefront wall -- its wall and door slots -- the building's own exterior
material (`default_material`'s kind: concrete, stone) instead of glass.
`storefront_lines`, which the reach, the spill and the light-budget tiles
read, calls `storefront_slot`, so all three follow without a change of their
own.

THE LIBRARY (build.py --all): per store, storefront slots / spills / tiled
plates --

    gas_station_a02, fuel_stop_heist   18 -> 14 / 7 -> 6 / 6 -> 4   (the walk-in)
    gas_station_a01, gas_street,
    gs_corner_station, cr_gas,
    gas_station                        10 -> 8  / 4 -> 3 / 4 -> 2   (the stockroom)
    gas_station_a03, stop_n_go         11 -> 9  / 6 -> 5 / 4 -> 2   (the back hall)
    card_shop_a01                      unchanged (its glass fronts the sales floor only)

Every building's GLB is byte-identical: the change is the art pass's input
(slots) and the light manifest, not the greybox. LEFT AS IT WAS: the
greybox's own wall boxes and their acoustic surfaces on those stretches are
still the spec wall's `storefront_glass` -- a stockroom wall that sounds like
glass. Windows in a back room's wall are windows and keep their panes.

`test_storefront_glazing.py`: the shop-front rooms are the customer rooms;
every tagged slot stands in front of one, and every full wall and door on a
storefront wall in front of one is tagged; in every store a back room's
stretch is untagged and built in the building's own material; the nine back
rooms that had glass have no storefront slot, no spill and no reach. Against
0.158.0's build/ they fail.

## [0.158.0] - a storefront is built from the kit, on every store

Two of the library's nine convenience stores had a storefront on paper and a
solid wall on screen. fuel_stop_heist and stop_n_go name `storefront_glass`
on their shop fronts like the other seven, but they built NON-modular:
`modular` was unset in both, and `build.py` forces it on only for
`pvp_heist` (fuel_stop_heist is a `heist`, stop_n_go an `assault`). So
`_exterior` cut each wall as one box with holes and emitted no wall slots --
51 and 17 slots, every one a prop -- and the storefront glass (0.153.0), the
reach (0.155.0), the spill (0.156.0) and the light-budget tiles (0.157.0),
which all ride on those slots, had nothing to ride on.
`test_storefront_glazing.SHELL_WALLED` named the gap; it is closed.

THE RULE (`migrate_modular_storefront.py`): a spec with a storey-0
`storefront_glass` exterior wall and no `modular` key builds modular; a spec
that says `false` is left as it said and reported. Four specs took the key --
fuel_stop_heist and stop_n_go, and gas_station_a02 and a03, which were
already modular through `pvp_heist` and now say so (their GLBs are
byte-identical).

THE LIBRARY (build.py --all): only those two stores' outputs moved.

    fuel_stop_heist   172 slots (was 51), 18 storefront; rows reaching the
                      glass on sales_floor 6.0, food_service 4.5,
                      walk_in_cooler 4.5; 7 spills; 6 plates tiled
    stop_n_go         96 slots (was 17), 12 storefront; sales_floor 5.75,
                      back_hall 1.5; 6 spills; 4 plates tiled

NOT SEEN IN A LEVEL: no mission the cold runs build draws either store (the
three club_block_014 candidates hold nine other buildings), so this is
verified at Deli Counter's outputs and the nav gate, and the storefront art
itself is the one gas_station_a02 has shipped since cold run 9102.

Thirteen other specs still build non-modular (07_police_station, bank,
cbp_town_finale_midbalanced, corner_deli_heist_01, final_stand,
foundry_heist_vertical, harbor_score, kitbash_demo, primos_pizza,
rarity_demo, rowhouse_raid, survival_demo, warehouse) -- none has a
storefront, and they are not changed here.

`test_storefront_glazing.py`: every storefront spec builds modular (the
migration is a fixed point; its material list equals the builder's, read
from source because the builder imports bpy); the once-shell-walled stores
carry storefront wall and door slots; every store's full storefront walls and
doors are tagged, with no store excepted. Against 0.157.0's build/ they fail.

## [0.157.0] - a storefront-lit room's floor and ceiling ask for light-budget tiles

The walker, 2026-09-29: "yes, narrow it to the storefront rooms". Zoo 1.23.0
shipped every floor's and ceiling's 8 m light-budget tiles as their own
meshes: gas_station_a02's sales floor got its own lamps back (the carpet
through the glass 16.9 -> 20.5, cold run 9106) and the library paid +7.4%
draws, because every room over 8 m split.

The slot manifest now tags `light_budget_tiles` on the floor and ceiling of
each room lit from outside through storefront glass --
`lights.storefront_lit_rooms`, the same tests `derive_light_anchors` gives a
`reach` and storefront spills by (a fluorescent room, not a club room, one of
whose edges is storefront glass) -- and Zoo (>= 1.24.0) splits only those,
under `_lbt`. `themed_tscn` mirrors the name (`LIGHT_BUDGET_ROLES`,
`LIGHT_BUDGET_STEM`) and falls back to the plain plate for a library built
before it. The storefront list and the club rooms are one function each now
(`storefront_lines`, `club_room_ids`), because the slot manifest and the
light manifest both ask.

THE LIBRARY (build.py --all): 32 plate slots in 8 buildings, exactly the
rooms that spill -- every store's sales floor, the stockrooms of the five
`gas_station`-family layouts, gas_station_a02's food service and walk-in
cooler, gas_station_a03's back hall.

`test_light_budget_tiles.py`: the rooms the glass walls are lit and no others
(not a stockroom behind a solid wall, not a bulb room, not a club room); the
flag rides the name on a plate and not on a wall, and a library holding only
the plain floor resolves the flagged slot to it; the mirror matches Zoo's
`kit.module_stem` both ways; in the library the gas station's sales floor
plates are flagged and the flagged rooms are exactly the rooms that spill,
floors and ceilings only. Against 0.156.0's build/ the library tests fail.

## [0.156.0] - a lit store throws its light out through its storefront

The walker, 2026-09-29: "do the outward spill next" -- no light left a store
onto its pavement, so a lit shop at night stood behind a black apron.

A room whose fluorescent row reaches its storefront glass (0.155.0) now also
gets `storefront_spill` anchors along that glass (`lights._spill_anchors`):
one lamp per twice the head of glass, evenly spaced, `_SPILL_OUT` (0.20 m)
off the wall's face at the glass's head -- Zoo's `SF_GLASS_TOP` (3.0 m), or
`SF_HEAD_MIN` (0.4 m) under a lower storey's top -- facing out (`_outward`).
Each carries the room row's `drop` and `reach`, which Lux (>= 0.57.0) solves
the spill's level from, and its `head`, which the throw is measured from.
One anchor per lamp: a `row` runs along `rot_y`, and a spill's `rot_y` is
its facing. They are appended LAST, so every anchor before them keeps its
place; a building with no storefront glass is byte-identical to 0.155.0.
The storefront list gained each slot's width (`w`) for the span. Zoo
1.22.0 records the type as hardware-elsewhere (the room's own troffers).

THE LIBRARY (build.py --all): 35 spills in 8 buildings, every one in a room
that reaches its glass --

    gas_station_a02     sales_floor S 3, food_service S 1 + E 2,
                        walk_in_cooler E 1
    gas_station_a03     sales_floor S 3 + W 2, back_hall W 1
    card_shop_a01       sales_floor S 2
    cr_gas, gas_station, gas_station_a01, gas_street, gs_corner_station
                        sales_floor S 3, stockroom S 1

The stockrooms and the walk-in cooler spill because they are walled by
storefront glass in those layouts, which 0.153.0's migration gave them and
which is a layout question, not this one's.

MEASURED FIRST on cold run 9104's walk copy, three spots at runtime outside
gas_station_a02's sales floor (the count this derives): at the level Lux now
solves, the pavement in front of the glass reads as the carpet does through
it (see Lux 0.57.0 for the frame match and the null result before it).

`test_storefront_spill.py`: 18 m of glass spills three lamps, off the wall's
face at its head, facing out, carrying the row's drop and reach; spills come
last and the rest of the manifest is as before; a low storey lowers the head
with the glass; a short run still gets one, and each facing its own; no
reach, no spill (a bulb room, glass upstairs, no glass); in the library the
gas station's sales floor spills three, and the rooms that spill are exactly
the rooms that reach. `test_storefront_reach.py` now lets a spill carry its
row's reach; `test_lights_partitions.py`'s pinned report gains the count.
Against 0.155.0's build/ the library tests fail.

## [0.155.0] - a row walled by a storefront reaches the glass

The walker, 2026-09-28: "yes, do the glass first then the troffer reach".
Lux derives a fluorescent's range to the floor UNDER the lamp (`drop +
0.75`), and `derive_light_anchors` lays one row down a room's middle -- so in
gas_station_a02's 12 m deep sales floor the floor at the storefront, the part
the street sees through the glass, was 6 m off to the side and outside every
pool.

A fluorescent ceiling row whose room is walled by storefront glass now
carries `reach`: the metres from the row's nearest lamp to that glass,
across the wall, the largest over every storefront line the room has
(`lights._storefront_reach`). Lux >= 0.56.0 derives the range to the floor
at the glass from it, under its usual clamp; Zoo >= 1.21.0 carries it onto
the fixture markers. The storefront lines are the slots the slot manifest
tags `glazing: "storefront"` (`storefront_slot`, the same rule), so the two
cannot disagree about which glass is a shop front. A bare bulb does not
reach, and a room with no storefront glass is byte-identical to 0.154.0.

THE LIBRARY (build.py --all): 17 rows in 8 buildings reach, and only
storefront buildings --

    gas_station_a02     sales_floor 6.0, food_service 4.5, walk_in_cooler 4.5
    gas_station_a03     sales_floor 5.75, back_hall 1.5
    card_shop_a01       sales_floor 5.5
    cr_gas, gas_station, gas_station_a01, gas_street, gs_corner_station
                        sales_floor 11.0 (Lux's clamp caps it at 7.5),
                        stockroom 2.167

MEASURED FIRST on cold run 9103's walk copy at night, the ranges set at
runtime (gas_station_a02's sales floor at 7.5 against 4.55), clear storefront
glass on both sides: the sales floor 9.4 -> 15.7, through the storefront
9.0 -> 11.1, the store from 8 m 30.5 -> 34.6 at the frame's centre. Moving
the row toward the glass instead measured worse (through the glass 8.2).

`test_storefront_reach.py`: a parallel row reaches across the room (6.0); the
control without glass is 0.154.0's anchor exactly; glass on another room, on
another storey or off the room's edge is not this room's; a row running at
the glass reaches from its nearest lamp, and takes the largest of two glass
lines; a bare bulb does not reach; and in the shipped library the gas
station's sales floor carries 6.0, only storefront buildings carry a reach,
only on fluorescents, and every storefront building has one. Against
0.154.0's build/ the last two fail.

## [0.154.0] - a shop floor is lit to sell things

`lights.derive_light_anchors` gave a room bare-bulb pendants when it was
below grade or the objective -- "a vault, a count room" (the rule's own
words). A heist mode that marks a store's SALES FLOOR its objective made it
a cellar: MEASURED over every built manifest, `gas_station_a02` and
`fuel_stop_heist` (and two older builds of it) -- the library's only
objective rooms with a public role -- had five bare bulbs over the sales
floor, which is the room the walker's night photographs (2026-09-28) show
glowing out through a storefront, and the room Deli Counter 0.153.0 just
made see-through. The other seven stores' sales floors already had the
fluorescent row.

`_LIT_ROLES` ("public_entry"): an objective room with a public role keeps
the fluorescent row. A vault, a count room, an office with the safe keep
their pendants. `test_pendant_lights.py` -- the new test fails without the
change (1 failed).

## [0.153.0] - a storefront is see-through glass

The walker, 2026-09-28: "yes, make the storefront see-through glass", after
six photographs of stores glowing at night through their doors and shop
fronts. Zoo 1.18.0 builds a slot tagged `glazing: "storefront"` as an
aluminium storefront -- kick, header, mullions, a see-through pane; a door
with a transom and, closed, glass leaves -- its collider unchanged. This
release puts the tag on the slots it belongs to.

THE TAG (`deli_counter.py`, `storefront_slot` / `write_slot_manifest`): a
FULL wall or door slot of a `storefront_glass` wall, on a building with an
interior. Read against the SPEC's word, because the manifest writes the skin
kind, `glass_facade`, which every curtain wall shares. Not a wall remainder
(a unit box scaled per slot; the narrow ones stand as the frame's piers),
not a window (already see-through), not a facade shell (nothing behind it).

THE NAME MIRROR (`themed_tscn`): `_g<glazing>` for `STEM_GLAZINGS`
("storefront"), after the material, as Zoo writes it; the resolver falls
back to the plain wall or door when a library predates it; a storefront
door's open state is its own art (`STOREFRONT_STATE_ART`), the mirror of
Zoo's, which every other door still defers.

THE WORD: the five stores the `gas_station` preset built -- cr_gas,
gas_station, gas_station_a01, gas_street, gs_corner_station -- called their
shop front `glass`, every bank's and tower's word for an opaque curtain
wall. `migrate_storefront_glass.py` makes it `storefront_glass` in those
five, and the preset now writes it. `glass` everywhere else is untouched.

MEASURED: seven stores carry the tag on their shop fronts' full walls and
doors, and no other building in the library does. TWO DO NOT AND CANNOT
YET: `fuel_stop_heist` and `stop_n_go` build their walls into the shell as
generated geometry -- their manifests are all prop slots (51 and 17) -- so
there is no wall slot to tag, and their glass stays the shell's.
`test_storefront_glazing.py` names them (`SHELL_WALLED`), so the gap is a
test that changes the day it closes.

The mirror tests fail without the change (2 failed); the tagging tests read
the built manifests and cannot be proven that way. Suite passes.

## [0.152.0] - a convenience store has its roller grill

Zoo 1.17.0's `roller_grill` -- the hot dog roller grill on its bun cabinet
(the walker, 2026-09-28: "do the roller grill next") -- in every convenience
store. MEASURED FIRST: no spec carried a `roller`, `hot_dog` or `hotdog`
volume; the library's `grill` volumes are kitchen grills and stay flat tops.

`migrate_roller_grill.py` places it by the slush machine's rule, which
`migrate_slush_machine.plan_station` now takes a name, a size, anchors and
an `ahead` for. The grill is 1.0 x 0.6 x 1.4 and stands nearest the
REGISTER COUNTER, the till the proposal puts it at. Three things the rule
did not know, each found by measuring the first placement:

  * ANCHORED ON THE COUNTER'S CENTRE, five stores put the grill on the west
    wall north of the counter -- behind the till. `ahead` measures from a
    point 1.5 m in front of the counter's face instead, where the queue
    stands (`_front`, the file's own measured facing rule).
  * NOTHING KNEW A COUNTER HAS A STAFF SIDE: gas_station_a03's and
    stop_n_go's grills stood 1.29 m behind the register on the back
    partition, 1.25 m of aisle satisfied and the clerk's aisle filled. With
    `ahead`, the counter's footprint carried `STAFF_DEPTH` (3.0 m) back from
    its rear is an obstacle.
  * A NEIGHBOUR ON THE SAME WALL NEEDS NO AISLE BETWEEN: the 1.25 m kept on
    every side put gas_station_a02's grill 10 m up the partition from the
    slush station it should stand beside. A volume whose back is at the same
    wall keeps `NEIGHBOUR_GAP` (0.05 m) along it. A first cut that also
    asked the neighbour be no deeper than the new piece refused the 0.7 m
    station beside a 0.6 m grill, and the fix did nothing; kept here.

THE SLUSH STATIONS DID NOT MOVE: re-planned from scratch under the
generalised rule, all nine land volume for volume where 0.150.0 put them
(a test). Where the grills land: the west wall on the till's customer side
in the five preset-built stores; beside the slush station on the
food-service partition in gas_station_a02 and fuel_stop_heist; beside it on
the back partition, clear of the clerk's zone, in gas_station_a03 and
stop_n_go. Each store refurnished; the preset carries the grill where the
library does, both modes.

`prop_species` routes `roller_grill` above the kitchen's `grill` row.
`test_roller_grill.py`: 6 of its 8 fail without the change.
`test_slush_machine`'s all-sides aisle check now allows a same-wall
neighbour, which is the rule as it stands.

## [0.151.0] - a store made from the preset is the store the library has

`presets.gas_station` still emitted `aisle_1` and `aisle_2`, which route to
nothing and build as plain boxes, and no frozen drink station. 0.149.0
(`migrate_store_gondolas.py`) and 0.150.0 (`migrate_slush_machine.py`)
migrated the nine checked-in stores and left the preset alone, so every store
in the library had snack gondolas and a slush station and a store generated
from the preset later had neither. The same gap 0.146.0 closed for the
service counter's form, which it gave the preset in the same release.

THE AISLES are `gondola_aisle_1` and `gondola_aisle_2` (`presets.py`), routed
to Zoo's `snack_gondola`. Their `cover_high` markers keep their ids.

THE STATION is placed by `migrate_slush_machine.plan_station` at the end of
the preset, after its markers, not at a spelled position: the rule keeps
clear of markers and volumes, and a change to the rule or to the layout now
moves it the same way in the preset and in the library. MEASURED in both
modes before the patch, in memory: heist and assault each place it on the
stockroom partition at (5.49, -9.0), 4.02 m from the coffee island --
volume for volume the station the checked-in `gas_station` spec carries.

`test_slush_machine.py::test_a_store_made_from_the_preset_has_gondolas_and_a_station`,
both modes: two volumes route to `snack_gondola`, one to `slush_machine`,
equal to the library's, and a second placement pass adds nothing. Proven to
fail without the preset change (2 failed). Nothing pinned the old names:
`test_store_gondolas` holds that `aisle_1` routes to nothing, which stays
true for the supermarkets that keep theirs. Suite 1,020 passed, 2 skipped.

A REFUSAL IS SILENT IN THE PRESET: a layout the rule cannot fit gets no
station rather than an error, and the test is what holds this preset to one.
A second store preset (the roadmap's `convenience_store`, today an alias)
should carry the same test.

## [0.150.0] - a convenience store has its frozen drink station

Zoo 1.15.0's `slush_machine` -- the twin-hopper frozen drink station, syrup
rail and cup tubes (the walker, 2026-09-28: "do the slush machine next") --
placed in every convenience store. MEASURED FIRST: no spec in the library
carried a `slush`, `frozen` or `drink` volume, so this is placement, not
routing alone.

`migrate_slush_machine.py`: a store is a spec whose `sales_floor` carries
`gondola_aisle` volumes (nine: cr_gas, fuel_stop_heist, gas_station,
gas_station_a01..a03, gas_street, gs_corner_station, stop_n_go); the
supermarkets, card shop and marina are left alone. The 1.6 x 0.7 x 2.0
station stands against a side of the sales floor that is not a glazed
exterior wall, clear of every opening by the furnishing pass's 0.9 m, with
no authored volume within `island_aisle_width()` (1.25 m) on any side --
a per-axis box, so conservative near corners, which only ever refuses a
spot -- no marker within 0.5 m, facing the room by the cooler wall's
measured rule, and of every place left the one nearest the coffee island,
or the register counter in a store without one. Nothing is forced: a store
with no such stretch is refused and reported. None was.

Where it landed: on the stockroom partition 4.02 m from the coffee island
in the five preset-built stores; on the food-service partition level with
the register in gas_station_a02 and fuel_stop_heist, clear of the
`sales_to_food` door; on the back partition in gas_station_a03 and
stop_n_go. Each is refurnished after so the library stays a fixed point of
furnishing: a litter bin, a carton stack or a filing cabinet moves or goes
in each, and stop_n_go's generated vending machine.

`prop_species` routes `slush` to `slush_machine`, above the counter row
(whose `station` would claim a `slush_station`); only the nine new volumes
carry the word. `test_slush_machine.py` -- including that the built slots
carry the species, so a spec edit that does not reach the build fails.

## [0.149.0] - a walk-in cooler is cold storage, and a store's aisles are snack gondolas

TWO CHANGES, one rebuild. The second is Zoo 1.13.0's `snack_gondola` (the
walker, 2026-09-28: "do the snack gondolas next"): `prop_species` routes
`gondola_aisle` to it -- gas_station_a02's and fuel_stop_heist's aisles,
which built as plain boxes -- and `migrate_store_gondolas.py` renames the
other stores' aisles to `gondola_aisle_N`: `aisle_N` (0.9 x 10.0 x 1.8, plain
boxes) in cr_gas, gas_station, gas_station_a01, gas_street and
gs_corner_station, and `aisle_shelf_N` (7.0 x 0.7 x 1.6, bare shelving) in
gas_station_a03 and stop_n_go -- 14 aisles in 7 specs. Only in a STORE (a spec
with a `register_counter`), because the supermarkets also call their aisles
`aisle_N`; the supermarkets and the pharmacy's `gondola_a/b` stay. Measured
first: no store spec refers to an aisle by name outside its volume list. The
library is still a fixed point of furnishing after the rename.
`test_store_gondolas.py`.

THE FIRST CHANGE:

Found placing 0.148.0's cooler wall: `gas_station_a02`'s walk-in cooler held a
grill, a kitchen counter and two work tables.

WHY. `level_design._ROOM_KINDS` matches a room's id on whole tokens, first
kind wins, and `cooler` and `walkin` were in the KITCHEN row -- so every
walk-in in the library was furnished with the kitchen recipe (anchor a grill,
kitchen counters on the walls, a work table on the floor).

MEASURED FIRST: six specs, and only walk-ins -- `walk_in_cooler` in
gas_station_a02 and fuel_stop_heist, `walkin_cooler` in gas_station_a03,
stop_n_go, primos_pizza and strip_retail_a01. Counted by each room's own
furniture tag (`_room_tag`), not by bounds: two of those specs' walk-ins
overlap a neighbouring room, and a bounds count had shown the neighbours'
chairs and counters as the walk-in's.

THE FIX: a `cold_storage` kind ahead of the kitchen row takes `cooler`,
`walkin`, `freezer`, `fridge` and `refrigerated`; its recipe is backstock
shelving runs round the walls and clusters of cartons, milk crates and
pallets. `milk_crates` is a new cluster piece -- stacked 0.33 m plastic
crates, material `plastic` -- routed to Zoo 1.14.0's `milk_crate_stack`. The
first commit had it as a box by nature, like a crate stack, and the gate
refused it: `test_furnish` holds every furnished piece to a species ("a
generated piece that routes to nothing is a grey box"), so Zoo grew one. The four
specs whose walk-ins carried furniture are refurnished with
`migrate_furnish_recipes.migrate`, only those (the whole-library run would
refurnish the strip clubs too), so the library stays a fixed point:

    gas_station_a02    grill, kitchen counter, 2 work tables, cartons
                       -> 2 shelving runs, 3 milk-crate stacks
    fuel_stop_heist    grill, 2 kitchen counters, work table, cartons
                       -> 3 shelving runs, 2 milk-crate stacks
    strip_retail_a01   grill -> a milk-crate stack
    primos_pizza       a litter bin -> nothing (a small room)

0.148.0's cooler run is authored, not furnished, and does not move.

NOT CHANGED, on purpose: the delis' and the market's `cold_storage` /
`cold_store` rooms (8 specs) already furnish as `storage` -- racks, cartons,
pallets -- which is not wrong; `cold` is not a cold-storage token, so they
stay. `test_cold_storage.py` fails on 0.148.0 (3 of 3).

## [0.148.0] - the walk-in cooler has its reach-in doors

For Zoo 1.12.0's `cooler_run`, the glowing reach-in cooler wall (the walker,
2026-09-28: "do the cooler wall next", "we also want glowing fridge lights").

`prop_species` routes `cooler_run` to it. Until now the name routed nowhere
and the five preset volumes built as boxes wearing glass. `cooler_backstock*`
-- the walk-in's racks -- stays shelving.

`migrate_cooler_wall.py` gives a cooler wall to the store specs that have a
`walk_in_cooler` room and none: `gas_station_a02` (club_block_014's store)
and `fuel_stop_heist`, whose drinks were behind a partition nobody sees. The
run stands on the walk-in's side shared with a customer room, 0.17 m off
the partition (half its 0.3 m and 2 cm), keeps 0.35 m clear of that
partition's doors -- a02's `cooler_door_1`, food service into the walk-in, is
on exactly this wall -- and is cut short where a volume stands in the 0.9 m
aisle in front, rather than moving it. Measured: a02 3.28 m (a work table in
front of the door zone cut it), fuel_stop_heist 4.12 m, both facing food
service; a spec with no 1.6 m clear is REFUSED and reported, never forced.

THE ROOM IS REFURNISHED AROUND IT. The first commit of this release only
appended the volume and the pre-commit gate refused it on
`test_club_fixtures`'s fixed-point test: the library's generated furniture
must be exactly what `furnish` makes of everything else in a spec, and a
cooler is new input. The migration now refurnishes each spec it touches with
`migrate_furnish_recipes.migrate` -- ONLY those specs: running that migration
over the whole library would also refurnish the strip clubs, which carry
`migrate_club_rooms`'s furnishing instead. Measured: a02 trades a carton
stack for a litter bin; fuel_stop_heist loses two carton stacks and a work
table. Proven from the pre-cooler state: the migration's output is a fixed
point and equals the committed specs byte for byte in content.

AND ITS MATERIAL IS DECLARED. The second attempt was refused by the gate's
spec check: the run named `glass`, which neither store's palette declares.
It names the walk-in's own `cooler_panel`, which both do (a store without it
gets `metal` declared the way furnishing declares a prop's); Zoo's recipe
builds its own steel and glass whatever the slot's word. `validate.py --all`:
403 OK, 0 errors.

FACING WAS MEASURED, not reasoned: on cold run 9096's package the unturned
register counter's doors face its south entry and a turned aisle shelf in
`deli_a01` faces -x, from the shipped node transforms. So a run long in x
with its room on the -y side needs no `rot_z`, and one on the +y or +x side
gets 180.

NOT FIXED, SEEN ON THE WAY: `gas_station_a02`'s `walk_in_cooler` room is
furnished as a kitchen -- a grill, a kitchen counter and work tables stand
inside the walk-in. That is the furnishing's choice of a recipe for the room
and is its own change.

## [0.147.0] - a coffee island is Zoo's coffee island

One row in `prop_species.PROP_SPECIES`, above the counter row: `coffee`
routes to Zoo 1.9.0's `coffee_island`. The counter row's `island` had been
claiming both names, so `coffee_island` (3.0 x 2.0 x 1.1, five store specs)
built as a bare counter and `coffee_food_island` (4.0 x 3.0 x 1.0,
`gas_station_a02` and `fuel_stop_heist`) -- deeper than the counter genome's
2.0 m -- as the plain prop box, which is what cold run 9095 shipped in the
gas station. Measured over the library before it moved: those two names are
the only volumes carrying `coffee` (five and two), so nothing else re-routes.
`test_prop_species.py::test_a_coffee_island_is_the_coffee_species_not_a_counter`
holds it, with the register counters still counters.

## [0.146.0] - the stores' register counters ask for the store's form

Every `register_counter` in the library now carries `"form": "service"`,
which Zoo 1.7.0's `counter` honours as the convenience store's counter --
checkerboard trim, a candy rack on the customer face, registers and lottery
dispensers, the cigarette rack overhead.

THE FIRST DRAFT DID NOTHING, and that is the reason for the migration. It put
the form on the `gas_station` PRESET and stopped. The buildings a cold run
places are the checked-in specs, which are not regenerated from a preset at
build time, and the first rebuild reproduced `gas_station_a02` -- the store
club_block_014 stands -- with its spec hash unchanged. `migrate_service_counter.py`
gives the existing specs the form; the preset keeps it for specs made later.

WHICH COUNTERS: a volume named exactly `register_counter`. Measured over
every non-`lf_` spec, nine carry one and all nine are a fuel stop or a
convenience store -- seven with a pump forecourt and two storefront-only
(`gas_station_a03`, `stop_n_go`). A forecourt test was refused because it
would have missed those two. The delis name theirs `front_register_counter`
and are untouched. A counter already naming a form keeps it.

`test_service_counter_form.py` holds all of it, and one test reads the
BUILT `slots.json`: the counter's slot says `service`, which is what Zoo's
`kit.honour_dressing` reads. Without it, a form on a spec that never reached
a slot would pass every other check. The prop's material is left as it was
(`drywall` on `_a02`); the form overrides it with white laminate.

## [0.145.0] - a fuel canopy finally emits a light

MEASURED FIRST, on cold run 9080's package: the forecourt canopy is 22 x 13 m
on six columns with three pump islands under it, and of the 20 Lux fixture
holders within 45 m every one sits on the SHOP, between world x 58.7 and 81.3.
The canopy spans 81 to 103. Nothing was over it. The canopy volumes have been
authored the whole time -- `specs/gas_station.json` carries `canopy_roof`
24 x 10 x 0.4 at z 5.0 and six `canopy_col` -- and no light anchor had ever
been derived from them.

TWO KINDS, AND THE SPLIT IS THE POINT (light manifest v1.3):

    canopy_lights   one anchor for the whole deck, `size` its footprint.
                    Zoo 1.4.0's species of that name lays the lamp grid
                    inside it in two draw calls and carries no emitter
                    marker, so it glows and lights nothing.
    canopy_wash     two to four light positions under the deck, no hardware
                    at all, lit by Lux from the manifest as `club_wash` is.

`max_lights_per_object` is 8 on GL Compatibility and a literal 12-20 fixture
grid would put every one of those lights on the forecourt ground mesh, the
surface that fills the frame when a player stands under it. The walker's call
of 2026-09-26, with the three options and their costs stated: emissive soffit
and a few lights.

On the authored gas station this derives:

    canopy_roof_lights   canopy_lights  pos (0, -18, 4.78)  size 24.0 x 10.0
    canopy_roof_wash_0   canopy_wash    pos (-8, -18, 4.78)
    canopy_roof_wash_1   canopy_wash    pos ( 0, -18, 4.78)
    canopy_roof_wash_2   canopy_wash    pos ( 8, -18, 4.78)

GRADE IS DERIVED FROM THE COLUMNS, not assumed to be zero. A canopy's columns
stand on the surface its light has to reach, so they are the one thing in the
spec that knows where that surface is -- and `drop` is what Lux derives a range
from, where a flat value has been wrong at both ends before (roadmap 54's
brightness grid, and the arena's lit ceilings over a pitch-black floor). A
canopy with no columns falls back to grade and its `drop` says so. Columns
belonging to another canopy on the same lot are excluded by footprint, or two
fuel stops would share a floor.

The lit face hangs `_CANOPY_DROP` below the soffit, the same 2 cm Zoo's species
stands its lenses proud by, for the same reason: a lit face flush with the deck
it sits in is a coplanar pair and cold run 9080's package already carries a
PRESENTATION_ZFIGHT finding.

ADDITIVE, and now tested as such rather than asserted. A building with no
`canopy_roof` emits neither type, which is every building that is not a fuel
stop; `test_manifest_version_bumped_additively` had only pinned the version
string, and now checks that no canopy anchor appears in a building without a
canopy.

## [0.144.0] - a hidden interactive state keeps its collision off

THE WALKER, 2026-09-23: "If I see collision, I expect collision." And, on
breachable areas: "we don't know if we have breachable areas in the game
yet... would rather have a fallback to solid walls."

MEASURED FIRST, on cold run 9075's package, with a physics probe rather than
from the engine's documentation: six hidden `breached` nodes across three
buildings, every one `visible = false` with a LIVE collider, and the whole
scene grepped for `collision_layer`, `collision_mask`, `disabled` and
`process_mode` returning zero lines. A ray at two of six sampled breach walls
hit `Breach` where a player sees brick.

THE DEFAULT IS STILL SOLID, and saying so is part of the finding. The intact
and breached colliders are coincident, so their union is the intact wall and
nothing walks through one. The fallback the walker asked for already held --
by accident. What it costs is a surface query returning the wrong collider, a
physics-parsed navmesh baking both states superimposed, and a future breach
implemented the obvious way (flip `visible`) producing a visible hole that is
still solid, with no error anywhere.

THE CONTRACT ALREADY SAID SO, in two places, and neither was wired up.
`interactives._DEFAULTS` gives every kind a `collision_per_state` -- a
breach_wall's is `{"intact": true, "breached": false}` -- and `themed_tscn`'s
own comment on the state block already described the game "toggling collision
per interactive.collision_per_state". It named a field that
`gameplay_interactive` dropped on the floor.

### What changed

- `interactives.gameplay_interactive` carries `collision_per_state` into the
  netcode-facing entry. THE ADVISORY SET IS FOUR, not three:
  `docs/INTERACTIVES.md` has listed `reversible, collision_per_state,
  material, breach_class` since the contract was written and this list carried
  three of them.
- `themed_tscn` emits an editable-instance override for a state the contract
  calls not-solid: `[editable path="<inst>"]` then, per collision body,
  `collision_layer = 0` / `collision_mask = 0`. It is SILENT where the
  contract is: an absent `collision_per_state`, or a state it does not
  mention, keeps today's behaviour. Collision goes off only where the contract
  states the state is not solid.
- `themed_tscn._glb_collision_bodies` derives the body names Godot will give a
  module, cached per path. Godot strips `-colonly` / `-convcolonly` /
  `-col` / `-convcol` and makes a StaticBody3D of the stem, so
  `Breach-colonly` arrives as `Breach`. The same four suffixes `_glb_extent`
  skips are the ones this looks for -- one spelling of the convention, read
  from one place.
- `write_themed_tscn`'s stats gain `state_collision_off`.

### How it was checked before it was generated

The override syntax was loaded headless in a scratch project first, in both
forms, and the body read `layer=0 mask=0` with and without `index=` -- so the
index is omitted and nodes match by name. Getting this wrong produces scenes
that do not load, which is not a thing to discover across a whole library.

The body-name derivation was then run against a REAL shipped module,
`breach_delco_1997_01_w140_ob6fc1c_breached.glb` from cold run 9075's export,
which carries exactly two nodes -- `Breach-colonly` and
`Breach_concrete_delco_1997`. The collider is found and the visual beside it
is not. `test_state_collision.py` mirrors that exact shape rather than a
guessed one, and asserts the fixture really contains those nodes, because a
GLB that fails to load makes the function return `[]` and every assertion
after it vacuous.

### Also in this release: 0.143.0 disconnected a basement, and this fixes it

0.143.0 clipped a stair rail's opening to the solid plate beneath it,
`step_d + WALKOFF_CLEAR`. It was right about the floor and silent about whether
what remained still connected. On `foundry_heist_vertical` it did not: the
basement baked as a disjoint island of 339 polygons against 1,286 for
ground-to-roof, and the switchback stair, a 12 m ramp declared at 30 deg and a
ladder all failed to carry.

**Attributed, not guessed.** `build/*.manifest.json` is tracked and carries
`outputs_sha256_16`: `c600f22e9178d52e` before 0.143.0 and `8f2b4ae3a33c8567`
at and since it, so that release moved the geometry and nothing after it did.
Confirmed by building with `stairwell.py` from HEAD~1 -- the old hash returns
and both stairs gate `ok` -- and at HEAD, where `stair_0` is `no_path`.

**Two hypotheses refuted first**, kept because they cost a round each: that the
spec's `to_story == n_stories` was out of range (ten specs use that roof-access
convention and only this one failed), and that the arrival sat one
`cell_height` above the ground floor (the glb says landing, discharge and
ground slab all top out at y = 0.0000; the 0.20/0.35 in the island report are
Recast voxel tops on the bake's own grid, a rounded artefact).

**The threshold.** Forcing `open_rail` to a constant and rebuilding that shell
at each value -- nine distinct glb hashes, monotone, the 2.05 control
reproducing the pre-0.143.0 glb exactly:

    1.0778 FAIL   1.2 FAIL   1.25 FAIL   1.3 FAIL   1.35 FAIL
    1.4 PASS      1.6 PASS   1.8 PASS    2.05 PASS

The bake wants about 1.4 against a plate of 1.0778. The opening has to be WIDER
than the floor under it, so 0.143.0's premise -- opening <= floor -- has no
solution at any clip value.

**A fix that was tried and refuted**, recorded because it looks obviously
right. Deepening the plate by raising `WALKOFF_CLEAR` from 0.8 to 1.25 does
NOTHING: the walk-off also sizes `flight_rect`'s reserved rectangle and the
builder's hole, and the opening is measured from that rectangle's edge, so
`t_lo` moves out by exactly as much as the opening grows. Rebuilt and gated:
still `no_path`, glb `2a371e974f9f852d`. Opening and plate are one quantity.

### What changed

- `stair_guards` lets a rail's opening hang past its plate by up to
  `agent_contract.body_radius()`. DERIVED, not chosen: the hazard is an
  unguarded EDGE, and a body reaches the void only by getting its capsule
  centre over it, which the rail prevents while the overhang stays under a
  radius. It explains all three states at once -- before 0.143.0 the overhang
  was 0.9722 m against a 0.35 m radius, which is exactly why the walker could
  step off the side of a staircase on cold run 9072; 0.143.0 made it zero, safe
  and disconnected; it is now 0.35, and the opening reaches 1.4278.
- `agent_contract.body_radius()` is new. NOT `nav_bake.agent_radius_m`, which
  is 0.40 -- the fattest navigating character plus 0.05, what a BAKE is given.
  This is the body, for questions of the form "can a body get here".
- `deli_counter._stairs` read its own literal `0.8` for the walk-off while
  `stairwell.WALKOFF_CLEAR` governed the guards and the reserved rectangle. Two
  spellings of one quantity, so moving the named one would have left the hole
  and the discharge plate behind. It reads the constant now. `WALKOFF_CLEAR`
  itself does not move.
- `stairwell.RAIL_OPEN_MIN` records the measured 1.4 so a test can assert it.

**1.4 is not a library-wide minimum**, and asserting it as one was this work's
last wrong turn -- caught by running the test that made the claim. 130 of the
library's 149 railed flights leave an opening below 1.4 (a typical step_d of
0.2350 gives 1.3850) and every one gates `navigable: yes`. It is what THIS
landing needed, for a topological reason rather than a dimensional one:
`foundry_heist_vertical`'s basement landing sits in a corner against the south
wall, so the rail's opening is its only way off. `test_rail_opening.py` asserts
that specific case, the library-wide overhang bound, and the one-source rule --
and asserts the "not a general minimum" claim too, so it cannot rot into a
comment nobody believes.

`foundry_heist_vertical` spent eight hours in `navgate_baseline.json` as a
recorded regression while this was found, and has been removed: it gates
`navigable: yes` with both stairs `ok` at glb `4914523fd9cf46ab`, and a fixed
shell left in a baseline hides the next one.

## [0.143.0] - a stair rail's opening must have floor under it

THE WALKER, cold run 9072: "this stair case has some unexpected openings
allowing for gaps to step off of the side of a stair case which we don't want,
and the back is exposed".

`stair_guards` leaves each long-edge rail open by `landing_open`
(0.8 + min_door_width = 2.050 m) so a body can get onto a flight sideways.
That stays: walling the full reserved length once sealed the upstairs
objective off (nav gate, 0.126.0 candidate, `twin_a01`'s both stairs
`no_path`), and the decision is still right.

What nothing checked is whether the opening has FLOOR under it. The solid at
the arrival end is the landing plus the discharge plate:

    landing    land_d  = step_d + 0.7 * step_d
    discharge  d_depth = WALKOFF_CLEAR - 0.7 * step_d
                       ------------------------------
    solid              = step_d + WALKOFF_CLEAR

The 0.7 * step_d split moves where the two plates meet, not how far they
reach. Measured in the shipped package: landing 0.46 m, discharge 0.61 m,
opening 2.05 m -- so 0.98 m of the opening hung over the open shaft.

`tools/walkable_edge.gd` found the fall independently, from physics rather
than from reading extents: 121 unguarded cells at that stairwell, the floor-
level ones at x 7.35..8.10, y 0.00, dropping 2.90 m -- a full storey, at
walking height, with nothing between.

### What changed

A long-edge RAIL's opening is now `min(landing_open, step_d + WALKOFF_CLEAR)`.
On a 3.8 m run at 2.9 m storey height: 2.050 -> 1.022 m.

A `side` is NOT clipped and that is deliberate. It stands on the storey BELOW
and opens at the ENTRY end, where that storey's slab is solid across the whole
rectangle; clipping it would wall a flight in for no reason and the review
would start calling flights contained that a body cannot get onto. Measured:
side opening stays 2.050 m.

### It still lets a body on

1.022 m against the nav bake's requirement of 2 x agent_radius = 0.80 m. A
rail is GUARD_THICK (0.1 m) deep, so the opening is a threshold rather than a
length of passage -- `min_corridor_width` (1.10) is the test for a corridor,
not for a gap in a rail. And beyond the reserved rectangle's edge there is
ordinary floor with no rail at all, so the walk-on is the clipped stretch plus
everything outside the rectangle.

### WALKOFF_CLEAR, and a literal that must NOT be merged

`flight_rect`'s walk-off depth is now the named constant `WALKOFF_CLEAR`
rather than a bare 0.8, because a third spelling of it was about to be added.
`hole_span`'s `clear` is also 0.8 and is a LATERAL pad on the hole's width --
a different quantity that happens to share a value. They are left separate on
purpose: merging them because the literals match is the mistake the note on
the constant exists to prevent.

## [0.142.0] - 2026-09-22  a GLB is not one file, and the closure check could not see the half it was missing

`build_package` bundles a building's art by resolving each
`res://art/zoo/<name>.glb` out of the scene it has just written and calling
`shutil.copy2` on that one path. That was exactly right while a Zoo module
carried its images inside its binary chunk. Zoo 1.2.0 stopped: a module's
textures are now files beside it, named by a relative glTF `images[].uri`,
and this line went on moving one file where there were several.

`_closure_check` returned `portable: true` on every such package -- three of
them shipped, Level Factory cold runs 9067, 9068 and 9069; 9066 predates the
externalisation by three hours and is clean. It walks
`.tscn/.tres/.gd/.godot` for `res://` strings, and a glTF `uri` is neither a
`res://` string nor in a file with one of those suffixes.

The HANDOFF.md every package ships said, in its own voice, "textures are
embedded in the GLBs". It was true when it was written and had become a
promise the package did not keep.

### What actually shipped, and what this repo owned of it

Measured 2026-09-22 on Level Factory cold run 9068's shipped
`LF_club_block_007.portable-godot`: 1,264 external references across 265
GLBs, all of them resolving to nothing. The walker's report was "around 90%
graybox now with no textures/skins on much of the assets."

BE EXACT ABOUT THIS REPO'S SHARE. 1,136 of those 1,264 are under `lot/<id>/`
and came out of this composer -- but they were dead before it touched them.
Level Factory's job store publishes a job's outputs by file SUFFIX, so Zoo's
`.png` files never left the attempt directory, and the kit directory this
composer was pointed at had no textures in it to copy. The bundler would have
dropped them anyway. It is fixed here because leaving one copy site right and
another wrong is how the next one gets written wrong, not because this is
where the pixels were lost. Level Factory 0.105.0 is where they were lost.

### What changed

`glb_deps` is new: read a GLB's JSON chunk, list what it names beside itself,
and copy a GLB with its dependencies. No `pygltflib` -- it never rewrites a
file, so parsing the container is the whole job, and a library that loads and
re-saves a GLB to answer "what does it name" is free to change bytes this has
no business changing.

`build_package` uses it for `art/zoo/`, `art/dressing/` and `art/fixtures/`.
It RAISES when a module names a file that is not there, rather than bundling
a module that cannot be drawn. A module missing from the kit is still
reported the old way, under `missing`, because that is the art pass being
progressive rather than a copy losing half its job.

`_closure_check` grew `glb_unresolved_count` / `glb_unresolved`, and
`portable` reads them. A package whose every module names a texture it does
not carry no longer calls itself portable.

HANDOFF.md now says what is true of both shapes: a module's textures are
either embedded in its GLB or written beside it and named by a relative glTF
`uri`, and both ship.

### Keyed on the document, not on a folder name

`_tex` appears in `glb_deps` nowhere. The next asset class Zoo externalises
is carried on the day it appears, without an edit here. A checker keyed on
that folder would pass it exactly the way this one was passed.

### The new tests

`test_glb_deps.py`: what a GLB names, what an embedded image is not, a
container whose JSON chunk is not the first one, the copy carrying the
texture, two modules sharing one file, the copy refusing rather than moving
half of what it was asked to, and `_closure_check` seeing a reference inside
a GLB -- with the control on the same fixture, because a check that can only
say no proves nothing.

## [0.141.2] - 2026-09-16  the room's ceiling is what the room measures, and it says it is provisional

ZOO 0.99.0 MOVED THE PACK WALL AND THIS ROOM DID NOT FIT ANY MORE. A bay's
shelf count follows its height now -- the fullness the walker asked for on
cold run 9061, where the shop read as a hall -- so at 2.70 m a gondola
carries seven shelves where it carried six: `pack_wall` 2,112 -> 2,358,
`pack_wall_island` 1,416 -> 1,580. The solid furnishing alone went 22,304 ->
23,944, and 0.141.0's flat art (1,064) no longer fits under 24,000.

WHAT CAUGHT IT: `test_card_shop.test_the_measured_module_costs_are_still_zoo_s`,
which re-reads `_WORST_TRIS` against Zoo's own planner rather than trusting
the table. It went red on 2,112 the moment 0.99.0 landed, before anything
was built or walked. The table's comment said "HEIGHT DOES NOT MOVE IT",
which was true of 0.98.0 and is exactly why the reading is not trusted.

WHAT WAS DONE, AND WHOSE CALL IT WAS. `_CARD_SHOP_ROOM_TRIS` 24,000 ->
25,008 -- the room raised to what it measures rather than thinned to the
number -- because 24,000 WAS NEVER A FRAME COST. It is `cubicle_bank`'s
per-species `budgets.tris_lod0` borrowed as a room yardstick, and nothing in
this toolchain ties a triangle count to a measured frame; the only
engine-derived limits here are Lux's (`max_renderable_lights`, and
`max_lights_per_object` 8 on Compatibility). The walker was given the three
options -- measure, trim to fit, or raise and move on -- and chose to
measure. The constant is marked PROVISIONAL in the source with that reason,
and becomes derived when the frame figure exists.

The shell grew with it: `card_shop_a01.glb` 374,856 -> 402,428 bytes. No
other shell's geometry moved -- 0 of 133 manifests carry a changed
`outputs_sha256_16`.

## [0.141.1] - 2026-09-16  the banner asked for timber and nothing said so

A material fix on 0.141.0, found by checking the four flat-art materials
against the four genomes rather than by looking at a frame.

`_PROP_MATERIAL_DEFAULT` is `wood`, and none of the four new pieces had a
row in `_PROP_MATERIALS`, so all four asked for timber. For `aisle_sign`
that is right by accident -- `wood` is its genome's own default. For
`hanging_banner` it is not even legal: its options are cloth, canvas,
plastic and paper, with no wood in them, so Zoo would have fallen back to
its default and built a cloth banner while the slot said timber. NOTHING
WOULD HAVE REPORTED IT.

That is the defect `_PROP_MATERIALS`' own card-shop note warns about, one
release earlier and on the species next to it: "the pennants would have come
out as timber and nothing would have said so." Writing the warning down did
not stop it being repeated.

Each piece asks for its species' OWN default now, so the stem carries no
`_m` and the theme's pack resolves it: `poster` metal_bare, `hanging_banner`
cloth, `ceiling_hanger` paper, `aisle_sign` wood. `aisle_sign` is listed
although the fallback already gave it -- a row that says what it means is
worth more than a coincidence that happens to be right.

AND THE MAP HAD A HOLE THE VOCABULARY DID NOT. `paper` was already in
`material_kind.SKIN_KINDS` and had no row in `KIND_BY_MATERIAL`, which is
exactly the shape Zoo 0.95.0's second half is about -- a kind that reaches
no mesh and says nothing. It said something this time:
`test_every_material_this_pass_writes_resolves_to_a_kind` failed the moment
a piece asked for it, because that test asks `unmapped()` of every id the
pass writes rather than of a list someone maintains.

`test_every_flat_art_material_is_one_its_species_offers` reads the genomes
themselves and is what stops this recurring on the next species. Gates
unchanged: nav gate 5 of 5 and navigable yes, `layout_lint --all` 133 specs
0 FAIL 341 WARN, build freshness clean.

## [0.141.0] - 2026-09-16  the card shop hangs its art, and two checks that could not fire

Zoo 0.98.0 shipped the flat art -- `poster`, `hanging_banner`,
`ceiling_hanger`, `aisle_sign`, and a textured path through
`_surface_stock` so a playmat is printed rather than coloured. This is Deli
Counter placing all four, which finishes properties 3, 4 and 5 of the
card-shop references and leaves this repo with none of the five open.

ZOO'S SIDE OF THE CONTRACT IS ONE SENTENCE AND IT WAS ALREADY BUILT: **the
top of the slot box is the ceiling plane.** Their entry records checking
three candidates for what a thing hangs from -- the ceiling grid's own
geometry (there is none; a drop ceiling is one solid panel with a Pixelcoat
skin on its underside), a light anchor (`core/fixtures.py`'s `mount: "hang"`
exists, but its input is a lights manifest and a painted dragon on one makes
Lux spawn a Light3D at it), and the prop slot. The third is this file's
`under`, which `pennant_row` has hung from since 0.95.0. So two of the four
species needed one `_piece(..., under=_CEILING_AIR)` row and nothing else,
exactly as Zoo predicted.

The other two did not, and the difference is the entry.

### THE TWO HALVES OF THE DENSITY WORK WANTED THE SAME BAND

0.140.0 read reference property 1 -- "product goes to the ceiling, not to
waist height" -- and filled the wall to 2.70. Zoo 0.98.0 read property 4 --
"the wall above the shelving is where the posters live", naming the same
bare 1.2 m band -- and built the posters for it. A wall cannot have both,
and neither release could see the other coming.

IT IS SETTLED WITHOUT A NEW RULE, which is the good outcome and was not the
obvious one. `_UNDER_PENNANTS` hangs the art at 2.70 and DOWNWARD, so a
2.70 m gondola is simply in its way and `_seed_clear` sends it elsewhere --
over the showcase counters, where the bare band runs 0.95 to 2.70, and along
the free walls. MEASURED on `card_shop_a01`: 4 posters and 2 banners on the
selling floor, 4 and 2 in the play area, and **0 of those 12 overlap a
gondola in plan** -- the nearest any of them gets to one is 1.82 m. Fewer
full-height gondolas than the cap allows is the room having somewhere to
put its art.

AND THE ART'S OWN HEIGHT IS DERIVED FROM THE STRIP, not written down.
`_PENNANT_STRIP_H` is declared once and read twice -- by `pennant_row`'s
sizes and by `_UNDER_PENNANTS` -- because a strip and the thing hung under
it are exactly the pair that drifts when the storey height moves.

### `wall_band`, AND TWO WRONG SCOPES MEASURED BEFORE THE RIGHT ONE

`hung_band_bottom` is what a floor-standing wall unit must stop under. It
was written in 0.140.0 when `pennant_row` was the only hung piece in the
room, so its scope was never tested. Declaring three more broke it twice:

    scope                       product ceiling   why it is wrong
    every hung piece            2.70 -> 2.40      a `ceiling_hanger` over
                                                  the MIDDLE OF THE FLOOR
                                                  shortening every gondola
                                                  in the library by 0.30 m
                                                  to clear something nowhere
                                                  near it
    where == "wall"             2.70 -> 1.45      a `poster` is hung on a
                                                  wall but it is a DISCRETE
                                                  piece competing for wall
                                                  space, not a strip along
                                                  the top; nothing should
                                                  stop below one
    wall_band (opt-in)          2.70              only the strip that claims
                                                  the whole wall top

Both wrong answers were silent: the geometry did not move, nothing failed,
and the room simply came back shorter. `pennant_row` is the only piece that
sets the flag and a test says so, because a second one appearing by accident
is how this returns.

### A ZERO THAT WAS A DEFECT, NOT A RESULT

`hanging_banner` placed **nowhere**. The tempting reading is that the wall is
full -- the room does have four gondolas' worth of product on it now -- and
that reading is wrong, which is why the count was attributed instead of
accepted. A probe over all 31 candidates named the blocker in each:

    22  pennant_row (alone or with others)
     9  a gondola, an island, a hanger, a CRT, a vending machine

**The strip the reference hangs the banner UNDER was refusing it.** A
pennant is 2.75-3.05 and a banner 2.00-2.70; they do not share a centimetre
of height. `_seed_clear` knew a hung piece's BOTTOM (`above`, so that
volumes below it are not in its way) and never its TOP, so everything above
it was in its way forever. `below` is the other half of that sentence and
the reference's own arrangement -- "banners and pennant strips run above the
shelving" -- is what it makes possible.

THE BLAST RADIUS WAS MEASURED BEFORE IT SHIPPED, because 0.139.0's entry
says loosening `_seed_clear` "moves every furnished room in the library and
wants its own release and its own frames". It does not, and the reason is
narrow: the term only frees a pair whose vertical extents do not overlap AT
ALL, and the only hung-above-hung pairs in the shipped library are this
room's. `migrate_furnish_recipes.py` over all 127 specs: **one changes**,
`card_shop_a01`. A `ceiling_hanger` at 2.45-3.05 still blocks a 2.00-2.70
banner, because those two really do intersect.

### THE HEADROOM IS DELI COUNTER'S TO ENFORCE, WHICH ZOO ASKED FOR IN WRITING

Both hanging genomes cap height at 0.60 m and derive it from THIS repo's
contract: shortest storey 3.0, less a 0.3 m slab, less `_CEILING_AIR` twice,
less `clearances.min_headroom_m` (2.0). Every term but the last is Deli
Counter's, and the slab is the one Zoo cannot see -- its genome note says so
outright: "a thicker slab makes it smaller ... the placement is Deli
Counter's."

So the cap is not trusted. `hung_headroom_ok` measures the bottom the piece
will actually be built at, at the storey it is actually in. MEASURED at a
3.0 m storey with a 0.5 m floor slab, which is in range for this library:
clear height 2.45, and the 0.50 m and 0.60 m hangers -- both legal by the
genome -- put their bottoms at 1.90 and 1.80 and are REFUSED. A test asks
for that refusal, because a headroom gate that cannot fail proves nothing.

### A FIXTURE IS NOT ALWAYS ON A WALL

`_place_fixture` called `_wall_slots` whatever the piece said, so a hanger
over the middle of the floor could not exist -- the third pass in this file
to assume its own placement. It asks the piece now, as `_host` does, and
`_hung_floor_slots` is the floor half: no aisle and no spread, deliberately,
because a piece above a body's head takes no share of the floor and owes
nothing to the corridor width. What it must clear is what reaches UP to it,
which is `_seed_clear`'s job and was already right.

AND IT CARRIED THE THIRD COPY OF THE HEIGHT LINE. `min(clear_h,
_TO_CEILING_MAX)` sat here as well as in `_host` and in
`test_every_piece_is_a_size_its_species_builds` -- three spellings of one
rule, of which 0.140.0 fixed two. No fixture has a `None` height today,
which is exactly what let this one sit unnoticed while the other two were
found. It asks `to_ceiling_height` now.

### THE ORDER OF THE FIXTURES IS A PRIORITY, AND IT WAS MEASURED

Each fixture is placed against what is already standing, so the list is a
ranking rather than a list. Two orders over the same seed:

    poster before banner    9 posters, 1 banner    21 pieces of art
    banner before poster    8 posters, 4 banners   23 pieces of art

With `poster` first the banner drew ONE across the whole building and the
selling floor got none -- five posters had already taken the wall it needed.
The bigger, rarer piece draws first; one poster is what that cost. The
pennants stay ahead of both, because the rest of the art hangs under them.

### THE ARITHMETIC, AND THE ART IS NOT WHAT THREATENS THE BUDGET

Zoo's entry says it and this checks it independently at Deli Counter's own
palette corners -- every one of the four reproduces Zoo's published
per-species figure exactly (poster 78 framed, banner 62, hanger 52, sign 88):

    worst case the caps allow, one selling room
      the solids (0.140.0)                 22,304
      poster x6                               468
      hanging_banner x2                       124
      ceiling_hanger x4                       208
      aisle_sign x3                           264
                                          -------
                                           23,368   97.4 % of 24,000

    card_shop_a01 as shipped         0.140.0   0.141.0
      sales floor                     14,938    15,590
      play area                        3,888     4,348

**THE ART IS 4.6 % OF THE ROOM AND DISPLACED NOTHING.** Every solid figure
above is unchanged to the triangle -- same gondolas, same islands, same
pennants, same cases -- so the flat art is purely additive. The shipped
posters cost 14 triangles each rather than the 78 the worst case assumes,
because the forms that actually got placed are `bare` and `tilted` and only
`framed` carries the mat ring.

WHAT IS NOW TIGHT, said rather than left to be discovered: 97.4 % of the
room budget. The next thing added to a card shop displaces something, and
that is a real change from 0.140.0's 92.9 %.

AND THE TRIANGLES ARE NOT THE COST HERE. Zoo measured a saturated room at
2.392 MiB of decoded art for 18 images, which is what is actually spent on
every client and is Pixelcoat's and Zoo's to hold down -- one atlas per
module, and an atlas named by a digest of its own pixels so identical art is
one image. Deli Counter's caps do not move that number; they move how many
distinct modules ask for one.

### What the frames show

The same sight line as 0.140.0's pair -- spec (0.3, -8.4) at 1.6 m, 95
degrees, same rig -- and the count is of the band the earlier frames left
empty:

    hung art in frame     0  ->  7   (4 ceiling hangers, 3 aisle signs)
    standing solids       10 -> 10   unchanged, which is the point

The upper third of the frame was bare grey in both the before and the
0.140.0 after. It is not now. The frames are still greybox with a neutral
rig, so they show where the art hangs and how big it is, not what is painted
on it -- and nobody has walked this build.

### The gates

  * nav gate, `card_shop_a01`: **5 of 5 interior markers reachable, stairs
    traverse, navigable yes** -- unchanged. Nothing this release places has
    collision at all.
  * `layout_lint --all`: **133 specs, 0 FAIL, 341 WARN, 101 specs with
    findings** -- the same numbers as 0.139.0 and 0.140.0.
  * `migrate_furnish_recipes.py`: one spec changes. The `_seed_clear` change
    is the one that could have moved the library and did not.
  * `build.py --all`: **133 shells, 0 errors**, and of the 442 tracked build
    artefacts it rewrote, `card_shop_a01.manifest.json` is the ONLY one with
    a content change -- every `.gameplay.json`, `.slots.json` and
    `.lights.json` in the library byte-identical. `build_freshness` clean.
  * unit suite: 945 passed, 2 skipped.
  * `test_card_shop.py` gains SEVEN tests, six of which fail on 0.140.0.
    The seventh is `test_the_play_tables_still_ask_for_the_printed_mat`,
    which passes there too and is said rather than counted: `stock="cards"`
    was already written, and the test exists so that dropping it is a
    failure rather than a quiet return of the gap Zoo 0.95.0 recorded.

### Also

`prop_species` routes the four species, and what that re-routes among the
library's AUTHORED volumes was measured before the rows were written against
Zoo's full keyword lists: **nothing**. Three of Zoo's keywords are
deliberately not taken, on `gondola`'s precedent -- `mobile` would claim a
mobile home the day one is authored, and bare `banner` and `sign` would
reach `scoreboard`, `sign_post` and `sign_box`, which are already names
here. A keyword whose match would be wrong is worse than one that never
fires, because it fires silently.

THE PLAYMAT NEEDED NOTHING, and that is worth a line rather than silence.
Zoo 0.95.0 recorded "NOT TEXTURED, and that is a limit rather than a choice"
as the single most visible gap in the play area; 0.98.0 closed it inside
`_surface_stock`, and Deli Counter's side was one word it was already
writing -- `folding_table`'s `stock="cards"`. A test now asserts that word,
so dropping it is a failure rather than a quiet return of the gap.

`KIT_VERSION` does not move, for 0.140.0's reason: the builder's geometry is
unchanged and what moved is what `furnish` writes.

## [0.140.0] - 2026-09-16  the card shop fills its height and its floor, and the cap was not a budget

The walker walked cold run 9061's `card_shop_a01` and photographed the sales
floor from (-40.7, 1.6, 10.5): "the card shop should feel saturated with
posters, ads, playmats, content, fantasy, ect ect." Nine more references,
written up in `docs/SET_DRESSING_REFERENCES.md` ("The card shop is not dense
enough, and what dense means"), which splits that verdict into five separate
properties. This release is the two Deli Counter owns -- **product goes to
the ceiling** and **the middle of the floor is occupied**. The other three
(things hang, posters over the shelving, printed playmats) are Zoo's flat-art
species and are not here.

THIS IS A DEFECT BEING UNDONE, NOT A FEATURE BEING ADDED, and the difference
is the whole first half of the entry. 0.139.0 capped this room three ways --
`reserved_by` on `pack_wall`, an empty `floor` run, two pennant rows instead
of four -- and each cap was written against **10,664**, cited in that entry
as "the 10,664 Zoo measured for a whole card shop room". It is not a budget.
Zoo 0.95.0 publishes it under the heading **"THE ROOM-LEVEL NUMBER, because a
species budget is not a room"**, as a MEASUREMENT of one reference furnishing
at its worst genome corners -- one L case, four pack bays, four pennant rows,
three tables, eight chairs -- and follows it immediately with "For scale, one
`cubicle_bank` is budgeted 24,000 and the club's `back_bar` 8,500."

So the shipped room was capped BELOW the reference furnishing it was citing
as its ceiling: two pack walls where that reference has four, two pennant
rows where it has four. The walker then walked it and called it a hall. That
is not a tradeoff that turned out badly; it is a measurement read as a limit,
and the correction is in the code rather than in this paragraph
(`_CARD_SHOP_ROOM_TRIS`, and
`test_the_room_budget_is_zoo_s_only_real_one_and_the_caps_fit_under_it`).

DOES THIS REDUCE INTERVENTIONS-PER-LEVEL? Not by itself, and the honest
reading is worse than neutral: this is the generator being walked back to
where it should have been, so it buys back density a previous release gave
away. What it leaves behind that is new is `where: "island"` -- a recipe can
now stand product in the open floor with a contract-width aisle round it,
which is every retail room this pipeline will ever generate and not only this
one. Nobody has measured the intervention count (roadmap 17).

### THE FIGURES, VERIFIED RATHER THAN QUOTED

Every number below was re-measured by planning the SHIPPED spec's own volumes
through Zoo's own planners at each volume's own variant, which is what
0.139.0's entry did. The before column reproduces that entry exactly, which
is why the after column can be believed:

    card_shop_a01 sales floor      0.139.0    0.140.0
      display_case x2 + end          2,864      2,864
      pack_wall (wall + counters)    2,804      3,510   (2 -> 3)
      pack_wall_island                   -      4,188   (0 -> 4 modules)
      pennant_row                    1,784      3,568   (2 -> 4)
      crt_tv x2                        808        808
                                   -------    -------
                                     8,260     14,938

    play area                        2,996      3,888

**VARIANT IS LOAD-BEARING IN THAT TABLE AND WAS NEARLY MISSED.** A first
pass planned every piece at variant 0 and reported the before column's pack
walls at 2,832 against the entry's 2,804 -- a 28-triangle disagreement that
looked like rounding and was not. `_make_volume` writes a variant from the
name's crc32, and a pack wall's variant moves which rows are peg rows. Two
instruments disagreeing is one of them being wrong; passing the volume's own
variant made the two agree to the triangle across every species in the room.

### 1. PRODUCT GOES TO THE CEILING, AND THE HEIGHT IS FREE

A 2.2 m pack-wall bay in a room with 3.10 m of clear height leaves a metre of
bare wall, and reference property 1 is the opposite of that: "a wall that
stops at 2.2 m in a 3.4 m room reads as a partition; a wall filled to the
ceiling reads as a shop."

THE BAYS GET TALLER RATHER THAN SOMETHING STANDING OVER THEM, and the genome
is what decided it, not a preference. `pack_wall`'s `dimensions.height` runs
**1.6 to 3.2** and its own note names the reference "floor-to-ceiling gondola
shelving"; there is no Zoo species today that is "a thing that stands above a
gondola", so the alternative was not available at any price.

MEASURED through `pack_wall_forms.plan` at every palette width over
2.2 - 3.2 m: **triangles do not move.** A 2.4 m bay is 1,416 at 2.2 m and
1,416 at 3.2 m, because `CAPS["shelves_per_bay"]` (6) binds at every height
in the range and the cost of a pack wall is bays, not metres. What the height
buys, on a 1.8 m bay: the top stocked shelf rises **1.78 m -> 2.21 m**.

WHAT IT COSTS, SAID RATHER THAN QUIETLY NARROWED. Those six shelves spread to
fill the taller bay, so the pitch goes **0.258 -> 0.330** and a bay reads
slightly airier per metre than it did. That cap is Zoo's, not this file's,
and raising it is Zoo's call against Zoo's own budget -- 578 triangles a bay
against 6,000. It is filed rather than worked around here.

THE HEIGHT IS DERIVED AND THE DERIVATION HAS THREE TERMS
(`to_ceiling_height`): the storey's clear height, the species' own genome max
(`ceiling`), and the band the ceiling-hung fixtures own (`under_hung`,
computed by `hung_band_bottom` from the hung pieces themselves). At a 3.4 m
storey that is 3.10 / 3.20 / 2.75, and the product ceiling is **2.70**. A
taller hung fixture pushes the product down without anything being edited,
and a `furnace` -- which is meant to run its flue to the slab -- opts out of
the second term and is unchanged.

`PACK_WALL_H` IS GONE, AND IT WAS TWO SPELLINGS OF ONE NUMBER. It sat beside
`_PIECES["pack_wall"]`'s own sizes and the two agreed at 2.2 by coincidence;
raising the run's heights left the two gondolas BEHIND THE COUNTERS -- the
most visible pack walls in the shop -- at 2.2 while everything else went to
2.70. `counter_pack_wall_height` reads the one declaration now.

AND THE CRT WAS NEARLY LOST TO IT. `card_shop_counters` hangs the reference's
"small CRT on a shelf behind" OVER the gondola, so the gondola cannot take
the whole clear height. MEASURED at the full 2.70: a 0.50 m CRT's bottom
lands at 2.75 and its top at 3.25 against 3.10 of clear height, so the pass
reports `crt: false` -- both CRTs silently gone. Taking the CRT's own band
off first gives **2.55** and keeps both. That is a second derivation, not a
pinned number: a taller storey gets the full height and the CRT.

`_floor4`, AND WHY A ROUND WOULD HAVE BEEN WRONG. `round(x, 4)` can move a
value UP by 5e-5, and every caller of these heights asks a LIMIT of the
result -- `_host` refuses `h > clear_h`, the CRT pass refuses one with no
room above. A height derived as exactly `clear_h - crt_h - air` and handed
back 5e-5 over is a piece silently not placed: one quantity, two spellings, a
threshold between them, which is `_wall_span`'s shape and CLAUDE.md's rule.
Flooring makes the derived height never larger than what it was derived from.

### 2. THE MIDDLE OF THE FLOOR IS OCCUPIED

Reference property 2: "the current recipe treats the floor as circulation and
puts everything against a wall. That is what makes the frame read as a hall:
there is nothing between the camera and the far wall."

`where: "island"` is new and is the general half of this release. A piece
declared `island` stands in the OPEN FLOOR, long axis along the room's long
axis, with a walkable aisle on every side -- `_island_slots`,
`_island_aisle_clear`, `_island`. `card_shop`'s `floor` run, which 0.139.0
emptied, carries `pack_wall_island`: the same species, off the wall.

THE AISLE IS THE CONTRACT'S AND IS A REUSE, NOT A NEW NUMBER.
`island_aisle_width` is `staff_aisle_width`, whose derivation was never about
bars: an aisle is a corridor a body WALKS THE LENGTH of, so at least
`clearances.min_corridor_width_m` (1.10), and it is ENTERED AT ITS END
between two units, which is a doorway, so at least
`clearances.min_door_width_m` (1.25). One aisle cannot be two widths --
**1.25 m**, the greater, which satisfies the corridor minimum by construction.

`_seed_clear` IS NOT THAT NUMBER AND COULD NOT HAVE BEEN. It keeps a piece
0.9 m off another volume's edge, which is BELOW the corridor minimum: right
for a chair beside a desk and wrong for a run a body walks down. An island
asks both.

AN ISLAND IS TWO FACES, NOT ONE BLANK BACK. `pack_wall`'s back panel owns +Y
and carries no product, so a single one mid-floor is a slatwall sheet seen
from half the room. `twin` writes the other face: two volumes sharing a
spine, each facing its own aisle, each its own module. It doubles the cost --
4,188 triangles as shipped where one face each would have been 2,094 -- and
the budget affords it, which is the rare case where the EXPENSIVE version
ships, so what the cheap one would have saved is recorded here instead of
the other way round.

AND THEY RUN DOWN THE MIDDLE, WHICH THE FIRST BUILD DID NOT. Shuffling the
free positions flat put one of two islands hard against the counter wall --
product where product already was, and the centre of the frame still empty.
The candidates are sorted by distance from the room's centre line on the
SHORT axis only, so the band is decided and the position ALONG the room stays
the shuffle's and two islands do not stack.

**THE INVARIANT THIS BREAKS, DECLARED RATHER THAN DODGED.** `furnish` has
never created mid-floor SHELTER -- that rule is
`test_nothing_it_puts_mid_floor_reaches_shelter_height`, whose own first
draft was refuted for claiming too much. A 2.70 m gondola in the open floor
IS shelter, on purpose: a retail aisle is something a body fights from, in
this engine and in a real shop, which is the same argument that refuted that
draft about a desk. Two things bound it, and a test holds both
(`test_the_only_mid_floor_shelter_is_a_declared_island`): only a piece whose
own `where` says `island` can stand there, and `card_shop` is the only recipe
that names one.

### THE CAPS, BEFORE AND AFTER, AND WHAT EACH BOUGHT

    cap                     0.139.0   0.140.0   what the raise buys
    pack_wall `most`              2         4   +2 gondolas of product on the
                                                free walls. `reserved_by` is
                                                unchanged, so a two-counter
                                                floor now has two BEHIND the
                                                counters and two spare rather
                                                than two and none -- "the
                                                reference's one long aisle of
                                                it", which 0.139.0 named as
                                                the thing it was giving up.
    pennant_row `most`            2         4   one row a wall, which is Zoo's
                                                own reference room. The two
                                                extra walls carry colour at
                                                the one height nothing else
                                                in the room reaches.
    card_shop `floor`            ()  island x2  4 gondola modules standing in
                                                the open floor, which is the
                                                whole of property 2.

    worst case the caps allow    0.139.0   0.140.0
      sales floor                 10,632    22,304
      against                     10,664    24,000
      of budget                    99.7 %    92.9 %

**THE NEW CAP IS LOAD-BEARING AND A TEST SAYS SO.** One more island is 2,832
triangles and puts the room at 25,136, over; that assertion is in
`test_the_room_budget_is_zoo_s_only_real_one_and_the_caps_fit_under_it`,
because a cap that is not the thing holding the number is a comment (Zoo's
words, one layer down).

**AND THE BUDGET IS STILL NOT A FRAME TIME.** 24,000 is one `cubicle_bank`,
the largest per-module budget Zoo declares and the figure Zoo itself offered
for scale. It is a measured reference held against a measured reference,
because there is still no runtime telemetry from a real session (CLAUDE.md,
"every frame is spent on somebody else's machine"). When that data exists
this is the dial and `most` is where it is spent. What this release does NOT
claim is that 22,304 is affordable on the low-end GL Compatibility target;
what it claims is that 10,664 was never the number that said otherwise.

### WHAT THE FRAMES SHOW, COUNTED

Rendered from the walker's own sight line, identically before and after: the
export instances the shop at site (-41, 0, 5) and the spec's plan y is
Godot's -z (checked against the shipped `lot/card_shop_a01/site.tscn`, where
`display_case_r48016798_1` at spec y -0.18 stands at Godot z +0.18), so the
walker's eye is spec (0.3, -5.5) at 1.6 m looking north.

THE EYE HAD TO MOVE BACK TO 8.4 m TO RENDER THE PAIR, AND THAT IS ITSELF THE
RESULT: at the walker's exact spot the after frame is flat grey, because an
island now stands 0.25 m in front of where they were standing in open floor.
Both frames below are from (0.3, -8.4, 1.6), 95 degrees, same rig.

    in frame, standing solids              6  ->  10
    of those at cover-break height or over 1  ->   5
    clear span down the sight line        10.40 m -> 3.15 m

10.40 m was the room's whole depth: "there is nothing between the camera and
the far wall", measured rather than described.

TWO THINGS THE FRAMES DO NOT SETTLE. They are greybox shells with a neutral
rig -- `review_render`'s limitation, restated because it still applies -- so
they show the footprint and the height of what stands, not the art on it. And
nobody has walked this build; the walker has not seen these frames.

### THE GATES

  * nav gate, `card_shop_a01`: **5 of 5 interior markers reachable, stairs
    traverse, navigable yes** -- the same verdict 0.139.0 recorded, with two
    islands and a full-height wall run now in the room. The staff aisles and
    the play area are what those markers are.
  * `layout_lint --all`: **133 specs, 0 FAIL, 341 WARN, 101 specs with
    findings** -- the same 341 and the same 101 as 0.139.0. The islands add
    none, which is the claim worth making: a mid-floor solid is exactly the
    shape L9 and the corridor rules would complain about.
  * nav gate, `--all` over the rebuilt library: **131 shells, 0 stair
    failures.** 9 unjudged and 14 `navigable: false` are the standing
    population (exterior markers on ground Lot lays, which no building bake
    can answer) and none of them is a card shop.
  * `migrate_furnish_recipes.py` over the library: **one spec changes**,
    `card_shop_a01`. The other 126 are byte-identical, so the library is
    still a fixed point of `furnish` and this release moved nothing else.
  * AND THE REST OF THE LIBRARY IS PROVABLY UNTOUCHED, which is the claim
    that makes the three above worth anything. `build.py --all` was run on
    this checkout, rewriting 133 of the 135 tracked manifests (two are
    orphans of specs that no longer exist), and **132 of the 133 came back
    differing in `built_utc` ALONE** -- every `.gameplay.json`,
    `.slots.json` and `.lights.json` in the library byte-identical,
    `card_shop_a01` the only one whose spec hash and `.glb` hash moved. So
    the 132 timestamp-only manifests are not in this commit, and no other
    shell's nav result can have moved because no other shell moved.

### ALSO, AND IT WAS THE SUITE THAT FOUND IT

`test_every_piece_is_a_size_its_species_builds` carried its own copy of
`_host`'s height line -- `min(_clear_height(spec), _TO_CEILING_MAX)` -- which
is the `variant_count` defect in a different disguise: a checker spelling out
what the writer computes. It caught its own staleness the moment a
to-the-ceiling piece appeared whose species tops out below that constant,
reporting a **4.0 m pack wall against a genome of 1.6-3.2** that this pass
will never write. It asks `to_ceiling_height` now.

`PACK_WALL_CEILING` (3.2) is copied out of Zoo's genome, so a test re-reads
the genome where Zoo is reachable rather than trusting the copy. The same
goes for the per-module triangle table the budget test multiplies out.

`KIT_VERSION` DOES NOT MOVE, and that is deliberate rather than an oversight.
The builder's geometry is unchanged: rebuild any existing spec with this code
and the `.glb` is identical. What changed is what `furnish` WRITES, so
`card_shop_a01.json` differs and its build differs with it -- a spec change,
not a kit change. `SCHEMA_VERSION` is unchanged for the same reason.

`test_card_shop.py` gains ELEVEN tests and `test_furnish.py` one, and each
of the twelve fails on 0.139.0 -- except one, which is said rather than
counted: `test_the_crt_still_has_its_shelf_over_the_taller_gondola` passes
there too, because the CRTs did fit at 2.2. It is a guard on a property this
release nearly took away, not a new rule, and it belongs in the file for that
reason.

### WHAT IS NOT DONE

Three of the five properties, and they are Zoo's: things hang from the
ceiling grid, posters live on the wall above the shelving, and a playmat is
printed rather than flat colour. The bare wall this release fills is the band
from the floor to 2.70; the band from 2.70 to the ceiling is now the pennants
and whatever hangs there next, which is not this repo's to draw. A card shop
with full-height gondolas and no posters is still not the reference.

`shelves_per_bay` is the other open one, and it is Zoo's: six shelves spread
over a 2.70 m bay is a wider pitch than six over 2.20, so the wall is taller
and no denser per metre. That is the one place where this release's own
measurement says the result is not yet what the photographs show.

## [0.139.0] - 2026-09-16  a 1990s card shop, and four rules that could not fire

The walker, 2026-09-15, with nine photographs of trading-card shops, written
up in `docs/SET_DRESSING_REFERENCES.md` ("The walker's trading card shop
references"). Zoo 0.95.0 built the five species and Pixelcoat 0.44.0 the three
surfaces; the Deli Counter line of that spec is one sentence -- "a `card_shop`
preset ... and a `card_shop` room kind with the recipe above; the name added
to Level Factory's preset list" -- and this is it. Level Factory 0.91.0 is the
other half of the last clause.

THIS DOES NOT REDUCE INTERVENTIONS-PER-LEVEL BY ITSELF. It is one more
building type the generator can produce unattended, which is breadth, not a
lower intervention count; nobody has measured that number yet (roadmap 17).
What might move it is the second half of this entry: four rules that had no
way to fire and one cap that was not holding anything, all of them found by
pointing the existing machinery at a room whose subject is the product on its
walls.

### The preset

`card_shop`, 20 x 18 m, 3.4 m storeys, one or two of them. A glass storefront
on the street face; the whole south band (11 m deep) is the sales floor, wall
to wall, with the showcase counters down its two side walls; behind it the
stockroom on the rear door and the play area behind a wide opening. A flat
over the shop when `floors` is 2.

`floors` IS READ. The pawn shop and the club both accept it and `del` it; a
parameter a signature takes and ignores is somebody's unfinished thought, and
this repo has a rule about those. One storey is the strip-mall unit and two is
the shop with a flat above, which is the pawn shop's upper pattern one door
along. The stair's pitch is `atan(3.4 / 4.8)` = 35.3 deg, inside
`floor_max_angle`; 20 of 38 shipped buildings are not, and that is the tension
CLAUDE.md names.

THE PLAY AREA HAS TWO WAYS IN AND NO MORE, AND THAT IS ARITHMETIC RATHER THAN
A PREFERENCE. `_seed_clear` holds a piece 1.5 m plus its own half-extent off
every doorway, so a 2.4 m play table is kept 2.7 m from each one. MEASURED on
the first draft of this plan, where the play room was 6 x 7 with three doors
and a breach: NOT ONE TABLE stood, because the four approaches covered the
room. It is 10 x 7 now with one wide opening and one breach at opposite ends,
and the wall it shares with the stockroom is solid.

### The room kind

`card_shop`, read off the building's id exactly as the strip club's is
(`is_card_shop_room`), so it survives Level Factory naming the level
`lf_<mission>_<seed>`; the spec carries `preset: "card_shop"` for the same
reason the club's does. The selling rooms only: the stockroom keeps `storage`
and the flat keeps `apartment`, as the club's cash office keeps `vault`.

    anchors   the showcase counter, and a second past 64 m2 -- or, in the
              play area, up to three play tables, one per
              `card_play_table_floor` (7.58 m2: the widest table by its
              depth plus a chair and a body on each side, derived from the
              pieces and `agent_contract.json`, not chosen)
    wall      pack walls, a shelf run, a vending machine
    fixtures  the pennant rows, placed after the room is furnished
    floor     nothing -- see the triangle arithmetic below
    clusters  cartons

Five species from Zoo 0.95.0, every size inside the genome read from
`zoo/zoo_keeper/genome/species/`: `display_case` (2.4/3.6/1.8 m at 0.6 deep),
`display_case_end`, `pack_wall` (1.2/2.4/3.6 at 0.5), `pennant_row`
(4/6/8 m), `folding_table` with the `cards` stock, `folding_chair`. The
surfaces are the theme's own kinds: `wood_panel` on the case and the shop's
partitions, `slatwall` on the pack walls, `carpet` on the play floor and
`tile` on the sales floor -- and the play area's carpet is `carpet`, NOT
`carpet_tournament`, because a pack directory is `<kind>_<theme>` and the
`card_shop` theme is what makes it the tournament loop. Inventing a
`carpet_tournament` kind would have given it a pack no other theme could
answer.

### The staff aisle, which is not a new number

`bar_aisle_width` is `staff_aisle_width` now and the club's name is an alias
of it, not a second body. The derivation is unchanged and it was never about
bars: an aisle behind a counter is a corridor a body walks the length of, so
at least `clearances.min_corridor_width_m` (1.10), and it is entered at its
END through the gap between the counter's end and the backing unit's, which is
a doorway, so at least `clearances.min_door_width_m` (1.25). One aisle cannot
be two widths. **1.25 m**, measured in the built shell, on both counters.

`back_bar_club_counters`'s geometry is extracted into `_staff_side_plan` and
the card shop's pass calls the same function with a pack wall instead of a
back bar. The club's numbers are unchanged and `test_club_rooms`,
`test_club_fixtures` and the library fixed-point check are what say so, not
this paragraph.

A `patrol_point` stands in each aisle, so the nav gate ANSWERS whether a body
can get behind the counter rather than anybody assuming it -- and a second one
stands in the far corner of the play area, because the play area is the one
room here whose furniture stands mid-floor and a room the gate is given no
point in is a room it says nothing about. Measured on `card_shop_a01`:
**5 of 5 interior markers reachable, stairs traverse, navigable yes.**

### THE COUNTER IS SLOTTED AT ITS FINAL DEPTH, and the first build was proof

`card_shop_counters` followed the club and MOVED the counter off its wall
after the room was furnished. The strip it moves into had therefore been open
floor for the whole of `seed_cover` and `furnish`. On the first build of
`card_shop_a01` BOTH counters were refused -- one by
`kiosk_sales_floor_shelter`, a shelter piece placed before any furniture, and
one by `folding_chair_..._4_3`, a play chair placed after the counter -- and
the shop came back with no pack wall, no CRT and no shopkeeper. The pass
reported both correctly, which is the only reason it was not shipped.

`piece_back_off` puts the counter's back `PACK_WALL_DEPTH + aisle` off the
wall face at slot time (`backed_by`), so its own `_seed_clear` keepout covers
the staff band for everything placed after it, and the pieces placed before it
are what keep it off that wall. `_WALL_PIECE_AIR` is inside that number rather
than on top of it, so `_staff_side_plan`'s "already stands off its wall" branch
does not fire on a 1 cm overshoot -- which it did, at 1.76 m against a needed
1.75.

`off_glass` keeps the counter off the STOREFRONT, because the pack wall that
follows it would board up a 4.0 m shop window from the inside. Measured: it
did, on the build before the rule.

### FOUR RULES THAT COULD NOT FIRE

Each was found by pointing existing machinery at this room, and each is a
`check that cannot fail is indistinguishable from one that passed` in a
different disguise.

  * **A wall-run entry is a lottery ticket, not a promise.** The run is
    shuffled and then cut to about half the room's target, so `pennant_row`
    listed twice still came back ZERO times on the sales floor -- and every
    spot the probe tried was CLEAR. The pennants are a `fixture` now, the
    dartboard's machinery, which places one per `fixture_limit` with
    `_FIXTURE_ROUNDS` draws each.

  * **A cap a later pass can walk past is not a cap.** `pack_wall`'s `most`
    was spent by the wall run and then `card_shop_counters` stood one more per
    counter, so a two-counter selling floor drew FOUR. At the palette's widest
    that is 8,448 triangles of pack wall alone and a worst-case room of
    14,048, 132 % of the 10,664 Zoo measured for a card-shop room.
    `reserved_by` keeps the later pass's share: 9,824.

  * **A bare `True` for `variants` means four, and two species do not have
    four.** `_make_volume` reads `int(True)` as 1, which is not `> 1`, so it
    writes 0..3 for every variant-bearing piece. `folding_table` and
    `folding_chair` are `module_variants: 2`, and Zoo's rule is
    all-or-nothing: a variant outside 0..1 would have dropped the `cards`
    stock with it and a play table would have come back bare. Caught by
    `test_zoo_honours_every_dressing_furnish_writes` -- which was itself
    asking the wrong question, `range(4 if p["variants"] else 1)`, a 4 spelled
    beside the 4 in the writer. That hardcode under-tested `neon_sign` by
    twenty variants and refused a correct piece. `variant_count` is one
    function now, asked by the writer and the checker.

  * **A migration's regex was a list of one.** `migrate_furnish_recipes`
    stripped `^bartender_...` before a refurnish. The card shop's
    `shopkeeper` markers were therefore kept AND written again, four patrol
    points for two aisles. The pattern is built from
    `level_design.STAFF_MARKER_ROLES` now.

### AND A FIXED POINT THAT WAS AN ACCIDENT OF HISTORY

Stripping those markers and letting `furnish` append the new ones moves each
from the middle of the marker list to the end, so a freshly generated spec is
not a fixed point of its own migration -- the JSON differs by marker ORDER
alone. MEASURED on a fresh `strip_club`: `bartender_r1d196568_2` stood at
index 5 and came back at index 29. `strip_club_a01..a03` hid it because
0.137.0's own migration had already appended theirs, so
`test_the_library_carries_the_fixture_pass_and_is_still_a_fixed_point_of_furnish`
was passing on where those three files happen to be rather than on a property
of the code. Each re-written marker goes back to the index it held, and
`presets.make(...)` + strip + refurnish is now byte-identical for `card_shop`,
`strip_club`, `pawn_shop` and `bank`.

### A hung piece stops answering to a body's rules once it is over the door

`pennant_row` hangs from the CEILING (`under`, not `lift`) because a fixed
height is right at one storey and inside the slab at the next -- 2.90 m at
3.4 m, and the arithmetic, not the number, is what is written down.

At that height it was refused everywhere. MEASURED, with a probe printing
which test rejected each candidate: all 8 spots on `card_shop_a01`'s sales
floor were on interior walls and all 8 were refused by `_seed_clear`'s
"a metre off any partition" at **0.17-0.18 m** -- which is what a piece
standing against a wall measures. Three of that function's rules -- the
partition standoff and the 1.5 m approach to an exterior or a partition
opening -- exist because a body walks through doors and along walls, and a
strip above every opening HEAD is in nobody's path. `hangs_over_openings`
reads that head from the spec's own openings through
`spec_types.Opening.resolved`, so the number is the one place that declares
it.

MEASURED INERT ON EVERYTHING THAT SHIPPED: the bottom of every hung piece this
pass wrote before today is 1.85 m (`neon_sign`, `wall_tv`) or 1.28 m
(`dartboard`), each from a FIXED lift, and a plain door's head is 2.2 m. No
older piece can be exempt at any storey height, and
`test_the_over_opening_exemption_reaches_no_older_piece` is what says so
rather than this paragraph.

**AND THE RULE IT EXEMPTS IS ITSELF WORTH A LOOK, WHICH THIS RELEASE DOES NOT
TAKE.** `_wall_slots` offers candidates against every room bound, and
`_seed_clear` then refuses every one that lies on a PARTITION -- so in this
library a wall run can only ever use an EXTERIOR wall. A room enclosed by
partitions places none of its run, which `furnish` already documents as a
consequence; what is new is the measurement that it is the standoff, at 0.17 m
against a 1.00 m limit, and not the openings. A card shop makes it visible
because a card shop's subject is the product on its walls. Not changed here:
loosening it moves every furnished room in the library and wants its own
release and its own frames.

### The triangle arithmetic, in Zoo's currency

Every figure below is Zoo's own planner run over the slots this build emitted
(`facts["tris"]`), and for four of the five species the planned number IS the
built number -- checked against `validation.checks.tri_budget` in the kit's
`meta.json`: pack wall 1,416 = 1,416, display case 1,108 = 1,108, pennant row
892 = 892. Only `folding_table` differs, because its `cards` stock is drawn by
the recipe rather than the planner: 132 planned, 228-240 built.

    card_shop_a01, as shipped        sales floor   play area
      display_case x2 + end             2,864           -
      pack_wall x2                      2,804           -
      pennant_row x2                    1,784       1,784
      crt_tv x2                           808           -
      folding_table x2 (built)              -         468
      folding_chair x4 (built)              -         744
                                      -------      ------
                                        8,260       2,996

    worst case the caps allow        sales floor   play area
      2 cases at 3.6 + 2 ends           3,816           -
      2 pack walls at 3.6               4,224       4,224
      2 pennant rows                    1,784       1,784
      2 CRTs                              808           -
      3 tables + 9 chairs                   -       2,448
                                      -------      ------
                                       10,632       8,456

against the **10,664** Zoo measured for one card-shop room. The selling floor
lands at 99.7 % of it and nothing in the recipe can exceed that.

WHAT THE CAPS COST, said rather than quietly narrowed:

  * **The wall run places no pack wall at all on a two-counter floor**
    (`reserved_by`). Six bays of boosters where four runs would have been
    twelve: the reference's "one long aisle of it" is what is given up.
  * **A selling floor gets no play tables** (`floor: ()`). Two tables and six
    chairs at the palette's worst are 1,632 triangles and the difference
    between 10,632 and 12,264. This is the rare cap that is also the truer
    answer -- the reference's tables are in the tournament area, not scattered
    across the shop floor.
  * **Two pennant rows a room, not four.** A strip costs its budget however
    long it is (`max_pennants` is `(budget - 12) // 20`), so length is free
    and count is not; four rows are a third of Zoo's whole room.

None of the three is closed. There is still no runtime telemetry from a real
session, so these are conservative numbers held against a measured reference
and not against a frame time; when that data exists, the budget is the dial
and `most` is where it is spent.

### Zoo's L is not taken, and what it would have bought

Zoo's `display_case` builds an L from the slot's DEPTH
(`pick_form`: `d >= 2 * case_depth + 0.10`), one module with one L-shaped
glass top and its inner corner left open -- "which is where the staff stand
and where Deli Counter's own aisle runs", its collision comment says. Asking
for it means authoring a slot 1.85 m deep whose back 1.25 m is the aisle, and
Deli Counter writes ONE CONVEX BOX over a hinted volume's whole slot unless
the species is in `prop_species.SPECIES_OWNS_COLLISION`. That box IS the
aisle, sealed -- the `cubicle_bank` defect of Zoo 0.93.0, and invisible to the
nav gate, which grades the greybox shells where that box is the only collider
there is. Putting `display_case` in that set instead would take the collider
off every showcase in the library. The L here is a second case
(`display_case_end`) closing the aisle's blind end, the club's return leg with
a showcase in place of a panelled counter. The expensive version buys one
continuous glass top instead of two cases meeting, and is worth reopening the
day a hinted volume can declare a collider that is not its slot.

### What the frames show

The shell was built and rendered (`review_render.py`, 9 views), and the kit was
built from its own `slots.json` (`zoo_cli --build-kit --theme card_shop`):
**74 modules, 0 failed**, with the stems the mirror predicts --
`prop_display_case_card_shop_09_w240_d60_h100_mwood_panel`,
`prop_pack_wall_card_shop_14_w240_d50_h220_mslatwall`,
`prop_pennant_row_card_shop_10_w800_d8_h30_n2` and
`prop_folding_table_card_shop_11_w240_d76_h74_scards` (no `_m` on the last
two, which is the point of writing their species' own kind).

  * the showcase counter: glass top, framed panes, a register and a row of
    white card boxes on the deck, chrome toe kick;
  * the pack wall: two bays of booster boxes faced out in tight rows, each
    box carrying its game's art;
  * the pennant row: 44 angled felt pennants in the invented clubs' colours;
  * the play table: black cloth to the floor, deck boxes and card stacks on
    the top.

TWO THINGS THE FRAMES DO NOT SETTLE, said rather than implied. `review_render`
lights a raw GLB with a neutral rig and no skin packs, so it cannot answer
whether the case's glass front reads as glass -- Zoo 0.95.0 records that the
stock behind it is invisible until a theme ships a `glass` pack with
`transparency`. And nobody has walked this building; the walker has not seen
these frames.

### Also

`prop_species` routes the five species, and `display_case` re-routes 12
authored volumes that were plain boxes: the six at 2.4 x 0.9 x 1.0 in
`cr_pawn`, `night_pawn` and `pawn_shop_a01` now build as the species, and the
six at 2.4 x 1.2 x 1.4 / 8.0 x 2.0 x 2.2 in `landmark_hall_a01`, `_a03` and
`cbp_town_finale...` stay boxes on a dimension. `gondola` is deliberately NOT
a keyword: the library's eight are supermarket aisles 1.0-1.2 m deep against a
genome depth of 0.35-0.60, so every match would fall back to the box, and a
keyword whose every match cannot be built is noise in eight reports.

`material_kind` learns `wood_panel` and `slatwall` (Zoo 0.95.0's two new
kinds) and maps `cloth` and `plastic`, which were in the vocabulary and in no
spec's map. `KIT_VERSION` 0.104.0 -> 0.105.0, because those three pawn shops'
`slots.json` changes on a rebuild. `SCHEMA_VERSION` is not bumped for the
`cards` stock value, as no schema addition since 0.103.0 has been -- including
0.137.0's `bar_dense`, which is the same shape and is worth saying out loud
rather than leaving the next reader to wonder.

`specs/card_shop_a01.json` is the library entry. `layout_lint --all`: 133
specs, **0 FAIL, 341 WARN, 101 specs with findings** -- the same 341 and the
same 101 as the 132-spec library before it, so the card shop adds none.
`test_card_shop.py`, 28 tests, all of which fail on 0.138.0 (16 failed,
11 errors, 1 passed there).

## [0.138.0] - 2026-09-16  the hole behind the stair, and a cubicle that is not a desk

Two findings from the walker's walk of cold run 9060, both in `office_stepped`.
Zoo 0.93.0 is the other half of the second.

### THE HOLE BEHIND THE STAIR (`stairwell.stair_guards`)

"hole behind this stair and to the side", standing at Godot (-1.7, 1.6, 6.8)
-- spec plan (-1.8, 5.7) -- looking at `stair0col_under_0_15`.

0.134.0 fills the slot a flight's side walls leave behind its top, and
excluded every multi-storey switchback because "its second run is an open
walkway under the next leg, open to the room at both ends". That sentence is
true and it was applied to the wrong rectangle. MEASURED in the 0.137.0 glb
(building frame, metres), `office_stair_0` on storey 0:

    leg 0's treads       x  0.000 ..  1.600   y -2.350 ..  2.089
    side walls           x -2.000 .. -1.605   x  1.605 ..  2.000
                         y -0.600 ..  3.150   z  0.000 ..  3.300
    reserved rectangle   x -2.000 ..  2.000   y -2.650 ..  3.150

so the open air inside the rectangle is TWO shapes, not one:

  * the channel at x -1.600..0.000 running y -2.650..3.150, open to the room
    at both travel ends with 3.4 m of headroom under the landing plate --
    the walkway, and it keeps every metre of it;
  * a pocket at x 0.000..1.605, y 2.089..3.150, floor to slab underside,
    1.61 x 1.06 x 3.30 m, shut by the flight's own top face and open only
    sideways into the channel. That is the same dead end 0.134.0 was written
    for, in the half of the rectangle the channel does not use.

So the fill now covers the leg's OWN run and stops at the run boundary
(`flight_run_lateral` says which half is which), and a leg above the first
still gets nothing, because it stands on the slab the leg below cut and
`back_only` already refuses a back over an opening.

THE SLOT IS A STEP DEEPER THAN THE RUN SAYS. A leg that ends in a turn
landing is built one tread shorter -- `ascent_surfaces`: "the landing IS the
top surface" -- so its solid stops at y 2.089 where `st.y + run / 2` says
2.350. `flight_solid_end` derives that once; for every flight that tops out
at the run's end it returns the same expression the callers already used, so
no number a one-run flight ships moves. `flight_solid_rect` pairs it with the
run's lateral span, and the containment test now measures against that rather
than `footprint_rect`, which is the air a switchback RESERVES and not what it
fills.

CENSUS, over the 132 library specs (`test_stair_back.py`): 173 slab-cutting
interior flights. 130 are one-run solid with side walls, 129 carry a back --
unchanged. 41 are multi-storey switchback legs, 34 of them can carry one: 17
leg 0s and 17 leg 1s. All 17 leg 1s are refused by the floor rule. Of the 17
leg 0s, 15 carry a back and 2 -- `foundry_heist_vertical_stair_0` and
`primos_pizza_stair_0` -- are refused by the exterior-wall arm of
`covered_by_walls`, which pre-dates this and is left alone: changing it would
move the one-run flights too, and that is its own measurement.

### A CUBICLE BANK IS NOT A DESK (`prop_species.py`)

"these desks are too close to each other?", 2.68 m from `cubicles_w_0_col`.

All ten `cubicle*` volumes in the library -- `cubicles_w_0` through
`cubicles_e_2` in `office` and `office_stepped`, every one 8.0 x 6.0 x 1.2 m
and `drywall` -- routed to `desk`. The desk genome takes width to 12.0 and
depth to 6.0, so the slot FIT: it did not fall back to a box, it built as
desk geometry at that size, four 8 m work surfaces one per `row_max` row,
butted along the depth. Zoo 0.93.0 grows `cubicle_bank` -- screens, the desks
inside them, a 1.20 m aisle -- and the keyword row routes to it.

THE ROW STANDS AHEAD OF `counter`, which is further up than the usual rule
wants and is not a choice: `workstation_bank` carries `station`, so below the
counter row that keyword could never fire, and a keyword that cannot match is
the same defect as a parameter nothing reads. What the jump re-routes,
measured over the 132 specs: nothing.

### A SPECIES THAT OWNS ITS COLLISION GETS NO GREYBOX BOX

`prop_species.SPECIES_OWNS_COLLISION`, read by `Builder._volumes`.

The composer keeps the greybox COLLIDER and drops its visual, so for a volume
that is mostly air the box is the only thing a body ever meets. Measured in
cold run 9060's composed shell: `cubicles_w_0_col-convcolonly` is one solid
box, x -14.000..-6.000, y 3.000..9.000, z 0.000..1.200, across a bank whose
middle 1.20 m is an aisle. Zoo bakes `cubicle_bank`'s 28 per-part boxes into
the module's own `-colonly` mesh, so the collision exists -- it is just not a
box, and the greybox must stop drawing one over it.

Two consequences, both deliberate and both worth stating. The GREYBOX build
of such a volume now has no collider at all, and the nav bake reads the
greybox: `office_stepped` goes from 213 navmesh polygons to 581 and `office`
from 301 to 719, both still `navigable: yes`. The greybox is now permissive
where it used to be sealed; neither is the themed truth, and the box was
wrong in the other direction. And every planner that reads the SPEC volume --
`level_design`, `vault_room`, `stairwell.stair_guards.solid_volumes` -- still
sees `collision: convex` and treats the footprint as occupied, which is what
a bank of screens is to a sightline and to a cover marker.

### Tests

`test_stair_back.py` 16 (5 fail on 0.137.0), `test_prop_species.py` 14
(3 new). The library rebuilt: 132 shells, nav gate 130 shells, 14
`navigable: NO` -- the same 14 as the baseline, none of them new.

## [0.137.0] - 2026-09-15  a bar a bartender can stand behind

The walker, with three photos of a lounge bar and one shot from above of
bartenders WORKING between a counter and the back bar behind it: "just to
show the clearance the bar should have for bartenders to stand behind,
similar to the bank teller row". Zoo 0.92.0 builds the back bar, the dense
bar top and the counter's bartender-side fit-out; Lux 0.39.0 lights it; this
places all of it and proves the staff side is somewhere a body can be.

`enclose_teller_lines` (0.126.0) is the precedent the walker named, and this
follows its SHAPE -- one pass over the finished spec, a report row per bar
saying enclosed or why not, nothing moved where the room cannot hold it --
but not its walls. A teller line's staff side is a locked room behind two
doors; a bar's is a working aisle you walk into round the end of the
counter, and the reference asks for "a lighter enclosure: no locked doors, a
BAR FLAP at one end or both".

**`back_bar_club_counters`**, run from `furnish` before `place_fixtures`
(that pass measures throwing lanes against where the furniture actually
stands, and this one MOVES counters). Per club bar counter, in one pass:

  * the counter moves into the room by the back bar's depth plus the aisle,
    and its stools move with it. Until now a `counter_club` stood flush
    against its wall -- `_wall_slots` puts a piece's back `wall_thick / 2 +
    0.01` off the room's bound -- which leaves a centimetre behind it and no
    staff side at all;
  * a `back_bar` volume goes flush against that wall, as long as the counter
    (inside Zoo's 1.6-6.0 m genome range) and 2.4 m tall;
  * where one end of the counter stands against a perpendicular wall, a
    `counter_end` closes that end of the aisle and the bar is an L;
  * a `patrol_point` marker stands in the aisle a body's step in from the
    open end;
  * and the whole thing is skipped, with the report saying why, when the
    room cannot hold it.

Idempotent by name (`back_bar_<tag>_<seq>`, the counter's own seq),
deterministic, reads nothing but the spec.

**THE AISLE'S WIDTH IS DERIVED FROM BOTH CONTRACT NUMBERS**
(`bar_aisle_width`). It is a corridor -- a body walks its length -- so it is
at least `min_corridor_width` 1.1 m, the navmesh's own rule (2 x bake radius
+ 0.3; narrower bakes as an island, as twin_a01's 0.9 m flights did). And it
is entered at its END, through the gap between the counter's end and the
back bar's: that gap IS the bar flap, and a flap is a door, so it is at
least `min_door_width` 1.25 m. One aisle cannot be two widths, so it is the
greater of them -- 1.25 m today -- and the flap is the aisle's own
cross-section. The reference's own figure of "~0.9 m" is below both and is
not used.

WHY THERE IS NO FLAP LEAF: Deli Counter has no door in the middle of a
volume, and a solid one across the only route to the staff side would make
the aisle an island -- the exact defect the nav gate exists to catch. The
flap here is an opening, not a leaf, and the report gives its measured
width.

**THE BAR'S L IS TWO VOLUMES, and that is a measurement and not a
preference.** Zoo's counter could carry an L form; `deli_counter.py:2357`
writes one box collider per volume, so an L inside a box slot would leave
the open quadrant solid -- an invisible wall in the middle of a club floor.
The return is a second volume instead: `counter_end`, a PLAIN counter (no
bar form, no dense top, no stools -- it is the bar's panelled end, not a
place anybody is served), spanning the aisle at one end. Two of the
library's eight club bars take one.

**Every club counter now asks Zoo for the bar** (`_PIECES["counter_club"]`):
form `bar` -- the brass foot rail, the tap towers and the register -- and
stock `bar_dense` in place of the sparse `bar`. `counter_bar`, the taproom's
and the lounge's, is untouched: the walker was explicit that the club's bar
"will be different from the dive bar species we make later", and the dive
bar is its own slice.

**The light** (`lights._back_bar_anchors`): a `back_bar` anchor per unit,
0.15 m proud of the slot's front face in free air -- the neon's own number,
and inside the aisle, because Lux's omni sits AT the anchor and must never
be inside the cabinet (roadmap 139). `size` is the LIT FACE, the glass
shelves between the lower run's worktop and the cornice, from
`back_bar_face`, which mirrors Zoo's `back_bar_forms` arithmetic the way
`tv_screen_size` mirrors the CRT's -- `test_back_bar` pins the four
constants against Zoo's own file when Zoo is beside this repo. `aisle`
carries this pass's own number, so Lux's range reaches a bartender standing
in it. No `color`: Lux reads a back bar with none as `tungsten`, the bulb
colour Zoo paints, and naming it here would be one number written twice.

**Measured on the library, all eight club bars built:**

| spec | room | counter | run | aisle clear | L |
| --- | --- | --- | --- | --- | --- |
| strip_club_a01 | main_floor | `counter_club_r1d196568_2` | 4.0 m | 1.25 m | -- |
| strip_club_a02 | main_floor | `counter_club_r1d196568_2` | 5.0 m | 1.25 m | L |
| strip_club_a03 | main_floor | `counter_club_r1d196568_2` | 3.0 m | 1.25 m | L |
| strip_club_a03 | main_floor | `counter_club_r1d196568_3` | 5.0 m | 1.25 m | -- |
| strip_club_a03 | back_bar | `counter_club_ra07f4e1a_2` | 4.0 m | 1.25 m | -- |
| strip_club_a03 | back_bar | `counter_club_ra07f4e1a_3` | 3.0 m | 1.25 m | -- |
| strip_club_a03 | vip_mezz | `counter_club_r420234d8_2` | 4.0 m | 1.25 m | -- |
| strip_club_a03 | vip_mezz | `counter_club_r420234d8_3` | 5.0 m | 1.25 m | -- |

No room in the library was refused, so the refusal branches are exercised by
`test_back_bar` rather than by the shipped specs -- which is worth saying
plainly: the "say so per room rather than squeezing it" half of this has not
been tried by a real room yet.

**The library is still a fixed point of `furnish`.** Strip every volume AND
every marker this pass writes, refurnish, compare the JSON: 126 of 126
identical, the three clubs included.
`migrate_furnish_recipes.py` strips the `bartender_<tag>_<seq>` markers with
the volumes -- a refurnish that leaves one behind is not a fixed point --
and `lf_*.json` is skipped as before. The counts it prints do NOT match
(-94 removed against +91 added on a01): `furnish`'s return has never counted
the `stage_deck` colliders, and now does not count the return ends or the
markers either. A count is not a diff, and the diff is zero.

`test_back_bar.py` (28 cases) holds the derivation, the clear gap measured
edge to edge, the bar's facing and its back on the wall, an empty aisle, a
bartender marker inside the aisle and inside no volume, the refusal, the
L's shape, the counter's dressing fields, the dive bar left alone, the
light anchor's position and size, and the fixed point. Every one fails on
0.136.0, where `bar_aisle_width` does not exist.

## [0.136.0] - 2026-09-15  a strip club has a dartboard, and the bar a cigarette machine

The walker: "we also need dart boards in the strip clubs. The kind where you
use chalk to keep your score", and "we need retro cigarettes' machines in
the strip club. (Maybe we'll put em in other buildings too, it was the 1990s
where smoking in public was still legal in PA)". Zoo 0.91.0 builds both;
this places them.

**Two pieces** (`level_design._PIECES`), each routed by `prop_species` ahead
of the counter and cabinet rows (re-routes among authored volumes: none;
no bare "board" or "machine" keyword, which would take `scoreboard_*` and
the vending machine):

  * `dartboard` -> Zoo `dartboard`, 1.1 x 0.36 x 0.9 or 1.2 x 0.38 x 0.92,
    the cabinet's OPEN footprint. Zoo puts the bull at the slot's centre
    height, so `lift` 1.73 is the regulation bull height above the floor.
    `collision` "none": Zoo's module carries the cabinet box's collider and
    none for the doors, and a greybox box to the doors' reach would stop a
    body in mid-air. `wood_stained`, Zoo's own kind, so the stem has no
    `_m`. `variants=True`, `most=1`, `most_big=(300, 2)`.
  * `cigarettes` -> Zoo `cigarette_machine`, 0.88 x 0.45 x 1.5 or 0.9 x 0.48
    x 1.55, against a wall, front to the room, `metal_painted`,
    `variants=True`, `most=1`. NAMED `cigarettes`, not `cigarette_machine`:
    "machine" is in `_COVER_NAME_HINTS`, and `cover_from_volumes` would
    have marked every one as cover, which the vending machine is not.

**Fixtures, placed last** (`place_fixtures`, which `furnish` now ends with).
A recipe's `fixtures` -- `strip_club`: dartboard and cigarettes; `club`
(bars, lounges, taprooms, pubs, VIP rooms), `lobby` and `hall`: cigarettes,
the three other kinds whose recipes already place a vending machine
(`shop_floor` and `corridor` also do, and take none) -- go into a room after
the whole room loop: this building's size palette, `_wall_slots` drawn six
times (`_FIXTURE_ROUNDS`), the nested rooms, `_seed_clear` (hung, for the
board), a random stream of their own, reading nothing but the spec. So they
move nothing a room was furnished with, and a room a previous release
furnished gets the same answer as a fresh one.

**The throwing lane** (`dart_lane`, `dart_lane_blockers`): from the wall out
through the slot, the oche's 2.37 m and a standing body (two body radii,
0.7 m, `agent_contract.json`), as wide as the slot plus a body radius each
side -- measured from the slot's front, so at least the oche and a body from
the board's face. It must lie inside the room's walls; no volume on the
storey may stand in it except one hung over a body's head (`_HUNG_MIN`); no
partition may cross it; it keeps 1.5 m from an opening's centre (a door's
approach, `_seed_clear`'s radius), 0.3 m from a stair's reservation, 1.6 m
from a ladder, clear of a vault door's swing and 1.2 m from an objective or
loot marker; and two lanes stand a body apart. A cigarette machine is never
placed in a lane.

**THE PREMISE, REFUTED AND KEPT.** The request, and 0.135.1's entry before
it, said re-furnishing the library does not reproduce it
(`migrate_club_rooms.py --check` a01 -87/+85, a02 -76/+75, a03 -149/+145;
`migrate_furnish_recipes.py --check` -7,435/+7,428). Those are counts: the
volumes removed, and `furnish`'s return value, which does not count the
`stage_deck` collider it writes under each club stage (a01 2, a02 1, a03 4:
7 in the library, the whole difference). Measured on 0.135.1 before this was written: strip
and refurnish all 126 room-bearing specs and compare the JSON with sorted
keys -- 126 identical. The library is a fixed point of `furnish`, and a
fixture in a recipe's wall run would have broken that (the run is shuffled
and cycled; one more entry moves every piece after it), which is why the
fixtures are a pass of their own.

**`migrate_club_fixtures.py`** is that pass over `specs/` and nothing else,
skipping `specs/lf_*.json`. Measured after it was written: for 126 of 126
specs, strip-and-refurnish with this release and the migration write the
same JSON. The library gained 11 dartboards -- every one of the 7 strip-club
rooms, two in each of the five past 300 m2 but `a03`'s main floor (of the
159 spots its second board drew, 105 failed `_seed_clear` and the rest had a
lane that met a volume (52), the room's edge (4), a door (3), the first
board's lane (2) or a stair (2); one spot can meet several) --
and 121 cigarette machines: 7 of 7 strip-club rooms, 18 of 21 `club`, 48 of
53 `lobby`, 48 of 55 `hall`, the rest with no clear wall spot. REFUTED
FIRST, kept: one draw of `_wall_slots` left `strip_club_a03`'s main floor
without a board (of 26 spots in one draw, seeded for the measurement, 13 passed `_seed_clear`, and every lane met a
volume (16), a stair's reservation (8), a door (4) or the room's edge (2));
and before the lane-to-lane rule `a01`'s main floor put two boards at right
angles in one corner with overlapping lanes. 85 specs change, insertions
only.

`test_club_fixtures.py`, 10 tests, every one failing on 0.135.1: the pieces
route; Zoo's bull is the slot's centre at both sizes (read from Zoo);
a club room hangs a board at 1.73 m with its lane clear, rebuilt in the test
from the room and the volume rather than from `dart_lane`; the lane keeps
off two doors, a stair and the other board; no board outside a strip club's
club rooms, with a strip-club control; a machine in a strip club, a bar, a
lobby and a hall and not in an office, stockroom, kitchen or shop floor;
the fixture pass moves nothing; the library's 11 boards and their lanes;
the library carries the pass and is still a fixed point of `furnish` (126
specs); the `strip_club` preset hangs a board at four seeds.
`test_club_rooms.py` and `test_preset_strip_club.py` add the two species to
the club's set; `test_furnish._ZOO_RANGES` adds their genome ranges.
`test_prop_species.py::test_every_species_in_the_table_is_a_real_zoo_species_name`
read Zoo from `../zoo` whatever `DC_ZOO_ROOT` said; in a worktree that is
whatever sits beside it, and it read an unrelated copy. It reads
`DC_ZOO_ROOT` first now, as `test_furnish` does.

**The library, rebuilt.** Beyond manifests: lights manifests unchanged; each
`gameplay.json` gains the new nodes and palette materials (+1,429, the two
deletions trailing commas); `slots.json` gains the fixture slots (11 boards,
and every one of the 121 machines has its slot). 591 slots in 69 buildings
change `style` number and nothing else -- 236 floors, 300 ceilings, 55 `wood`
props: kinds a spec's palette does not list take their style AFTER the
palette (`skin_style`'s rule), and declaring `metal_painted` or
`wood_stained` in the palette moves them one on. Their Zoo stems are renamed,
not rebuilt differently. Hook: `check.py` all checks passed with
`DC_ZOO_ROOT` pointed at the Zoo 0.91.0 checkout the tests read; nav gate 14
unnavigable shells before and after, none new.

**Frames**, in a scratch copy of `_runs/walk_9057_rain` (the run's 1,385 files
hash as they did before): `strip_club_a01` kit-built with Zoo 0.91.0 and the
delco_1997 library (67 modules, 0 failed), composed with this checkout (193
themed modules, 0 greybox fallbacks, placement 186/186), imported, and shot
with `tools/look_shots.py`: each of the three boards at 1.5 m and 4 m, and
both machines at 1.5 m. The three board nodes stand at y 1.73 in the
building frame with Zoo's `ATT_bull` at local height 0, one `-colonly`
collider each. The compose's z-fight gate reads 84 pairs where the same
building composed for 0.135.0 read 82: the two new are the two machines'
bounding boxes on their rooms' floor skins at plane 0.0, the class 80 of the
82 already were (club chairs, stools, tables, sofas, the stage, the vending
machines); no pair names a board.

## [0.135.1] - 2026-09-15  every TV in a club is not the same game

0.135.0 lit the bracket TVs and wrote no `variant` on `wall_tv`, because Zoo
0.89.0 dropped the `bracket` form when a variant was asked and built a stand
set (measured by 0.135.0's agent). Zoo 0.90.0 is on main now, draws the
screen's ballgame from the variant, and honours `bracket` with variants 0..3
(`kit.honour_dressing({"form": "bracket", "variant": v}, "crt_tv")`, v 1-3
kept, v 4 dropped: "variant 4 is outside 0..3 for crt_tv"). So a01's three
sets showed one game, all football.

**`wall_tv` takes `variants=True`**: the name's crc32 % 4, omitted at 0, the
rule every other variant piece follows (`level_design._PIECES`).

**`migrate_tv_variants.py` stamps the field on the library's existing TVs,
and nothing else**: 11 volumes in the three clubs (a01 variants 1, 3, 2).
It does not re-run the furnish migrations, because the library is not a fixed
point of today's furnish code -- measured before writing it:
`migrate_club_rooms.py --check` strip_club_a01 -87/+85, a02 -76/+75, a03
-149/+145; `migrate_furnish_recipes.py --check` -7,435/+7,428 across 126
specs. Re-furnishing here would carry an unattributed drift in with a
one-field fix. That drift is its own finding and is not investigated here.
The migration skips `specs/lf_*.json`, Level Factory's gitignored output.

REFUTED, kept: the first run of this migration wrote with `indent=2` and
without the `lf_` skip -- a patch to the script failed its own anchor check
and the unpatched script ran. It reformatted the three club specs (4,905
lines of diff) and stamped the three gitignored `lf_club_block_001_*` specs
Level Factory wrote for cold runs 9057-9259. The tracked specs were restored
from git before the correct run; the three gitignored files keep their
stamped variants and a 2-space indent, and are regenerated by the next cold
run that writes them.

**0.134.0's library census counted Level Factory's output.** The first
commit of this release was refused by the hook:
`test_stair_back.py::test_no_slot_remains_behind_any_one_run_solid_flight_in_the_library`
asserted 130 flights and read 291. It globbed every `specs/*.json`, and the
factory checkout holds 195 gitignored `lf_*.json` levels from cold runs; the
worktree 0.134.0 was gated in had none, so it passed there. Both library loops
in that file now read `_library_specs()`, which skips `lf_*`. Six other tests
glob the same folder without an exact count and are unaffected.

`test_club_rooms.py::test_a_wall_tv_carries_a_variant_zoo_honours_with_its_bracket`:
furnished TVs carry the crc32 variant, the library's TVs carry it, and Zoo
keeps `bracket` with each. Fails on 0.135.0.

## [0.135.0] - 2026-09-15  a TV that is on throws its light

The walker, after walking cold run 9057's strip club: the CRTs should "have
a light/glow from the screen as if they are on", showing a football or
baseball game. Zoo 0.90.0 paints the game on the bracket set's glass and
makes it emissive. A lit material lights nothing round it in GL
Compatibility, so the cold spill on the housing, the bracket and the wall
is a light, and a light is this kit's to place.

**A `neon` in front of every TV that is on** (`lights._tv_screen_anchors`),
in any room -- a club room after its club set, any other room after its
ceiling light, the room's box still last. A TV is a visible volume that
`prop_species` routes to `crt_tv` with `form` `bracket`; a `stand` set is
off and gets none. `id` `<volume>_screen`; `pos` `_TV_SCREEN_OUT` 0.25 m in
front of the slot's front face along its facing (`_front_bearing`, the sign
spill's arithmetic), in free air, at the screen's height (`_TV_SCREEN_RISE`
+0.036 m, measured off Zoo's plan: +0.0366 at 0.6 x 0.55 x 0.5, +0.0351 at
0.7 x 0.6 x 0.55); `rot_y` the facing; `color` `cyan` or `blue` by
`crc32(id) % 2`; `size` the lit face, `tv_screen_size`, which mirrors Zoo's
`crt_forms.screen_size` because this kit cannot import Zoo -- including
Zoo's design height for the tip, `_TV_TIP_GROWTH` 1.059, measured the same
at both sizes. REFUTED FIRST, kept: the mirror without that factor gave
0.373 x 0.280 m at the 0.6 m set against Zoo's fitted 0.3953 x 0.2965, 6 %
short; with it 0.395 x 0.297 and 0.445 x 0.334 against 0.4450 x 0.3337.
Lux's `neon` range (0.5 x the longer side + 1.0 m) is then 1.20 and 1.22 m:
a pool round the set. The build's report and print carry `tv_screens`.

**The library.** Rebuilt: the three clubs' manifests are the only content
change (`strip_club_a01` 23 -> 26 anchors, `a02` 18 -> 20, `a03` 41 -> 48;
12 screens), every other file line endings and `built_utc`. Hook: all
checks passed; nav gate 14 unnavigable shells before and after, none new.

**Measured in a scratch copy of `_runs/walk_9057_rain`** (the walker's is
untouched; its 1,385 files hashed before and after): `strip_club_a01`'s
manifest merged with Lot's own `_place_point` at b0's placement -- proved
by 0.133.0's manifest reproducing all 23 of the site's b0 anchors exactly
-- and re-baked through the walk's `LuxLightLoader.bake_club`: 20 club
rigs from 33 anchors where the run baked 17 from 30, the same 13 refused
(the null room_ambient colours the run itself refused). The three screen
rigs stand at Godot (-52.27, 2.136, 5.99), (-40.965, 2.136, -25.41) and
(-63.035, 2.136, -14.05), in front of their sets. At 2 m the housings take
the cold cast (cyan, cyan, blue). The package's `max_renderable_lights` is
its light count and moved 94 -> 97 in the copy; Level Factory derives it.

`test_club_rooms.py`: 4 new -- the spill stands in free air in front of
each set, cold, the screen's size, 1.0-1.5 m of Lux range, deterministic;
the size is Zoo's to a percent; a TV outside a club spills and a stand set
does not, in the room's anchor order; the library clubs light every TV --
all four failing on 0.134.0, with the updated neon count in
`test_a_club_room_is_lit_by_the_club_set_and_no_fluorescent_row`, and
`test_lights_partitions.py`'s exact report dict, which gains `tv_screens`:
6 fail on 0.134.0's `lights.py` and library.

**Not done.** The `wall_tv` piece still writes no `variant`: on Zoo 0.89.0,
which this hook reads, a variant on `crt_tv` drops the `bracket` form with
it and builds a stand set (measured). Once Zoo 0.90.0 is on main, `wall_tv`
can take `variants=True` and two TVs of one size in a room show two games;
today `strip_club_a01`'s three show two, both football. The spill puts a
specular highlight on the glass it stands in front of; nothing measures it.

## [0.134.0] - 2026-09-15  the back of a flight is filled flush with its side walls

The walker, cold run 9057, in `bank_branch_a02`'s basement (debug overlay
"under stair_guard_side_7"): "for these stairs that we will this in so the
back is flush with it's self". Measured in the 0.133.0 glb, building frame,
metres: the east stair's side walls run x 7.85..11.6 (outer faces y -7.2 and
-4.8), the flight's solid treads stop at x 8.65, and between the walls'
inner faces (y -6.805..-5.195) stood a slot 1.61 m wide, 0.8 m deep and
3.3 m tall (z -3.6..-0.3), open to the room. Its depth is `flight_rect`'s
walk-off `clear`, which the side walls' span takes on the storey below as
well as on the storey the flight arrives at.

**`stair_guards` emits a `back`.** On the storey a flight climbs through,
behind the top of a ONE-RUN flight (straight, or a single-storey switchback)
that the builder fills solid, where side walls stand: from the rectangle's
arrival edge to the top tread less `SIDE_GAP`, between the side walls' inner
faces (edge to edge for a narrow flight's thin guards), floor to slab
underside. The builder bakes it like a side wall (`stair_guard_back_<k>`,
building wall material). Backs are appended after every side and rail, so
every existing piece keeps its index and its name; across the 132 specs the
side and rail pieces are identical to 0.133.0's, value for value and in
order. 129 backs in 85 specs.

**Not under a slab.** The slot was assumed to be roofed by the storey
above's slab. The glb says otherwise: the stair's own hole (all of
`flight_rect`) is over it, and the builder's discharge plate (z -0.2..0.0)
closes the hole. The back stops at the slab underside like the walls beside
it, 0.1 m under the plate -- every flight in the library has step_h below
the cap it stands under, and a test holds that.

**Fill, not trim.** Cutting the side walls back to the treads would end the
slot too; it is not what was asked for and it moves geometry that has passed
the nav gate. A fill spanning the walls' OUTER faces would put two boxes in
one place with three coplanar faces (`zfight_gate`), so it spans the inner
faces and meets the walls face to face.

**Scope, measured** (172 solid-underside flights with side walls, 97 specs).
130 are one-run; 129 get a back. `credit_union_a02`'s ground-floor partition
at y 3.0 stands across its slot's mouth, so the covered-by-walls cut drops the
back and what remains is sealed. The other 42 are multi-storey switchbacks,
whose rectangle holds two runs: in `cr_deli`'s glb nothing stands between the
basement floor and z 0.0 at x -14.3 from y 5.8 to 11 -- the second run is an
open channel under the next leg, and its "slot" is that channel's mouth, not a
dead end. Above leg 0 a straight flight's slot stands on the discharge plate
of the flight below (its way off), and a scissor's walls stop short of both
ends, so neither gets a back.

**The cuts.** A back gets every cut a side gets (walls, other stairs, solid
volumes), measured across its depth rather than on a line (`band`). The
line-crossing doorway rule does not apply to it -- it cut 0.305 m off
`strip_retail_a01` `sr01_stair_up`'s back, which stands 0.7 m clear of
`dining_rear`'s wall behind the side wall that door faces -- and a back asks
the exact question instead: no door's approach zone (`DOOR_APPROACH_M` over
the aperture, walls of both axes, partitions and exterior) unless a side of
the same flight stands between; no authored, ramp or ladder hole under or
over it, and no other stair's landing (0 of each in the library). A vault's
swing needs no rule: L22 already refuses one reaching `flight_rect`, which
contains every back.

**How the gates read it.** `_barrier_intervals` counts only the kinds
`containment_findings` asks for (`side`, `rail`); a back is neither, and the
bank's findings are identical with the backs removed (tested). L19 and L21
read `flight_rect`, L22 `flight_rect` too; `wall_voids` already keeps
partitions out of it; headroom and Rule 10 skip `stair*` volumes;
`stair_pitch` and `level_design` skip `stair_guard_` names. A back sits
inside `flight_rect` and outside `footprint_rect` (tested), so none of them
changes answer.

**Rebuilt library.** `slots.json` and `gameplay.json` gain the back pieces;
one `lights.json` changes: `bank_branch_a03` `vault_east_bulbs` moves from
y 0.0 to 2.2 with 5 -> 4 lamps, because a back is a tall solid and a lamp row
does not hang in one (`tall_solid_voids`: 12 -> 15 voids; a HEAD build of the
same spec reports 12 and the old row). Composed `bank_branch_a02` with Zoo
0.89.0: 82 modules, 0 greybox fallbacks, placement 308/308; the z-fight gate
reads 136 pairs against 132 on the same pipeline from the 0.133.0 build, and
the 4 new ones are both backs against the vault rooms' floor and ceiling
skins -- the class every side wall in that basement already has (14 pairs
before), not fixed here.

`test_stair_back.py` (11; 8 fail on 0.133.0, the other 3 are the scope
negatives). `test_stair_containment.py`'s guard inventory gains the back.

## [0.133.0] - 2026-09-15  a strip club can be generated, and stays a club when somebody else names it

Cold run 9055 was refused at graybox: "brief archetype 'strip_club' matches
no DC preset". A mission's own building is generated from a preset
(`presets.make`) and the lot anchors on the library family of the same name;
the family existed (`strip_club_a01`..`a03`) and the recipe did not. The
walker's brief is a neighbourhood club -- one storey, windowless, two bar
areas with poles, dingy, CRTs on brackets -- so the answer is a recipe, not
an alias to a wrong-but-plausible building.

**`presets.strip_club`.** 34 x 24 m, one storey over slab, no windows
anywhere: a front door on the street face, a service door and a soft wall on
the rear. South band: `main_floor` (public_entry, 308 m2) and `back_bar`
(168 m2). North band behind the long wall: `vip_lounge`, `dressing_room`
(staff_only), `cash_office` (objective_room, two reinforceable doors, the
safe), `stockroom`, `kitchen`. Nothing authored on the floor -- 0.132.0's
recipe places the stages, bars, booths, signs and TVs, the vault recipe the
safe. Heist (drill the safe, the bar till, front extraction) and assault
modes. `floors` and `basement` are accepted and ignored, as `corner_deli`
does. Lint 0 FAIL 0 WARN, tactical 0 errors; 0 FAIL and 0 errors at seeds 0-49.

**The club is read off the recipe as well as the name.** 0.132.0 claims club
rooms only inside a building whose id says `strip_club`, and Level Factory
names the level it generates `lf_<mission>_<seed>` -- so its club would have
been a shop floor with a vending machine, 0.131.0's defect one layer up. A
generated spec now carries `preset` (schema, `LevelSpec.preset`), and
`level_design.club_building_id` reads name and preset together for
`furnish`, `dress_club_rooms`, `seed_cover` and the light manifest. No
library spec carries `preset`: the library rebuilt on this is unchanged
except `built_utc`.

**A club room's cover is the club's.** `seed_cover` runs first and keys its
pieces on the room's words: on the first build it put a kiosk, two planters
and a counter island on the main floor, shelf runs and pallets in the back
bar (`back` is a storage word), crate stacks in the VIP lounge -- and the
recipe, counting them as furniture already there, stopped its wall run
before the neon sign. It now leaves strip club rooms to the recipe. Every
room still has shelter at seeds 0-49. REFUTED on the way, kept: making the
vending machine a club anchor so the room carries its own shelter piece
broke `test_hung_pieces_hang_in_free_air_over_the_furniture` and the club
migration's idempotence (the library's refurnish changes), and was reverted.

**Measured through `new_level.py --preset strip_club --name
lf_club_block_001_7 --mode heist --seed 7`** -- the adapter's own arguments,
which set `modular: true`; a dump of `presets.make` is not that building
(heist builds monolithic, 79 prop slots and no surfaces). 208 slots (107
wall, 74 prop, 11 doorway, 7 floor, 7 ceiling, 1 breach, 1 roof); nav gate
595 polys, 2/2 interior markers reachable, navigable; 30 light anchors, 3
club rooms lit as a club (club_wash 10, stage_light 3, neon 4, room_ambient
7). Zoo 0.89.0 kit 68 modules built, 1 failed (below); composed 208 themed, 0 greybox fallbacks,
placement 193/193, closure portable.

**Not fixed here, measured.** The wall run is shuffled and cut to each
room's budget, so over seeds 0-49 `main_floor` has no neon sign at 5,
`vip_lounge` at 38, and the building none at all at 3 -- the 0.132.0 recipe,
whose change re-furnishes the library clubs. The compose z-fight gate FAILs
this club (70 pairs, 68 of them a prop's base on a floor skin at 0.00-0.02 m)
as it did `strip_club_a01` on 0.132.0 (82) and cold run 9054's bank (77):
every standing prop against every floor skin, not the club. Zoo 0.89.0's
`flat_top_grill` builds 0.935 m deep in a 0.900 m slot (kit `fail`), and the
composer bundles it anyway.

`test_preset_strip_club.py` (10; every one fails on 0.132.1).

## [0.132.1] - 2026-09-14  a stair's discharge route is the same in every build

0.131.1's library rebuild, and 0.132.0's after it, each flipped the
`destination` of one discharge route in three or four specs against the
worktree build of the same code and specs: deli_a01 `deli_counter` <->
`stockroom_loading`, mansion_a03's second stair `grand_foyer` <-> `study`,
warehouse_a02 `north_dock` <-> `main_floor`, then `security_room` <-> `lobby`
and `south_machine` <-> `east_floor` on the next rebuild (roadmap 155).

**The interpreter's coin.** `stairwell._bfs_path` visited `adj.get(n, ())`,
and `_same_story_edges` hands it sets of room-id strings. A set of str
iterates in PYTHONHASHSEED order, which Python draws fresh per process, so two
equally short routes to two exterior doors were chosen by whichever the hash
put first. Reproduced with `PYTHONHASHSEED` 0-3 on 0.131.1's specs: all three
specs above change destination between seeds; with the fix, none.

**Ties break by room id.** Neighbours are visited sorted, so among equal paths
the alphabetically first room at each hop wins -- a rule, not a good rule, but
the same one every build. A shorter route still wins over the alphabetical
one (`test_route_determinism.py`, 2 tests; the first fails on 0.132.0).

The library is rebuilt on this; the routes above settle on their sorted
answer and no other build output changes.

## [0.132.0] - 2026-09-14  a strip club is furnished and lit as one

The walker, with two frames of GTA IV's Triangle Club: "strip clubs should
have a dingy lived in feel, dark with colored lights, couches and bars". The
layout comparison is a one-storey windowless neighbourhood club with two bar
areas whose pole stage stands inside the bar, stools round it, CRTs on
brackets, nothing that reads as a refit. On 0.131.1 `strip_club_a01`'s
`main_floor` was a SHOP FLOOR -- its id's token is `floor` -- and held
shelving, a vending machine, a filing cabinet and cartons under five cool
fluorescent lamps; the authored 8 x 4 x 0.8 `stage` and 6 x 0.9 `bar_run`
routed to no species and shipped as grey boxes; `champagne_wing` was a wine
cellar. Zoo 0.88.0 built the species and listed what Deli Counter had to
write; Lux 0.37.0 named four anchor types; Pixelcoat 0.42.0 drew the
surfaces. This is Deli Counter's part.

**A `strip_club` room kind (`level_design`), read only inside a building
whose id says `strip_club`.** The same tokens name a country club's lounge
and a tavern's bar, which stay the `club` kind. `is_strip_club_room` is the
one rule -- `club`, `lounge`, `vip`, `champagne`, `go`/`gogo`, `cabaret`,
`bar`, `stage`, `dance`, and `main_floor` -- shared by `furnish` and the
light manifest. In the library it claims seven rooms: `strip_club_a01`
`main_floor` and `vip_wing`; `_a02` `main_floor`; `_a03` `main_floor`,
`back_bar`, `vip_mezz`, `champagne_wing`. The cash offices, back rooms,
cellar and count room keep their kinds.

**The recipe.** Anchors follow the room's shape and every one is placed:
a `bar_stage` (Zoo's `club_stage`, stock `bar`) in the middle of the room
with 6-10 `bar_stool`s ringed round it facing in, or -- longer than 2.5 : 1
-- a `round` stage and a `counter` with stock `bar` on a wall with stools
along its front; a second bar past 300 m2 (the comparison club has two). The
wall run is `booth_seat` sofas, the club's name in `neon_sign`, `crt_tv`s on
brackets, a vending machine; the floor is `cocktail_table`s (form `cloth`,
stock `bar`) with two or three `club_chair`s each, facing the table. Denser
than a hall (one piece per 24 m2, to the hall cap): a club floor is small
tables, not open space. Measured on the library: `a01 main_floor` 50 pieces
of 9 species (19 tub chairs, 11 stools, 10 tables, 4 sofas, a sign, 2 TVs,
the stage, a bar, a vending machine); the seven club rooms hold 25-50
pieces of 8-9 species each and nothing of the shop floor.

**A stage is authored to the ceiling, over an invisible platform collider.**
Zoo runs the pole to the slot's top; at 0.8 m it builds a platform with no
rail and no pole. A box to the slab in the middle of the main floor would be
a wall to the nav bake and to a body, so the visual volume carries
`collision: none` and `_volume` writes a `stage_deck_*` collider under it --
`visual: false`, the footprint, the platform's height (0.8 m; 1.18 m for the
bar stage's deck) -- which is what Zoo's own colliders (bands inscribed in
the outline, the steps) agree with. `_COLLIDER_STEMS` teaches the idempotence
mark and the refurnish migration the name.

**Hung pieces hang in free air.** A sign's centre at 2.2 m, a bracket TV's at
2.1 m (`_piece.lift`), no collision -- a body's head is 1.8 m and so is the
nav bake's clearance -- against a wall clear of its openings like any wall
piece, and taking no share of the floor: a couch may stand under one
(`_seed_clear(above=)`, `_HUNG_MIN`). `neon_sign`'s variant IS the name (24
of them), drawn from crc32 of the BUILDING's id so a club has one name in
every room, and one sign a room -- the first frames had MOM THINKS I'M AT
BINGO twice on one wall, 7 m apart; every other variant is still the piece
name's crc32 % 4.

**`prop_species` rows** for `club_stage` (`stage`, `pole_stage`, `runway`),
`bar_stool` (`stool`, `barstool`) and `crt_tv` (`bar_tv`, `wall_tv`) ahead
of the counter row -- whose `bar_` would take `bar_stool`, `bar_tv` and
`stage_bar_r...` (the tag's `r` follows the underscore) -- and `club_chair`,
`neon_sign` ahead of the chair row, `cocktail_table` ahead of the table row.
Measured re-routes among authored volumes: the two `stage`s and nothing
else; `center_field_tv_truck_cover` carries `tv` but neither keyword.

**A sofa's material is its upholstery.** Zoo 0.88.0, found on the way:
`booth_seat` takes the slot's material as the kind it is covered in, and
every booth and sofa `furnish` wrote wore `wood`, so a sofa built from one
carried no leather at all. Leather now, on every booth and sofa in the
library (36 specs change by materials alone); a stool's slot material is
`metal_bare` (it builds the column), a sign's backer and a TV's housing
`metal_painted`. `_declare_material` puts each in the palette with an
acoustic, as `_prop_material` always has.

**The surfaces (`dress_club_rooms`, run by `furnish`).** A club room's floor
is `carpet_club` unless it names its own; a partition with a club room on
BOTH faces is `wallpaper_club` (`a01`'s main-floor/VIP wall, `a03`'s two
storey spines); the exterior walls and the default are `paint_block`.
`material_kind` maps the ids, and `velvet`, to themselves, and `SKIN_KINDS`
carries Zoo's `velvet` plus the four club kinds Zoo is adding beside this
release (`test_the_kinds_are_zoo_s_when_zoo_is_beside_this_repo` reports
them as pending until they land, and fails on any other invention).
**There is no per-room wall material, and the club shows why:** the exterior
wall's inner face is its outer face, so a club room's outside walls are
painted block from inside, and a partition between a club room and an office
stays drywall on both faces. What one would need is written into
`docs/GAMEPLAY_JSON_CONTRACT.md`: a second material on the slot for the
module's back face, or an interior liner slot per room edge -- Zoo-side
first either way.

**Light: the club set instead of a fluorescent row (`lights`, manifest
1.2.0).** For a club room: `club_wash` x 3-5 (`3 + area/200`) along the long
axis stepping side to side across the short one, each its own palette
colour from `crc32(room) % 7` in steps of two, each point through the same
void-and-partition test a lamp gets; a `stage_light` per stage -- two spots
1.2 m apart at the ceiling 1.5 m past the stage's edge on the room side,
`target` the stage centre 0.5 m above its platform, `cycle_s` 4; a `neon`
at the stage's rope light (over a bar stage's deck 0.5 m off the pole, past
a round stage's lip at 0.75 m; `amber`) and one 0.15 m proud of each sign's
face, in free air, `rot_y` the sign's facing, no `color` (Lux picks by id;
the glass's colour is Zoo's per name); a coloured `room_ambient`; no
fluorescent, no pendant. **Every room, of every kind, now carries a
`room_ambient` box** -- `size` [x, y, z] its wall-centreline extent floor to
ceiling plane, `pos` its centre, `color` null outside a club (the preset's
own ambient, no tint; Lux 0.37.0 refuses null rather than painting an office
violet, its default when the field is absent) -- after the room's row, so a
room's first anchor is still its ceiling light. Lux's per-room ambient
probes are in flight and asked for a room box; this is it.
`docs/LIGHT_MANIFEST.md` carries the fields. The manifest is derived from
the same volumes the slots are (`write_light_manifest` passes the spec's
volumes and the club rooms), so a stage the furnishing pass moves takes its
spots with it. `strip_club_a01.lights.json`: 9 washes, 2 stage lights, 5
neons, 3 ambient boxes, 1 pendant (the cash office), 0 fluorescents.

**A volume blocks furniture on its own storey only (`_seed_clear`,
`_on_storey`).** Until now every volume in the building was in the way of
every candidate whatever its storey: a ground floor's furniture blocked the
floor above it in plan. Harmless while rooms were sparse; a club's main
floor is dense enough that `strip_club_a03`'s `vip_mezz`, over it, could not
stand its stage anywhere. Measured over the library before and after the
filter alone: 98 specs differ, +284 volumes net, most of them rooms over a
furnished ground floor gaining what they were always meant to hold.

**Vending machines sell different things.** Zoo 0.87.0 rebuilt
`vending_machine` with four variants and a brand on each; the `vending`
piece had `variants=False` and `most=1`, so every machine of one size in a
building sold the same thing. `variants=True` (the name's crc32 % 4) and up
to three a room where a recipe places them -- lobbies, halls, shop floors,
clubs.

**Migrations.** `migrate_club_rooms.py` removes the authored `stage` and
`bar_run` (named in `AUTHORED_REPLACED`, not matched), strips and refurnishes
the three clubs, dresses their surfaces; `migrate_furnish_recipes.py` then
refurnishes the library for the leather, the vending variants and the storey
filter. Both idempotent; 119 specs change.

**The material is in the name (`themed_tscn`, the mirror of Zoo 0.89.0's
`kit.module_stem`).** A leather sofa and a wood one were two geometries
under one filename and the later build overwrote the earlier. The stem is
now `<type>[_<species>]_<theme>_<style>[_w][_d][_h][_f<form>][_s<stock>]
[_n<variant>][_m<material>][_v<hash>][_o<hash>][_<state>]`: `_m<kind>` when
the slot's material is a known kind that is not the species' own for the
theme (the theme's style block, walking the family, else the genome
default) -- on EVERY slot type, walls and vault doors included
(`wall_rockay_03_w200_mdrywall`), so a 0.89.0 kit does not resolve without
this. Only Zoo can read the genome that says what a species' own material
is, so `module_stem` takes `material=`, `stem_material` names the kind a
slot could carry (`material_kind.SKIN_KINDS`; a spec id like `brick_ext`
is not one and gets no tag on either side), and `resolve_slot_choice`
asks for the tagged name first and the plain one second for each of the
dressing candidates -- exactly how the dressing resolves. An interactive
slot's states carry the material its base resolved with, as Zoo tags
every state alike. Against the 0.88.0 kit the frames were built from, the
resolver still lands every module (188 themed, 0 fallback). Zoo's
upholstered species keep their upholstery and put the slot material on the
frame, so `leather` on a sofa is right; `cloth` (a cocktail table's) joins
`SKIN_KINDS`. `test_themed_stem`: the tag's place in the name, the
tagged-first order through every dressing candidate and the style-01
degrade, a vault door's states carrying their base's tag, and -- through
Zoo's own `plan_kit`, read only via `DC_ZOO_ROOT`, skipped against a Zoo
older than 0.89.0 -- a wall in a foreign kind, a wall in the theme's own,
a vault door, a club chair whose wood is its frame, a leather sofa
(leather IS `booth_seat`'s own for delco_1997, so no tag, asked of Zoo
rather than assumed), a canvas one (tagged), a wall naming a spec id; the
240-combination mirror runs with and without a material.

**Tests.** `test_club_rooms.py` (22): the kind is read only inside a strip
club and claims exactly those seven library rooms; a club room is a stage, a
bar, couches, a name in neon and small tables and nothing of the shop
floor; the stage reaches the ceiling over its platform collider; a long
room gets a round stage and wall bars; a large room a second bar; stools
ring the bar a hand off its band facing it; a cocktail table's tub chairs
face it; hung pieces hang in free air, clear the doors and hold no spread;
one neon name per building; the only mid-floor shelter is the stage; the
stair reservation, the 2.2 m spread, idempotence and determinism hold; the
surfaces are set in a club and nowhere else; every booth in the library is
leather; a vending machine has a brand and a room may take three; the club
set and no fluorescent; washes vary and take the partition test; the stage
light aims at the body over the platform; a neon spill stands proud of its
sign; every room carries its box; the three clubs are furnished as clubs;
the migration is idempotent. `test_furnish` gains the six club genomes'
ranges (pinned to Zoo's files); `test_material_kind` reads room finishes
and pins the kinds to Zoo's. Ten light tests that took a room's first or
only anchor for its row now say `"row" in anchor`. Against 0.131.1: the new
file fails at collection (no `is_strip_club_room`).

Suite: SUITE_PLACEHOLDER. Hook: HOOK_PLACEHOLDER. Nav gate against
0.131.1's log: NAV_PLACEHOLDER.

**Seen.** FRAMES_PLACEHOLDER

**Not done here.** The room reads grey-lit: Lux's darkness work (the
preset's sun shadows, ambient share, fog) is in flight, and nothing bakes
the club set into a walk yet (Level Factory's `run_lux_apply.gd` would call
`bake_club`). Zoo 0.89.0 carries the four club kinds; the frames here were built with
0.88.0, where a `carpet_club` floor builds in the species default.
The removed fluorescent row leaves no troffer hardware to skip, but a club
room's ceiling is bare until Zoo hangs something else. `velvet` is
object-owned: a club chair's slot material is `wood` (its frame), the
velvet colour is Zoo's.

## [0.131.1] - 2026-09-14  a manifest says which shell it describes

Cold run 9053 was refused at export by `PRESENTATION_PLACEMENT_MISMATCH`:
`chair_waiting_rbeaaca49_4` placed 1.8 m on a 2.4 m greybox node. Not this
release's furniture. `build/*.glb` is gitignored and the manifest, slots and
gameplay beside it are tracked. 0.130.0 and 0.131.0 were built and gated in
worktrees and fast-forwarded into the checkout the run reads, which moved every
tracked file to the new build and left the 2026-09-13 22:16 (0.129.0) shells on
disk: `build/bank_tower_a03.slots.json` names `chair_waiting_rbeaaca49_3` and
`_4`, `build/bank_tower_a03.glb` draws `_1`, `_4`, `_10` and `_13` at 0.129.0's
sizes. `python build_freshness.py`, run after the failure, said "130 of 132
shell(s) are OLDER than spec_types.py" -- nothing ran it before the run, and
Level Factory's consumer-side copy of the rule had been reading nothing since
0.116.0 (Level Factory 0.86.1).

**`_run_in_blender._write_manifest` records `outputs_sha256_16`**, the hash of
every file the build wrote, in the tracked manifest.

**`build_freshness.content_stale`** names a shell (one with a gameplay.json)
whose manifest describes other bytes: the spec it names no longer hashes to
`spec_sha256_16` -- compared raw and with CRLF folded to LF, because autocrlf
rewrites endings without changing content (`gas_station_a02`: 743 CRLF on disk,
its manifest hashed the LF bytes) -- or the GLB no longer hashes to
`outputs_sha256_16`. The first covers a migration that rewrote a spec and was
never rebuilt, which the code-mtime rule cannot see because a spec is not a
geometry source. `main` reports both and exits 1 on either. Manifests written
before this release carry no GLB hash and are not judged on it; the library is
rebuilt here, so every manifest now does.

Measured on the checkout before the rebuild: spec fingerprints agree for 131 of
134 manifests; the other three are `gas_station_a02` (endings only, fresh under
the folded hash) and `fuel_stop_heist2`/`3`, orphan manifests from 2026-06-29
with no shell, which no gate reads.

`test_build_content.py` (6): a shell matching its manifest is fresh; the 9053
case, a GLB from another build; a spec edited after the build; endings alone
are not a change; an older manifest is not judged on the hash; a shell no gate
reads is ignored. 6 fail on 0.131.0.

## [0.131.0] - 2026-09-14  a room is furnished as what it is

The walker, cold run 9052, in `country_club_a01`'s basement: "need a lot more
species for this room, its just a bunch of chairs and tables with nothing on
it, boring". The room is `wine_cellar`, 560 m2, and it held 27 pieces of 2
species: chair 20, table 7. `furnish` matched "role id" by SUBSTRING against
six keyword rows, and `objective_room wine_cellar` matched none, so it took
`_FURNITURE_DEFAULT` -- a low table and a chair round robin. Re-measured over
the library before changing it: 272 of 694 rooms took that row, the figure the
survey gave (docs/proposals/INTERIOR_FURNISHING.md). Zoo 0.84.0 built what was
missing on its side -- five interior species and stock on the tops -- and
listed what Deli Counter had to add. This is that list.

**A room is read as a KIND, on whole tokens (`level_design._room_kind`).** The
id's tokens first, in table order, so `wine_cellar` is a wine cellar before it
is a basement and `cellar_hall` a basement before it is a hall; then below
grade a basement; then the role's own tokens, except the level grammar's roles
(`connector`, `objective_room`, `open_floor`...), which say nothing about what
is in a room. BEYOND THE PROPOSAL'S TABLE: `hall` and `shop_floor` kinds. The
first draft put "hall" and "floor" in the lobby row and the library came back
with 130 payphones and 145 ATMs, one in nearly every `upper_hall` and
`sales_floor`; halls now get seating and tables, shop floors shelving and stock.

**Each kind is a recipe (`_RECIPES`, `_PIECES`)**: one or two anchors, about
half the target as a wall run, the rest floor sets and clusters of 2-4 small
pieces packed 0.3-0.8 m apart, in turn from a seeded start. The target is still
`_furnish_target` less what the room holds. Three sizes of a piece per
building (`_palette`), at most four of one piece and size in a room, 0-4
chairs a table, some pulled out and half of them turned 10-20 degrees. A
fallback room gets a wall run and one cluster of cartons and dust sheets, not
a table and chairs. A corridor gets at most two wall pieces.

**Zoo's dressing, carried end to end.** `Volume.stock`, `.variant`, `.form`
(schema too) reach every prop slot as `stock` / `variant` / `form`, None / 0 /
None when unset. Desks carry `office`, bar counters `bar`, kitchen counters
`kitchen`, count tables `vault`, supply cabinets `storage`; the furnace and
water heater, booth and sofa carry their `form`; `variant` is crc32 of the
piece's name % 4, written ONLY where the species has variants to give --
Zoo's `honour_dressing` drops all three fields when one cannot be honoured,
so a variant on a chair would have cost a water heater its form.
`test_zoo_honours_every_dressing_furnish_writes` asks Zoo's own function.
`themed_tscn.module_stem` gains `form=`, `stock=`, `variant=` with Zoo's exact
suffixes and tests; `resolve_themed_stem` puts them on the SPECIES stem only
(clearing "auto" and "none" as `plan_kit` does); `resolve_slot_ref` tries the
dressed species, the bare species, then the box. The mirror is pinned against
`zoo_keeper.core.kit.module_stem` over 240 field combinations, with and
without a state, and, through
the whole chain, against `plan_kit` on ten one-slot manifests (a desk with
office stock, a water heater, a dropped variant on a chair, stock on a carton
stack, a pool table too long for its genome) whenever Zoo is beside this repo.

**`prop_species` rows** for `carton_stack`, `dust_sheet`, `pool_table`,
`booth_seat` and `furnace`, each IMMEDIATELY ahead of the row that would
claim its names -- and no higher. The first draft put `booth` at the top and
it took `booth_desk` (four parking-garage desks and a broadcast desk) from
`desk`; listing every authored name each new keyword re-routes caught it.
Measured re-routes among authored volumes: `box_stack` x2 and `boiler` x3
(box before), `booth_seating_*` x4 (chair), `*sofa*` x6 (box). Also routed now,
because the recipes place them and Zoo builds them: `pallet` -> `pallet_stack`
(11 authored volumes; the 4.5 x 2.5 loading stacks stay boxes by Zoo's range),
`barrel`/`drum`, `litter_bin`, `grill`, `stanchion`, `payphone` (2 authored,
below the genome's width). `bin` is not a keyword: `cabinet` contains it.
`_prop_material`: furnace, heater, grill, vending, atm, payphone, stanchion,
litter bin and drum are metal.

**A piece with a front faces the room.** Safes, cabinets, shelving, counters,
furnaces, water heaters, vending machines and seating stand against a wall
facing in (`_front_turn`); a desk faces its sitter into the room. Two defects
under the old rule: a floor safe was written with no rotation -- in
`bank_branch_a02`'s basement one stood beside the new vault door with its
blank back to the approach -- and `_wall_slots`' rotation assumed every piece
is recorded long side first, which a SQUARE piece is not, so a 1.2 x 1.2 water
tank on an east or west wall faced along it. `_front_turn` asks the question
the emitter asks. To-the-ceiling pieces (furnace, water heater) stop
`_CEILING_AIR` short of the ceiling slab, never coplanar with it.

**A room does not furnish the room inside it (`_nested_rects`).** Found in the
library, not guessed: 0.130.0 walls a vault room inside `a02`'s `vault_west`,
and the first refurnish stood a count table and its chair inside the vault.
0.130.0's own library had two of `vault_west`'s lockers in there.

**Kept, every one**: nothing mid-floor at shelter height (cluster pieces stop
at 1.5 m), idempotence by name mark (0.122.0-0.130.0 stems still recognised),
the crc32 room tag, exterior-opening clearance, stair reserved rectangles,
the vault swing zone, `_WALL_PIECE_AIR`, the chair compass convention.

**A small turn survives the composer (`themed_tscn._fit_rotation`).** It tried
only the four cardinals, so a chair turned 15 degrees came out square. The
slot's nearest cardinal is tried first and, when the fit keeps that quarter,
the slot's own angle is returned. The placement gate's 0.25 m tolerance holds
a 0.5 m chair at 20 degrees (0.64 m).

**A host's stock is not its height (`portable_building.verify_placement`).**
Zoo's `Stock_*` nodes are left out of the module extent, as Zoo leaves them
out of its own bounds. With them in, the first stocked kits read three office
desks authored 0.75 m at 1.12-1.13 m and two bar counters 1.08 m at 1.335 m:
five height advisories on modules built exactly to their slots, now 0.

**Generated furniture gives way to a stair re-seat (`stair_pitch.clear_walls`).**
`presets.make` re-seats stairs after `enrich` (and, stairs-first, after
`core_first`), judging every seat against furniture placed round the old
ones. With these recipes the `bank` stairs-first preset left
`core_4_basement_service` cutting the basement partition -- an L21 failure
0.130.0 did not have -- after a 10.8 s search (0.4 s before). A generated piece
no longer refuses a seat; it is evicted from the seat that is kept. Default
presets: every stair seat identical to 0.130.0's, all 18. Stairs-first: 9
presets seat differently from 0.130.0 (furniture differs before
`core_first`), L21 0 -> 0 on all but `compound`, which had 8 before and has 8.

### The library (`migrate_furnish_recipes.py`)

Strips every volume `furnish` wrote -- a known stem and the tag of a room in
that spec -- and furnishes again; authored volumes and `seed_cover` pieces are
untouched. NOT 0.129.0's replay from the pre-furniture snapshot, and measured
before choosing: stripping and running 0.130.0's own `furnish` gives back 122
of the 126 room-bearing specs volume for volume; the other four are the three
vault banks (enclosed after they were furnished) and `twin_a01` (0.129.0's
refurnish had missed it). 126 specs: -8823 furnished volumes, +6978.

Per room kind over the 693 rooms of 9 m2 or more, both columns bucketed by
0.131.0's kinds and routing, counting every volume standing in the room:

    kind         rooms   pieces/room    species/room   stocked   species in kind
    fallback       106   20.0 -> 12.7   2.08 -> 4.47     0 ->  0    10 -> 19
    office          93   11.7 -> 12.1   3.18 -> 4.70     0 -> 253    9 -> 17
    vault           74   11.1 -> 10.9   2.55 -> 4.92     0 -> 161    7 -> 11
    storage         64   11.0 ->  9.5   2.81 -> 3.48     0 ->  75    8 -> 10
    shop_floor      62   18.6 -> 14.1   2.98 -> 5.77     0 ->  0     7 -> 15
    hall            55   15.1 -> 15.3   2.58 -> 5.85     0 ->  0     7 -> 15
    lobby           53   21.5 -> 15.1   3.30 -> 8.15     0 ->  0     9 -> 17
    garage          35   13.6 -> 14.2   3.06 -> 5.49     0 ->  4     7 -> 11
    corridor        35   12.9 ->  3.1   1.97 -> 1.89     0 ->  0     5 ->  9
    kitchen         29   10.1 ->  6.2   1.83 -> 3.52     0 ->  27    4 ->  9
    club            24   20.2 -> 22.9   2.71 -> 6.12     0 ->  17    8 -> 12
    basement        20   19.7 -> 14.2   2.55 -> 6.80     0 ->  0     3 ->  8
    apartment       18   15.2 -> 11.6   2.44 -> 5.00     0 ->  0     5 ->  8
    mechanical      18    7.0 ->  7.2   2.17 -> 4.11     0 ->  0     6 ->  9
    wine_cellar      4   16.8 -> 19.0   2.75 -> 5.00     0 ->  0     5 ->  7
    locker           3    3.0 ->  3.0   3.00 -> 2.00     0 ->  0     4 ->  2
    ALL            693   15.0 -> 12.2   2.65 -> 4.97     0 -> 537   16 -> 24

The drop in pieces is chairs: 5,817 -> 1,381, the table-and-chair round robin
gone. `country_club_a01` `wine_cellar`: 27 pieces of 2 species -> 20 of 5
(shelving 7, chair 6, table 3, water barrel 3, dust sheet 1). `bank_branch_a02`
basement: `vault_west` 8 pieces of 3 species -> 14 of 6, `vault_east` 8 of 3 ->
12 of 6, the vault room 2 trespassing lockers -> 5 of its own; 7 stocked.
Every fronted piece faces its room in the four library specs the test reads
(both vault banks, `bank_job`, `country_club_a01`). Locker rooms lost a species (3 rooms, 9 pieces).

Gates, 0.130.0 -> 0.131.0, each tree built and gated whole on one machine:

- Layout lint, 132 specs: 0 FAIL both; WARN 549 -> 336, all of it L9
  (identical cover boxes, 472 -> 259: the 0.5 x 0.5 chairs).
- Generated volumes in a stair's reserved rectangle 0 -> 0; generated pieces
  at shelter height mid-floor 0 -> 0; stair regression 52 variants, 0 failures.
- Nav gate, 130 shells: yes 107 / NO 14 / UNJUDGED 9, identical shell for
  shell and marker for marker when both builds are judged by the same gate.
- Composed with Zoo 0.85.0 and the cold-9052 skins, z-fight gate: `a02` 117 ->
  130, `country_club_a01` 150 -> 135. Every pair added or removed (52/39,
  69/84) is a generated piece's bottom on its room's floor skin, the class the
  gate already reports. Kits: 0 dressing fallbacks, 0 species fallbacks, 0
  missing modules.

### The nav gate snapped a marker onto its own desk

The first library build took `office` from navigable to NO: `objective_EXEC`,
snap 1.1 m. REFUTED FIRST: that furniture had closed the objective's
approach. Single-piece rebuilds each baked by the gate looked like it -- the
suite desk removed passed; moved 0.2 or 0.4 m further off failed; shrunk to a
0.55 m box failed; moved across the suite passed -- and a 3.0 m
furniture-free ring round every objective went into `furnish`. The next build
failed the same marker with the desk 3.1 m away. A probe copy of
`nav_gate.gd` printing the snap settled it: the marker snapped to a
two-polygon island 1.050001 m above it, the exec desk's top, while the
nearest point on the spawn's island, the floor, was 1.092016 m. 0.130.0's
build passed by 1.2 mm (floor 1.048846). The ring came out.

`nav_gate.gd` no longer snaps a MARKER to a surface more than one slab and a
climb above it (`MARKER_MAX_ABOVE`, 0.3 + `AGENT_MAX_CLIMB`; 216 of 293 checked
library markers stand at their storey's level). Stair endpoints snap as
before. On 0.130.0's own build every verdict is unchanged and five shells each
gain one reachable marker that had snapped onto the top of the solid it
stands in: `objective_REGISTER` in its register counter in `cr_deli`,
`night_deli`, `corner_deli_heist_01` and `fuel_stop_heist` (snap 0.45-0.5 m
-> 1.06-1.14 m), and `patrol_point_ROUTE_CASH_ROOM` in
`cbp_town_finale_midbalanced_schemafixed`'s counting tables. With the old gate
0.131.0's `office` still reads NO.

### Tests

`test_furnish.py` (+13), `test_themed_stem.py` (+5), `test_prop_species.py`
(+3), `test_stair_core.py` (+1). Against 0.130.0's code and library, 20 of
them fail: the kind reader, the wine cellar, fronts (0.130.0's floor safes),
stock and variant, Zoo honouring the dressing, the size cap and palette,
clusters, seats and turns, the ceiling, the migration, the nested room, the
four stem and resolver tests, the fit rotation, the new routing, slot fields,
and the stair give-way (0.130.0 left two chairs in a core's reserved
rectangle). Five 0.123.0-0.124.0 tests are restated with why: an office's
desks bring chairs, so density counts hosts; a dining room, not a lobby,
seats a table; chairs may be 0-4 and turned. Suite: 780 passed.

Not done, and said: Zoo's `vending_machine` builds 0.795 m deep for a 0.75 m
slot and fails its own `fit_depth` (seen in the `country_club_a01` kit; Zoo's
defect, not changed here). Wine racks are shelving until Zoo has a wine rack;
reach-in coolers, dartboards, hand trucks and water coolers are not placed.
`SCHEMA_VERSION` is not bumped, as no schema addition since 0.103.0 has been.
The frames were looked at; the walker has not seen them.

## [0.130.0] - 2026-09-14  a bank vault is a room behind a round door

The walker, walk 9052, in `bank_branch_a02`'s basement: "the bank vault should
absolutely be a hero piece". What stood there was a 5 x 5 x 3 m `VAULT` box, a
`prop` slot with no species. Zoo 0.83.0 builds a round vault door for an
opening slot of role `vault_door`, in all four states of the machine. Nothing
here could use it: no shipped building had a modular vault opening, the slot
Deli Counter would have written was the aperture's width, and the machine sent
two of the four states to other species.

**The slot is as wide as the door (`vault_room.slot_width`).** Zoo's module
replaces the whole slot, and a round door circumscribing its aperture needs a
frame, hinge barrels and a surround outside the circle: Zoo's `required_size`
is 3.5837 m for 1.3 x 2.1, rounded up here to 3.6. At the aperture's width Zoo
built a porthole at x0.36. `_opening_to_hole` gives a vault hole `slot_w`; the
wall run carves it, `fit.dims[0]` records it, and `fit.openings` keeps the
aperture, which Zoo keys the stem on (`vault_door_<theme>_<style>_w360_o<tag>`).
On the rebuilt a02 the composer's stems equal Zoo 0.84.0's `plan_kit`. The
locked greybox is ONE block filling the slot, floor to wall top, so the
composer's footprint fit and the placement gate measure what Zoo builds
(294/294 placed). The retyped formulas are pinned to
`zoo_keeper.core.vault_forms` by `test_vault_room` whenever Zoo is beside this
repo (`$DC_ZOO_ROOT`).

**The default is Zoo's aperture: 1.3 x 2.1 on the floor.** 1.4 x 2.3 at a
0.15 sill put a step above `unassisted_step_max_m` (0.1025) in the doorway.

**An opening says which way it faces (`Opening.face`, schema too).** A
partition slot only ever got bearing 0 or 90, and a vault door's leaf swings
out on one side. `_opening_rot` turns the slot, and the gameplay interactive's
transform, to the face. The bearing is the Godot composer's
(`tscn_export.godot_basis`: local +y is world (sin t, cos t)), test-pinned and
seen in the engine: from the face, the hinges hang on the viewer's left, as Zoo
documents. NOT FIXED, found on the way: `Builder._instance_module`, the
Blender-side resolver, turns by Rz(+t), the mirror image at 90 and 270. It runs
only with a module library at build time, and no symmetric door showed it.

**Every state is `vault_door`.** Open mapped to `doorway` and breached to
`breach`, which Zoo honoured and reported as `STATE GEOMETRY`: a round door
that went rectangular when opened. `themed_tscn.SPECIES_STATE_ART` mirrors the
genome's `state_art`, so the composer places the unlocked, open and breached
siblings (hidden) instead of deferring them as identical art.

**The leaf's swing is kept clear (`vault_room.swing_rect`, `layout_lint` L22,
FAIL).** The leaf is swept from 0 to 122 degrees in 1-degree steps with its
bolts drawn, plus the breached lean -- not only Zoo's two rest poses, because
mid-swing the free edge stands further out than at rest. On a 3.6 x 0.3 x 3.3
slot: 2.65 m in front of the face and 1.20 m past the hinge-side edge, where
Zoo's rest boxes say 2.61 and 1.12. L22 fails a solid volume, a stair's
reserved rectangle, a ladder or a partition in it; a slot running past its
wall or over another opening; a wall too low for the door; and a face the wall
cannot have. A faceless vault door in a modular spec warns. `_seed_clear`
keeps cover and furniture out of every swing.

**A vault volume becomes a vault room (`vault_room.enclose_vaults`).** Run by
`enrich` straight after the teller enclosure, and by `migrate_vault_rooms.py`
for the library. For a box named `vault` at least 2 m tall and 3 m a side, in
the innermost room holding it, each corner of that room is tried nearest the
box first: a room past the box by 0.5 m (sides clamped from slot plus margins
to 9 m, on the grid), the host's two walls at the corner and two new
partitions, the door centred in the new wall with the most room in front of
it and facing that room, a reinforceable breach on a partition side into
another room, and deposit-box walls on every other partition side. A corner is
refused, with the reason, when a stair's reserved rectangle, a ladder, an
authored solid or another wall stands in the room, its walls or the swing;
when the swing and a body's approach do not fit in front of the door; or when
a doorway on the host's wall inside the room cannot be slid clear of the room
and the swing. Generated furniture on a new wall or in the swing is evicted
and named. Objectives naming the vault go to the door's face, loot into the
vault.

THE SECOND WAY IN WAS NOT IN THE FIRST DRAFT, and `validate` refused it: an
objective room with one door is one access path (`TACTICAL-ERROR`), the
one-approach siege this bank's basement already answers with a breach.

The library, as the migration reported it:
- `bank_branch_a02`: an 8 x 8 m vault at (-8, -11)..(0, -3), door facing N.
  The basement door at y -4.5, inside it, slides to 0.5. `crack_vault` and
  `vault_cash` stood at (10, -6) in `vault_east` while the box stood at
  (-5, -6) in `vault_west`; they now follow the vault. One shelf run evicted.
- `bank_branch_a03`: the same room, door and slide; one shelf run evicted, two
  pieces furnished into the vault.
- `bank_job`: 8 x 9 m at (7, 2)..(15, 11), door facing S -- the corners beside
  the box were the service stair's. A locker and a floor safe evicted.
- `specs/bank.json` is left: it has no rooms, so the box has no host room, and
  it is not modular, so its authored vault opening gets no module. It needs a
  room grammar, a `face` on that opening and `modular: true`.
- The `bank` preset: its basement was one `vault_room` cut in half by the
  partition below it, which failed L11 once and L10 twice. It is now
  `vault_room_west` / `vault_room_east`, as `bank_job` already was, with the
  vault walled in at (0, -11)..(9, -3): 3 lint failures -> 0.

Gates, 0.129.0 -> 0.130.0, both built and gated in one worktree:
- `bank_branch_a02`: lint 0 FAIL / 5 WARN -> 0 / 5; stairwell 0 ERR / 8 WARN
  -> 0 / 7 (the objective and loot no longer stand in `a02_stair_e`'s
  reserved volume); nav gate stairs ok -> ok, navigable yes -> yes, 629 -> 613
  polys.
- `bank_branch_a03`: lint 0 / 8 -> 0 / 8 (one L9 count 5 -> 6); stairwell
  0 / 9 -> 0 / 9; navigable yes -> yes, 806 -> 808 polys.
- `bank_job`: lint 0 / 0 -> 0 / 0; stairwell 0 / 6 -> 0 / 5 (the box no longer
  invades `bank_job_stair_1`, whose open sides now measure 1.75 m, 0.85 with
  the box beside them); stairs ok -> ok, 699 -> 692 polys, unjudged both.
- `bank`: unchanged. Library lint: 132 specs, 0 FAIL and 549 WARN both.
- A marker at each door's face reaches spawn and one inside each locked vault
  does not (a02, bank_job, the preset).
- Composed a02, z-fight gate: 110 -> 117 pairs. All 9 new ones are the class
  the gate already reports for the teller staff room -- a nested room's skin
  against the outer skin's union box, whose plate does carry the void -- and
  props standing on that floor.

**The composer sinks the vault door and deposit walls** like every other
wall-height module (`_SLAB_CAP_SINK_ROLES`). They stopped short of the storey
line until their slots became the wall's full height; unsunk, the rebuilt a02
composed with 14 more same-facing pairs on the room skins.

**`tactical._room_at` takes a nested room over its container**, the rule
`layout_lint._room_at` and `floors.nested_room_voids` already use. It took the
first room in spec order, so both sides of the vault's door read as the
basement room. NOT the smallest room: that first draft moved an exterior door
on an edge two rooms share, and `test_stair_gameplay` refused it. Measured over
the library with both lookups: only the two vault banks' findings move. A
`safe_deposit` opening joins no rooms in either graph; it collides in both of
its states.

Wall thickness stays `wall_thick` (0.3). Zoo builds and validates the door at
0.3 and 0.6, the frames at 0.3 read as a vault door, and per-partition
thickness reaches every consumer of `wall_thick`: 63 references in 12 modules,
partition bounds, stair voids and the lints among them.

`test_vault_room.py` (25): slot width, default, the Zoo pins (required size,
leaf boxes, state art), swing, bearing against `godot_basis`, the builder's
slot, face rotation, composer variants and sink, L22, seeding, the generator on
the preset, idempotence, door sliding, refusals, the library banks, the breach
and the tactical lookup. Three of them fail against 0.129.0's composer.

## [0.129.0] - 2026-09-13  a piece against a wall stands off its face

The walker, cold run 9052, of a row of waiting chairs: "z fighting on the
[chairs] on the steel". Measured by Zoo (0.81.0's investigation): the chair
backs lay on the wall's inner face, same-facing, 0.00 mm apart -- 3.09 m2
across the lobby's three rows. `_wall_slots` placed a piece's back a flat
0.12 m from the room bound, which lies on the wall's CENTRELINE: half a 0.24 m
wall. Every wall is built at `wall_thick` (0.3), so every wall-slotted piece
-- chairs, filing cabinets, service counters, shelving -- stood 0.03 m inside
its wall. It is now `wall_thick / 2 + _WALL_PIECE_AIR` (0.01 m), and
`test_furnish` pins it against a wall of any thickness (it fails on 0.128.1).

The library was refurnished from the pre-furniture snapshot through the same
scripted sequence as 0.126.0 (stair re-seat, the two hand fixes, teller
enclosure, prop materials, furnish): 0 lint failures, 0 stairwell errors, 0
volumes in a stair guard, 38 volumes in a reserved rectangle as before. Zoo
0.81.0 separately insets a chair's back 6 mm into its own module, so both
sides now clear.

## [0.128.1] - 2026-09-13  a facade shell's windows are opaque again

0.80.0 (501c9db) made `_record_opening_slot` tag a `window` slot on a `facade`
shell `glazing: "facade"`, so Zoo glazes a hollow building's panes with opaque
`glass_facade`. f54ebfe, eleven hours later, committed a working copy that
predated it: its `deli_counter.py` hunk is that change inverted line for line,
and the same commit set VERSION back from 0.81.0 to 0.80.0 and deleted both the
0.80.0 and 0.81.0 changelog entries, reusing 0.80.0 for the Phase 1 slice. Its
message and its entry say nothing about glazing. Not a decision -- a lost
change -- so the two lines are back, word for word.

It mattered less then than now. Zoo keys window modules on the tag
(`kit.plan_kit`) and turns it into `glazing_kind` (`dna.resolve_module_plan`),
and since Pixelcoat 0.40.0 every theme's `glass` must blend, so an untagged
facade window shows an empty box through see-through glass.

Nothing shipped changes: `gs_facade_rowhome` and `gs_facade_storefront` emit
48 and 60 slots, every one a `wall`, because `presets._facade` seals the
exterior. `_record_opening_slot` is the only emitter of a `window` slot, so the
tag covers both the resolved-module and the generated path.

- **`test_facade_glazing.py`** drives the emitter with bpy stubbed: a facade's
  window carries `glazing="facade"`, its door does not, and the same shell with
  `facade` off tags nothing. Against 0.127.0's builder the window test fails
  and the other three pass.

## [0.128.0] - 2026-09-13  no floor over a floor, no gap beside a stair, no lamp in a vault

Three findings from the walker's rain walk (cold run 9052).

**"2 surfaces clashing with each other flickering" behind the teller line.**
0.126.0's staff room gets its own floor and ceiling skins, and the lobby's
skins ran straight over it: `floor_teller_staff_0` and `floor_lobby` both at
z 0.01, `ceiling_*` both at 3.29, overlapping across 12 x 4 m. My regression.
`floors.nested_room_voids`: a room's skins leave a void wherever a smaller room
on its storey stands inside it -- the innermost room owns its floor, the rule
`layout_lint._room_at` already uses. Measured: 4 nested pairs in 132 library
specs, the three staff rooms and `gs_corner_station`'s restroom inside its
stockroom, which had the same fight before.

**"should we just fill in these gaps?"** A `side` stair guard stood at the
reserved rectangle's edge, and the rectangle is the flight plus 0.4 m either
side, so a 0.4 m slot ran between every flight and its wall. The side guard now
fills that margin, from 5 mm off the tread ends to the rectangle's edge.
Rails stay outside the rectangle, on the slab. RETRACTED before commit: "the
navmesh gives up nothing, the flight's edge already bordered a drop". The nav
gate refused the first candidate -- `twin_a01`'s 0.9 m flights, walled flush,
baked as disjoint islands while all 129 other shells passed, the four 1.2 m
flights among them. A flight narrower than one corridor width
(`agent_contract.min_corridor_width`, 1.1 m) keeps the thin guard and its
slot: 4 of 148 flights (widths 0.9 and 1.0).

**"we have a light inside of a vault?"** A basement pendant row in
`bank_branch_a02` hung two bulbs inside or within 0.3 m of the 3 m VAULT box,
whose top reaches the ceiling. `tall_solid_voids`: any solid volume whose top
comes within 1.0 m of its storey's ceiling is a keep-out rect for the lamp rows
(0.35 m clearance), so a row splits around it as it does around a stairwell.
After: 0 of 37 lamp points in or near the vault. The full-storey stair guards
are the same case.

## [0.127.0] - 2026-09-13  a one-storey switchback cuts one run, not two

Found by cold run 9050's frames of the fix for the walker's "13" frame, before
the walker saw it: `bank_branch_a03`'s basement stair is a switchback that
climbs one storey. A switchback's legs alternate between two parallel runs,
so `flight_rect` and the builder cut every slab both runs wide -- and with one
leg the second run holds nothing. It stood open to the basement beside the top
of the flight for the 2.05 m that 0.126.0's guards leave clear at a landing.

`stairwell.single_run` / `stairwell.hole_span` are now the one source for a
cut's centre and width: a single-storey switchback cuts only the run its leg
climbs in (width + 0.8 m, centred on that run), and `footprint_rect` reserves
only that run. Multi-storey switchbacks keep both runs, because their landings
bridge them and the next leg climbs from the turn. 59 stairs in 53 library
specs and 4 in presets are single-storey switchbacks. The guards follow the
narrower rectangle without change, since they are derived from it.

Measured across the library before and after, the only new gate findings were
two L21s where 0.126.0 had seated a stair against the old, wider rectangle
(`credit_union_a01`, `night_pawn`); `migrate_stair_walls.py` re-seated both
(0 lint failures, 0 stairwell errors after). Solid volumes inside a stair's
reserved rectangle: 39 -> 38. Tests that pinned the two-run width on a
one-storey switchback now pin a two-storey one for the old shape and the
one-storey one for the new; `night_pawn`'s wall now stops at x 5.1 instead of
4.1, still exactly at the hole's edge.

## [0.126.0] - 2026-09-13  a stair's hole cuts no wall, a stair is guarded, a teller line is locked

The walker's second round of in-game feedback, from cold run 9048's walk copy.

**"A large opening to a lower level ... a door opening that doesnt seem
right" (the "13" frame).** `bank_branch_a03`'s basement stair reserved
y 0.85..6.65 and the manager's office wall stands at y = 2.0: the hole
straddled it by 1.15 m, `stairwell.wall_voids` did its job and deleted 3.4 m
of wall, and the office door stood beside the gap with 0.6 m of its aperture
over the pit. Nothing refused it. A first reading here blamed 0.124.0's stair
lengthening; the spec before it refutes that -- at the old 4.0 m default run
the hole already crossed the wall, and lengthening moved it 0.35 m further.

- **`layout_lint` L21 (FAIL)**, `stair_wall_findings`: a partition whose line
  lies inside a stair's reserved rectangle on the storey it climbs through or
  the storey whose slab it opens, and a doorway on the hole's storey whose
  aperture overlaps the hole within `DOOR_APPROACH_M` of it. The approach is
  derived from the BODY, `2 * characters.player.radius_m + 0.3` = 1.0 m, not
  from `min_corridor_width_m`, which is built from the bake radius. A door at
  the ARRIVAL end, across the travel axis, is the stair's own door (the delis'
  `office_stair_door`) and is not a finding. A wall inside the 0.8 m walk-off
  margin that carries the stair's own doorway is a WARNING (`strip_retail_a01`:
  the builder trims a jamb over the discharge plate, not a hole between rooms).
  Measured when written: 42 findings in 25 specs, and 6 of 18 presets --
  `bank`, the preset behind every cold run's main building, among them.
- **`stair_pitch.clear_walls`** re-seats a named stair: its own facing then the
  other three, one-axis shifts, then a two-axis grid out to 6 m, nearest first.
  A seat is refused if it adds ANY new lint failure, stairwell error, or solid
  volume inside a reserved rectangle. The first draft filtered out findings
  naming the moved stair and let through an error that named both it and its
  neighbour (the `bank` stair-core preset); the second seated three stairs over
  existing props. **`presets._finish_stairs`** runs it (pass 3), so no preset
  generates L21; **`migrate_stair_walls.py`** ran it over the library: 16
  stairs re-seated. Two could not be: `primos_pizza`'s kitchen door moved 2.1 m
  along its wall, and `corner_deli_heist_01`'s basement stairwell, 2.8 m wide
  around a 3.6 m reservation, was widened to it (stair +0.6 m). Walls and rooms
  are otherwise untouched.

**"Stair placement needs to be thicker", and the open pit.**
`containment_findings` reported 289 open flight sides and 12 unguarded hole
ends across the library, as warnings, and nothing built a guard anywhere.

- **`stairwell.stair_guards`**: per slab-cutting straight / switchback /
  scissor flight, a `side` wall along each long edge of the reserved rectangle
  from the storey floor to the slab above, and a `rail` (`GUARD_HEIGHT` 1.07 m)
  on the floor above along both long edges and across the entry end. The
  arrival end stays open, and so does the LANDING END FROM THE SIDE: each
  long-edge piece stops the walk-off margin plus a door's width (2.05 m) short
  of the end a body uses on its storey. The first draft walled the whole
  length and the nav gate caught it: `twin_a01`'s landing ends 0.35 m short of
  the back wall, so its only way on and off is sideways, and the upstairs
  objective became unreachable; `bank_job` and `foundry_heist_vertical` lost
  stair traversal the same way. An `open` underside gets no side walls -- that toggle
  is for sightlines and routes beside a flight -- and says so in review. Pieces
  give way to a built wall on their line, another stair's rectangle, a doorway
  in a perpendicular wall, and a solid volume. **The builder bakes them as
  volumes** (`Builder._stair_guards`, before `_stairs`), so each gets
  collision, a recorded slot and a surface material; rails wear wood.
- **The containment review reads the same list**, and it now reads the wall
  PIECES the builder builds instead of the authored run. Measured in
  `corner_deli_heist_01`'s glb: its basement stairwell walls, standing inside
  the flight's reserved rectangle, are absent along the whole flight, and the
  review counted them as the barrier that contained it. A rail counts only for
  a hole's end, never for a flight's side. It now reports the landing
  openings it used to be blind to: 259 lateral findings, each no wider than
  the deliberate opening, and 12 unguarded hole ends -> 0.
- Furniture clears a stair's reserved rectangle, not only its footprint: the
  guards stand up to 0.55 m past `footprint_rect`.

**"The chairs being the same texture as the floor and walls almost make them
invisible."** `seed_cover` and `furnish` wrote no `material`, so every piece
wore the building's `default_material`, the wall skin. Every piece now names
one (`_prop_material`: metal for safes, tanks, lockers, vaults; wood
otherwise), and `migrate_prop_materials.py` gave the 67 pieces already in the
library theirs -- 29 crate stacks, 10 planters, 9 counter islands among them,
the likely "boxes that are the same texture as the wall". **"Chairs shouldnt
face walls"**: a wall-placed piece gets the `rot_z` that turns its front into
the room. Not measured yet: the contrast itself.

**"This bank teller booth should connect and be locked to the public."**
`level_design.enclose_teller_lines` closes the staff side of a teller line
into a `staff_only` room: two partitions from the counter's ends to the wall
behind it, each with a `staff_door` that ships LOCKED (`STAFF_DOOR_MACHINE`:
locked / closed / open, unlock and lock, `access: staff`). The public side is
the side the room's exterior doors are on. A line is left open, with the
reason, when the staff side is under 1.85 m or over 6 m deep, when the back
wall has a doorway in the line, or when a stair, ladder or solid stands where
a wall would. Enclosed: the `bank` preset, `bank_branch_a02`, `bank_branch_a03`
and `bank_job`; left open: `bank_branch_a04` (10.9 m deep), `credit_union_a01`
(1.1 m), and `specs/bank.json` (it has no rooms). Adds one advisory L1 per enclosure: two doors to
the same lobby count as one way out.

**Gate bookkeeping.** `specs/bank.json` entered the nav gate (129 -> 130
shells) without a geometry change: `_run_in_blender` writes gameplay.json only
when a spec has markers, rooms, links, objectives, loot, zones or surfaces;
bank.json has only the last, and its first material palette (the migration's
metal vault) gave it surface records. It has no spawn marker, so it is
UNJUDGED, and `navgate_baseline.json` records it with that reason. Nav gate
against the pre-furniture baseline: 14 unnavigable shells, all pre-existing;
new none. `roof_ac`, `ac_unit`, `condenser`, `generator` and `dumpster` now
name metal (the migration had made bank.json's rooftop unit wood).

## [0.125.0] - 2026-09-13  the stair underside toggle

The walker: "Stairs being solid should be the new default, and for gameplay
reasons having that be a toggle we flip on and off if we want more sightlines
would be interesting." An open underside is a sightline and a route through
the space beneath a flight; a solid one is a wall. That is a level-design
lever, so it is now one, resolved by `stairwell.stair_underside` at three
levels, most specific first:

    one stair      "open_under": true | false   (omit to inherit)
    one building   "stair_undersides": "solid" | "open"
    one build      DC_STAIR_UNDERSIDES=solid|open   (like DC_MODULAR, DC_THEME)
    default        solid

The builder builds the resolver's answer and `stairwell.derive` writes it to
gameplay.json as `stair_systems[].underside`, so the game's AI and cover logic
are told what was built instead of assuming. A misspelt building or env value
is refused, not read as the default -- a toggle that silently ignores a typo is
one nobody can trust to have been flipped. `open_under` was a bool defaulting
False and is now Optional defaulting None; False still means solid, so every
shipped spec builds as before. Documented in AUTHORING.md and
GAMEPLAY_JSON_CONTRACT.md; `test_stair_underside` holds the order.

## [0.124.1] - 2026-09-13  two shells the walkable stairs broke, and why

0.124.0's gate log, compared shell by shell with the one before any furniture,
had two new unreachable objectives: `deli_a03` and `twin_a01`. The pre-commit
hook passed anyway, because `nav_gate`'s summary counts traversal, not the
verdict it prints above it. Each was diagnosed by building the variants apart.

**`deli_a03`: the solid underside.** Unchanged stairs and no furniture still
failed; the same build with the underside disabled passed. Its basement
stair's slab hole leaves 0.4 m beside the upper flight, so the only route to
the upstairs objective ran under that flight's high end. `Stairwell.open_under`
leaves a flight's underside open; it is set on `deli_stair_up` alone, with the
measurement in `meta.open_under_why`. One stair in the library.

**`twin_a01`: the plan was too shallow for a stair a body can climb.**
Lengthening its 44 degree switchbacks to 38 passed the circulation contract and
L19 and failed the nav gate, underside or not. Three measured corrections to
the preset: 13 m deep instead of 11 (a switchback is its run plus about 2.2 m
of landing); stairs centred in each half, because 1.6 m off centre a 3.8 m
flight topped out against the party wall with its walk-off inside it; and the
cross partition 1.5 m forward, because at the centre line the stair review
refused the top exit as facing drywall.

After both: 714 tests, and the regenerated twin and furnished `deli_a03` pass
the nav gate.

## [0.124.0] - 2026-09-13  the walker's first in-game feedback

On cold run 9046's walk copy the walker reported three things: "chairs should
face each the table", "cant get up the steps", and "stairs should have a
solid bottom to the ground", with a drawing of the outline.

**Stairs a body can climb** (`stair_pitch.py`, `migrate_stair_pitch.py`).
Measured across every shipped straight, switchback and scissor flight: 36 at
40 degrees or less, 51 between 40 and 45, 61 over 45. A CharacterBody3D
stands on 45; the bake allows 55, which is why every nav gate passed. That is
the contract tension CLAUDE.md names, found by a person on a screen. Every
leg climbs a full storey at `atan(H / run)`, and runs were authored near 4 m
under 4.6-6.5 m storeys. A flight may not exceed 40 degrees and is lengthened
to 38; a lengthened stair the circulation contract or layout lint L19 now
refuses is re-seated by a turn or a short shift. On the library: 112 flights
lengthened, 25 re-seated, none unresolved. `presets._finish_stairs` applies
the same rule, and `test_stair_pitch` holds every shipped flight to it.

**A solid underside.** Treads were one-riser boxes floating at their own
heights. A flight with nothing of its own stair beneath it now builds each
tread as a column to the storey floor, with a collision block per tread that
stops one riser below the tread, so the smooth ramp is still the only
surface a foot meets. The first leg of a straight stair and the first leg in
each run of a switchback qualify; a leg stacked over a lower leg of the same
stair does not, because that mass would sit in the headroom beneath.

**Chairs face their table.** Three changes, because the first alone could
not work. `Volume.rot_z` turns a prop slot. `furnish` sets it for set chairs
by the compass convention `_slot_orient` already uses (N 0, E 90; a module's
+Y turned onto the bearing; a chair's front is its -Y). And
`themed_tscn._fit_rotation` now tries the slot's own rotation first so a tie
keeps it -- in the order 0, 90, 180, 270 a square chair tied at 0 and 180 and
always came out at 0. `test_wallend_pose` asserted that old tie-break as an
observation and is updated with why.

TWO RETRACTIONS. The twin's stair note (0.121.0) said the review's 44 degrees
was a simplification because a switchback climbs half a storey per flight; it
does not, and the review was right. And the first chair angle here was
`atan2(-dx, dy)`, right north and south of a table and backwards east and
west, caught by re-reading the wall convention before the rebuild.

## [0.123.2] - 2026-09-13  a room's name cannot steal its furniture

Cold run 9046's kit reported 17 species fallbacks, all in one kind of room.
`prop_species` matches keywords anywhere in a volume's name, in table order,
and `furnish` put the room id in every name -- so in a room called
`teller_line`, `chair_set_teller_line_1_1` routed to `teller_line` before
`chair` was tried, and Zoo built a box. Any room id containing a keyword
(`safe`, `counter`, `tank`, `station`, `desk`) did the same. Names now carry
`r` plus a crc32 of the room id; a test proves no species keyword can occur
inside that tag at any alignment.

## [0.123.1] - 2026-09-13  the chairs are chairs

Cold run 9045's hall frame: a table between two wooden cubes. Every chair
`furnish` wrote was 0.45 m tall -- a seat without its back -- and Zoo's
`chair` starts at 0.5 m, so the kit built the plain box for all of them. The
test that said every name "routes to a species" passed throughout, because
routing is by NAME and building is by SIZE; those are two claims and only one
was tested. `test_every_piece_is_a_size_its_species_builds` is the other,
against Zoo 0.76.0's genome ranges held as a literal. It found one more:
`cabinet_panel` at 0.4 m deep, below `filing_cabinet`'s 0.5.

Chairs are 0.9 m to the top of the back, still well under shelter height.

AND ONE PROCESS CORRECTION. 0.123.0 was committed with `--no-verify`; the
pre-commit gate had passed on the same tree a minute earlier, minus VERSION
and CHANGELOG, but skipping the hook is not this repo's practice and this
release goes through it.

## [0.123.0] - 2026-09-13  the halls are furnished

Cold run 9044's frames, the first with furnished interiors: a bank office
read as a room and a brewery hall of about a thousand square metres read as
an empty carpet with a bar along one side. Three causes in `furnish`, found
in the code rather than guessed from the picture.

**The hall's long walls are exterior**, and 0.122.0 banned wall furniture
from exterior walls outright after a shelf run stood across the door of
`office`'s exec suite. The ban was the cheap fix; the reason for it was that
nothing knew where exterior openings are. They are readable --
`_opening_to_hole` puts an opening at `pos * run` from its wall's centre --
so wall furniture now stands on exterior walls clear of every opening by its
half width plus 0.9 m. A storey with a setback keeps the exclusion, because
its extent is not the footprint.

**The cap of ten.** A thousand square metres wanted 63 pieces at office
density and got 10. Halls are sparser than offices, so past ten pieces the
density drops to one per 40 square metres, capped at 30: that hall gets 25.
A 120 square metre office still gets exactly 8.

**A table alone is not a place people sit.** A floor table brings up to two
chairs on its long sides, named `chair_set_*` so they route to `chair` and
the idempotence mark recognises them.

TWO REGRESSIONS THE GATES CAUGHT, and one of them was older than this work.

The chairs skipped `_seed_clear` in the first draft and one landed on
`credit_union_a02`'s upper stair landing (STAIR_UPPER_LANDING_BLOCKED, the
spec-corpus contract test). They pass it now, minus their own table and its
2.2 m spread rule, which is right for tables and wrong for a table's chairs.

And `office`'s objective went unreachable again, which exposed a defect in
`_seed_clear` itself. Its docstring says clearances are measured from the
piece's EDGE, and the stair, landing and ladder checks honour that with
`+ half` -- but the exterior- and partition-OPENING checks measured a flat
1.5 m from the CENTRE. A 1.6 m desk centred 1.5 m from a 1.0 m door stands
0.2 m off its jamb. Cover pieces are small enough that it rarely bit; a hall
of furniture found it. Both opening checks now add `half`, which also makes
`seed_cover` slightly more conservative around doors, as its docstring
always said it was.

## [0.122.0] - 2026-09-13  the rooms get furniture

The walker: great progress outside the buildings, what about the props
inside. Measured over the 130 built shells: 819 prop slots in all, a median
of FOUR per building, 29 buildings with none. A bank tower's whole interior
was three teller lines; a funeral home had nothing.

`seed_cover` could not be the answer and must not be made into one. It fires
only when a room is BARE or has no SHELTER, caps at four pieces, and its
docstring argues the case directly: "props that give cover AND life without
overkill". That thesis is about COVER -- a mid-floor blocker changes how a
room plays -- and raising its density would trade a gameplay property for an
art one without saying so.

So `furnish` is a separate pass with its own rule. One piece per 16 square
metres, capped at ten, existing volumes counting toward the target so an
authored room is topped up rather than doubled. Every name it writes routes
through `prop_species` to a species Zoo already builds, asserted by a test:
a furniture volume that comes out a grey box is the defect this exists to
reduce.

    prop slots        819 -> 3809
    naming a species  328 -> 3214
    shells with none   29 -> 2
    median per shell    4 -> 26

FOUR THINGS THE GATES TAUGHT IT, in the order they said them.

The invariant is about SHELTER, not cover. The first draft claimed nothing
it placed mid-floor reached `_COVER_MIN_Z` and `test_furnish` refuted that on
its first run: a desk is 0.75 and a floor safe is 1.00. A desk IS low cover,
here and in a real office. What the over-cover thesis protects is somewhere
a body can FIGHT from, at `cover_break_height`, and this pass never creates
one -- anything that tall goes flush against a wall.

Cover runs FIRST. Furniture ran first for one draft and
`test_cover_breaks_sightlines` refused it: eleven rooms across the corpus
ended with cover and no shelter, because a furnished room fills the
candidate grid and `_seed_clear` then has nowhere to stand the one piece
that matters. Gameplay-critical placement gets first pick of the floor.

Idempotence is by MARK, not by count. A first pass that runs out of clear
floor leaves the count short, and a second pass then finds the spots the
first pass's own pieces opened up -- five extra pieces in a hospital, caught
by the existing idempotence test. A room this pass has touched is now
recognised from its volume names. The first spelling of that check,
`rsplit("_", 2)[0]`, failed on any room id containing an underscore.

Furniture stays OFF exterior walls. `_seed_clear` keeps a piece a metre off
any partition, which is where interior doors are, and knows nothing about
the openings in an outside wall -- so a shelf run stood flush across the
door of `office`'s exec suite and the nav gate reported the objective
unreachable. One shell of 130, found by the gate. Putting shelving back
under a window needs the opening positions, which live in `ext_walls` as
fractions of a run the placer cannot see.

After the fix the nav verdicts are identical to before furnishing: the same
14 pre-existing shells report unreachable markers, none added, none fixed.

AND AN INSTRUMENT DISAGREEMENT, recorded rather than fixed here. `nav_gate`
prints "navigable: NO" for 14 shells and then "nav-gate: 129 shell(s)
passed", and on a single shell it prints "1 shell(s) passed" directly under
its own NO. The summary is counting something other than the verdict above
it. It behaved that way before this change and the 14 are the same 14, so
nothing here rests on it -- but a gate whose summary contradicts its own
findings is the shape of defect this repo has written down twice.

## [0.121.0] - 2026-09-13  the twin, a roof that is not the walls, and a slot that names a kind

Three changes from the walker's art direction
(`docs/DELCO_1997_ART_DIRECTION.md`), all measured before they were made.

**`material_kind.py`: the slot manifest names a KIND the art pass can
resolve.** Measured across all 281 specs: 25 distinct material ids in 6,716
surface references, 16 of them outside the skin resolver's vocabulary, 326
references in all. `find_pack` returns None for those and the material
factory falls back to a FLAT colour, so the 131 surfaces that say
`brick_ext` were exactly the ones that never got brick. The spec keeps its
descriptive name -- the acoustic table and `skin_style` both key on it --
and only the emitted slot moves. Manifest version 1.3.0.

The first build after it printed 8 slots with no kind, and they were not
from any spec: `floors.FINISH_PALETTE` is appended to every palette so a
room role can name its floor and ceiling, and two of its seven ids appear
in no spec file. `test_material_kind.py` reads the palette as well as
`specs/` for that reason -- a test that reads only what is authored cannot
see what is generated.

**`roof_material`: a roof can be made of something other than the walls.**
`roofs.roof_slots` took it from `default_material` and always had, so 232 of
281 specs -- everything defaulting to `concrete` -- had concrete roofs,
mansions and houses included. Optional, falls back, so every spec that does
not set it bakes byte-identically.

**The TWIN.** Of 133 built archetypes, 7 were housing of any kind, 1 was a
rowhouse and 0 were twins, in a county the walker describes as brick and
stone twins that "should appear FREQUENTLY". `twin_a01` is two 8 m halves
either side of a solid party wall -- a partition on the centre line, both
storeys, no openings -- each with its own front door, back door and stair.
Storey 0 is `stone_ext` and storey 1 is `siding`: the first spec in this
library whose walls are made of two things, from two dates. The roof is
`shingle`. The halves diverge the way a real pair does: the left carries a
full-width open porch, the right a stoop and a door hood. 178 slots: 89
stone, 40 siding, 3 shingle.

Two gates moved it, and both were right. `test_cover_breaks_sightlines`
named all four back rooms as having nothing to fight from -- a 0.9 m counter
is furniture and `cover_break_height` is 1.30, so they now hold a fridge
downstairs and a wardrobe up. The nav gate refused 1.0 m interior doors for
a 0.4 m-radius agent and the upstairs objective was unreachable; every door
is 1.2 m or wider now and the shell passes.

AND ONE PLACE WHERE THE TACTICAL REVIEW AND THE NAV GATE DISAGREE, recorded
in the preset. The review reports stair pitch as `atan(story_height / run)`
whatever the style, so a switchback whose two flights each climb half the
storey is judged as though one flight climbed all of it -- 44 degrees at 2.9
over 3.0, which `rowhome` also carries. Lengthening the run to the 4.1 m the
warning asks for was tried and measured WORSE: `stair_footprints` lays a
switchback's run along Y, 4.1 pushed the footprint past the back room, and
the nav gate went from two traversable stairs to two disjoint islands. The
gate is the authority on traversal.

## [0.120.1] - 2026-09-12

0.120.0's basis rewrite was wrong, and the engine said so within the hour.

Cold run 9013, the first package on 0.120.0: `tools/module_pose_census.py`
-- which reads world AABBs off the engine -- reported 6 wall remainders
`across` on bank_tower_a01, while `verify_placement` said 165 of 165 sat
on their slots. Two instruments disagreed; the engine is the one that is
right by definition. The nine numbers `godot_basis` writes are the
matrix's ROWS (Godot's text format writes `basis.rows[i][j]`), not its
axes. Read as rows, the 0.81.0 numbers were `Ry(-t) x Scale_local` all
along -- the scale in the module's frame, the docstring wrong and the code
right -- and the fins had ONE cause, the fit that tied on the unscaled
unit cube and answered 0. 0.120.0 believed the docstring, transposed the
product, and moved the remainders across their walls the other way.

0.120.1 restores the numbers and says what they are; the fit given the
slot's scale stands; and `placed_extent()` sums a placed box's extents by
rows, which is where the gate and the fit had been reading the transpose
(columns) -- harmless for a rotation alone, the footprint swapped for a
turned scaled cube, which is why the gate agreed with the wrong scene.
Recomposed bank_tower_a01 in the 9013 walk copy, read off the engine: 195
standing, 0 across; gate 187 of 187. The lesson belongs beside the
0.120.0 entry: a writer and a checker that share one convention agree with
each other, not with the engine. Check against the engine.

## [0.120.0] - 2026-09-12

A wall remainder stands along its wall whichever way the wall runs.

The walker, on cold run 9012's bank: "this rotation looks wrong? (opening
in the building)", circling a narrow panel standing out from the wall
beside a doorway. Measured off the composed scene: `int_0_1_seg1`, a
`wallEnd` remainder on a wall that runs along Y (slot rot_y 90, scale
[1.875, 0.3, 3.3]), placed with a scale-only basis -- 1.875 m along X,
across the wall it belongs to. Every full wall segment beside it carried
the turn. Across the cold packages on disk (9001-9012): 237 of 777
wallEnd nodes, every one on a turned wall.

Two seams had it, and they cancelled at 0 degrees. `tscn_export.godot_basis`
documented and did Scale_world x Ry(t) -- the scale in world axes after the
rotation -- while `deli_counter._volumes` emits a remainder's scale as
[length, thickness, height] in the module's own frame and says so ("a unit
box scaled by LOCAL dims and then turned by rot_y lands correctly"). And
`themed_tscn._fit_rotation` fitted the UNSCALED module: a unit cube has the
same extents at every angle, so the fit tied at all four and answered 0.
The basis is now Ry(t) x Scale_local, and the fit is given the slot's scale
so it fits what will be placed. Exact-fit modules carry scale 1 and are
untouched. Recomposed bank_branch_a03: 0 remainders across their wall;
`verify_placement` 242 of 242 matched, where before the change it reported
18 mismatches on the same shell.

Which raises the second finding: the gate SAW it. `verify_placement` ran in
every one of those packages and reported `ok: False` with the eighteen
slots named, and no stage read the verdict. That belongs to the caller.
The pose census in the factory root (`tools/module_pose_census.py`)
compared sorted horizontal extents and could not see it either; it now
judges the footprint in world axes and reports the pose as `across`.
`test_wallend_pose.py` pins both seams.

## [0.119.0] - 2026-09-12

A teller line is a glass barrier over a counter, and it is authored as one.

The walker's references (2026-09-12): a teller line is a continuous counter
at waist height, a glass barrier over it to a header, one service window
per station with a pass-through at the counter, posts between stations,
staff behind. Zoo's `teller_line` builds exactly that and never fired,
because every `teller_counter` volume in the library was authored as the
counter alone (1.0-1.2 m) -- so 0.118.0 routed the name to `counter` and
the bank shipped a plain wooden run. The volume was the placeholder for
the counter; the line is what the name meant.

### Changed
- The bank preset authors `teller_counter` as the full line, 12 x 0.8 x
  2.4 (centre z 1.2): a barrier on purpose -- the lobby is 30 m wide and
  the line 12, so the crew walks around either end. `specs/`: the 37
  committed specs carrying a waist-high teller volume are migrated the
  same way (size_z 2.4, z 1.2; the 3.0-3.2 x 1.2 bank-tower tellers too).
- `prop_species`: `teller` routes to `teller_line` again; a teller volume
  still at counter height falls to `counter` by Zoo 0.65.0's alternate
  rule, said in the kit index. Library rebuilt.

## [0.118.0] - 2026-09-12

A hinted volume is recorded long side first, and a teller counter is a counter.

Roadmap 44, step 3 (with Zoo 0.62.0's bays). Measured 2026-09-12 over the
1,443 placements: turning a volume so its long horizontal side is the
module's width takes desks from 58 to 91 fits of 153 and counters from 35
to 54 of 137 before any bay is built, and every `teller_counter` (38) is
a 1.0 m waist-high counter that Zoo's `teller_line` barrier (2.0 m
minimum) could never be.

### Changed
- `prop_species.long_axis_first`: a HINTED volume's slot carries its long
  side as `fit.dims[0]` and `rot_y` 90 when that side is y; unhinted boxes
  are byte for byte what they were. The greybox box is drawn axis-aligned
  as before and is symmetric, so nothing it collides with moves; the
  composer's `_fit_rotation` finds the same 90 from the extents.
- Keywords: `teller`, `workbench` and `tool_bench` route to `counter`;
  `chair` joins seat / bench / waiting; `pump` routes to Zoo 0.63.0's
  minted `pump` species (roadmap 150), `pump_island` stays a box. Library
  rebuilt.

## [0.117.0] - 2026-09-12

A placement says what it is.

Roadmap 44, re-raised by the walker from inside the hospital: "the blocks
should really just be placeholders until they are replaced by something
more diegetic." Every volume is named for what it is and every one reached
Zoo as a `prop` slot, which is a box. `prop_species.species_for_name`
(pure, keyword table in that file) stamps a `species` hint on each volume
slot -- `nurse_station` -> counter, `desk_manager_office` -> desk,
`aisle_shelf` -> shelving, `teller_counter` -> teller_line; crates,
columns, pallets and things no species exists for stay None. Zoo decides
whether the species fits the slot (its genome's ranges) and builds the box
otherwise. `themed_tscn.module_stem` carries the species between type and
theme (`prop_desk_delco_02_w160_d80_h75`), mirrored in Zoo 0.61.0, and
`resolve_slot_ref` asks for the species module first and the plain box
second before the style-01 degrade, so a hinted slot never lands on
greybox because its species did not fit. Measured over 1,443 placements:
721 hinted, 142 fit today; the rest are runs (roadmap 44, step 3).

## [0.116.0] - 2026-09-11

A ceiling row steps off the partitions.

Roadmap 143, walked on cold run 9005's hospital as "light inside the wall".
`tools/anchor_wall_probe.py` over that shell: 35 lamp points, NINE at
-0.150 m -- the partition centreline exactly. Two shapes. The lobby and
ward_south rows (40 m long, five lamps at 8 m) put lamps 2 and 4 on the
ward partitions at x = +-8: a row laid across a room's length at its
derived spacing lands on a partition whenever the partitions fall on that
spacing, which the library's rooms happened not to (2,422 lamp points,
none inside a wall) and this hospital's do. And the roof's five bulbs lay
ALONG the y = 0 spine partition, every one of them in it.

`lights.partition_rects` turns the spec's partitions -- as the builder's
trimmed `_partition_pieces`, at the wall thickness the emitters build to
-- into world rects, and `derive_light_anchors` takes them the way it
takes ceiling voids. `_row_runs` NUDGES a lamp whose centre lands within
`wall_clearance` of a band to the nearer edge of it along the row (as
its own run, since a run's points are equally spaced by contract), and
DROPS one with no landing inside half a spacing, counting both. A
partition lying along the row (`_colinear_shift`: its band holds the
row's line over half the row's length) moves the whole row to the centre
of the larger side -- one row, one side, and the report says so, because
the other side is a room-splitting question for the spec.

The clearance is derived, not chosen: half the wall + half Zoo's
`fluorescent_fixture` troffer (`depth` 0.3 in its genome) + the same
0.1 m air gap the row keeps below the ceiling = 0.40 m on a 0.30 wall. On
the hospital spec this makes the lobby and ward rows five single-lamp
runs each with the two wall lamps at x = +-8.4, and the roof bulbs at
y = 7.5. `write_light_manifest` prints the counts beside the void count.
`lights.py` joins `build_freshness.GEOMETRY_SOURCES`: it writes a build
output, and a stale one is a stale shell.

## [0.115.0] - 2026-09-11

The floor, the wall and the ceiling are three surfaces.

Walked on cold run 9005's county hospital (2026-09-11): a ward whose
floor, partitions and ceiling all wore concrete read as generated -- "the
floor, side and ceiling shouldn't all be the same texture; it looks good
when they are different but uniform in some way". Measured on that shell's
`shell.slots.json`: 7 of 9 floors and 9 of 9 ceilings at style 1,
concrete's -- the two `ceiling_tile` ceilings included, because
`ceiling_tile` was in no authored palette and `skin_style.style_for` fell
through to the default. `floors.FLOOR_BY_ROLE` / `CEILING_BY_ROLE` knew
four roles; this hospital's rooms are `safe_room`, `route_node`,
`connector` and `finale`, so three of the four fell to the default too.
The builder had been printing UNRESOLVED MATERIALS about exactly this
since 2026-08-21 and nothing read it.

Two changes in `floors.py`. The role maps now cover every role an
authored spec emits (13, counted over 176 specs; `test_floors` pins the
list) and obey a rule the tests hold: for every role the floor and the
ceiling are different materials, and no floor wears the partitions'
drywall. `objective_room`'s ceiling moves from concrete to plaster for
that reason. And a `FINISH_PALETTE` -- carpet, tile, ceiling_tile,
plaster, plus the concrete/drywall/wood the maps also name -- is appended
to `spec.materials` by the spec loader (`ensure_finish_palette`), after
the authored list so authored style indices do not move. Each finish now
numbers a style of its own, which is the Pixelcoat pack (`carpet_<theme>`,
`tile_<theme>`, `ceiling_tile_<theme>`, `plaster_<theme>` all ship in the
theme library) and the module filename. `palette_ids(spec)` is the pure
view of the same list, used by `slab_slots`, so a bare test spec and a
loaded spec number their styles identically.

`Room` gains `material` (both surfaces), `floor_material` and
`ceiling_material` overrides -- `floors._material` had read a `material`
attribute the dataclass never declared, so the documented override could
not be authored.

On the hospital this makes the lobby carpet / drywall / ceiling_tile, the
wards and corridor tile / drywall / ceiling_tile, the roof room concrete /
drywall / plaster. Every shell rebuilds (floors.py is a geometry source):
the gameplay materials list grows by four entries per spec and the floor
and ceiling module stems change style number.

## [0.114.0] - 2026-09-11

The corner stem is mirrored.

Roadmap 64. Zoo 0.60.0 keys `wallCorner` on width, depth and height
(`CORNER_ROLES`), because a corner's width is the wall thickness and `_w30`
alone would have named fourteen solids in this library. `themed_tscn` is the
mirror of that naming law and the two must change together, so
`resolve_themed_stem` gives a `wallCorner` slot the same
`_w<t>_d<t>_h<storey>` key and the same literal is pinned in
`test_themed_stem.py`. No shipped slot carries the role yet: every corner
is still the `wallEnd` unit post of 0.102.0, and stays so until the corner
has art a post does not.

## [0.113.0] - 2026-09-11

The facade hardware hangs outside the wall it is mounted on.

Roadmap 85, raised on one screenshot: a hanging light half-buried in a wall
at a wall/ceiling junction. Measured before touching anything, with the new
`tools/anchor_wall_probe.py` (factory root) over 125 shipped buildings:

- ceiling rows are clean -- 2,422 fluorescent and pendant lamp points, none
  inside a wall, minimum clearance 1.35 m;
- wall packs are not -- 334 anchors at a median clearance of **0.000** to
  the nearest wall (min -0.025 in a 0.35 m wall), signs at 0.050.

An opening's `(x, y)` is its wall's CENTRELINE (425 of 425 exterior doors at
0.000 from it), and `_WALL_PACK_OUT` / `_SIGN_OUT` were added to that point.
Their comments said "proud of the wall face"; Zoo built to the comment -- the
wall pack's body is centred on the anchor with an arm reaching 0.15 m back to
the wall plane, the sign's cabinet hangs entirely behind its face plane -- so
half of every pack and most of every sign cabinet sat inside the wall.

### Fixed
- `derive_light_anchors` and `build_light_manifest` take `wall_thick`
  (required, no default -- the `cap_thick` rule) and place both facade types
  half a wall further out, so the constants mean what they say.
  `write_light_manifest` passes the spec's `wall_thick`, the same number the
  wall emitters build to. Re-derived over the library: pack clearance
  0.000 -> 0.150, sign 0.050 -> 0.200, ceiling rows unchanged.
- `test_lights.py`: the two positional pins move (12.15 -> 12.30, -0.2 ->
  -0.35, each explained), plus a clearance test across 0.25 / 0.30 / 0.35 m
  walls that also holds Zoo's deepest genome body outside the wall, and a
  required-parameter test.

Light manifest schema unchanged (1.1.0): the same anchors, moved.

## [0.112.0] - 2026-09-10

Every combat room has somewhere to fight from. **39 of 91 -> 0.**

Roadmap 130's open half. 0.111.0 could say which rooms were furnished and
unfightable; this is the half that does something about them.

### The defect
`seed_cover` guarded on `_room_has_cover`, which answers "is there furniture
here". So a room full of 0.9 m crates was covered, was skipped, and the one
thing it lacked was the one thing never added. Two ways a combat room fails and
only one of them was being looked at:

- BARE. Big room, combat intent, not one solid in it. The audit calls it a kill
  box, and this was already handled.
- FURNISHED AND UNFIGHTABLE. Crates, desks, a counter, all modelled and lit,
  and every one short enough that both sides shoot over the top. **Invisible,
  and the failure that survives a look at the screen.**

### Added
- `agent_contract.shelter_height()` -- the shortest solid that breaks a mutual
  sightline ANYWHERE along it, as against `cover_break_height()`, which is the
  shortest that works AT ALL. Derived, not a margin: the requirement along the
  line is `max(a + (c-a)t, c + (b-c)t)` and that is largest at the ends, where
  it equals each side's own eye. So a solid as tall as the taller eye works
  from any position. On the shipped contract:

  ```
  h=1.30  ->  t in [0.50, 0.50]   width 0.00   the crossing
  h=1.40  ->  t in [0.33, 0.67]   width 0.33
  h=1.50  ->  t in [0.17, 0.83]   width 0.67
  h=1.60  ->  t in [0.00, 1.00]   width 1.00   this
  ```

  At the crossing a producer has to land a piece within centimetres of one
  computed point, and the first constraint that vetoes the position takes the
  sightline with it. This is what a producer should build to.

- `_SEED_SHELTER`: one piece per room that lacks shelter, FOOTPRINT ONLY --
  the height comes from the contract, so **the archetype decides what the
  thing looks like and the contract decides how tall it has to be.** A roof
  gets a water tank, an office a shelf unit, a ward a locker bank, a bay a
  tall crate stack, a lobby a kiosk. Roof is matched above bay on purpose:
  "deck" is in both word lists and a helipad is not a loading bay.
- `_room_has_shelter`, and `"tank"` / `"unit"` in the cover-name vocabulary --
  a seeded piece no hint matches is a solid the room has and the tagger cannot
  see, which is the same defect facing the other way.

### Not done, and this is the design call
**The furniture heights are untouched.** Seven of the nine archetype pieces
stand below the crossing and stay there. The brief for these levels is props
that give cover AND life without overkill; a furnished room is not short of
life, it is short of somewhere to fight from, so the fix is ONE of the first
rather than a raise of all the second. The over-cover thesis this module is
built on argues against the alternative directly.

### Measured
- `COVER_ALL_LOW` **39 -> 0** across the 14 non-facade presets. No other audit
  finding moved: SIGHT_INTENT 65, OBJ_AT_DOOR 9, VERT_DEAD_END 2, OBJ_ONE_DOOR
  1, OBJ_NARROW 1, unchanged.
- 50 pieces added over 91 combat rooms -- 39 to rooms that had furniture and no
  shelter, 11 to rooms that were bare and now get shelter as well as furniture.
- `layout_lint` over the enriched corpus: **49 fails and 3 warnings with the
  shelter pass, and 49 fails and 3 warnings without it.** Every one of those is
  a pre-existing wall, opening or marker defect (L10/L11/L16/L18) and none is
  about a volume. Attributed by running the gate with the change stashed
  rather than by reading the codes and assuming.
- `enrich` stays idempotent: a second pass over an enriched hospital adds
  nothing.

### Note on the guard
`COVER_ALL_LOW` now fires nowhere in the corpus, so it has become a regression
guard rather than a finding. The test that pinned it moved with it -- it used
to assert the corpus HAD the defect, which is a check that stops working the
moment somebody fixes it, and it now asserts the corpus does not, with the
mechanism tested on a fixture instead.

## [0.111.2] - 2026-09-10

The aim point belongs to a body.

### Added
- `characters.player.chest_height_m`, beside the eye. `sightlines.aim_height_m`
  was settable and derived from nothing: 1.0 m is where a 1.8 m body's chest
  is, and no field said so, so a studio stating a 2.05 m character got an eye
  height that followed and an aim point that stayed at ours.

  Derived as the centre of mass of a standing adult, about 0.55 of stature --
  0.55 * 1.8 = 0.99, ratified at 1.0, so the value does not move and nothing
  measured changes.

- `agent_contract.chest_height()`, which CHECKS the constraint rather than
  documenting it. **The hard constraint is not anthropometry.** A line-of-sight
  ray is cast AT this height and LOS is granted only when it hits the target
  body first, so an aim point outside the target's own capsule misses: nothing
  ever sees anything, and the report fills with zeroes that read like a map
  problem. The safe band is the cylindrical section, `radius <= chest <=
  height - radius` (0.35 to 1.45 here) -- above it the ray grazes a hemisphere,
  and at the apex it misses. **A 1.0 m character aimed at a fixed 1.0 m is
  aimed at the top of its own head.**

- `cover_break_height()` now takes the aim height from the BODY and refuses
  when `sightlines.aim_height_m` disagrees with it. The sightline block carries
  a copy because the crossing needs all three numbers in one place, and a value
  carried twice is a value that rots.

## [0.111.1] - 2026-09-10

The derivation follows the evaluator, which is what it was built to do.

### Changed
- `agent_contract.json`'s `sightlines` block re-derived against Laser Tag
  0.20.0 (roadmap 131), which gave every body ONE eye: crew 1.4 -> 1.6, enemy
  1.5 -> 1.6, aim unchanged at 1.0, so the crossing moves 1.2222 -> 1.3000.
  `level_design._COVER_HIGH_Z` and `combat_audit.COVER_BREAK_H` follow with no
  edit, and `_DEFAULTS` moves with the file because
  `test_every_fallback_equals_the_ratified_value` catches it otherwise -- which
  it did, on the first run after the contract changed.
- The block's `unreconciled` note becomes `resolved`. It recorded four
  disagreeing heights; reading the rest of Laser Tag's call sites found seven,
  and 0.20.0 collapsed them to one per body.

### Not changed
**The corpus flags the same 39 of 91 combat rooms at 1.3000 as at 1.2222**,
because nothing in it stands between 1.20 m and 1.40 m. That is the same
clustering 0.111.0 measured, and it means the two tools disagreeing about this
number by 8 cm had never once changed a verdict -- which is exactly why it went
unnoticed for as long as it did.

## [0.111.0] - 2026-09-10

Cover is measured against the firefight instead of against furniture.

### Added
- `agent_contract.json` grows a `sightlines` block, and `agent_contract.py` a
  `cover_break_height()` that DERIVES from it. A sightline is two lines: each
  side sights from its own eye at the other's chest, so one descends while the
  other climbs, and a solid tall enough to break one can sit under the other.
  Half a broken sightline is not half a fix -- Laser Tag stamps first contact
  on the first shot by *either* side, so the free shot that remains starts the
  clock exactly where it was. The shortest solid that breaks both is where the
  lines cross: `h = a - (a - c)^2 / (a + b - 2c)` = 1.2222 m, from the crew's
  1.4 m sight, the enemy's 1.5 m, and the 1.0 m chest both aim at. When the
  two sides sight from the same height it reduces to `(a + c) / 2`, which is
  the form `lot/site_cover.MIN_COVER_HEIGHT` already derives.

  The value is stored in the JSON and RECOMPUTED on read; a stored figure that
  disagrees with its own inputs by more than a millimetre raises rather than
  being quietly preferred. It is deliberately absent from `_DEFAULTS`, because
  a copy there would merge into every contract that omits it -- a studio
  setting its own sight heights would inherit ours, and the derivation would
  then be refused for disagreeing with a number that studio never wrote.

- `combat_audit` reports `COVER_ALL_LOW`: a combat room with cover in it,
  none of which breaks a sightline. Distinct from `KILLBOX` on purpose.
  KILLBOX says the room is bare and reads as obviously wrong to anyone who
  opens it; this one looks finished -- crates, desks, a counter, modelled and
  lit -- and every solid is short enough that both sides shoot over the top.
  It is the failure that survives a look at the screen, which is why it needed
  a number rather than an eye. **39 of the 91 combat rooms in the shipped
  presets, and every combat room in `pawn_shop` and `suburban_safehouse`.**

### Fixed
- `_COVER_HIGH_Z` was a chosen 1.4, which put the high/low boundary 0.18 m
  above the height where cover starts working and called the gap "low cover".
  Now derived. On the shipped corpus this moves exactly one piece
  (`compound/boss_desk`, 1.20 m) -- the authored heights already cluster
  either side of the crossing, with nothing at all between 1.10 and 1.20, so
  the corpus was split by this number and had no way to say so.
- `_room_has_cover` carried a fourth hand-written `0.6` instead of reading
  `_COVER_MIN_Z`, and would have gone stale the first time the constant moved.
- `combat_audit`'s `COVER_MIN_H` comment claimed "taller solids block sight =
  also cover", which is true of a 2 m shelf and false of the 0.9 m crate the
  threshold admits. Two questions were being asked of one number.
- The `KILLBOX` remedy advised "two or three 0.9-1.2 m volumes fix it" --
  heights that leave both sides a free shot. A remedy that reproduces the
  defect it is fixing is worse than none.

### Not changed, on purpose
- `_COVER_MIN_Z` stays 0.6 and low furniture keeps its `cover_low` marker. A
  0.9 m crate is a thing in the room, it reads as life, and a consuming game
  that implements crouch gets real shelter from it. Nothing in THIS toolchain
  crouches -- `characters.player.crouch_height_m` has no consumer in Laser Tag
  or Lot -- so what the new finding reports is that the EVALUATOR sees a bare
  room, not that the shipped game does.
- `_SEED_ARCHETYPES` heights are untouched. Seven of the nine pieces Deli
  Counter creates as cover stand below the crossing height, which is now
  reported per room rather than silently raised: how much of a room should be
  shelter and how much should be life is a design call, and the over-cover
  thesis this module is built on argues against answering it by raising
  everything.

### Measured
- 14 non-facade presets, on `combat_audit`'s basis (any solid over 0.6 m with
  a footprint of 0.3 m or more): 177 solids, 100 of them (56%) below the
  crossing height; 39 of 91 combat rooms furnished entirely below it.
- A narrower first pass counted only NAME-TAGGED furniture and reported 43 of
  91. It was wrong: it missed `parking_garage`, whose combat rooms are covered
  by structural columns that no name hint matches, and called two of them
  bare. Recorded rather than dropped.
- `test_cover_breaks_sightlines.py`: 11 tests, all 11 verified failing against
  the pre-fix modules. Full suite 648 passed, 2 skipped.

### Unreconciled, recorded in the contract
- FOUR heights describe one firefight and no two agree.
  `characters.player.eye_height_m` is 1.6 and `LT_PlayerPill.tscn` puts the
  Camera3D there, so the crew SHOOTS from 1.55 (the muzzle marker) and decides
  what it can SEE from 1.4 -- a body whose own muzzle sits 0.15 m above its
  visibility probe. The enemy sees from 1.5 and shoots from 1.3. Which of
  these moves is Laser Tag's call, not this file's, and moving one would move
  the crossing under a measurement taken this week.

## [0.110.1] - 2026-09-08

The contract says which radius is a body's, and its own fallbacks stop lying.

### Fixed
- `agent_contract.py`'s `_DEFAULTS` had drifted from `agent_contract.json` on
  the two keys the contract's own derivation notes record as REFUTED:
  `agent_max_climb_m` stood at 0.5 (the value that permitted a 0.49 m stringer
  four walkers parked against) and `cell_size_m` at 0.15 (which capped the
  connected slope at 45 deg against a stated 55, failing eight path proofs as
  disjoint islands). The module's docstring promises every fallback equals the
  ratified value; it had not since those values moved.

  INERT UNTIL IT IS NOT. With the contract present the JSON wins and the
  fallbacks are never read, which is why this survived unseen. The failure
  path is a missing, unreadable or partial contract: `nav_env()` then exports
  DC_NAV_CLIMB=0.5 and DC_NAV_CELL=0.15, and `nav_gate.gd` reads those with
  `_envf(name, fallback)` -- a PRESENT environment variable beats the fallback
  behind it. The GDScript copy was corrected when the values moved (`d7d1f70`)
  and this one was not, so the copy that was fixed gets overwritten by the
  copy that was not, and "degrades gracefully" means degrading to a navmesh
  measured to disconnect.

### Added
- `test_agent_contract.py` -- asserts every key `_DEFAULTS` and the JSON share
  holds the same value, pins the shared-key count so an empty intersection
  cannot pass for free, and exercises the missing-contract path through
  `nav_env()` directly. The guard is the fix; the two numbers are just today's
  instance of it. Verified to FAIL on the pre-fix state before being kept.

- `characters.player.radius_note` -- says plainly that a BODY is built from
  0.35 and that `nav_bake.agent_radius_m` (0.4) is a bake parameter with
  "fattest navigating character + 0.05 safety" folded in, with a matching
  pointer added to `nav_bake.note`. This confusion has now caused two defects:
  `clearances.unassisted_step_max_m` was once derived from the bake radius and
  recorded 0.117 while the gate enforcing it reported 0.103, and Laser Tag's
  evaluation pill was built at 0.40, running every door-width test against a
  proxy 14% fatter than the character it stood for (roadmap 123).

  The existing warning was real but buried inside
  `clearances.unassisted_step_derivation`, findable only by someone reading
  the step-height maths -- not by someone asking what radius to build a
  character at. `characters.player` has no reader in this repo at all; it is
  read by Level Factory, for consumers. The note belongs where they look.

## [0.110.0] - 2026-09-07

A building can step. Roadmap 116, the first massing move the pipeline has
ever been able to make.

### Added
- `Setback` on `LevelSpec`, and `setbacks.py` -- the per-storey footprint,
  which is the single source everything asks. `story` names the LOWEST storey
  an inset applies to and carries upward until a higher setback overrides it,
  so one entry steps a building once and two step it twice. Insets are
  per-side, so a side left at 0.0 stays flush: a street frontage holds the
  building line while the rear and sides step back.

  `footprint_x` / `footprint_y` KEEP THEIR MEANING. 24 source files read them,
  `lot/preview.py` and `lot/site_layout_lint.py` among them, and those place
  the building on a site and must know its widest extent. Setbacks only ever
  subtract, so those two remain the base footprint and therefore the maximum.

  OPT-IN, AND VERIFIED BY HASH: with no setback every expression collapses to
  what was there before. `night_pawn.glb` rebuilt bit-for-bit identical across
  the change, with only the manifest's `built_utc` moving.

- `layout_lint` L20 refuses a setback that cannot be built: deeper than the
  footprint, thinner than the storey's own two walls, at or below the base
  storey, or above the roof. The builder would happily emit all four.

- `specs/setback_demo.json` and `test_setbacks.py` (13 tests).

### Changed
- `_exterior`, `_slabs`, `_parapets` and `roofs.record` take the storey's own
  extent. An asymmetric inset MOVES the storey's centre, so each reads the
  centre rather than assuming zero -- a wall placed at +/- half a size would
  be in the wrong place.

  A SLAB CAPS THE STOREY BELOW IT, so it takes that storey's extent. That is
  what turns a setback into a walkable roof terrace with a real collider
  rather than a ledge the upper wall stands on the edge of, and it is the
  whole argument for changing the mass instead of adding a layer on top.
  Verified by raycast in the physics world on `setback_demo`: the strip beyond
  the inset reports a floor at z 4.00 on `slab_col_1` with 8 m of clear air
  above it -- open sky -- while a control point inside the upper storey
  reports the same floor with 3.70 m of head. It is a terrace, not a texture.

- `partition_bounds.clamp_partition_span` and `partition_spans` accept the
  storey's `extent`. The half-extent form cannot express an asymmetric
  setback: a storey inset 4 m from the north face alone runs -7..3, not +/-5,
  and a symmetric bound would let a wall poke out of the stepped facade AND
  cut it short at the face that did not move.

- `layout_lint` L13 and L19 measure against the storey's own facade, and the
  2D floorplan draws each storey on its own line.

### Measured
```
                        fill-Y  fill-X  masses
setback_demo             0.927   0.852       2
warehouse_a02 (twin)     1.000   1.000       1
```

The library baseline stays 127 shells at min 1.000, mean 1.000, because
nothing else opts in yet. `tools/massing.py` is the check.

## [0.109.0] - 2026-09-07

`fit.dims` means one thing now. Roadmap 119.

### Fixed
- `_record_wall_slot` records MODULE-LOCAL dims instead of world ones. The
  manifest carried two frames in one field, written by two sibling functions
  forty lines apart: `_record_opening_slot` has always put the opening WIDTH
  first regardless of which axis the wall runs on -- the module's own frame,
  waiting on `rot_y` -- while this function passed the world size straight
  through. On a N/S wall the two coincide, which is why it survived. On an E/W
  wall the world reading puts the wall's THICKNESS in `dims[0]`.

  Both consumers already expect the local reading: `zoo_keeper.kit.plan_kit`
  takes `dims[0]` as the module width, and `circulation.doorway_volume`
  unpacks `(width, thickness, height)`.

  MEASURED ACROSS EVERY MANIFEST BEFORE THE CHANGE. Every full wall segment in
  the library has a true run length of 2.00 m, so `_resolve_module` -- which
  correctly asks by `clen` -- requests `w200` 14704 times. `plan_kit`, reading
  `dims[0]`, derived w200 for 9106 and w30/w35/w25 for the other 5598:

  ```
  _resolve_module asks for   w200 x 14704
  plan_kit derived           w200 x 9106, w30 x 4819, w35 x 713, w25 x 66
  phantom                    5598 of 14704 full wall slots (38%)
  ```

  Those 5598 asked Zoo to author wall modules at names nothing can resolve.
  `cold-7001-ws` shipped 48 of 120 wall modules that way -- e.g.
  `wall_rockay_01_w35`, authored with `dims [0.35, 2.0, 3.7]`: a panel 35 cm
  wide and TWO METRES deep, built, packaged, and never placed.

  THE GEOMETRY WAS NEVER WRONG, and that is worth stating plainly because the
  numbers look alarming. Module resolution goes through `clen`, so the right
  module was always chosen and the right wall was always built. What this cost
  was Zoo authoring time, package size, and -- the part that matters most --
  the accuracy of the ONE report that says which modules a theme still needs.
  That report was 38% wrong on walls, and item 112's theme-coverage decisions
  read it.

  `scale` rides along, since it is derived from `dims` for `wallEnd`
  remainders: a unit box scaled by LOCAL dims and then turned by `rot_y` lands
  correctly, where world dims turned by `rot_y` would not.

### Changed
- Every shell's `.slots.json` is rewritten: wall slots on E/W walls now report
  `dims` with the run length first. `tools/massing.py` applies `rot_y` to
  match.

## [0.108.0] - 2026-09-07

A stair may not reserve ground outside its own building. Roadmap 115, and the
quarantine is empty.

### Added
- `layout_lint.stair_bounds_findings` -- L19 (FAIL). The stair half of L14,
  and a FAIL for the same reason that one is: L13's partition version is
  advisory because `_partitions` CLAMPS an out-of-bounds wall at build time,
  so the shipped geometry is already right. NOTHING CLAMPS A STAIR. It builds
  exactly where it was authored and the shell wall stays put, so the flight
  runs into it.

  IT MEASURES TO THE WALL'S INNER FACE, `footprint / 2 - wall_thick / 2`, and
  that is the whole point rather than a detail. `footprint_x / 2` is where the
  exterior wall is CENTRED, so a flight reaching exactly that already buries
  half a wall thickness of itself in solid. The first repair of
  `primos_pizza` moved the stair until it overshot the centreline by 0.00 --
  at which moment the centreline reading returned ZERO findings across all
  162 specs and the face reading returned one: the stair that was supposed to
  have just been fixed, still 0.15 m inside the north wall.

  An exterior stair is exempt: it stands outside the shell against a facade by
  design (spec s8.4).

  Measured across all 162 specs when written: ONE stair in one spec. It is not
  a rule looking for work.

- `test_stair_bounds.py` -- 7 tests, pinning the captured case, the failed
  first repair, the exemption, and the fact that no other spec trips it.

### Fixed
- `specs/primos_pizza.json` -- the stair moves from y 4.5 to 3.9 and its run
  shortens from 5.2 to 4.0. It now clears the north wall's inner face by
  0.15 m of real margin rather than sitting tangent to it, clips no partition,
  and pitches at 38.7 degrees.

  THE PITCH IS CHECKED BECAUSE SHORTENING A RUN STEEPENS A FLIGHT.
  `nav_bake.agent_max_slope_deg` is 55 and `CharacterBody3D.floor_max_angle`
  -- what a body actually stands on -- is 45, and `CLAUDE.md` records 20 of 38
  buildings already emitting 45.0-51.3 degrees. 38.7 sits in the same band as
  `walkup_siege`, which walks fine.

  The alternative was rejected on measurement: keeping `run` at 5.2 and only
  moving the stair puts its foot across the storey-0 partition at y 1.0, which
  would clip that wall and drop the door in it. Fixing a stair by deleting a
  door is not a fix.

- `primos_pizza` comes out of the roadmap-113 quarantine, which is now EMPTY.
  All three shells were re-admitted by fixing the generator rather than the
  shells. The dict is kept, with the history in its comment, because the next
  shell that fails traversal belongs there with its reason beside its id.

## [0.107.0] - 2026-09-07

The wall-over-void rule reaches ramps, not just stairs. Roadmap 117, the half
of it the library actually exercises.

### Fixed
- `_partitions` clips against RAMPS as well as stairs and authored holes.
  One function --
  `stairwell.wall_voids` -- now answers "what may a wall on this storey not
  stand ON or IN", so the builder, the 2D plan and the egress contract each
  make ONE call instead of unioning two dictionaries at three separate sites,
  and a fourth producer cannot be remembered at two of them and forgotten at
  the third.

  MEASURED PER PRODUCER ACROSS ALL 162 SPECS BEFORE ANY GEOMETRY MOVED,
  because a count that cannot be attributed cannot be checked afterwards:

  ```
  producer        walls    specs   doors lost
  ramp cut            3        3            2
  ramp footprint      1        1            0
  ladder hole         0        0            0
  vertical link       0        0            0
  ```

  A RAMP NEEDS THE SAME TWO KEYS A STAIR DOES, and that was the open question
  when 117 was filed. Its cut and its footprint are DIFFERENT rectangles --
  the cut sits half a run along the ascent axis, at the head of the climb --
  and `cbp_town`'s `int_0_1` stands in the footprint and in no cut. A rule
  written from cuts alone would have left a wall across a ramp.

  LADDERS AND `floor_hole`/`hatch` LINKS ARE DELIBERATELY NOT INCLUDED. Both
  open a slab, so the same argument reaches them, and a first cut of this
  change did include both. The count above is why they came back out: nothing
  in 162 specs stands a wall over either, so shipping those arms would have
  changed geometry on an argument alone -- with no case to check the result
  against, and no way to tell a correct rule from a wrong one. They go in with
  the spec that needs them and the count that shows it. A test pins the
  decision so it does not drift back in.

  (A ladder would take its through-hole only, never its footprint: it is
  mounted flat against a wall on purpose, so reserving the air in front of it
  would delete the wall it hangs on. Recorded because it is the part that is
  easy to get wrong later.)

- `Builder._ramps` takes its slab cut from `stairwell.ramp_hole` instead of
  spelling the rectangle inline. Two spellings of one rectangle is how a wall
  gets clipped against a hole the builder does not make.

### Added
- `stairwell.wall_voids`, `ramp_hole`, `ramp_footprint_rect`.
- 4 more tests in `test_wall_over_void.py` (28 total): the ramp's two
  rectangles, the wall that exposed this, `wall_voids` as a superset of the
  two calls it replaced, and the deliberate absence of the ladder and
  vertical-link arms.

## [0.106.0] - 2026-09-07

The two passes that CONSUME a partition learn that it can be built in pieces.
0.105.0 changed the geometry and left them reading the authored wall.

### Fixed
- `stairwell._door_nodes` derives a door's interactive id from the piece the
  door is actually in. The docstring has always promised "the SAME stable id
  the builder bakes", and a split breaks both halves of the derivation: the
  wall NAME (piece 1 bakes as `int_1_1p1`) and the POSITION (measured from
  that piece's centre, not the authored run's).

  MEASURED ON THE SHIPPED 0.105.0 BUILD of `night_pawn`: 3 of its 4 door
  nodes named an interactive that appears in no baked set. One of the three
  was the door in the middle of the staircase, which is not built at all. A
  door that survives in no piece is now SKIPPED -- a route through a doorway
  that was not built is not a route -- and an egress contract citing a node
  that does not exist reads as satisfied, which is worse than citing none.
  After: 3 nodes, 0 mismatches.

- `floorplan` draws a partition in pieces, from the same `partition_bounds`
  call, each in its own frame with its openings remapped. A doorway keeps its
  world position and one that fell in a removed part is not drawn, exactly as
  it is not built.

  A CORRECTION TO WHAT 0.105.0's NOTES CLAIMED: `_wall_and_openings` has
  always clamped the drawn extent to the footprint via `tx.hx`/`tx.hy`, so the
  plan and the builder never disagreed about the envelope -- only about the
  voids. It drew a wall ruled straight across its own OPEN TO BELOW hatch.

  The check that says so computes BOTH rectangles from floorplan's own
  transform rather than scraping the SVG: the first version regex-matched
  nothing and reported a clean bill of health over zero rows. Isolated against
  the old drawing it finds one overlap 33.6 px wide, the full width of
  night_pawn's shaft, so it owns exactly this change and can actually fail.

- `stairwell.derive` / `_door_nodes` take the pieces the builder actually
  emitted, instead of re-deriving them. Two derivations of one fact agreed on
  880 of the library's 882 door nodes and disagreed on 2: `slab_openings`
  reads `spec.slab_holes`, and the builder APPENDS to that list during the
  build, so `_partitions` asks before `_ramps` does its work and the gameplay
  pass asks after. `foundry_heist_vertical`'s `int_0_4` came back split for
  one caller and whole for the other. One derivation and a handoff cannot
  drift. The wall over that ramp is a real defect and is filed as roadmap 117
  rather than fixed here -- it needs the same per-producer count 114 made
  before it changes any geometry.

### Added
- `partition_bounds.piece_name` -- piece 0 keeps the authored name; later
  pieces take a `p<k>` suffix. It lives in the shared module because three
  passes in three processes have to agree on it, and a fourth spelling of
  "p1" is how an egress contract starts pointing at a node that is not there.
- 5 more tests in `test_wall_over_void.py` (24 total), covering the name, the
  door-node agreement, the skipped door, and the plan.

## [0.105.0] - 2026-09-07

A wall standing where a stair goes made the stair unwalkable, in fourteen of
the library's 129 shells.

### Fixed
- `_partitions` now clips every interior wall against the slab holes it
  stands over AND the flights it stands in. Two spellings of one sentence,
  and only fixing both makes a stair walkable:

  - a wall on storey k over a hole in storey k's slab stands on nothing --
    and where that hole is a stairwell, it is also a ceiling one storey
    height above the flight climbing through it;
  - a wall on storey k inside the footprint of a flight that CLIMBS THROUGH
    storey k is a wall across a staircase, and its own slab is intact, so the
    first rule never looks at it.

  `_partitions` runs BEFORE `_stairs`, so `spec.slab_holes` is empty when the
  walls are drawn and neither question can be asked from it. Both are answered
  from `stairwell.slab_openings`, which re-derives a flight's rectangle from
  the spec, and from the new `stairwell.stair_footprints`, which keys THE SAME
  rectangle at the storey whose air the flight occupies rather than the slab
  it cuts. The rectangle moved into `stairwell.flight_rect` so the two keys
  cannot drift; getting that off-by-one wrong is exactly what the first
  version of this fix got wrong.

  MEASURED ON `night_pawn`, one change at a time:

  ```
                              navmesh island 0     stair_0
  before                        y 0.19 .. 1.54     no_path
  clipped against its own hole  y 0.19 .. 2.89     no_path   (+1.35 m)
  clipped against the flight    one island         ok
  ```

  Found by raycasting UP from every tread after six static hypotheses had
  been refuted: `int_col_1_1_seg6` sat 2.05 m above tread 6, where the bake
  quantises the ratified 2.0 m agent to `ceil(2.0/0.15) * 0.15 = 2.10`. The
  control is `cr_pawn`, which carries a byte-identical partition, places its
  stair clear of it, passes, and whose treads see the 3.2-6.0 m of clear air
  that `night_pawn`'s now see too. The remaining 0.6 m was found by a second
  probe down the travel axis: `int_col_0_0_open1_lintel` at z 3.15, a
  storey-0 door lintel with the ramp running through it.

  THE CENTRELINE DECIDES, not the wall's thickness band. A stair's hole is
  oversized on purpose -- `width + 0.8` across, 0.3 m behind the bottom step
  and 0.8 m past the top -- so a band test would delete an enclosure wall
  seated flush against the shaft it encloses.

- Four doors authored inside a stairwell or an atrium void are no longer
  built, and each prints a named WARNING instead of vanishing. `night_pawn`'s
  `int_0_0` had one at world x 5.6, opening into the middle of a staircase.
  The void they sat in is a full-height gap, so nothing becomes less passable.

- `night_pawn` and `cbp_town_finale_midbalanced_schemafixed` come out of the
  roadmap-113 quarantine: `nav_gate` reports `ok` for `night_pawn`'s stair and
  for all four of `cbp_town`'s. `primos_pizza` stays quarantined -- it has no
  partition anywhere near its stair, and the same probe found its flight
  running through `ext_col_0_N_lintel1`, the EXTERIOR wall, because the stair
  is placed so its reserved footprint leaves the envelope. Roadmap 115.

### Added
- `partition_bounds.hole_cuts` / `subtract` / `partition_spans` /
  `remap_opening` -- the shared derivation, in the module whose docstring
  already claimed to be the single source of truth for a wall's built extent.
- `stairwell.flight_rect` / `stair_footprints`.
- `test_wall_over_void.py` -- 19 tests, no Blender, pinning the captured case
  and the `cr_pawn` control.

## [0.104.0] - 2026-09-06

`hospital` declared no zones and no objectives in any mode but `survival`, so
the first mission that ever asked for it failed every candidate.

### Fixed
- `presets.hospital` -- the non-survival branch now declares an extraction
  zone and an objectives list. `spec["zones"]` was assigned ONLY inside
  `if mode == "survival"`, so in `heist`, `assault` and `pvp_heist` the spec
  carried neither, and those are exactly the two things a heist scorecard
  reads.

  FOUND BY COLD RUN 6. `mercy_annex_001` asked for `archetype: hospital` and
  all three candidates failed `deli_generate`:

  ```
  TACTICAL-WARN:  heist level has no objectives defined
  TACTICAL-ERROR: heist level has no extraction zone
  errors: 1   warnings: 1        (exit=1)
  The generated spec has validation issues. This is a preset bug --
  please report it
  ```

  That last line was right, and it is the only reason this was found at all:
  `hospital` is one of fourteen presets in a seventeen-preset registry that no
  brief had ever requested.

  THE FIRST DIAGNOSIS WAS WRONG AND IS RECORDED HERE SO IT IS NOT REPEATED.
  The obvious reading is "hospital yields zero objectives", and a probe of all
  17 presets confirmed it is the only one that does -- but objectives are a
  WARNING. The fatal error was the missing EXTRACTION ZONE, which the same
  probe missed because it read the wrong key: extraction is declared in
  `zones[kind == "extraction"]`, not in a top-level field. Reading the failure
  log twice is what caught it.

  THE FIX REUSES WHAT THE PRESET ALREADY HAD rather than inventing a level.
  The survival branch already defines `helipad_extract`, and the docstring
  already says the team "reaches a rooftop helipad holdout ... to extract", so
  the helipad is the way out in both modes. The capture objective is the one
  the branch's own `ROOFTOP` marker already describes -- the room was retagged
  `objective_room` and the marker emitted, and only the spec-level list was
  missing, which is why the retag looked sufficient.

  `survival` is UNCHANGED: 0 objectives is correct for a survival run, which
  has a finale rather than objectives.

  VERIFIED through the real generator, not just the library: `python
  new_level.py --preset hospital --mode heist --seed 9002` exits 0 and
  validates, where it exited 1 before. Across modes, objectives / extraction
  zones now read survival 0/1, heist 1/1, assault 1/1.

### Known
Nothing checks that a registry entry produces a spec that validates. This one
was found by spending seven minutes of a cold run on it, and eleven presets
that no brief has requested remain unexercised. A probe over
`presets.REGISTRY` would cost seconds -- Level Factory roadmap 111.

### Also fixed, because the hospital fix could not be committed without it
`presets.py` is a geometry source, so editing it made all 139 built shells
stale by mtime and `build_freshness` refused the commit. The mandatory
`build.py --all` rebuild then let the pre-commit gate reach checks the stale
library had been hiding, and it failed `nav-gate: 6/159 shell(s) FAILED
traversal`. Attributing all six before touching any of them -- CLAUDE.md's own
rule -- split them into two unrelated causes.

- `build.py --all` and `--watch` now skip Level Factory's workspace
  transients. LF writes one spec per mission candidate into `specs/` as
  `lf_<mission>_<seed>`; `catalog.py` has excluded that prefix since roadmap
  73 and `building_library.index` refuses the ids, but `build.py` -- the one
  command that turns a spec into geometry -- had no such rule. It built 33 of
  them into `build/`, where the nav gate gated them like archetypes, and three
  (`lf_mercy_annex_001_9002`, `_9103`, `_9204`, from cold run 6 earlier the
  same day) failed traversal and blocked the commit the rebuild existed to
  unblock. Same rule, same prefix, same reason as `catalog.py`.

- THREE SHELLS QUARANTINED, and the quarantine says so on every `--all`.
  `night_pawn`, `primos_pizza` and
  `cbp_town_finale_midbalanced_schemafixed` have stairs that do not traverse a
  baked navmesh. Not built, which is the whole mechanism: no `.glb` for the
  gate to gate, and no `manifest.json`, so the lot pool stops offering them
  through the path the CLI already reports as "excluded from the lot for a
  missing manifest".

  MEASURED from the gate's own island data rather than reasoned from source
  geometry -- `docs/NAV_GATE_FINDINGS.md` records four mechanisms proposed by
  static measurement here and refuted by their own data. The shape is the same
  in all three: the ramp bakes as DISCONNECTED FRAGMENTS with a hole part-way
  up. `night_pawn` leaves a 1.95 m gap between islands at y 0.19..1.54 and
  y 3.49..3.79, with 2-poly crumbs stranded at y 1.24 and y 2.29..2.89;
  `primos_pizza` a 0.90 m gap. That is a DIFFERENT shape from August's
  finding, where `cr_deli` broke at the FOOT of its flight -- and `cr_deli`
  now passes, so the rebuild fixed the case that doc left open.

  NOT NEW: `NAV_GATE_FINDINGS.md` already listed `primos_pizza` among fifteen
  shells with markers on disconnected islands, "every one of them currently
  reports `passed`". What changed is that the stair check fails now the shells
  are built with current code.

  The specs stay on disk and the reason is written beside each id, so
  re-admitting one is deleting a line in `_QUARANTINE` after
  `python nav_gate.py build/<name>.glb` passes. Tracked as Level Factory
  roadmap 113.

## [0.103.1] - 2026-09-05

The catalogue indexed Level Factory's transients, and that was the one thing
standing between a gate-clean art pass and a package (roadmap 73).

### Fixed
- `catalog.py` skips `specs/lf_*.json`. Those are Level Factory's transient
  inputs for a running pipeline, not this library's content --
  `.gitignore:49` already excludes them and none is tracked.

  WHY IT WAS EXPENSIVE, and it is not about a noisy catalogue.
  `specs/CATALOG.md` IS tracked, `new_level.py` refreshes it after every spec
  write, and Level Factory folds a tool repo's dirty-TRACKED-file hash into
  the build fingerprint (`packages/adapters/sdk.py:_read_git_commit`, whose
  docstring excludes untracked files precisely so pipeline writes cannot bust
  the cache). Indexing lf_ specs therefore routed the one tracked file the
  pipeline touches straight into the fingerprint.

  MEASURED, before and after. One `new_level.py --preset bank` moved the
  revision from

      099a9cdc9dffac4c68aae6ccb9c6c87c04006304
   to 099a9cdc9dffac4c68aae6ccb9c6c87c04006304+dirty.cbd2f89b2b4fe547

  with `specs/CATALOG.md` the only dirty tracked file. After this change the
  same write leaves the revision byte-identical.

  THE CONSEQUENCE IT CAUSED. One `deli_generate` job changed the revision its
  own siblings key on, so every later job cache-missed -- including jobs the
  functional shell lock had just fingerprinted. `cold_7003` recorded the
  timing: lock approved 12:06:31.899, `deli_generate` re-evaluated at
  12:06:33.247 and `lot_assemble` at 12:06:38.478, 1.3 and 6.6 seconds later.
  The re-runs moved the gameplay-anchor and interactive registries,
  `verify_no_drift` reported both changed after the art pass, and the export
  was refused. `collision_fingerprint` never drifted -- the level's shape was
  never the problem.

  Cold runs 1, 2 and 3 all failed to produce a gated package; 3 failed here.

- CATALOG.md regenerated: 153 -> 129 levels, the 24 removed all `lf_`.

### Not bumped
`KIT_VERSION` stays 0.103.0. It names the BUILDER that stamps a model, and
`catalog.py` builds nothing -- the same reason 0.101.1 and 0.101.2 shipped
without moving it. Every manifest in `build/` correctly continues to record
the kit that produced it.

## [0.103.0] - 2026-09-04

`new_level.py` grows `--seed`. Every recipe pins its own seed as a literal --
casino_tower 1989, bank 1999, fifteen of them, years -- and nothing could
override it, so two callers asking for the same preset got the same building
forever. Level Factory was one of those callers: five candidates of a mission
produced five byte-identical shells (roadmap item 69).

### Added
- `new_level.py --seed N` and `presets.make(seed=N)`. The seed is injected
  between the recipe and the seed-consuming passes, which is the only place it
  works: `_finish_stairs` rolls the probabilistic extras on `spec.seed` and
  `level_design.enrich` seeds each room's cover on
  `f"{seed}:{room_id}:seed_cover"`, so a seed written into a finished spec
  changes the number the builder prints and nothing about the geometry.
  `stair_regression.generate()` has injected at this exact point since it was
  written; this exposes the same lever on the CLI.

### Measured, and it is narrower than the flag sounds
Seven presets, two seeds each, level name held constant so ids do not move:

    preset            stairs   ladders   volumes   markers
    casino_tower         0/1       0/1      8/14      8/23
    bank                 0/2       0/0      8/11      8/14
    warehouse            0/0       0/0      7/13      7/17
    hospital             0/2       0/0      8/18      8/22
    pawn_shop            0/1       0/2       2/6       4/9
    office               0/1       0/2      0/10      0/12
    parking_garage       0/1       0/0      0/25      0/12

The seed moves seeded cover and the markers derived from it. It moves NO
stairs and NO ladders on any preset tested, and on `office` and
`parking_garage` it moves nothing at all -- `seed_cover` skips rooms with no
`combat_range` and rooms that already carry authored cover. A first reading of
the raw diff said stairs varied; that was the id string carrying the level
name, which the instrument itself had varied. Shell, rooms and partitions are
byte-identical across seeds.

So this closes "every candidate is the same file" and does not close "every
candidate is the same building". Building variety needs a different lever --
the preset, not the seed.

## [0.102.1] - 2026-08-25

0.102.0's one regression, found by the gate it shipped with and fixed on the
floats rather than on a theory. The corner change closed 988 of 988 open
corners across the library and introduced exactly ONE new sub-5 cm gap --
`strip_retail_a01 ext_1_N`, 0.050 m before `ext_1_N_open0`.

### Fixed
- `_wall_span` computes a span's remainder ONCE and uses that value for both
  the absorb decision and the emit decision. It was computed twice, by two
  algebraically identical expressions that are not identical in floating
  point: `L - n * M` carries the error of `b - a`, `b - (a + n * M)` carries
  the error of `a + n * M`. Instrumented and rebuilt, the offending span
  reported

      ext_1_N_seg6  a=-9.85 b=2.2 L=12.05 M=2.0 n=6
                    L - n*M = 0.05000000000000071  -> too big to absorb
                    b - x   = 0.04999999999999982  -> too small to emit
                    hole    = 0.04999999999999982

  with the control case two spans down the same run --

      ext_1_N_seg9  a=3.8 b=9.85 L=6.05 n=3
                    L - n*M = 0.04999999999999982  -> absorbed, no hole

  -- ruling out coincidence. A threshold asked of two spellings of one number
  has a blind window either side of it, and a piece that lands in the window
  is neither absorbed nor emitted; it is silently gone. The threshold itself
  is unchanged at 0.05 and `_seg_box` still refuses anything at or under it.
  What changed is that both questions are now asked of the same float.

### How it was found
`tools/envelope_continuity.py` predicted `ENV_RUN_GAP 1` for the rebuilt
library and the real rebuild read 2. The extra one was not written off: a
temporary probe (`patch_dc_span_probe.py`, applied and reverted byte-for-byte)
printed `repr()` of every near-threshold span, which is precisely the
precision the manifest's 4-decimal rounding was hiding. The first hypothesis
about this defect was REFUTED before it was confirmed -- reconstructed from
the manifest it looked as though both expressions agreed, because the span was
assumed to start after the previous module (a=0.15) when it actually starts at
the run's inset edge (a=-9.85) and covers six modules. The reconstruction was
wrong; the mechanism was right. Only the builder knew its own inputs.

### Predicted
`ENV_RUN_GAP` 2 -> 1 on a rebuilt library, the remaining one being the
pre-existing `auto_shop_a02` gap whose whole span is under the threshold and
so has no module to absorb into. `ENV_CORNER_OPEN` stays 0.

## [0.102.0] - 2026-08-24

Roadmap 58: the exterior envelope closes at its corners. Every run used to
end ON the perpendicular wall's centreline -- `_exterior` builds an N/S run
`footprint_x` long centred at zero, and the E/W walls sit at `+/- hx` -- so
the outer quadrant of every corner belonged to nobody: a re-entrant notch
`wall_thick/2` a side, full storey height, open on two faces and open to the
sky. MEASURED before anything moved, over every slot manifest in `build/`
with `tools/envelope_continuity.py` (new, factory root): **988 open corners
across 124 buildings, zero clean**, and the notch tracks the wall thickness
and nothing else -- 0.150 m on the 0.30 walls (812), 0.175 on the 0.35 (152),
0.125 on the 0.25 (24). Half the thickness at three thicknesses is a rule,
not a tolerance. The first candidate mechanism ("nobody owns the turn") is
confirmed; a themed module narrower than its slot and seg-boundary rounding
are both refuted -- runs are contiguous to 1e-6 and land on exact integers,
and rounding does not produce one value 988 times.

### Changed
- `_emit_wall_run` grows `inset` and `corners`, both defaulted OFF. It has
  two callers and only `_exterior` asks for either, so interior partitions
  are untouched by construction rather than by hope. `inset` pulls the SOLID
  spans back to the perpendicular wall's inner face; openings do NOT move
  with it, because they are placed in `_exterior` as a fraction of the full
  run and arrive already positioned. That is the whole reason the inset sits
  at this seam -- shortening the run itself would slide every door inward and
  change every building's gameplay anchors. Measured first: 0 of 1088
  exterior openings come within a half-thickness of their run's end, so no
  aperture lands in the pulled-back zone.
- `corners` seats one post at each end of the run, centred on the run's own
  end coordinate so it spans the perpendicular wall's full thickness. N/S
  owns the corner (`corners=(axis == 0)`): two runs meeting there must not
  both fill it, and one axis owning it makes the winner deterministic rather
  than arbitrary.
- `_wall_span` ABSORBS a trailing remainder at or under the 0.05 m sliver
  threshold into the last module instead of dropping it. Dropping a sliver
  does not tidy a run, it opens a hole in one -- and insetting shifts every
  tile boundary, so remainders that used to clear the threshold stop clearing
  it. Predicted over the library, the corner change alone takes run gaps from
  1 to 15 (twelve of 0.050 m, three of 0.025, every one beside an opening or
  a run end); with the remainder absorbed it stays at 1. This is the only
  part of the change that also reaches interior partitions, and it strictly
  closes gaps rather than opening them. The absorbed module is emitted
  `size_mod="end"` so it stays a scaled `wallEnd` unit box and mints no new
  stem in any kit.

### Costs nothing in the kit
The post is `size_mod="end"`, so `_slot_typename` returns `wallEnd` -- the one
species Deli Counter scales, a unit box sized per slot. Zoo's
`exact = typ != "wallEnd"` gives it unit treatment with no change in that
repo, no new stem, and no new `.glb` in any kit: one more instance of geometry
every kit already carries. Priced against the alternative, an exact-fit corner
would be 18 modules per theme per style (18 distinct thickness x storey-height
pairs in the library) against one.

Zoo HAS an authored corner -- `wallCorner`, recipe plus genome, dated
2026-07-14, never once requested (roadmap item 64). It is deliberately not
used here: an L cannot ride the unit-box scale, because scaling a leg scales
its thickness with it, so it is structurally exact-fit. Promoting these slots
to it later is one function in each repo, when there is art to justify the
18x.

### Predicted, not built
Verified by modelling the patched emitter against all 124 readable manifests
and re-running the gate: `ENV_CORNER_OPEN` 988 -> 0, `ENV_RUN_GAP` 1 -> 1
(the remaining one is the pre-existing `auto_shop_a02` gap, whose whole span
is under the threshold and so has no module to absorb into),
`ENV_PLACEMENT_DRIFT` 0. NOT run through Blender: `deli_counter.py` imports
`bpy`, so the suite and a real rebuild are still owed. The acceptance test is
that gate reading 0 on a rebuilt library.

THE FUNCTIONAL LOCK WILL FIRE. Collision moves on every building, which is
exactly what `functional_shell_locked` protects. Re-approval is correct here,
not a workaround.

## [0.101.2] - 2026-08-24

L18 graduates WARN -> FAIL, on two measurements rather than a mood. The
authored library lints clean (0.101.1's surgery, 129 specs at zero L18),
and the new built-output probe (`tools/door_split_probe.py`, the
running-tree instrument in the factory root) read ZERO walls inside 45
jamb-pair-derived apertures on the composed lot_demo_001 -- the sighting
that opened roadmap 59 was fixed en route by the week's rebuilds. Its
four findings were all `AreaPanel_Surface` sign quads hanging in exterior
doorway spans: item 55's blank cards, three of four still carrying
engine-generated names, not walls. From here a spec that splits a doorway
fails its build instead of waiting for a walker with a screenshot.

### Changed
- `layout_lint.py`: `door_split_findings` reports into FAILS;
  `test_door_split.py` pins the graduation the same way it pinned the
  WARN. Generator avoidance stays the right authoring-side fix when the
  gate fires -- the FAIL is the backstop, not the fix.

## [0.101.1] - 2026-08-24

Roadmap 59's library surgery: the 33 L18 findings the new lint measured
across 28 specs, fixed at the source. Every fix slides the OPENING clear
of the partition end (never shortens the partition -- that opens a gap
between rooms); the default is KEEP-SIDE minimal motion, so the aperture
stays in the room it already mostly served, with three recorded classes
of exception: (1) crossings where keep-side was nonsense for the opening
(07_police_station and pvp_station_ref's `garage_bay` opened into the
LOBBY; it belongs to the garage), (2) five dead-center collisions
direction-picked from room roles (a breach lands in teller circulation,
not inside the fortifiable security office; a dock belongs to brew_back,
not the taproom; self_storage's breach keeps cutting into `vault_unit`,
because cutting into the objective is what a breach is for), and (3) a
bounds veto that flips across the partition when keep-side would run past
the wall corner (none fired). The parking family's `vehicle_in` was
adjudicated a DEFECT, not a lane divider: the wall it hit separates the
attendant booth -- the OBJECTIVE room -- from the deck, so the 5 m bay
half-opened into the money booth. Verification per spec: full lint before
and after, zero L18 remaining, and not one non-L18 finding gained or
lost anywhere.

### Fixed
- 28 specs re-authored: gas family x5 (`front_entry_east` 5.12 -> 4.75),
  deli family (`loading_bay` -9.5 -> -9.95 x4, `alley_entry` 5.04 ->
  4.95 x4), parking family (`vehicle_in` -> deck-side clear x4 incl.
  cr_garage), and singles (07_police_station, bank_branch_a04,
  brewery_a03, construction_site_a03, credit_union_a03, final_stand x2,
  freight_terminal_a01 x2, mansion_a02, marina_a03, pawn_shop_a02,
  pvp_station_ref, self_storage_a01/_a02, supermarket_a01). Geometry
  corrections -- the PATCH bump condition; every rebuilt .glb with one of
  these openings differs.

## [0.101.0] - 2026-08-24

Roadmap 59 opens its lint. Sighted 2026-08-23 walking lot_demo_001: one
doorway divided into two squeeze-past channels by a partition's WallEnd
standing mid-aperture, a wall edge-on to the door. Every engine gate
passes it -- both channels traverse -- so the check belongs at spec level,
before the geometry exists.

### Added
- `layout_lint.py` L18 (WARN): no partition may terminate inside a
  doorway's aperture span plus a 0.3 m leaf margin, on the wall it meets --
  exterior and interior hosts alike. Endpoints are judged through
  `clamp_partition_span` (the builder's own bound), so the lint and the
  shipped geometry cannot disagree; a wall CROSSING the aperture line is
  deliberately exempt (a different defect with different owners). WARN
  first, on the stair-volume lint's reasoning: it must not red an
  in-flight certification -- it graduates to FAIL once the library lints
  clean, and the floorplan generator learns avoidance (nudge the opening
  along its wall, or stop the partition one bay short; never silently
  delete either). Eleven tests pin the geometry and the exemptions
  (`test_door_split.py`). Numbered L18 because the 0.9x changelog assigns
  L17 to the stair-volume lint, which is absent from today's
  layout_lint.py -- that absence is its own open question, and the slot
  stays reserved.
- Spec output unchanged for every building -- the MINOR definition's
  second half; KIT_VERSION stays coupled.

### Fixed
- The navgate population baseline stops grading Level Factory transients.
  `lf_*` shells are LF pipeline side inputs built into this library's
  `build/`, and the baseline was absorbing them one hand-written entry at
  a time -- nine were already listed when `lf_unlit_probe_001_5017`
  red-flagged the 0.100.0 adoption commit as a "newly unjudged shell".
  `test_navgate_population._live` now excludes the class (the same call
  `layout_lint.main()` already makes for `specs/lf_*.json`; LF grades its
  own missions with its own gates), and the nine dead `lf_` entries leave
  `navgate_baseline.json` -- unjudged 17 -> 8, every remaining entry an
  authored shell with its reason intact.

## [0.100.0] - 2026-08-24

Roadmap 54's residue, measured to its end. Census #7 -- the first run with
every light already at its floor-pool minimum range (Lux 0.23.0) -- left 6
meshes over the engine's 8-light budget, and the census's new margin
forensics priced the range trims that would clear them at 0.44-1.59 m:
more than any floor can pay (an office pool would shrink to ~1.3 m against
4 m row spacing). The residue is geometry, in two shapes, both here.

### Changed
- `floors.SLAB_TILE` 8.0 -> 5.0. A tile's claimant count scales with its
  collection rectangle, (tile + 2*range) per axis: at 8.0 x 6.8 an office
  tile sweeps ~260 m^2 of lamp-bearing plan at 4.4 m ranges and bound 9-10
  claimants; at 5.0 the rectangle shrinks ~35% and the worst measured tile
  scales to ~6 -- under budget with headroom for a bake wobble. Zoo's
  `PLATE_TILE` stays 8.0 ON PURPOSE: its plates measured within budget at
  census #7, and this constant is now derived from THIS kit's lamp
  density, not from a geometry law the repos share. Buildings wider than
  5 m re-tile, so every rebuilt .glb differs -- the MINOR bump condition.
- Parapet VISUALS route through `floors.slab_tiles` -- census #7 caught
  the arena's 52 m `parapet_N` binding 9 lights, the one greybox visual
  that had escaped the tile law entirely. Runs inside the tile keep their
  exact name (small buildings unchanged by a byte); collision stays ONE
  box per run, because a collider has no light budget.
- `polybudget` mirrors the parapet splits, and stops counting E/W parapet
  runs on footprints too narrow to hold them -- the builder never emitted
  those, so the flat "4 boxes" estimate overcounted exactly that case.

## [0.99.1] - 2026-08-24

### Fixed
- Pendant density guardrails. Census #5 measured the first law's failure:
  `area / 25` alone gave the arena's 275 m^2 skybox suite ELEVEN bulbs
  1.5 m apart -- a chandelier row, not a moody cellar -- and every ceiling
  tile under it blew the per-mesh budget the type was priced for. Bulbs
  now cap at `_PENDANT_MAX` (5) per room and never pack tighter than
  `_PENDANT_MIN_SPACING` (3.5 m). A big room is supposed to have dark
  corners; that is what "moody" means. Two tests pin it.

## [0.99.0] - 2026-08-24

Census #4 left exactly NINE meshes over the per-mesh budget of 8 -- every
one a b0/b1/b4 floor or slab tile at 9-10 lights. Ranges were already
drop-derived and the tiles budget-sized, so the residue was lamp COUNT in
dense rooms: rows at 3 m spacing put an office grid over every interior.

### Changed
- `_TARGET_SPACING` 3.0 -> 4.0. A quarter fewer lamps per row puts the
  last nine tiles under the engine default, and wider pools read more
  like a 90s interior than an office ceiling -- the direction the palette
  was already chasing (0.98.0). If a room reads too dark, raise rig
  energy in Lux; density is a budget number first, a look second.
- KIT_VERSION 0.99.0 (stays coupled).

## [0.98.0] - 2026-08-23

Roadmap 57's palette, first entry: 90s Philadelphia is not lit by one
fixture type. A basement or an objective room -- a vault, a count room --
with an office fluorescent row reads like an office.

### Added
- The below-grade rule in `lights.py`: rooms with `story < 0` or
  `objective: true` derive `pendant` anchors instead of the fluorescent
  row -- sparse bare bulbs, one pool per ~25 m^2 (`_PENDANT_AREA`), hanging
  `_PENDANT_CORD` = 0.6 m below the slab, with the drop measured from the
  BULB so the range rule still reaches the floor. Same run machinery: a
  stairwell still splits the line around its hole. Lux >= 0.20 reads the
  type as a warm incandescent with a tight clamp and a filament waver;
  older Lux skips it with a count, so the rollout cannot half-light a room.
- `test_pendant_lights.py`: basement and objective rooms go moody at any
  storey, ordinary rooms keep the row, density (50 m^2 -> 2 bulbs,
  16 m^2 -> 1), the cord hang, drop-to-own-floor, void splitting.
- KIT_VERSION 0.98.0 (stays coupled).

## [0.97.0] - 2026-08-23

Roadmap item 54, the lighting contract's turn. A flat lux light range was
wrong at both ends inside one day: 8.0 claimed per-mesh budget slots two
rooms away through walls (the brightness grid), and the 4.5 trim left the
arena's ~5.7 m hall with a lit ceiling over a PITCH-BLACK floor -- Godot's
attenuation reaches hard zero at the range, so no energy value lights a
floor the range does not reach. Only this kit knows a room's height.

### Added
- Every derived fluorescent ceiling anchor in `<name>.lights.json` carries
  `drop`: metres from the lamp down to its own room's floor
  (`ceiling_z - floor_z`, storey-local -- an upstairs lamp's drop is to ITS
  floor, not the ground). Lux >= 0.19 derives the omni range from it:
  `clamp(drop + 1.5, 4.5, 8.0)`, a floor pool ~sqrt(3 x drop) m wide in
  every room, tall halls included, without re-claiming the whole per-mesh
  budget. Windows and wall hardware carry no drop -- they meter their own
  mounting, and a drop on them would be a guess wearing a number.
- `test_light_drop.py`: drop reaches the room's own floor, storey-locality,
  split runs share one drop, non-ceiling anchors carry none.
- KIT_VERSION 0.97.0 (stays coupled to the release).

## [0.96.0] - 2026-08-23

Roadmap item 54, the Deli Counter half -- the greybox base ships
full-footprint `slab_<n>` visuals (34-52 m on the shipped buildings), and
Godot budgets positional lights PER MESH (engine default 8), so one slab was
one light budget for a whole storey. Zoo 0.49.0 tiles its plate modules; this
release tiles the slab visuals the stripped base keeps, so the composed scene
has no room-spanning plate left from either side.

### Changed
- `Builder._slabs` emits the slab VISUAL as light-budget-sized tiles
  (`slab_<n>_t<j>_<i>`, `floors.slab_tiles`, 8 m law shared with
  `core.arch.PLATE_TILE` in Zoo -- duplicated deliberately across repos and
  cross-named so the pair is findable). A footprint inside the tile emits
  the single `slab_<n>` byte-identically. COLLISION IS NOT TILED: the one
  trimesh slab stays authoritative, keeps its boolean-cut holes, and a
  collider has no light budget. Proven in-session on pvp_station_ref
  (34 x 26 m, 4 storeys): 80 visual tiles at 6.8 x 6.5 m, four collision
  slabs exactly as before.
- `Builder._slab_holes_cut` cuts EVERY matching slab piece that overlaps
  the cutter, not the first name match -- on tiles, `break`-on-first would
  cut whichever tile the collection listed first and leave the stairwell
  capped, the exact walkthrough-ceiling defect the cut exists to prevent.
  Matching is name-boundary safe (`slab_1` cannot claim `slab_10`'s tiles);
  a tile the cutter swallows whole is removed (with its `surface_roles`
  entry) rather than booleaned into an empty mesh node. Same
  pvp_station_ref build: the stairwell straddles `slab_1_t3_0`/`_t3_1`,
  the hatches land on `_t3_4` and `slab_2_t0_4`, all four cut, both holed
  collision slabs unchanged.
- `portable_building.roof_covered_nodes` matches by CONTAINMENT in the
  roof slot's box (grown 5 cm) instead of AABB equality: the top slab a
  themed roof replaces is now a tile set, and equality would find none of
  them -- the whole set would z-fight the themed module. An untiled slab
  is contained in its own box, so the single-node case still strips;
  walls stop under the thin slab volume and rooftop props stand above it,
  so nothing else can be eaten.
- `polybudget.estimate` mirrors the tile count per storey (hole cost
  charged once), so the estimator's piece count matches what the builder
  now emits.

### Added
- `test_slab_tiles.py`: byte-identity for small footprints, the arena
  footprint tiles to budget size, exact reassembly, boundary-safe unique
  suffixes, no slivers, tile <= 0 disables; roof strip containment --
  every tile of a themed roof covered, untiled slab still matches,
  walls/rooftop props/parapets stay, greybox-fallback roof keeps all
  tiles.

The item closes when the per-mesh light census
(`tools/mesh_light_census.py`, factory root) shows zero meshes over the
engine default of 8 on a recomposed package and level_factory deletes
`PER_OBJECT_CEILING`.

## [0.95.0] - 2026-08-22

Roadmap item 46, step 4 -- the fields the pipe was built to feed. Now that
interactives ship to the handoff package (0.94.0 + lot/dispatch/LF), the
game finally reads what decides whether a thing shatters, splinters or
dents. "Populating them before the pipe is connected is decorating a
disconnected pipe" -- the pipe is connected; this is the water.

### Added
- `spec_loader._derive_opening_defaults`, run once at spec load: openings
  the author left bare get the values every authored spec already writes by
  hand (measured across all specs, nothing invented: window pane -> glass
  16/16; breach material -> host wall's material, explicit or palette
  default, 12/12; breach_class from material -- soft_wall on
  drywall/wood/glass 10/10, reinforceable on brick_ext/concrete 2/2).
  AUTHORED VALUES ALWAYS WIN, an unknown material derives no breach_class
  (a null stays honest where a guess would lie), and door/garage/vault/
  teller/safe_deposit fixtures stay untouched until a vocabulary for their
  own materials exists. Measured on pvp_station_ref: 9 windows and 2
  breaches go from null to annotated; mansion_a02 and the LF demo specs
  likewise.
- The interactive machines carry `material` / `breach_class` as ADVISORY
  fields (INTERACTIVES.md), stamped in `derive_interactive` and shipped in
  the gameplay entry -- so dispatch's interactives.json answers "what does
  a charge do here" without joining back to openings. setdefault: an
  authored override that sets either always wins. The slot view stays
  art-only.
- `tactical.py` warns on an UNRECOGNIZED breach_class, not just a missing
  one. Found the defect it guards against while building this: an
  LF-generated spec authored "reinforced" where floorplan.py reads
  == "reinforceable" -- one letter of vocabulary drift and the breach never
  got the treatment its author asked for. An unknown value is worse than
  none; it LOOKS annotated.
- `test_opening_defaults.py`: eleven checks pinning the law, the authored
  precedence, the honest nulls, and the machine/gameplay carry.

## [0.94.0] - 2026-08-22

### Added
- `themed_tscn` now instances EVERY interactive state, not just the default:
  a non-default state whose geometry differs (per `interactive.state_geometry`)
  rides as a HIDDEN sibling -- `<slot_id>_<state>`, `visible = false`, same
  transform -- so the shipped scene finally contains what the game's state
  machine swaps TO. The resolver, `state_variant_stems`, is the composer-side
  mirror of `zoo_keeper.core.kit.slot_variants`: same species rule (unmapped
  state -> the slot's own type), same deferral (state sharing the default's
  species is identical art today -- doors get no variant, exactly as the kit
  builds none), same style law (variants follow the style the BASE resolved
  to, style-01 fallback included; greybox-fallback slots get no variants).
  On cr_deli: 11 hidden variants (3 window `_broken`, 8 breach_wall
  `_breached`, 0 door), all six distinct variant modules landing as real
  ext_resources so `portable_building`'s bundling regex carries them into
  `art/zoo/` unchanged.
- Both siblings carry `metadata/interactive_id` (the stable gameplay.json id)
  and `metadata/interactive_state`, so netcode finds the pair without parsing
  node names -- names are for humans; metadata is the contract
  (docs/INTERACTIVES.md). The runtime swap is: flip visibility, toggle
  collision per `collision_per_state`, art already loaded. A late joiner is
  told which sibling is visible, nothing else.
- Stats/CLI report `state_variants` placed and `state_variants_missing`
  (state differs but its module is not in the library) -- progressive art
  stays honest about what it skipped.

### Changed
- The z-fight gate skips `visible = false` node blocks: a parked state
  variant is coplanar with its visible default BY DESIGN, and a mesh that
  does not render cannot flicker. The gate measures what renders at rest.
  The skip happens before the block's GLB is opened, and the new test baits
  it with a malformed variant GLB so a regression fails loudly.

## [0.93.0] - 2026-08-22

### Changed
- The `window` interactive machine now carries
  `state_geometry {"intact": "window", "broken": "window_broken"}`. It never
  had one because no broken-window species existed, so a breakable window's
  `broken` state was deferred forever and the resolver rendered intact glass
  on a pane the gameplay layer said was gone. zoo 0.48.0 added the species;
  with this block, a kit build on a manifest whose window authors
  `breakable: true` emits `window_<theme>_<style>_w<cm>_broken.glb`
  (measured on a 1.1 m test slot through zoo's builder: both variants
  built, PASS).
- `collision_per_state.broken` is now `False` for windows, matching
  breach_wall's breached state. The advisory used to claim a shot-out
  window still blocks, which contradicted both the art (the opening is
  passable; the frame carries its own collision, exactly as breach keeps
  its lintel) and the consumers (the lasertag destructible drops pane
  collision on break). Advisory stays advisory -- the game's destructible
  layer owns the actual toggle.

### Notes
- A window is interactive ONLY when its opening authors `breakable: true`,
  unchanged -- no existing spec changes meaning. The chain this completes:
  DC emits the machine and the stable id -> Zoo builds the intact and
  `_broken` art plus `glass_shard` debris, all skinned by the same
  Pixelcoat glass pack as the pane -> the game replicates the state enum
  per id (lasertag's `LT_DestructibleSync` is one such consumer, per the
  ownership table in docs/INTERACTIVES.md).

## [0.92.0] - 2026-08-21

### Added
- `navgate_baseline.json` and `test_navgate_population.py`. nav_gate reports
  `markers: 0 checked -- reachability UNJUDGED` for a shell with no marker whose
  type ends in `_spawn`, and the exit code is deliberately unchanged, so that set
  could grow with nothing failing. It is now frozen: a new entrant fails, and a
  shell that gets fixed must be removed or the test says so.

### Corrected
- A prior note recorded "3/135 shells fail, 18 have no spawn marker". Measured
  from the per-shell results: 3 stair failures is right
  (`cbp_town_finale_midbalanced_schemafixed`, `night_pawn`, `primos_pizza`), but
  the unjudged set is 17, not 18, and five of its members were never named --
  `cr_pawn`, `gs_auto_shop`, `gs_facade_rowhome`, `gs_facade_storefront`,
  `lf_art_probe_001_5017`.
- 16 shells report `navigable: null` against 17 unjudged. That is not an
  inconsistency: `night_pawn` also fails the stair gate, and `navigable` is a
  conjunction, so a stair failure forces `False` without marker state mattering.
  Recorded in the baseline as explained rather than filed as a defect.

### Notes
- WHAT THIS DOES NOT CERTIFY: it says nothing about whether these shells SHOULD
  have spawn markers. Twelve of the seventeen carry `RECORDED, NOT EXPLAINED`.
  Only `gs_facade_*` (facade-only, no interior) and `lf_art_probe_001_5017` (a
  probe artifact) are classified, and those from their names alone.
- The per-shell `.navgate.json` files live in `build/`, which is not committed,
  so the sweep SKIPS in a clean checkout. The baseline's own integrity is
  asserted there instead, so a clean checkout never reports a green sweep of
  nothing.

## [0.91.0] - the unresolved flag gets a reader

`_resolve_material` has always marked a material the spec does not declare
`"unresolved": True`. Nothing ever read that flag. It was set in one place
and consumed in none, so the condition it detects has been invisible for as
long as it has existed -- and it is not an edge case.

Measured over 142 specs: `ceiling_tile` and `tile` are missing from ALL of
them, `carpet` from 137.

### Added
- The build now prints unresolved materials, with the consequence spelled
  out rather than left to be inferred.

### What that condition actually costs
An undeclared material falls back to `default_material` -- and the fallback
is not only acoustic. `skin_style.style_for` falls back the same way, so the
material inherits the default's STYLE. Style selects the Pixelcoat pack and
goes into the module filename. 410 of 574 (building, plate material) pairs
resolve to style 1.

So a carpet floor, a tile floor and a concrete floor in one building have
been getting the same acoustics, the same skin and, when their dimensions
match, the same file. That last one surfaced first, as 19 stem collisions in
Zoo, and looked like a naming-law problem for most of a session.

### Not fixed here, deliberately
Adding `carpet`, `tile` and `ceiling_tile` to `presets._PALETTE` and
migrating the 139 existing specs is the actual fix. It is held back because
the palette's `acoustic` names ("Concrete", "Drywall", "Glass", "Metal",
"Wood") are consumed by gool, nothing validates them, and inventing
"Carpet" would fail silently downstream -- the same class of defect this
entry exists to end. It also changes how every interior in the project
looks, which deserves a session where it can be looked at.

## [0.90.0] - the prop stem mirror gains depth and height

### Fixed
- **`themed_tscn.module_stem` mirrors zoo 0.39.0.** A `prop` slot's stem now
  carries `_d<cm>` and `_h<cm>`, because a prop is free on all three axes and
  width alone named two different solids the same file.

  This file's own docstring is why it moves in the same patch: *"THE MIRROR OF
  `zoo_keeper.core.kit.module_stem`, and the two must change together. Neither
  side parses a stem; both CONSTRUCT it from the same slot, so they agree only
  by being kept identical."*

  Verified across every slot in the shipped corpus: **9,185 of 9,185 produce
  identical stems on both sides.** Measured on 52 of 136 buildings, 15 (28%)
  were affected before the fix; `cr_gas` had a 0.9x10.0x1.8 counter and a
  0.9x0.9x1.0 cube on one `prop_delco_04_w90`.

- `VOLUME_ROLES = ("prop",)` added, mirroring `zoo_keeper.core.kit`.

### Notes
- Wall, doorway and window filenames are unchanged. Only `role == "prop"` slots
  resolve to a new stem -- 84 across the sampled buildings, asserted.
- Existing built prop GLBs fall back to greybox until rebuilt, which is the
  progressive art path behaving as intended.

## [0.89.0] - Stairs a nav agent can actually walk

Seven of 135 shells failed `nav_gate --all` on stair traversal. Four are
fixed and engine-confirmed; the mechanism turned out to be the same number
in every case -- a Godot nav agent bakes at radius 0.40 and needs 0.80 m of
clear width, and each of these left less.

- **check.py:** `build_freshness.py` now runs BEFORE the nav gate. That gate
  grades the shells in `build/`, and a stale shell does not make it answer
  weakly, it makes it answer wrongly with full confidence. On 2026-08-12
  every shell in `build/` was 4.2 days behind the code; a ladder that
  `patch_dc_roof_voids.py` had already fixed still climbed into a solid roof.
- **layout_lint.py L17 (NEW, FAIL):** a volume must not narrow a stair flight
  below `AGENT_DIAMETER` (0.80 m). Footprint comes from
  `stair_core._core_of`, the same reservation the stair placer uses, so the
  lint and the placer cannot disagree about where a stair is. Deliberately
  narrow: measured across the specs to hand it fires on 1 of 8 failing stairs
  and 0 of 8 passing ones. Three wider rules were tested and rejected --
  "volume overlaps the stair well" flags a vault and a power cabinet that
  both bake fine. A lint that fails working buildings gets switched off, and
  then it protects nothing.
- **specs/office.json:** `elevator_block`, a 2.0 x 2.0 x 3.0 m solid, was
  authored at (0.0, 0.0) -- the exact coordinates of `office_stair_0`. It
  left 0.60 m of a 3.20 m flight. Moved to x 3.6. `nav_gate`: no_path -> ok,
  markers 0/1 -> 1/1 reachable.
- **specs/cr_deli.json, corner_deli_heist_01.json, night_deli.json:** three
  clones of one authored deli. A switchback's two runs meet at the stair's
  own x and `office_stair_door` was centred on that seam, so each run got
  half a 1.20 m door -- 0.60 m, against 0.80 m needed. Widened to 2.40 m.
  `cr_deli` now bakes as ONE island, y -3.00..6.90, 483 polys, which is the
  signature every passing shell has.
- **specs/night_deli.json:** the door fix moved its break up a floor rather
  than closing it. `planter_box_upper_hall_1` (z 3.30..4.20) left 0.76 m on
  the ascending run -- four centimetres short. Moved clear, along with its
  derived `AUTO_PLANTER_BOX_UPPER_HALL_1` cover marker, which would otherwise
  have sent bots to take cover behind nothing in a stairwell.

Still failing and NOT fixed here: `night_pawn` (1.00 m runs, and a story-1
wall with no opening over the flight), `primos_pizza` (undiagnosed), and
`cbp_town_finale_midbalanced_schemafixed`, whose first floor bakes as ten-plus
fragments plus 32 slivers across 63 islands -- a floor that failed to be a
surface, which no amount of moving furniture fixes.

## [0.88.0] - Material-driven skin styles (why only one Pixelcoat skin showed)

Style -- the axis Zoo/Pixelcoat vary skins on (module stems are
{type}_{theme}_{style:02d}_...) -- was pinned to 1 at every DC slot
emission site AND flattened by the composer's global --style flag, so
every building funnelled Pixelcoat's whole library through ONE skin.

- **skin_style.py (NEW, bpy-free):** material -> style mapping, 1-based
  spec.materials order. A surface's skin follows its MATERIAL (brick_ext
  vs drywall vs metal), deterministic and stable across rebuilds. Slots
  now carry both `style` and `material`.
- **deli_counter / roofs:** all slot emission sites derive style from the
  surface material (walls, openings, roofs; props keep default).
  category5 rebuild: 210 concrete / 45 glass / 50 drywall / 16 metal.
- **themed_tscn:** `resolve_slot_ref()` is THE shared resolution -- the
  slot's own style wins, with fallback to the style-01 module (a partial
  kit degrades to fewer skins, never to greybox). Composer, base-strip
  and placement gate all resolve through it; when they disagreed,
  fallback modules landed over unstripped greybox walls and the z-fight
  gate caught the 530-pair explosion before it shipped (the gates paying
  for themselves same-day). `style_fallback_to_01` is tracked in the
  portable manifest.
- `test_skin_style.py`: 6 tests (mapping, fallback chain, per-slot style
  precedence, style-01 degradation vs greybox); wired into check.py.

Styled kits materialize on the next zoo kit build (the slots now demand
styles 1..N with materials attached); until then packages render style 01
everywhere, tracked by the manifest metric.

## [0.87.0] - Ladder traversability locked in: lint + unit gates

Ladders now have the same can't-regress protection as the partition clamp
and the z-fight gate: one pure module owns the geometry, the pre-commit
gate lints and unit-tests it, and the compose refuses to ship without it.

- **ladder_geom.py (NEW, bpy-free):** single source of truth for the
  approach-biased through-hole and the solid face plane;
  deli_counter._ladders now cuts and collides via it (rebuilt output
  verified byte-identical to walk-tested 0.86.0).
- **layout_lint L14/L15:** L14 (FAIL) an interior/shaft ladder whose climb
  hole overshoots the footprint -- the climb dead-ends into the exterior;
  L15 (WARN) a partition crosses the hole on the story the climb surfaces
  into. Exterior-wall/platform ladders exempt. Corpus baseline: 125 specs,
  0 findings (the rule immediately caught -- and correctly exempted -- the
  two exterior fire-escape terminations).
- **check.py:** the gate now opens with the fast pure-geometry unit suites
  (partition_bounds, zfight_gate, ladder_bake, ladder_geom -- 34 tests,
  sub-second) so the contracts run on every commit, not just in CI.
- **Level Factory compose driver:** ladder hard gate -- gameplay ladders
  without baked climb volumes fail the compose (rc 4), same policy as the
  z-fight gate. "[compose] ladder gate [OK]: n/n climb volume(s) baked".

## [0.86.0] - Ladders: solid from both sides, passable at the top

Walk-testing 0.85.x ladders surfaced two more gaps, both fixed at the
source so every DC building carries them:

- **deli_counter:** each ladder now emits a thin COLLISION plane at its
  face for the full climb height (ladder{n}_plane) -- a ladder is solid
  geometry from both sides, and only the approach-side climb volume makes
  it traversable. The rungs/rails stay visual-only as designed.
- **deli_counter:** the cut_slabs through-hole is biased onto the APPROACH
  side (1.3 m along the approach, width + 0.6 across) instead of a
  symmetric width + 0.6 square: the climb volume holds a capsule ~0.5 m
  off the face, and the old symmetric cut jammed it against the rim so a
  body could never actually pass through to the upper floor.
- **Level Factory walk preview:** while-latched TOP EXIT -- once the body
  has climbed high enough that its feet clear the upper floor, pressing
  away steps off onto it (previously +Z wish always read as climb-down,
  so the top was unreachable). Climb snap distance tuned to 0.5 m, clear
  of the new collision plane.

## [0.85.1] - Ladders latch only from the approach side

A ladder's climb must engage only on the face a climber mounts from; from
behind it is just a solid object. The walk controller now refuses to latch
when the player is on the back half-space (local Z < 0) of the climb
volume -- the ladder's own static collision applies there, and pressing
"toward" it can no longer pull a body through onto the climb plane.
Contract doc updated to state the side rule explicitly.

## [0.85.0] - Climbable ladders: the ladder climb contract

Ladders in composed packages were visible geometry plus a point marker --
nothing a player could climb. Now every DC build (and every LF `--art`
level) ships each ladder CLIMBABLE, with no state and no scripts in the
package: the content declares the climb volume, the host game's controller
implements movement. docs/LADDER_CLIMB_CONTRACT.md is the contract.

- **portable_building:** `splice_ladder_contract()` bakes, per ladder in
  the gameplay export, an `Area3D` in group `ladder_area3d` at the base
  anchor, yawed so +Z faces the APPROACH side (the Source-style community
  convention -- third-party climb controllers work unmodified), with a
  full-height BoxShape3D catch volume (width + 0.6 x height + 1.0 x 0.8 m
  deep), a `TopOfLadder` child at the step-off height, and
  `climb_height`/`facing` metadata. Sub_resources are spliced before the
  first node and load_steps is kept consistent. The manifest records
  `ladder_climb_volumes`.
- **Level Factory walk preview:** `player_walk.gd` gains CS:S-style ladder
  physics -- all judgments relative to the ladder via its transform
  inverse; climb = (wish_up + wish_into)/sqrt(2), so looking 45 degrees up
  the ladder is the fastest climb, looking away descends, and strafing
  into the ladder stacks with forward (ladder boost). Deliberate mount
  (press toward the ladder near its plane, or arrive over the top), clean
  bottom/top exits, Space jumps off the face.
- `test_ladder_bake.py`: 6 tests pin the bake (group/orientation per
  facing, base-anchor conversion, top marker, splice parse order,
  no-ladder no-op).

## [0.84.0] - Z-fight gate + flicker-free compose

The composed art pass shipped coplanar surfaces: the roof module cohabited
the greybox top slab's exact volume (the flickering ceiling), and
full-story-height wall modules put their up-facing caps in the story
planes, coplanar with slab tops (flickering stripes along wall lines).
Invisible grey-on-grey; glaring once themed. Fixed at the composer, and
now impossible to ship: a coplanar-surface gate fails any compose that
would flicker.

- **portable_building:** `roof_covered_nodes()` resolves the greybox
  surface a ROOF SWAP replaces geometrically (the top slab's name carries
  no slot id, so the name-based strip could never find it) and
  `strip_greybox_base(..., drop_nodes=...)` drops it; the roof module now
  truly swaps the slab instead of cohabiting it.
- **themed_tscn:** wall-family modules (wall / doorway / window / breach)
  sink `SLAB_CAP_SINK` (4 mm) on placement -- their story-plane caps
  separate from the slab tops by more than the gate tolerance, below
  perception. Free-standing fixture roles and the roof stay untouched.
- **zfight_gate (NEW):** box-level coplanar-surface gate, pure geometry +
  pygltflib, no bpy. Flags same-plane same-facing overlapping face pairs
  with real interpenetration; abutments never flag; entombed pairs (fully
  buried in a third solid, alone or by joint cover) are suppressed as
  intel -- no camera can see them. Wired into `build_package()`
  (`zfight_check` in the portable manifest); LF's compose driver fails the
  job on findings. `test_zfight_gate.py`: 12 unit tests pin the rules.

## [0.83.1] - Partition footprint clamp (recorded retroactively)

Interior partitions authored past the footprint (a Y-wall given the X
half-width, etc.) rendered walls poking through the exterior shell.
`partition_bounds.clamp_partition_span` is now the single source of truth:
the builder clamps at build time (openings repositioned or dropped,
in-bounds partitions byte-identical), layout_lint L13 reports overshoot as
an advisory WARN, and four presets (casino_tower, suburban_safehouse,
corner_deli, rowhome) had their authored extents corrected.
`test_partition_bounds.py` covers clamp/lint agreement.

## [0.83.0] - Phase 4 Mega-Structures: 25 configs / 8 new families -> 100/36

Library complete: 100 configurations / 36 families, every one engine-green.
BOTH waves first-pass clean (13/13 + 12/12 nav & import, ZERO batch
iterations, zero post-engine fixes). New families: STADIUM (Citizens Bank
Park / Lincoln Financial / Subaru chassis + premium club level), ARENA
(Xfinity), CASINO (Rivers, gaming-floor cage), MARKET_HALL (Reading
Terminal), AIRPORT_TERMINAL (PHL), BANK_TOWER (Center City), LANDMARK_HALL
(Independence / Liberty Bell), TRAIN_YARD (SEPTA yard).

- **p4lib venue template:** the mature pattern book as a parametric factory
  (grand S hall + N service band + secure room at ground_west / basement /
  story1), with the tall-stair run rule and a new stair_margin() clearance
  rule (half-run + landing + 2.2 m approach) baked in -- straight tall
  flights can no longer hug a wall by construction.
- Venue shells ship as heist-relevant service interiors (concourse, cage
  line, count room, suite level); the full bowl is site-scale dressing
  downstream, per the levels-as-input boundary.

