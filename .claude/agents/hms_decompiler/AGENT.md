# HMS Decompiler Agent

**Purpose**: Decode HEC-HMS Java classes to discover undocumented APIs, Jython scripting interfaces, and internal implementations that support hms-commander development.

**Version**: 1.0
**Last Updated**: 2025-12-12
**Status**: Production

---

## Overview

The HMS Decompiler Agent is a knowledge base and reference library for understanding HEC-HMS internals through decompiled Java source code. It provides:

1. **Decompiled Reference Classes** - Actual HMS Java code for analysis
2. **Knowledge Files** - Structured documentation of APIs and behaviors
3. **Tools & Scripts** - Utilities for decompiling HMS JAR files
4. **Integration with hms-commander** - Supports library development and feature discovery

### When to Use This Agent

- **Understanding HMS internals**: How does HMS really work under the hood?
- **Discovering undocumented APIs**: What methods are available in JythonHms?
- **Version compatibility**: What changed between HMS 3.x and 4.x?
- **hms-commander development**: Implementing new features or fixing bugs
- **Script generation**: Creating Jython scripts for HMS automation
- **Troubleshooting**: Understanding error codes and internal behavior

### What This Agent Does NOT Do

- Execute HMS workflows (see Update_3_to_4 agent)
- Query official documentation (see HMS_DocQuery agent)
- Provide support for HMS GUI operations
- Handle DSS file operations (use hms_commander HmsDss directly)

---

## Directory Structure

```
hms_agents/hms_decompiler/
├── AGENT.md                          # This file
├── knowledge/                         # Knowledge base files
│   ├── JYTHON_HMS_API.md            # Complete JythonHms API reference
│   ├── HMS_3x_SUPPORT.md            # HMS 3.x Jython scripting support
│   ├── HMS_CLI_OPTIONS.md           # HEC-HMS command-line options
│
├── reference/                        # Decompiled source code
│   ├── HMS_3.3/                     # HMS version 3.3 classes
│   │   ├── hms/
│   │   │   ├── model/
│   │   │   │   └── JythonHms.java   # HMS 3.3 Jython API
│   │   │   └── ...
│   │   ├── hec/
│   │   │   └── map/hms/
│   │   │       └── ...
│   │   └── hms/
│   │       └── ...
│   │
│   └── HMS_4.13/                    # HMS version 4.13 classes
│       ├── hms/
│       │   ├── model/
│       │   │   ├── JythonHms.java   # HMS 4.13 Jython API
│       │   │   ├── ProjectManager.java
│       │   │   └── ...
│       │   ├── command/
│       │   │   └── HmsCommandServer.java
│       │   └── ...
│       └── ...
│
├── tools/                           # Decompilation utilities
│   └── cfr.jar                      # CFR Java decompiler
│
└── examples/                        # Example usage and queries
    └── (example scripts)
```

---

## Quick Navigation

**What file to check for different questions:**

| Question | File/Location |
|----------|---------------|
| "What methods are available in JythonHms?" | `knowledge/JYTHON_HMS_API.md` |
| "How do I execute a Jython script in HMS 3.3?" | `knowledge/HMS_3x_SUPPORT.md` |
| "What command-line options does HMS support?" | `knowledge/HMS_CLI_OPTIONS.md` |
| "How is JythonHms.Compute implemented?" | `reference/HMS_4.13/hms/model/JythonHms.java` |
| "What's the difference between HMS 3.3 and 4.13?" | `knowledge/HMS_3x_SUPPORT.md` (compatibility section) |
| "What error codes does HMS use?" | `reference/HMS_*.*/hms/model/JythonHms.java` (error handling) |
| "How does HMS manage projects internally?" | `reference/HMS_4.13/hms/model/ProjectManager.java` |
| "Can HMS 3.3 run Jython scripts?" | `knowledge/HMS_3x_SUPPORT.md` (confirmed yes!) |

---

## Knowledge Files

### 1. JYTHON_HMS_API.md

**Complete API reference** for JythonHms class (HMS 4.13).

