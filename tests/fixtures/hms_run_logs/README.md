# HEC-HMS run logs captured from real computes

These files are unedited output from HEC-HMS. They are stored as `.txt`
because the repository ignores `tests/**/*.log`.

Source project: the `tenk` sample from the HEC-HMS 4.13 `samples.zip`
(`.hms` file `Version: 4.13`), extracted with
`HmsExamples.extract_project("tenk", version="4.13")`. The shipped
`Jan_96_storm.dss` and `Jan_96_storm.log` were deleted before each run. The
run "Jan 96 storm" was computed through the generated Jython compute script
(`HmsJython.generate_compute_script` and `HmsJython.execute_script`) on
2026-11-13.

| File | HEC-HMS | Content |
|---|---|---|
| `tenk_hms410_aborted_run_log.txt` | 4.10 | `Jan_96_storm.log`. 4.10 cannot read the 4.13 grid data source: `ERROR 20137`, `ERROR 20358`, then `WARNING 15303: Aborted run`. No `NOTE 15302`. |
| `tenk_hms410_aborted_stdout.txt` | 4.10 | Standard output of the same process. The generated script's `Error during computation:` line follows the echoed errors. |
| `tenk_hms413_finished_run_log.txt` | 4.13 | `Jan_96_storm.log`. The run finishes (`NOTE 15302`). It has warnings (`WARNING 40017`, `WARNING 40503`) and no ERROR line. |

Before the fix, `HmsJython.execute_script` reported success for both runs,
and the aborted 4.10 run still created `Jan_96_storm.dss`.

The `NOTE 15301` (began) and `NOTE 15302` (finished) codes also appear in
every shipped sample run log in the HEC-HMS 4.4.1, 4.5, 4.7.1, 4.9, 4.10,
4.12 and 4.13 `samples.zip` files.
