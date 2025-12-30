# Example: HMS 3.x vs 4.x Version Compatibility

**Scenario**: You need to understand the differences between HMS 3.x and 4.x for automation purposes.

---

## Question

Does HMS 3.3 support Jython scripting? If so, what are the key differences from HMS 4.x?

---

## Investigation

### Step 1: Check HMS 3.x Support

Open `knowledge/HMS_3x_SUPPORT.md`.

### Step 2: Key Finding

✅ **YES** - HMS 3.3+ DOES support Jython scripting!

This was **discovered via decompilation** and is not well-documented in official HMS materials.

---

## Key Differences: HMS 3.x vs 4.x

### Architecture

| Aspect | HMS 3.x | HMS 4.x |
|--------|---------|---------|
| **Bit architecture** | 32-bit | 64-bit |
| **Java** | 32-bit JRE (bundled in `java/`) | System Java (64-bit) |
| **Memory limit** | ~1.3 GB | 32+ GB (system dependent) |
| **Native DLLs** | jniLibHydro.dll, javaHeclib.dll | 64-bit equivalents |

### Python Syntax

| Feature | HMS 3.x | HMS 4.x |
|---------|---------|---------|
| **Jython version** | 2.5.x | 2.7.x |
| **Python syntax** | Python 2 | Python 3 |
| **Print statement** | `print "text"` | `print("text")` |
| **Division** | `/` is integer division | `/` is float division |
| **Exception handling** | `except Exception, e:` | `except Exception as e:` |

### JythonHms API Methods

| Method | HMS 3.3 | HMS 4.13 | Notes |
|--------|---------|----------|-------|
| **OpenProject()** | ✅ | ✅ | Same signature |
| **Compute()** | ✅ | ✅ (deprecated) | 3.x primary method |
| **ComputeRun()** | ❌ | ✅ | 4.x recommended |
| **ComputeTrial()** | ❌ | ✅ | 4.x only |
| **ComputeForecast()** | ❌ | ✅ | 4.x only |
| **Optimize()** | ✅ Works | ❌ NotImplemented | Removed in 4.x |
| **MoveResults()** | ✅ | ❌ | Replaced by CopyRunResults() |
| **CopyRunResults()** | ❌ | ✅ | 4.x only |

### CLI Options

| Option | HMS 3.x | HMS 4.x | Notes |
|--------|---------|---------|-------|
| **-script / -s** | ✅ | ✅ | Execute Jython script |
| **-lite / -l** | ✅ | ✅ | Headless mode |
| **-debug / -d** | ✅ | ✅ | Debug mode |
| **-info** | ❌ | ✅ | Print version (4.x only) |
| **CommandServer** | ❌ | ✅ | RMI server mode (4.x only) |

---

## hms-commander Support

### Python 2 Compatible Scripts

For HMS 3.x, use `python2_compatible=True`:

```python
from hms_commander import HmsJython

script = HmsJython.generate_compute_script(
    project_path="C:/Projects/watershed",
    run_name="Design Storm",
    python2_compatible=True  # Required for HMS 3.x!
)
```

**Generated script (HMS 3.x)**:
```python
# Python 2 syntax
from hec.script import *
JythonHms = HmsScriptAPI()

print "Opening project..."  # Python 2
JythonHms.OpenProject("watershed", "C:/Projects/watershed")
JythonHms.Compute("Design Storm")  # 3.x method
JythonHms.Exit(0)
```

**Generated script (HMS 4.x)**:
```python
# Python 3 syntax
from hec.script import *
JythonHms = HmsScriptAPI()

print("Opening project...")  # Python 3
JythonHms.OpenProject("watershed", "C:/Projects/watershed")
JythonHms.ComputeRun("Design Storm")  # 4.x method
JythonHms.Exit(0)
```

### Version Detection

hms-commander automatically detects HMS version:

```python
from hms_commander import HmsUtils

hms_version = HmsUtils.get_hms_version("C:/Program Files/HEC/HEC-HMS/3.5")
# Returns: "3.5" or "4.13"

is_32bit = HmsUtils.is_hms_32bit(hms_version)
# Returns: True for 3.x, False for 4.x

python2_required = is_32bit
```

### Execution

```python
from hms_commander import HmsCmdr

# hms-commander handles version differences automatically
HmsCmdr.compute_run(
    run_name="Design Storm",
    hms_version="3.5"  # or "4.13"
)
```