**Contains:**
- Project management methods (OpenProject, SaveAllProjectComponents)
- Basin model operations (OpenBasinModel, SetBasinUnitSystem)
- Compute methods (ComputeRun, ComputeTrial, ComputeForecast)
- Parameter modification (SetLossRateValue, SetBaseflowValue, SetBlendMethod)
- Time window management (SetTimeWindow)
- Results manipulation (CopyRunResults, RenameStateGridBPart)
- Deprecated/not implemented methods
- Complete example scripts
- Internal implementation notes

**Usage:**
```python
from hms_commander import HmsJython

# Use API knowledge to generate correct script
script = HmsJython.generate_compute_script(
    project_path="C:/HMS/MyProject",
    run_name="Run 1"
)
```

**Key Discoveries:**
- `ComputeRun()` preferred over deprecated `Compute()` method
- Many optimization methods throw NotImplemented exceptions in 4.x
- Project stored as static reference internally
- Error messages use 12xxx series error codes

**Last Updated**: 2025-12-10 (HMS 4.13 Build 134654)

---

### 2. HMS_3x_SUPPORT.md

**MAJOR DISCOVERY**: HMS 3.x versions DO support Jython scripting!

**Contains:**
- Supported versions (3.3 confirmed, 3.4-3.5 likely, <3.3 unknown)
- CLI options for HMS 3.3 (-script, -debug, -lite, -disableprint)
- JythonHms API for HMS 3.3 (very similar to 4.x with key differences)
- Key differences between 3.x and 4.x APIs
- Example scripts for HMS 3.3
- Execution instructions (must run from HMS directory)
- Architecture notes (32-bit Java, native DLLs)
- hms-commander implementation status
- Test results proving HMS 3.3 support works

**Usage:**
```python
from hms_commander import HmsJython

# Generate Python 2-compatible script for HMS 3.3
script = HmsJython.generate_compute_script(
    project_path="C:/Projects/MyOldProject",
    run_name="Run 1",
    python2_compatible=True  # Required for HMS 3.x
)

# Execute (version auto-detected)
success, stdout, stderr = HmsJython.execute_script(
    script_content=script,
    hms_exe_path="C:/Program Files (x86)/HEC/HEC-HMS/3.3",
    working_dir="C:/Projects/MyOldProject"
)
```

**Key Differences from HMS 4.x:**

| Feature | HMS 3.x | HMS 4.x |
|---------|---------|---------|
| Jython Support | ✅ Yes | ✅ Yes |
| ComputeRun method | ❌ No (use `Compute`) | ✅ Yes |
| ComputeTrial method | ❌ No | ✅ Yes |
| ComputeForecast method | ❌ No | ✅ Yes |
| Optimize() method | ✅ Works | ❌ NotImplemented |
| SelectOptimizationTrial | ✅ Works | ❌ NotImplemented |
| SetParameterLock | ✅ Works | ❌ NotImplemented |
| MoveResults method | ✅ Yes (vs CopyRunResults) | ❌ No |

**Last Updated**: 2025-12-10 (Test proven!)

---

### 3. HMS_CLI_OPTIONS.md

**Complete command-line interface** discovered through decompilation of hms.Hms.main().

**Contains:**
- Script execution options (-s, -script)
- Debug options (-d, -debug)
- Display options (-l, -lite, -disableprint)
- Information flag (-info)
- Command server mode (RMI)
- Java bytecode analysis (actual main() method decompilation)
- Example usage for each option
- Version compatibility matrix
- Key classes for further analysis

**Usage:**
```bash
# Run a Jython script in HMS 4.13
cd "C:\Program Files\HEC\HEC-HMS\4.13"
HEC-HMS.cmd -script "C:\path\to\script.py"

# Run in debug mode
HEC-HMS.cmd -debug -script "C:\path\to\script.py"

# Get version info
HEC-HMS.cmd -info

# Start command server on specific port
HEC-HMS.cmd CommandServer port=1099
```

**Last Updated**: 2025-12-10

---

## Reference Classes

### HMS 3.3 Classes

Located in: `reference/HMS_3.3/hms/model/`

**Available Classes:**
- `JythonHms.java` - Jython scripting API

**Related Packages:**
- `hms.Hms` - Entry point (main method)
- `hec.map.hms.*` - Mapping/GIS related

### HMS 4.13 Classes

Located in: `reference/HMS_4.13/hms/`

