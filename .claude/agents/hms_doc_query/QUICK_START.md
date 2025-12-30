# HMS Documentation Query Agent - Quick Start Guide

Get started querying HEC-HMS official documentation in under 5 minutes.

---

## Overview

The HMS_DocQuery agent helps you find technical information from official HEC-HMS documentation including:
- Method parameters (loss, transform, routing, etc.)
- File format specifications
- Version-specific features
- Best practices and workflows

**Key capability:** Can view images and screenshots in documentation using dev-browser plugin.

---

## Quick Example

**Question:** "What parameters does the SCS Curve Number loss method require?"

**Answer:** From https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm

```
Required Parameters:
1. Curve Number - SCS Curve Number (0-100, dimensionless)
2. Directly Connected Impervious Area - Percentage (%)

Optional Parameters:
3. Initial Abstraction (Ia) - Amount of precipitation before runoff (mm or in)
   - If not specified, calculated as 0.2 × potential retention (from CN)
```

---

## Installation

### Prerequisites

- Python 3.10+
- hms-commander installed
- dev-browser plugin (optional, for viewing images)

### Setup

```bash
# Install hms-commander
pip install hms-commander

# Or for development
cd hms-commander
pip install -e .
```

---

## Basic Usage

### Method 1: Direct Import

```python
from hms_agents.HMS_DocQuery import validate_method_name, get_method_parameters

# Validate a method name
is_valid, suggestion = validate_method_name("SCS Curve Number", "loss")
print(f"Valid: {is_valid}")  # True

# Get method parameters (returns placeholder currently)
params = get_method_parameters("loss", "SCS Curve Number")
if params:
    print(f"Required: {params.get_required_params()}")
    print(f"Optional: {params.get_optional_params()}")
```

### Method 2: Query Documentation (with Claude Code)

```python
from hms_agents.HMS_DocQuery import query_documentation

result = query_documentation(
    "What parameters does Deficit and Constant loss method require?",
    focus_area="loss_methods"
)

print(result.answer)
print("\nSources:")
for url in result.urls:
    print(f"  - {url}")
```

---

## Using with dev-browser (View Images!)

### 1. Start dev-browser Server

```bash
cd ~/.claude/plugins/cache/dev-browser-marketplace/dev-browser/*/skills/dev-browser
npm install  # First time only
npx tsx scripts/start-server.ts
```

Wait for "Ready" message.

### 2. Query with Screenshots

```bash
cd ~/.claude/plugins/cache/dev-browser-marketplace/dev-browser/*/skills/dev-browser

npx tsx <<'EOF'
import { connect, waitForPageLoad } from "@/client.js";

const client = await connect("http://localhost:9222");
const page = await client.page("hms-docs");

// Navigate to SCS Curve Number documentation
await page.goto("https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/canopy-surface-infiltration-and-runoff-volume/infiltration/scs-curve-number-loss-model");
await waitForPageLoad(page);

// Take screenshot
await page.screenshot({ path: "tmp/scs-cn.png", fullPage: true });

// Extract headings
const headings = await page.evaluate(() => {
  return Array.from(document.querySelectorAll('h1, h2, h3'))
    .map(h => h.textContent)
    .slice(0, 5);
});

console.log("Documentation sections:");
headings.forEach(h => console.log(`  - ${h}`));
console.log("\nScreenshot saved: tmp/scs-cn.png");

await client.disconnect();
EOF
```

**Output:**
```
Documentation sections:
  - SCS Curve Number Loss Model
  - Basic Concepts and Equations
  - Required Parameters
  - A Note on Parameter Estimation

Screenshot saved: tmp/scs-cn.png
```

The screenshot shows the full documentation page including equations and parameter descriptions!

---

## Common Use Cases

### 1. Validate Method Names

```python
from hms_agents.HMS_DocQuery import validate_method_name

# Check if method exists
is_valid, suggestion = validate_method_name("clark unit hydrograph", "transform")
if is_valid:
    print(f"Valid method: {suggestion}")  # Clark Unit Hydrograph (correct case)
else:
    print(f"Invalid. Did you mean: {suggestion}?")
```

### 2. List Available Methods

