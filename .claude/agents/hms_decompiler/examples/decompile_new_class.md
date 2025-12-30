# Example: Decompile New HMS Class

**Scenario**: You want to understand how HMS handles a specific feature by decompiling the relevant class.

---

## Question

How does HMS manage optimization trials internally? What class handles this?

---

## Investigation Workflow

### Step 1: Identify Target Class

Based on HMS functionality, likely candidates:
- `hms.model.OptimizationManager`
- `hms.model.OptimizationTrial`
- `hms.model.optimization.*` package

### Step 2: Check If Already Decompiled

Check `reference/` directory:
```bash
ls reference/HMS_4.13/hms/model/
```

**Result**: Not yet decompiled (OptimizationManager not in reference/)

### Step 3: Decompile the Class

Navigate to agent tools directory:
```bash
cd C:\GH\hms-commander\hms_agents\hms_decompiler\tools
```

Decompile `OptimizationManager`:
```batch
java -jar cfr.jar "C:\Program Files\HEC\HEC-HMS\4.13\java\hms.jar" --classfilter "hms.model.OptimizationManager" --outputdir output
```

**Output**:
```
===============================================================================
HMS Decompilation Tool
===============================================================================
JAR:     C:\Program Files\HEC\HEC-HMS\4.13\hms.jar
Pattern: hms.model.OptimizationManager
Output:  output
===============================================================================

Decompiling...

Processing hms/model/OptimizationManager.class
Decompiled 1 class

===============================================================================
Decompilation complete!
===============================================================================
Output directory: output
===============================================================================
```

### Step 4: Review Decompiled Source

```batch
type output\hms\model\OptimizationManager.java
```

**Discovered code** (example):
```java
package hms.model;

import hms.model.optimization.*;
import java.util.*;

public class OptimizationManager {
    private List<OptimizationTrial> trials;
    private OptimizationConfig config;

    public void addTrial(OptimizationTrial trial) {
        this.trials.add(trial);
    }

    public void runOptimization() throws Exception {
        // Implementation details...
        for (OptimizationTrial trial : trials) {
            trial.execute();
            // ...
        }
    }

    // ... more methods
}
```

### Step 5: Analyze Findings

**Key discoveries**:
1. Uses `OptimizationTrial` objects
2. Maintains list of trials
3. `runOptimization()` iterates through trials
4. May have `OptimizationConfig` for settings

**Related classes to investigate**:
- `hms.model.optimization.OptimizationTrial`
- `hms.model.optimization.OptimizationConfig`

### Step 6: Decompile Related Classes

Decompile entire optimization package:
```batch
decompile.bat "C:\Program Files\HEC\HEC-HMS\4.13\hms.jar" "hms.model.optimization.**" output_optimization
```

**Result**: Multiple classes discovered:
- `OptimizationTrial.java`
- `OptimizationConfig.java`
- `OptimizationAlgorithm.java`
- etc.

---

## Document Findings

### Step 7: Add to Agent Reference

Copy important classes to agent reference:
```batch
# Copy to agent reference directory
copy output\hms\model\OptimizationManager.java ..\reference\HMS_4.13\hms\model\

copy output_optimization\hms\model\optimization\*.java ..\reference\HMS_4.13\hms\model\optimization\
```

### Step 8: Update Agent Documentation

If this is important for common questions, document in AGENT.md:

Add to Reference Classes section or create note in knowledge/.

### Step 9: Document High-Value Insights

If this is important for hms-commander, add to agent knowledge:

`knowledge/optimization_internals.md` (if warranted):

```markdown
# HMS Optimization Internals

**Discovered**: 2025-12-12
**HMS Version**: 4.13

## Key Findings

1. **OptimizationManager** orchestrates optimization process
2. Uses **OptimizationTrial** objects for individual trials
3. Trials executed sequentially (no parallel processing in code)
4. Configuration via **OptimizationConfig**

## API Not Exposed in JythonHms

**Discovery**: JythonHms.Optimize() throws NotImplemented in HMS 4.x

**Decompiled code** (HMS 4.13 JythonHms.java):
```java
public static void Optimize(String trialName) throws Exception {
    throw new Exception("Not implemented");
}
```

**Implication**: HMS 4.x optimization only available via GUI, not scriptable.

## hms-commander Impact

Cannot automate optimization in HMS 4.x via scripting.

**Workaround options**:
1. Use HMS 3.x (Optimize() works)
2. Use HMS GUI for optimization
3. Implement custom optimization wrapper
```