**model/ Package:**
- `JythonHms.java` - Jython scripting API
- `ProjectManager.java` - Project management (singleton)
- Supporting classes for basin, met, control models

**command/ Package:**
- `HmsCommandServer.java` - RMI command server implementation
- Related command processor classes

---

## Tools

### cfr.jar

**Java Decompiler** - Modern, high-quality decompiler for Java bytecode.

**Location:** `tools/cfr.jar` (2.1 MB)

**Usage:**

```bash
# Decompile a single JAR file
java -jar cfr.jar <input.jar> --outputdir <output_directory>

# Example
java -jar cfr.jar "C:\Program Files\HEC\HEC-HMS\4.13\java\hms.jar" --outputdir decompiled/

# Decompile specific class
java -jar cfr.jar <input.jar> --analysisonly --outputtype kast

# Options
--outputdir <dir>        # Output directory for decompiled classes
--classfilter <pattern>  # Filter classes to decompile (e.g., hms/model/*)
--outputtype <type>      # Output format (java, kast)
--analysisonly          # Analyze without full decompilation
```

**Why CFR:**
- Handles modern Java syntax cleanly
- Excellent for decompiling HMS JAR files
- Better at recovering method signatures than alternatives
- Active maintenance and frequent updates

---

## Use Cases

### Use Case 1: Understanding JythonHms API

**Scenario**: You're implementing a new hms-commander feature and need to know what JythonHms methods are available.

**Steps:**
1. Read `knowledge/JYTHON_HMS_API.md` for complete method list
2. Find the specific method (e.g., `SetLossRateValue`)
3. Check parameter types, required arguments, exceptions
4. Refer to decompiled source if behavior unclear
5. Implement in hms-commander with confidence

**Example:**
```python
# From JYTHON_HMS_API.md:
# SetLossRateValue(elementName, parameterName, value)
# Parameters:
# - elementName (String): Name of subbasin
# - parameterName (String): Parameter name (e.g., "SCSCurveNumber")
# - value (Double): Parameter value

# Implement in hms-commander
HmsBasin.set_loss_parameter(
    basin_file="project.basin",
    subbasin_name="Sub1",
    parameter_name="SCSCurveNumber",
    value=80.0
)
```

---

### Use Case 2: Debugging HMS 3.x Support

**Scenario**: An hms-commander user has HMS 3.3 and wants to run simulations. You need to verify API differences.

**Steps:**
1. Check `knowledge/HMS_3x_SUPPORT.md` for confirmed support
2. Review key differences table
3. Generate Python 2-compatible script using `python2_compatible=True`
4. Reference `reference/HMS_3.3/hms/model/JythonHms.java` for API differences
5. Use `Compute()` instead of `ComputeRun()` for HMS 3.3

**Example:**
```python
from hms_commander import HmsJython

# HMS 3.3 requires Python 2 syntax
script = """
from hms.model import JythonHms

JythonHms.OpenProject("tifton", "C:/HMS/tifton")
JythonHms.OpenBasinModel("tifton")
JythonHms.Compute("Run 1")  # Use Compute(), not ComputeRun()!
JythonHms.SaveAllProjectComponents()
JythonHms.Exit(0)
"""

success, stdout, stderr = HmsJython.execute_script(
    script_content=script,
    hms_exe_path="C:/Program Files (x86)/HEC/HEC-HMS/3.3",
    working_dir="C:/HMS/tifton"
)
```

---

### Use Case 3: Discovering Error Codes

**Scenario**: Your HMS script fails with error code 12020. What does it mean?

**Steps:**
1. Look in `reference/HMS_4.13/hms/model/JythonHms.java`
2. Search for error code pattern "12020"
3. Read surrounding code context
4. Check exception handling to understand root cause
5. Update hms-commander error handling with new knowledge

**From decompilation:**
```java
// Example error code pattern discovered
if (/* some condition */) {
    throw new PyException("ERROR 12020: Project not found");
}
```

---

### Use Case 4: Version Compatibility Check

**Scenario**: You need to support both HMS 3.x and 4.x. What methods work in both?

