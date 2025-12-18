# HMS DSS Plotting Workflow

You are helping the user extract and visualize results from HMS DSS output files.

## Required Information

1. **DSS File Path**: Path to the .dss output file
2. **Elements**: Which outlets/junctions/reaches to plot
3. **Result Type**: Flow, stage, precipitation, etc.
4. **Time Window** (optional): Subset of simulation period

## Quick Start: Extract and Plot

```python
from hms_commander import HmsDss, HmsResults
import matplotlib.pyplot as plt

# List available pathnames in DSS file
catalog = HmsDss.get_catalog("results.dss")
print(catalog.head(20))  # First 20 pathnames

# Extract flow timeseries
flows = HmsResults.get_outflow_timeseries("results.dss", "Outlet")
print(flows.head())

# Quick plot
flows.plot(title="Outlet Flow", ylabel="Flow (cfs)")
plt.show()
```

## DSS Pathname Structure

HMS DSS pathnames follow the structure:
```
/A-Part/B-Part/C-Part/D-Part/E-Part/F-Part/
/Basin/Element/Parameter/DateTime/Interval/Version/
```

**Example pathnames:**
```
/WATERSHED/OUTLET/FLOW/01JAN2000/1HOUR/RUN:RUN 1/
/WATERSHED/SUB1/PRECIP-INC/01JAN2000/1HOUR/RUN:RUN 1/
/WATERSHED/REACH1/FLOW-ROUTED/01JAN2000/1HOUR/RUN:RUN 1/
```

## Common Extractions

### Extract Flow Hydrograph

```python
from hms_commander import HmsResults

# By element name
flows = HmsResults.get_outflow_timeseries("results.dss", "Outlet")

# By full pathname
flows = HmsDss.read_timeseries(
    "results.dss",
    "/WATERSHED/OUTLET/FLOW/01JAN2000/1HOUR/RUN:RUN 1/"
)
```

### Extract Precipitation

```python
# Incremental precipitation for a subbasin
precip = HmsDss.read_timeseries(
    "results.dss",
    "/WATERSHED/SUB1/PRECIP-INC/01JAN2000/1HOUR/RUN:RUN 1/"
)
```

### Extract Multiple Elements

```python
# Get flows from multiple elements
elements = ['J1', 'J2', 'J3', 'Outlet']
results = {}

for element in elements:
    results[element] = HmsResults.get_outflow_timeseries(
        "results.dss", element
    )

# Create DataFrame with all
import pandas as pd
combined = pd.DataFrame(results)
```

### Get Peak Flows Summary

```python
# Summary of peak flows for all elements
peaks = HmsResults.get_peak_flows("results.dss")
print(peaks)
#              Peak_Flow  Peak_Time
# J1            1250.3  2000-01-15 08:00
# J2            2340.5  2000-01-15 10:00
# Outlet        5670.2  2000-01-15 14:00
```

## Plotting Recipes

### Single Hydrograph

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(12, 6))
flows.plot(ax=ax, color='blue', linewidth=1.5)
ax.set_xlabel('Date')
ax.set_ylabel('Flow (cfs)')
ax.set_title('Outlet Flow Hydrograph')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```

### Multiple Hydrographs Comparison

```python
fig, ax = plt.subplots(figsize=(12, 6))

for element in ['J1', 'J2', 'Outlet']:
    flows = HmsResults.get_outflow_timeseries("results.dss", element)
    ax.plot(flows.index, flows.values, label=element)

ax.set_xlabel('Date')
ax.set_ylabel('Flow (cfs)')
ax.set_title('Flow Comparison')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```

### Precipitation + Flow Combined

```python
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

# Precipitation (inverted, top)
precip = HmsDss.read_timeseries("results.dss", precip_path)
ax1.bar(precip.index, precip.values, color='blue', alpha=0.7)
ax1.invert_yaxis()
ax1.set_ylabel('Precipitation (in)')
ax1.set_title('Precipitation')

# Flow (bottom)
flows = HmsResults.get_outflow_timeseries("results.dss", "Outlet")
ax2.plot(flows.index, flows.values, color='darkblue', linewidth=1.5)
ax2.set_xlabel('Date')
ax2.set_ylabel('Flow (cfs)')
ax2.set_title('Outlet Flow')

plt.tight_layout()
plt.show()
```

### Simulated vs Observed

```python
fig, ax = plt.subplots(figsize=(12, 6))

# Simulated
sim = HmsResults.get_outflow_timeseries("results.dss", "Outlet")
ax.plot(sim.index, sim.values, label='Simulated', color='blue')

# Observed (from CSV)
obs = pd.read_csv("observed.csv", parse_dates=['Date'], index_col='Date')
ax.plot(obs.index, obs['Flow'], label='Observed', color='red', linestyle='--')

ax.set_xlabel('Date')
ax.set_ylabel('Flow (cfs)')
ax.set_title('Simulated vs Observed Flow')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```

## Export Options

### Export to CSV

```python
# Single timeseries
flows.to_csv("outlet_flows.csv")

# Combined DataFrame
combined.to_csv("all_flows.csv")
```

### Export to Excel

```python
with pd.ExcelWriter("results.xlsx") as writer:
    flows.to_excel(writer, sheet_name="Flows")
    peaks.to_excel(writer, sheet_name="Peaks")
```

### Export Plot

```python
fig.savefig("hydrograph.png", dpi=300, bbox_inches='tight')
fig.savefig("hydrograph.pdf", bbox_inches='tight')
```

## DSS Catalog Exploration

```python
# Get full catalog as DataFrame
catalog = HmsDss.get_catalog("results.dss")

# Filter to flows only
flows_catalog = catalog[catalog['C-Part'] == 'FLOW']
print(flows_catalog)

# Find all elements with results
elements = catalog['B-Part'].unique()
print(f"Elements with results: {elements}")

# Find all result types
result_types = catalog['C-Part'].unique()
print(f"Result types: {result_types}")
```

## Your Response

1. **Ask for DSS file path** if not provided
2. **List available pathnames** (show catalog)
3. **Ask which elements/results** to extract
4. **Generate extraction code** ready to run
5. **Offer plotting options** based on data type
6. **Suggest export format** if needed

## Primary Sources

- Code: `hms_commander/HmsDss.py`, `hms_commander/HmsResults.py`
- Skill: `.claude/skills/extracting-dss-results/`
- Subagent: `.claude/agents/dss-integration-specialist.md`
- Examples: `examples/06_dss_operations.ipynb`
