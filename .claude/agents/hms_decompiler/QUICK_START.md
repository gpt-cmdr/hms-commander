# HMS Decompiler - Quick Start Guide

**Purpose**: 5-minute guide to using the HMS Decompiler agent for common tasks.

---

## What Is This Agent?

The HMS Decompiler agent helps you understand HEC-HMS internals through decompiled Java classes. Use it when:
- Checking if a JythonHms method exists
- Understanding HMS 3.x vs 4.x differences
- Finding CLI options
- Debugging HMS behavior
- Discovering undocumented features

---

## Quick Tasks

### Task 1: Check If JythonHms Method Exists

**Question**: "Does HMS 4.13 support `SetTimeWindow()`?"

**Answer**:
1. Open `knowledge/JYTHON_HMS_API.md`
2. Search for "SetTimeWindow"
3. Result: ✅ YES - See method signature

**API**:
```python
JythonHms.SetTimeWindow(startDate, startTime, endDate, endTime)
# Example: SetTimeWindow("01Jan2020", "00:00", "02Jan2020", "00:00")
```

---

### Task 2: Check HMS 3.x Compatibility

**Question**: "Does HMS 3.3 support Jython scripting?"

**Answer**:
1. Open `knowledge/HMS_3x_SUPPORT.md`
2. Result: ✅ YES (discovered via decompilation!)

**Key Difference**: HMS 3.x requires Python 2 syntax

```python
# HMS 3.x (Python 2)
print "Computing run"
Compute("Run 1")

# HMS 4.x (Python 3)
print("Computing run")
ComputeRun("Run 1")
```

---

### Task 3: Find CLI Options

**Question**: "How do I run HMS without the GUI?"

**Answer**:
1. Open `knowledge/HMS_CLI_OPTIONS.md`
2. Search for "lite"
3. Result: Use `-lite` or `-l` flag

**Usage**:
```batch
HEC-HMS.cmd -lite -script path/to/script.py
```

---

### Task 4: Compare Versions

**Question**: "What's different between HMS 3.x and 4.x?"

**Answer**:
1. Open `knowledge/HMS_3x_SUPPORT.md`
2. See "Key Differences" table

**Major Differences**:
- **Architecture**: 3.x is 32-bit, 4.x is 64-bit
- **Python**: 3.x uses Python 2, 4.x uses Python 3
- **Memory**: 3.x limited to ~1.3 GB, 4.x supports 32+ GB
- **API**: 3.x uses `Compute()`, 4.x uses `ComputeRun()`

---

### Task 5: Decompile New Class

**Question**: "How do I investigate `hms.model.OptimizationManager`?"

**Answer**:
1. Use decompiler:
   ```batch
   cd tools
   decompile.bat "C:\Program Files\HEC\HEC-HMS\4.13\hms.jar" "hms.model.OptimizationManager" output
   ```
2. Review: `output/hms/model/OptimizationManager.java`

**See**: `examples/decompile_new_class.md` for complete workflow

---

## Knowledge Files

| File | What It Contains |
|------|------------------|
| `knowledge/JYTHON_HMS_API.md` | Complete JythonHms method reference (HMS 4.x) |
| `knowledge/HMS_3x_SUPPORT.md` | HMS 3.x Jython support discovery and differences |
| `knowledge/HMS_CLI_OPTIONS.md` | Command-line arguments (all HMS versions) |

---

## Reference Classes

| File | HMS Version | Purpose |
|------|-------------|---------|
| `reference/HMS_4.13/hms/Hms.java` | 4.13 | Entry point, CLI parsing |
| `reference/HMS_4.13/hms/model/JythonHms.java` | 4.13 | Scripting API implementation |
| `reference/HMS_3.3/hms/model/JythonHms.java` | 3.3 | Scripting API (3.x version) |

---

## Tools

| Tool | Purpose |
|------|---------|
| `tools/cfr.jar` | CFR Java decompiler |
| `tools/decompile.bat` | Windows decompilation wrapper |
| `tools/decompile.sh` | Linux/Mac decompilation wrapper |
| `tools/TOOL_USAGE.md` | Detailed decompilation guide |

---

## Examples

| Example | What It Demonstrates |
|---------|---------------------|
| `examples/query_jython_api.md` | Check if method exists in JythonHms |
| `examples/version_compatibility.md` | Compare HMS 3.x vs 4.x differences |
| `examples/decompile_new_class.md` | Decompile and analyze new HMS class |

---

## Decompiling Additional Classes

**On-Demand Decompilation**: Use the included CFR decompiler for any HMS class

**What's included**:
- CFR decompiler (tools/cfr.jar)
- Decompilation scripts (decompile.bat/sh)
- Essential decompiled classes (reference/)

**For deep investigation**: Decompile HMS classes as needed using the tools provided

---

## Next Steps

**Need more detail?**
- Read `AGENT.md` for comprehensive documentation
- Check `examples/` for complete workflows
- Use `tools/` to decompile additional HMS classes

**Have questions?**
- Check AGENT.md FAQ section
- Review existing issues in GitHub
- Ask on hms-commander discussions

---

## Common Questions

**Q: Is this the same as HMS_DocQuery?**
A: No. HMS_DocQuery searches official documentation. This agent investigates internals via decompiled code.

**Q: Can I use this for HMS 4.14?**
A: Partially. CLI and general patterns apply. Decompile HMS 4.14 classes for specific details.

**Q: Does HMS 3.5 support Jython?**
A: Yes! HMS 3.3+ supports Jython (Python 2 syntax). See `knowledge/HMS_3x_SUPPORT.md`.

**Q: How accurate is decompiled code?**
A: Very accurate for understanding behavior. May have minor formatting differences from original source.

---

**Maintained by**: hms_decompiler agent
**Agent version**: 1.0
**Last updated**: 2025-12-12