**Steps:**
1. Compare `reference/HMS_3.3/hms/model/JythonHms.java` with `reference/HMS_4.13/hms/model/JythonHms.java`
2. Check `knowledge/HMS_3x_SUPPORT.md` differences table
3. Write compatibility wrapper in hms-commander
4. Test with both versions

**Example Wrapper:**
```python
class HmsJython:
    @staticmethod
    def compute_run(run_name, hms_version):
        """Compute a run, using correct method name for version."""
        if hms_version.startswith("3"):
            return f'JythonHms.Compute("{run_name}")'
        else:
            return f'JythonHms.ComputeRun("{run_name}")'
```

---

### Use Case 5: Understanding Time Series Results

**Scenario**: You want to know how HMS stores results internally for DSS extraction.

**Steps:**
1. Read `knowledge/JYTHON_HMS_API.md` results methods section
2. Check `reference/HMS_4.13/hms/model/JythonHms.java` implementation details
3. Understand RenameStateGridBPart method for DSS pathname manipulation
4. Implement HmsResults class methods based on discovered behavior

**From knowledge:**
```
RenameStateGridBPart(newBPart)
Renames the B-part of state grid DSS paths.
This allows HMS to write results to different DSS locations.
```

---

## Integration with hms-commander

The hms_decompiler agent directly supports hms-commander development:

### 1. HmsJython.py Implementation

The `HmsJython` class generates and executes Jython scripts based on decompiled API knowledge:

```python
# hms_commander/HmsJython.py uses knowledge from:
# - JYTHON_HMS_API.md (method signatures)
# - HMS_3x_SUPPORT.md (version differences)
# - HMS_CLI_OPTIONS.md (execution options)

from hms_commander import HmsJython

script = HmsJython.generate_compute_script(
    project_path="C:/HMS/Project",
    run_name="Run 1",
    python2_compatible=False  # Automatically set based on version
)

success, stdout, stderr = HmsJython.execute_script(
    script_content=script,
    hms_exe_path="C:/Program Files/HEC/HEC-HMS/4.13"
)
```

### 2. HmsBasin.py Implementation

Parameter setting methods derived from decompiled API:

```python
# hms_commander/HmsBasin.py
# Based on: SetLossRateValue() from JYTHON_HMS_API.md

HmsBasin.set_loss_parameter(
    basin_file="project.basin",
    subbasin_name="Sub1",
    parameter_name="SCSCurveNumber",
    value=75.0
)
```

### 3. Error Handling

HMS error codes and exceptions documented through decompilation:

```python
# From HmsJython error handling
# Based on decompiled hms/model/JythonHms.java error patterns
if "ERROR 12xxx" in stdout:
    # HMS-specific error occurred
    pass
```

### 4. Version Detection

Automatic HMS version detection for proper script generation:

```python
from hms_commander import HmsJython

# Version detected from HMS installation
# Uses knowledge of CLI options from HMS_CLI_OPTIONS.md
version = HmsJython.detect_version("C:/Program Files/HEC/HEC-HMS/4.13")
```

---

## Agent Completeness

This agent is **self-contained** and includes all necessary reference data:

**Included Resources:**
- Complete JythonHms API reference (HMS 3.3 and 4.13)
- Version compatibility documentation
- CLI options reference
- Essential decompiled classes (JythonHms.java, Hms.java)
- Decompilation tools (cfr.jar)
- Usage examples and workflows

**No External Dependencies:**
- All knowledge files are included in this agent
- All tools are provided in `tools/` directory
- Reference classes cover common use cases
- Examples demonstrate complete workflows

**On-Demand Decompilation:**
- Use `tools/cfr.jar` to decompile any HMS class
- Add findings to agent's `reference/` directory as needed
- Document high-value discoveries in `knowledge/` files

---

## Examples

### Example 1: Generate HMS 4.13 Script

