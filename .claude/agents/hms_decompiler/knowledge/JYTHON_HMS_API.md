# JythonHms API Reference

## Overview

This document details the complete JythonHms API discovered through decompilation of HEC-HMS 4.13.
The `hms.model.JythonHms` class provides the scripting interface for HEC-HMS automation.

## Import Statement (for Jython scripts)

```python
from hms.model import JythonHms
```

## Project Management Methods

### OpenProject
```python
JythonHms.OpenProject(projectName, projectDirectory)
```
Opens an HMS project.

**Parameters:**
- `projectName` (String): Name of the project
- `projectDirectory` (String): Full path to project directory

**Example:**
```python
JythonHms.OpenProject("MyProject", "C:/HMS/MyProject")
```

### SaveAllProjectComponents
```python
JythonHms.SaveAllProjectComponents()
```
Saves all project components. Raises `PyException` on failure.

## Basin Model Methods

### OpenBasinModel
```python
JythonHms.OpenBasinModel(basinName)
```
Opens a basin model within the current project.

**Parameters:**
- `basinName` (String): Name of the basin model

### SaveBasinModel
```python
JythonHms.SaveBasinModel()
```
Saves the currently open basin model.

### SaveBasinModelAs
```python
JythonHms.SaveBasinModelAs(newName)
```
Saves basin model with a new name (creates a copy).

### SetBasinUnitSystem
```python
JythonHms.SetBasinUnitSystem(unitSystem)
```
Sets the unit system for the basin.

**Parameters:**
- `unitSystem` (String): "English", "SI", or "Metric"

## Compute Methods

### ComputeRun
```python
JythonHms.ComputeRun(runName)
```
Executes a simulation run.

**Parameters:**
- `runName` (String): Name of the run to compute

### Compute (Deprecated)
```python
JythonHms.Compute(runName)  # Use ComputeRun instead
```

### ComputeTrial
```python
JythonHms.ComputeTrial(trialName)
```
Executes an optimization trial.

### ComputeForecast
```python
JythonHms.ComputeForecast(forecastName)
```
Executes a forecast run.

## Time Window Methods

### SetTimeWindow
```python
JythonHms.SetTimeWindow(startDate, startTime, endDate, endTime)
```
Sets the control specification time window.

**Parameters:**
- `startDate` (String): Start date (e.g., "01Jan2020")
- `startTime` (String): Start time (e.g., "00:00")
- `endDate` (String): End date (e.g., "02Jan2020")
- `endTime` (String): End time (e.g., "00:00")

## Results Methods

### CopyRunResults
```python
JythonHms.CopyRunResults(runName, sourcePath, destPath)
```
Copies results from one DSS path to another.

### CopyForecastResults
```python
JythonHms.CopyForecastResults(forecastName, sourcePath, destPath)
```

### CopyTrialResults
```python
JythonHms.CopyTrialResults(trialName, sourcePath, destPath)
```

### RenameStateGridBPart
```python
JythonHms.RenameStateGridBPart(newBPart)
```
Renames the B-part of state grid DSS paths.

## Parameter Modification Methods

### SetLossRateValue
```python
JythonHms.SetLossRateValue(elementName, parameterName, value)
```
Sets loss rate parameters for a subbasin.

**Supported Parameters by Loss Method:**

| Loss Method | Parameter Names |
|-------------|-----------------|
| EXPONENTIAL | InitialLoss, PrecipExponent, LossCoefficientRatio, StartLossCoefficient |
| GREEN_AMPT | InitialLoss, MoistureDeficit, WettingFrontSuction, HydraulicConductivity |
| INITIAL_CONSTANT | InitialLoss, ConstantLossRate |
| DEFICIT_CONSTANT | ConstantLossRate, PercolationRate, RecoveryFactor, InitialDeficit, MaximumDeficit |
| SCS_LOSS | SCSCurveNumber, SCSInitialAbstraction |
| All Methods | PercentImperviousArea |

**Example:**
```python
JythonHms.SetLossRateValue("Subbasin-1", "SCSCurveNumber", 75.0)
```

### SetBaseflowValue
```python
JythonHms.SetBaseflowValue(elementName, parameterName, value)
```
Sets baseflow parameters for a subbasin.

**Supported Parameters:**
- RecessionFactor
- InitialBaseflow
- Flow/AreaRatio
- ThresholdFlow
- FlowToPeakRatio

### SetBlendMethod
```python
JythonHms.SetBlendMethod(elementName, methodName)
JythonHms.SetBlendMethod(elementName, methodName, taperValue)
```
Sets the blend method for forecast operations.

## Exit Methods

### Exit / HMSExit
```python
JythonHms.Exit(exitCode)
JythonHms.HMSExit(exitCode)
```
Exits the script with specified exit code.

## Deprecated/Not Implemented Methods

These methods exist but throw `NotImplemented` exceptions:
- `SelectOptimizationTrial`
- `SetParameterLock`
- `SetPercentMissingAllowed`
- `SetObjectiveFunctionTime`
- `Optimize`
- `UseOptimizerTrialResults`

## Complete Example Script

```python
from hms.model import JythonHms

# Open project
JythonHms.OpenProject("Castro", "C:/HMS/Castro")

# Open basin model
JythonHms.OpenBasinModel("Castro")

# Modify a parameter
JythonHms.SetLossRateValue("Castro Creek", "SCSCurveNumber", 80)

# Set time window (if needed)
JythonHms.SetTimeWindow("01Jan2020", "00:00", "02Jan2020", "00:00")

# Run simulation
JythonHms.ComputeRun("Run 1")

# Save results
JythonHms.SaveAllProjectComponents()

# Exit
JythonHms.Exit(0)
```

## Internal Implementation Notes

From decompilation analysis:
- Uses Jython (`org.python.util.PythonInterpreter`)
- Project managed via `ProjectManager` singleton
- Basin model stored as static reference `e` (type `x`)
- Compute operations use Future/ExecutionService pattern
- Error messages use error codes (12xxx series)

---
*Generated by hms-commander decompilation analysis*
*HMS Version: 4.13 (Build 134654)*
*Last updated: 2025-12-10*
