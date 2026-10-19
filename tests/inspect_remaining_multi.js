let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

// Check the remaining 10 holes at 1800 from test_multi_era_closure logic
// Let's inspect their sizes and locations:
let bbox = [9.5, 49.5, 11.5, 50.8];
let target_ts = 1800 * 525960;

// Let's run a test to see the 10 holes
let test_years = [1707, 1736, 1753, 1787, 1800, 1803, 1806, 1815];

// ...