```python
from hms_commander._constants import (
    LOSS_METHODS,
    TRANSFORM_METHODS,
    ROUTING_METHODS
)

print("Loss Methods:")
for method in LOSS_METHODS:
    print(f"  - {method}")

print("\nTransform Methods:")
for method in TRANSFORM_METHODS:
    print(f"  - {method}")
```

### 3. Get Documentation URLs

```python
from hms_agents.HMS_DocQuery import get_focus_area_url

# Get URLs for loss methods documentation
urls = get_focus_area_url("loss_methods")
for url in urls:
    print(url)
```

**Output:**
```
https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/latest/basin-models/loss-methods/
https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/latest/
```

---

## Focus Areas

Use these focus areas to narrow documentation searches:

| Focus Area | Documentation Section |
|------------|----------------------|
| `loss_methods` | Loss methods (SCS CN, Green-Ampt, etc.) |
| `transform_methods` | Transform methods (Clark, Snyder, etc.) |
| `baseflow_methods` | Baseflow methods |
| `routing_methods` | Routing methods (Muskingum, Lag, etc.) |
| `precip_methods` | Precipitation methods |
| `file_formats` | File format specifications (.basin, .met, etc.) |
| `workflows` | Modeling workflows and best practices |
| `release_notes` | Version-specific changes |
| `installation` | Installation and setup |
| `troubleshooting` | Common issues and solutions |

---

## Integration Tests

Run the integration tests to verify dev-browser setup:

```bash
cd hms-commander/hms_agents/HMS_DocQuery
python test_webfetch_integration.py
```

**Expected output:**
```
✓ dev-browser server is running on localhost:9222

TEST 1: Basic Navigation to HMS User's Manual
✓ Navigation successful!

TEST 2: Navigate to SCS Curve Number Method Page
✓ Navigation successful!
  Images found: 8

TEST 3: Get ARIA Snapshot of Documentation Page
✓ ARIA snapshot retrieved!

Total: 3/3 tests passed

✓ All tests passed! dev-browser integration is working correctly.

Key finding: dev-browser CAN view images in HMS documentation!
```

---

## Troubleshooting

### dev-browser server not starting

**Problem:** `bun: command not found`

**Solution:** Use npm instead:
```bash
npm install
npx tsx scripts/start-server.ts
```

### Port 9222 already in use

**Problem:** Another process is using port 9222

**Solution:** Kill existing dev-browser or use different port:
```bash
# Kill existing process (Linux/Mac)
lsof -i :9222 | grep LISTEN | awk '{print $2}' | xargs kill

# Kill existing process (Windows)
netstat -ano | findstr :9222
taskkill /PID <PID> /F
```

### Screenshots not saving

**Problem:** Screenshot path not found

**Solution:** Make sure you're in dev-browser directory:
```bash
cd ~/.claude/plugins/cache/dev-browser-marketplace/dev-browser/*/skills/dev-browser
# Then run the script
```

---

## Next Steps

1. **Explore documentation** - Navigate HMS docs with dev-browser
2. **Build method index** - Create structured parameter database
3. **Automate queries** - Integrate with hms-commander workflows
4. **Visual comparison** - Compare method configurations visually

---

## Resources

**Official HMS Documentation:**
- User's Manual: https://www.hec.usace.army.mil/confluence/hmsdocs/hmsum/latest/
- Technical Reference: https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/latest/
- Downloads: https://www.hec.usace.army.mil/software/hec-hms/downloads.aspx

**Agent Documentation:**
- AGENT.md - Complete agent documentation
- WEBFETCH_INTEGRATION_REPORT.md - Integration test results
- test_webfetch_integration.py - Test suite

**hms-commander:**
- GitHub: (repository URL)
- Documentation: See CLAUDE.md in repo root

---

## Questions?

For questions about:
- **HMS_DocQuery agent** - See AGENT.md
- **dev-browser plugin** - See dev-browser skill documentation
- **hms-commander** - See main repository documentation
- **HEC-HMS software** - Visit https://www.hec.usace.army.mil/software/hec-hms/

---

**Version:** 1.0
**Last Updated:** 2025-12-10
**Agent Status:** ✅ READY (images confirmed visible via dev-browser)