**Behind the scenes**:
- Detects HMS version from installation
- Generates Python 2 or 3 syntax accordingly
- Uses `Compute()` for 3.x, `ComputeRun()` for 4.x
- Handles 32-bit vs 64-bit differences

---

## Test Results

**Tested in hms-commander**:

| HMS Version | Jython Support | hms-commander | Status |
|-------------|----------------|---------------|--------|
| 3.3 | ✅ Yes | ✅ Supported | Verified |
| 3.5 | ✅ Yes | ✅ Supported | Verified |
| 4.0-4.9 | ✅ Yes | ✅ Supported | Verified |
| 4.10-4.11 | ✅ Yes | ⚠️ Batch bug | Workaround implemented |
| 4.12+ | ✅ Yes | ✅ Supported | Verified |

**Batch file bug (HMS 4.0-4.11)**:
- HEC-HMS.cmd has quoting bug
- Fails when installed in path with spaces
- hms-commander bypasses batch file (direct Java invocation)

---

## Migration Guide: HMS 3.x → 4.x

### 1. Update Jython Scripts

**Change compute method**:
```python
# HMS 3.x
JythonHms.Compute("Run 1")

# HMS 4.x
JythonHms.ComputeRun("Run 1")
```

**Update Python syntax**:
```python
# HMS 3.x (Python 2)
print "Computing..."
results = 10 / 3  # Integer division (3)

# HMS 4.x (Python 3)
print("Computing...")
results = 10 / 3  # Float division (3.333...)
```

### 2. Remove Deprecated Methods

**Optimize no longer works in HMS 4.x**:
```python
# HMS 3.x - Works
JythonHms.Optimize("Optimization Trial 1")

# HMS 4.x - Throws NotImplemented error
# Use HMS GUI for optimization instead
```

### 3. Update Results Handling

```python
# HMS 3.x
JythonHms.MoveResults("Run 1", "Run 1 Baseline")

# HMS 4.x
JythonHms.CopyRunResults("Run 1", "Run 1 Baseline")
```

---

## Discovered via Decompilation

### JythonHms.java Comparison

**HMS 3.3** (`reference/HMS_3.3/hms/model/JythonHms.java`):
```java
public static void Compute(String runName) throws Exception {
    // Implementation...
}

public static void Optimize(String trialName) throws Exception {
    // Implementation...
}
```

**HMS 4.13** (`reference/HMS_4.13/hms/model/JythonHms.java`):
```java
public static void ComputeRun(String runName) throws Exception {
    // Implementation...
}

public static void Optimize(String trialName) throws Exception {
    throw new Exception("Not implemented");  // Removed!
}
```

### CLI Parsing

**HMS 3.3** (`reference/HMS_3.3/hms/Hms.java`):
- Simpler CLI parsing
- No `-info` flag
- No CommandServer mode

**HMS 4.13** (`reference/HMS_4.13/hms/Hms.java`):
- Enhanced CLI with `-info`, CommandServer
- RMI server integration
- Version printing

---

## Recommendations

### Use HMS 4.x When

- Large watersheds (>100 MB DSS files)
- Need >1.3 GB memory
- Want modern Python 3 syntax
- Need RMI command server

### Use HMS 3.x When

- Legacy projects requiring 3.x
- 32-bit only environment
- Need `Optimize()` functionality
- Existing 3.x workflow

### hms-commander

- ✅ Supports both HMS 3.x and 4.x
- ✅ Automatic version detection
- ✅ Handles syntax differences
- ✅ Use `python2_compatible=True` for 3.x

---

## Related Resources

**Agent knowledge files**:
- `knowledge/HMS_3x_SUPPORT.md` - Complete 3.x support guide
- `knowledge/JYTHON_HMS_API.md` - HMS 4.x API reference
- `knowledge/HMS_CLI_OPTIONS.md` - All CLI options

**Agent reference classes**:
- `reference/HMS_3.3/hms/model/JythonHms.java` - 3.x API implementation
- `reference/HMS_4.13/hms/model/JythonHms.java` - 4.x API implementation

**hms-commander implementation**:
- `hms_commander/HmsJython.py` - Handles version differences
- `hms_commander/HmsCmdr.py` - Version detection and execution
- `hms_commander/HmsUtils.py` - Version utilities

---

**Example completed**: 2025-12-12
**Tested HMS versions**: 3.3, 3.5, 4.0-4.13
**hms-commander support**: Full (both 3.x and 4.x)
