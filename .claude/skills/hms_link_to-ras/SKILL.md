---
name: hms_link_to-ras
description: Prepare the HMS side of a hydrograph handoff to RAS using current package contracts, explicit time and units, and reviewed outlet mapping.
shared_corpus: true
harness_scope: shared
source_owner: gpt-cmdr
security_review: internal
---

# Link HMS to RAS

Use [HMS–RAS Integration](../hms-ras-integration/SKILL.md) as the canonical handoff workflow. Scope this skill to HMS source/result preparation; route receiving-boundary work through the available RAS Commander workflow. Inspect current installed extraction APIs and optional dependencies before using them. Keep checks and mapping evidence in the shared integration contract; do not duplicate signatures or fixed engineering thresholds here.