```python
from hms_commander import HmsJython

# Script based on JYTHON_HMS_API.md
script = """
from hms.model import JythonHms

# Open project (ProjectName must match .hms file!)
JythonHms.OpenProject("tifton", "C:/HMS/tifton")

# Open basin model
JythonHms.OpenBasinModel("tifton")

# Modify parameter
JythonHms.SetLossRateValue("TC", "SCSCurveNumber", 85)

# Set time window
JythonHms.SetTimeWindow("01Jan2020", "00:00", "02Jan2020", "00:00")

# Run simulation
JythonHms.ComputeRun("Run 1")

# Save results
JythonHms.SaveAllProjectComponents()

# Exit
JythonHms.Exit(0)
"""

success, stdout, stderr = HmsJython.execute_script(
    script_content=script,
    hms_exe_path="C:/Program Files/HEC/HEC-HMS/4.13"
)

if success:
    print("Simulation completed successfully!")
else:
    print(f"Error: {stderr}")
```

### Example 2: Verify HMS 3.3 Compatibility

```python
from hms_commander import HmsJython

# Check if HMS 3.3 supports Jython (yes, per HMS_3x_SUPPORT.md)
# Generate Python 2-compatible script

script = """
from hms.model import JythonHms

JythonHms.OpenProject("tifton", "C:/HMS/tifton")
JythonHms.OpenBasinModel("tifton")
JythonHms.Compute("Run 1")  # Use Compute, not ComputeRun!
JythonHms.SaveAllProjectComponents()
JythonHms.Exit(0)
"""

success, stdout, stderr = HmsJython.execute_script(
    script_content=script,
    hms_exe_path="C:/Program Files (x86)/HEC/HEC-HMS/3.3",
    working_dir="C:/HMS/tifton"
)

if success:
    print("HMS 3.3 Jython scripting confirmed working!")
```

### Example 3: Compare API Differences

```python
# Reference knowledge files to understand version differences

# HMS 3.3 API reference
from pathlib import Path
with open(Path("knowledge/HMS_3x_SUPPORT.md")) as f:
    content = f.read()
    # Check "Key Differences from HMS 4.x" section
    # Learn that Compute() works in 3.3 but not 4.x

# HMS 4.x API reference
with open(Path("knowledge/JYTHON_HMS_API.md")) as f:
    content = f.read()
    # See that ComputeRun() is available
    # See that Optimize() throws NotImplemented
```

---

## Limitations

### What This Agent Can Do

✅ Provide decompiled source code
✅ Document discovered APIs
✅ Explain internal implementations
✅ Support hms-commander development
✅ Enable version compatibility analysis
✅ Help with script generation
✅ Troubleshoot error codes

### What This Agent CANNOT Do

❌ Modify or improve HMS source code
❌ Provide official HMS support or guarantees
❌ Document undocumented APIs as "correct"
❌ Support all possible HMS versions (focused on 3.3, 4.13)
❌ Guarantee behavioral accuracy (decompilation is best-effort)
❌ Provide legal advice on using decompiled code

### Known Limitations

1. **Decompilation Quality**: CFR produces high-quality output but method names are sometimes obfuscated (e.g., `e`, `x`, `w_0`)
2. **Limited Version Coverage**: Only HMS 3.3 and 4.13 fully decompiled; intermediate versions may differ
3. **API Stability**: Decompiled APIs are subject to change in future HMS versions
4. **No Guarantee of Completeness**: Some classes may not have been decompiled completely
5. **Binary Decisions**: Decompiler interprets bytecode but may miss intent

---

## Related Agents

### Update_3_to_4 - Version Upgrade Agent

**Location:** `hms_agents/Update_3_to_4/`

Upgrades HMS 3.x projects to 4.x with validation. Uses decompiler knowledge to:
- Understand version differences
- Generate compatible scripts
- Compare computational results

**Integration:**
```python
from hms_agents.Update_3_to_4 import upgrade_workflow
from hms_agents.hms_decompiler.knowledge import HMS_3x_SUPPORT

# Use version knowledge from decompiler
is_compatible = HMS_3x_SUPPORT.check_3x_api_call("Compute")
```

### HMS_DocQuery - Documentation Query Agent

**Location:** `hms_agents/HMS_DocQuery/`

Queries official HEC-HMS documentation. Complements decompiler by:
- Providing official API documentation
- Explaining methods documented by USACE
- Validating decompiled knowledge against official sources

**When to Use Each:**
- **Decompiler**: "How is this method really implemented?"
- **DocQuery**: "What does the official documentation say?"

---

## Contributing

### Adding New Knowledge