---

## Keep Agent Updated

### Step 10: Update AGENT.md

If this discovery is useful for common questions, update the agent documentation:

- Add to Reference Classes list
- Update navigation table
- Document key findings

This ensures future users can quickly find this information.

---

## Example Research Notes

### Optimization Not Scriptable in HMS 4.x

**Question**: Why can't we automate optimization in HMS 4.x?

**Investigation**:
1. Checked `knowledge/JYTHON_HMS_API.md`
   - Lists `Optimize()` as deprecated/removed

2. Decompiled `JythonHms.java` (HMS 4.13):
   ```java
   public static void Optimize(String trialName) throws Exception {
       throw new Exception("Not implemented");
   }
   ```

3. Decompiled `OptimizationManager.java`:
   - No JythonHms integration code
   - Designed for GUI use only

**Conclusion**: HMS 4.x removed scriptable optimization. Use HMS 3.x or GUI.

---

## Advanced: Deobfuscating Classes

### Scenario: Class Has Obfuscated Name

**Example**: Exploring basin operations, found `hms.model.basin.u.java`

**Workflow**:

1. Decompile the class:
   ```batch
   decompile.bat "C:\...\hms.jar" "hms.model.basin.u" output
   ```

2. Review method names for clues:
   ```java
   public class u {
       public void addSubbasin(Subbasin s) { ... }
       public List<Subbasin> getSubbasins() { ... }
       public void removeSubbasin(String name) { ... }
   }
   ```

3. Infer purpose from methods:
   - Has subbasin operations → **Subbasin collection manager**

4. Add comment to decompiled file:
   ```java
   // INFERRED PURPOSE: SubbasinManager
   // Manages collection of subbasins in basin model
   // Based on method signatures: addSubbasin(), getSubbasins(), removeSubbasin()

   public class u {
       // Original obfuscated name: u
       // Likely purpose: SubbasinManager
       ...
   }
   ```

5. Document in `research/obfuscation_patterns.md`:
   ```markdown
   ## Basin Package Obfuscation

   | Obfuscated | Inferred Purpose | Confidence |
   |------------|------------------|------------|
   | `u` | SubbasinManager | High (method names clear) |
   ```

---

## Tips & Best Practices

### Class Naming Patterns

**HMS follows patterns**:
- `*Manager` - Orchestrators (ProjectManager, OptimizationManager)
- `*Element` - Model components (BasinElement, MetElement)
- `*Config` - Configuration objects
- `*Impl` - Interface implementations (HmsCommandServerImpl)

### Decompilation Scope

**Start narrow, expand as needed**:
1. Single class first
2. If uses unknown classes, decompile package
3. If package is large, decompile selectively

### Documentation Depth

**Light touch for exploratory**:
- Keep in local output/ directory
- Test and verify findings

**High-value findings**:
- Add to agent reference/
- Create knowledge file if API-relevant
- Update AGENT.md if commonly asked

---

## Complete Example: From Question to Answer

**Q**: "How do I set loss method parameters via Jython?"

**Workflow**:

1. Check `knowledge/JYTHON_HMS_API.md`
   - Found: `SetLossRateValue(element, param, value)`
   - But: What are valid parameters?

2. Decompile `JythonHms.java` (already done):
   - `reference/HMS_4.13/hms/model/JythonHms.java`
   - Review implementation

3. Found internal call to `LossMethodManager`

4. Decompile `LossMethodManager`:
   ```batch
   decompile.bat "C:\...\hms.jar" "hms.model.basin.LossMethodManager" output
   ```

5. Found parameter validation:
   ```java
   private static final String[] SCS_PARAMS = {
       "Initial Abstraction",
       "Curve Number",
       "Impervious %"
   };
   ```

6. Document in knowledge file:
   `knowledge/LOSS_METHOD_PARAMETERS.md`

7. Update production agent

**Result**: Comprehensive parameter reference for all loss methods!

---

## Related Resources

**Agent Tools**:
- `tools/cfr.jar` - CFR decompiler
- Direct java -jar usage for decompilation

**Agent Reference**:
- `reference/HMS_X.X/` - Decompiled classes
- `knowledge/` - High-value findings and API references

**Agent Documentation**:
- `AGENT.md` - Comprehensive guide
- `QUICK_START.md` - Quick reference

---

**Example completed**: 2025-12-12
**Classes decompiled**: OptimizationManager, optimization package
**Knowledge added**: Optimization internals, HMS 4.x limitation documented
