# HEC-HMS 4.13 Frequency Storm reference fixtures

Reference hyetographs for `hms_commander.BalancedFrequencyStorm`, computed by HEC-HMS 4.13
(build 134654, Java 17.0.11) and extracted from the run output DSS.

- `hms_reference_series.csv` - `case,block,hms_incremental_in`: HMS incremental precipitation
  per computation interval (inches), first `duration/interval` blocks of Sub1 `PRECIP-EXCESS`.
- `cases.json` - inputs for every case (DDF depths, storm duration, interval, peak position,
  storm area, conversion options) plus provenance.
- `kerrville_pds_depths.csv` - NOAA Atlas 14 Vol. 11 v2 partial-duration depth table (inches)
  for Kerrville TX (30.05 N, -99.14 W), the DDF source for all cases.

Project used: one subbasin (10 sq mi), Loss Rate `None` (so PRECIP-EXCESS equals met-model
precipitation), SCS transform, Baseflow `None`; control time interval equals the storm time
interval. Met models are `Frequency Based Hypothetical` (the "Frequency Storm" method) in the
native 4.13 layout (`Depth <min>:` rows) except the `leg_*` cases, which use the 3.x layout
(`Depth:` rows with no 10-/30-min entries, which HMS augments on load).

The paired `resort_perturbed_off` and `resort_perturbed_on` cases use the same
positive, nondecreasing perturbed DDF table. Its nested increments are
non-monotone, so the HMS 4.13 `Re-sort Storm Symmetrically` setting changes the
output. They document the setting's observed behavior; the public generator does
not expose a corresponding option.

Regenerate (needs HEC-HMS 4.13 on Windows):

    python scripts/generate_frequency_storm_hms_fixtures.py
