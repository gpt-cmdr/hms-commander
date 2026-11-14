# HEC-HMS run logs captured from real computes

These files are output from HEC-HMS and shipped HEC-HMS sample files. They
are stored as `.txt` because the repository ignores `tests/**/*.log`.
`.gitattributes` keeps their bytes, including mixed line endings. The only
change is one redacted folder path, noted below.

The projects are the `tenk` and `castro` samples from the HEC-HMS 4.13
`samples.zip` (`.hms` file `Version: 4.13`), extracted with
`HmsExamples.extract_project(<name>, version="4.13")`. The runs were computed
on 2026-11-13 through the generated Jython scripts
(`HmsJython.generate_compute_script` or `generate_batch_compute_script`, then
`HmsJython.execute_script`). Before each run, the run's shipped log and
results DSS were deleted.

| File | HEC-HMS | Content |
|---|---|---|
| `tenk_hms410_aborted_run_log.txt` | 4.10 | `Jan_96_storm.log` of run "Jan 96 storm". 4.10 cannot read the 4.13 grid data source: `ERROR 20137`, `ERROR 20358`, then `WARNING 15303: Aborted run`. No `NOTE 15302`. |
| `tenk_hms410_aborted_stdout.txt` | 4.10 | Standard output of the same process. The generated script's `Error during computation:` line follows the echoed errors. |
| `tenk_hms413_finished_run_log.txt` | 4.13 | `Jan_96_storm.log` of run "Jan 96 storm". The run finishes (`NOTE 15302`). It has warnings (`WARNING 40017`, `WARNING 40503`) and no ERROR line. |
| `castro_hms413_future_finished_run_log.txt` | 4.13 | Run "Future" finished (`NOTE 15302`). Both castro runs had `Log File: shared.log` and were computed in one batch session. HEC-HMS rewrote the shared log for each run, so only the last run's ("Future") section remained. |
| `castro_hms413_future_aborted_run_log.txt` | 4.13 | `Future.log` of run "Future", computed with the project's DSS files deleted, so the gage data is missing: `ERROR 10311`, `ERROR 20358`, `WARNING 15303: Aborted run "Future"`. The absolute project folder in the `File:` line is replaced by `<project folder>`. |
| `run_files/tenk.run`, `run_files/castro.run` | 4.13 | The shipped sample `.run` files, unchanged. |

Before the fix, `HmsJython.execute_script` reported success for both tenk
runs, and the aborted 4.10 run still created `Jan_96_storm.dss`.

Every shipped sample run log in the HEC-HMS 4.4.1, 4.5, 4.6, 4.7.1, 4.8, 4.9,
4.10, 4.11, 4.12 and 4.13 `samples.zip` files (70 logs) quotes its run's name
in `NOTE 15301` (began) and `NOTE 15302` (finished). Every run in those
samples' `.run` files declares `Log File:` and `DSS File:`.
