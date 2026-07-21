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