1. **Decompile new classes** using cfr.jar:
   ```bash
   java -jar tools/cfr.jar "C:\Program Files\HEC\HEC-HMS\4.13\java\hms.jar" \
       --classfilter "hms/model/*" --outputdir reference/HMS_4.13/
   ```

2. **Analyze decompiled code** and extract key information

3. **Document findings** in knowledge/ files:
   - Method signatures
   - Parameters and types
   - Return values
   - Exceptions and error handling
   - Example usage

4. **Update AGENT.md** with new information if high-value for common questions

### Reporting Issues

If you discover incorrect or missing information:

1. **Verify** with actual decompiled source code
2. **Create issue** with:
   - What is documented
   - What you discovered
   - Decompiled source reference
   - Suggested correction

3. **Test** before and after correction

---

## FAQ

### Q: Is using decompiled code legal?

**A:** Using decompiled code for analysis and documentation is generally acceptable under fair use. However, this knowledge is provided for:
- Understanding HMS for integration with hms-commander
- Supporting open-source development
- Educational purposes

Do not:
- Redistribute HMS source code
- Create competing products from HMS code
- Claim ownership of HMS code

### Q: How accurate is the decompiled code?

**A:** CFR produces excellent quality decompilation with 95%+ accuracy for modern Java. However:
- Some method/variable names are obfuscated
- Complex control flow may be reconstructed
- Comments and original intent are lost
- Internal implementation details are preserved

### Q: Does this violate HMS licensing?

**A:** This agent documents discovered behavior, not HMS source. It supports:
- Development of compatible tools (hms-commander)
- Understanding HMS behavior for integration
- Documentation and education

It does NOT:
- Redistribute HMS code
- Create proprietary alternatives
- Violate any HMS license terms

Always review HEC-HMS licensing for your use case.

### Q: How often is this agent updated?

**A:** When:
- New HMS versions are released
- New decompilation knowledge is discovered
- Integration issues found in hms-commander
- API changes discovered in existing versions

Check `Last Updated` date in each knowledge file.

### Q: Can I use this for HMS 3.2 or 4.10?

**A:** Partially:
- **API methods**: Very likely same as 3.3 and 4.13 respectively
- **Implementation details**: May differ from documented versions
- **Recommendation**: Test with actual version to confirm

The safest approach is to decompile your actual HMS version.

---

## Files in This Agent

**Main Files:**
- `AGENT.md` - This documentation

**Knowledge Base:**
- `knowledge/JYTHON_HMS_API.md` - Complete JythonHms API reference
- `knowledge/HMS_3x_SUPPORT.md` - HMS 3.x Jython support documentation
- `knowledge/HMS_CLI_OPTIONS.md` - HEC-HMS command-line options

**Reference Classes:**
- `reference/HMS_3.3/hms/model/JythonHms.java` - HMS 3.3 decompiled source
- `reference/HMS_4.13/hms/model/JythonHms.java` - HMS 4.13 decompiled source
- Additional classes in HMS_3.3/ and HMS_4.13/ directories

**Tools:**
- `tools/cfr.jar` - Java decompiler (2.1 MB)

**Examples:**
- `examples/` - Example scripts and queries (directory)

---

## Quick Reference

**Find HMS 4.13 JythonHms API:**
→ Read `knowledge/JYTHON_HMS_API.md`

**Use HMS 3.3 scripting:**
→ Read `knowledge/HMS_3x_SUPPORT.md` and use `python2_compatible=True`

**Understand CLI options:**
→ Read `knowledge/HMS_CLI_OPTIONS.md`

**Decompile new HMS version:**
→ Use `tools/cfr.jar` following TOOL_USAGE.md

**Deep dive into implementation:**
→ Read decompiled source in `reference/HMS_*.*/`

**Report new discovery:**
→ Add to knowledge/ file and sync with library

---

## Support

For questions or issues:

1. **Check this AGENT.md** for answers
2. **Review knowledge files** for specific topics
3. **Consult reference classes** for implementation details
4. **Check decompilation library** for expanded knowledge
5. **Search hms-commander code** for working examples

---

**Generated by hms-commander development team**
**Part of: hms_decompiler production agent**
**License**: Open source (hms-commander)
**Last Verified**: 2025-12-12
