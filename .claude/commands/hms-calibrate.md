# HMS Calibration Workflow

You are helping the user design and execute an HEC-HMS calibration workflow.

## Required Information

Gather the following before calibrating:

1. **Project Path**: HMS project directory
2. **Observed Data**: Path to observed flow data (CSV or DSS)
3. **Calibration Elements**: Which subbasins/junctions to calibrate
4. **Parameters to Calibrate**: Loss, transform, and/or baseflow params
5. **Objective Function**: NSE, RMSE, PBIAS, Peak Error, etc.

## Calibration Strategy Planning

### Step 1: Identify Calibration Points

```python
from hms_commander import init_hms_project, hms, HmsBasin

init_hms_project(project_path)

# Find subbasins upstream of gage
subbasins = HmsBasin.get_subbasins("project.basin")
print(subbasins[['Name', 'Area', 'Downstream']])

# Identify gage locations
print(hms.gage_df)  # Available gages
```

### Step 2: Define Parameter Bounds

**Common Loss Parameters (SCS CN):**
| Parameter | Typical Range | Units |
|-----------|---------------|-------|
| Curve Number | 60-95 | - |
| Initial Abstraction | 0.1-0.3 * S | inches |
| Impervious % | 0-30 | % |

**Common Loss Parameters (Deficit & Constant):**
| Parameter | Typical Range | Units |
|-----------|---------------|-------|
| Initial Deficit | 0.5-2.0 | inches |
| Constant Rate | 0.1-0.5 | in/hr |

**Transform Parameters (SCS UH):**
| Parameter | Typical Range | Units |
|-----------|---------------|-------|
| Lag Time | 0.5-24 | hours |
| Graph Type | Standard | - |

**Transform Parameters (Clark):**
| Parameter | Typical Range | Units |
|-----------|---------------|-------|
| Time of Concentration | 0.5-48 | hours |
| Storage Coefficient | 0.5-24 | hours |

**Baseflow (Recession):**
| Parameter | Typical Range | Units |
|-----------|---------------|-------|
| Initial Flow | 0-100 | cfs |
| Recession Constant | 0.5-0.99 | - |
| Threshold Ratio | 0.05-0.5 | - |

## Clone-Based Calibration (Recommended)

**Non-destructive approach using clone workflows:**

```python
from hms_commander import HmsBasin, HmsMet, HmsRun

# 1. Clone basin for calibration
HmsBasin.clone_basin(
    template="Existing_Basin",
    new_name="Calibration_Basin",
    description="Calibration iteration 1",
    hms_object=hms
)

# 2. Modify parameters
HmsBasin.set_loss_parameters(
    "project/Calibration_Basin.basin",
    "Subbasin1",
    curve_number=85
)

# 3. Create calibration run
HmsRun.clone_run(
    template="Existing_Run",
    new_name="Calibration_Run",
    basin="Calibration_Basin",
    hms_object=hms
)

# 4. Execute and compare
result = HmsCmdr.compute_run("Calibration_Run")
```

## Validation Metrics

```python
from hms_commander import HmsResults

def compute_metrics(simulated, observed):
    """Compute calibration metrics."""

    # Nash-Sutcliffe Efficiency (NSE)
    # Range: -inf to 1, 1 = perfect
    nse = 1 - (np.sum((observed - simulated)**2) /
               np.sum((observed - np.mean(observed))**2))

    # Percent Bias (PBIAS)
    # Range: -inf to inf, 0 = perfect
    pbias = 100 * np.sum(observed - simulated) / np.sum(observed)

    # RMSE
    rmse = np.sqrt(np.mean((observed - simulated)**2))

    # Peak Error
    peak_error = (np.max(simulated) - np.max(observed)) / np.max(observed) * 100

    return {
        'nse': nse,
        'pbias': pbias,
        'rmse': rmse,
        'peak_error': peak_error
    }
```

**Acceptance Criteria:**
| Metric | Satisfactory | Good | Very Good |
|--------|-------------|------|-----------|
| NSE | 0.50-0.65 | 0.65-0.75 | >0.75 |
| PBIAS (%) | ±15-25 | ±10-15 | <±10 |
| Peak Error | ±20% | ±15% | <±10% |

## Region-Based Calibration

For large models, calibrate by regions:

```python
# Define regions (upstream to downstream)
regions = {
    'headwaters': ['Sub1', 'Sub2', 'Sub3'],
    'middle': ['Sub4', 'Sub5'],
    'lower': ['Sub6', 'Sub7']
}

# Calibrate each region sequentially
for region_name, subbasins in regions.items():
    print(f"Calibrating {region_name}...")
    # Apply regional parameters
    for sub in subbasins:
        HmsBasin.set_loss_parameters(
            basin_file, sub,
            curve_number=region_params[region_name]['cn']
        )
```

## Manual vs Automated Calibration

**Manual (Recommended for Learning):**
1. Run sensitivity analysis first
2. Adjust most sensitive parameters
3. Use clone workflow for each iteration
4. Compare visually and by metrics

**HMS Built-in Optimization:**
```python
# HMS supports Nelder-Mead and Univariate-Gradient
# Configure in .hms file via Optimization Manager
```

**External Optimization (Future):**
- scipy.optimize for Python-based optimization
- DEAP for genetic algorithms
- Multi-objective for Pareto fronts

## Your Response

1. **Ask for project details** if not provided
2. **Show current parameters** for calibration elements
3. **Propose calibration plan** with:
   - Parameters to adjust
   - Initial bounds
   - Suggested objective function
   - Number of iterations
4. **Create clone workflow** for first iteration
5. **Execute and report metrics**
6. **Iterate** based on results

## Primary Sources

- Subagent: `.claude/agents/basin-model-specialist.md`
- Skill: `.claude/skills/cloning-hms-components/`
- Rules: `.claude/rules/hec-hms/clone-workflows.md`
- Examples: `examples/` (calibration examples when available)

## Future Enhancements

The `HmsCalibrate` class (planned in Phase 3 roadmap) will provide:
- `calibrate_auto()` - Automated optimization
- `sensitivity_analysis()` - Morris/Sobol methods
- `multi_objective_optimize()` - Pareto optimization
- `compare_to_observed()` - Streamlined validation

See: `feature_dev_notes/DEVELOPMENT_ROADMAP.md` Phase 3
