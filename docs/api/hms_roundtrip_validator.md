# HmsRoundTripValidator

Clone-first HMS parser-of-record validation helpers for TauDEM-to-HMS project bootstraps.

Use this validator to prove that generated TauDEM-to-HMS project artifacts survive `OpenProject -> SaveAllProjectComponents -> Exit` cleanly in HEC-HMS. Passing round-trip validation means the scaffold is import-valid; it does not replace parameter QAQC, warning review, or the future pre-HMS readiness gate needed before production promotion.

::: hms_commander.HmsRoundTripValidator
    options:
      show_source: true
      heading_level: 2
      show_root_heading: true
      show_root_toc_entry: false
      members_order: source
