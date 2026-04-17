---
name: Feature Request
about: Suggest a new feature or enhancement
title: "[Feature] "
labels: enhancement
---

## Problem or Use Case

<!-- What problem does this solve? What workflow does it enable? -->

## Source Workflow

<!-- Which repo or workflow exposed this gap? Example: ras-agent Illinois integration -->

## Why This Belongs In `hms-commander`

<!-- Explain the generalizable hydrology/HMS/TauDEM/GIS value of landing this here -->

## Proposed Solution

<!-- How should it work? Include API design if you have ideas -->

```python
# Example of how the feature would be used
from hms_commander import NewFeature

result = NewFeature.do_something(basin_file="model.basin", hms_object=hms)
```

## Alternatives Considered

<!-- Other approaches you've thought about -->

## Downstream Impact

<!-- Which repos or workflows are blocked or enabled by this? Include issue links when relevant -->

## Additional Context

<!-- Related HEC-HMS features, example projects, references, etc. -->

---

> **Tip**: Consider prototyping with your LLM agent. Clone the repo, have your agent read `STYLE_GUIDE.md` and the `AGENTS.md` files, and submit a PR with a working implementation. We welcome LLM-assisted contributions.
