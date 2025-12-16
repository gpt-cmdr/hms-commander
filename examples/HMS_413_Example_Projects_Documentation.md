# HEC-HMS 4.13 Example Projects Documentation

This document provides comprehensive documentation of the HEC-HMS 4.13 example projects located in `examples/hms413_test/`. Each project demonstrates different hydrologic modeling capabilities and methods available in HEC-HMS.

---

## Table of Contents

1. [Castro Valley Project](#1-castro-valley-project)
2. [River Bend Project](#2-river-bend-project)
3. [Tenk Project (Tenkiller Lake)](#3-tenk-project-tenkiller-lake)
4. [Tifton Project](#4-tifton-project)
5. [Summary of Hydrologic Methods](#5-summary-of-hydrologic-methods)

---

## 1. Castro Valley Project

### Project Overview

| Attribute | Value |
|-----------|-------|
| **Project Name** | castro |
| **Description** | Castro Valley Urban Study |
| **Location** | Castro Valley, California |
| **Purpose** | Urban watershed hydrology study comparing existing vs. future development conditions |
| **Unit System** | English |
| **Time Zone** | America/Los_Angeles |

### Basin Models

The project contains two basin models representing different development scenarios:

#### Basin Model: Castro 1 (Existing Conditions)

| Component Type | Count | Names |
|----------------|-------|-------|
| Subbasins | 4 | Subbasin-1, Subbasin-2, Subbasin-3, Subbasin-4 |
| Reaches | 2 | Reach-1, Reach-2 |
| Junctions | 3 | East Branch, West Branch, Outlet |

##### Subbasin Parameters

| Subbasin | Area (sq mi) | Impervious (%) | Loss Method | Transform Method | Baseflow Method |
|----------|--------------|----------------|-------------|------------------|-----------------|
| Subbasin-1 | 0.86 | 2 | Initial+Constant | Snyder | Recession |
| Subbasin-2 | 1.52 | 8 | Initial+Constant | Snyder | Recession |
| Subbasin-3 | 2.17 | 10 | Initial+Constant | Snyder | Recession |
| Subbasin-4 | 0.96 | 15 | Initial+Constant | Snyder | Recession |

**Loss Rate Parameters (Initial+Constant):**
- Initial Loss: 0.02 inches
- Constant Loss Rate: 0.14 in/hr

**Transform Parameters (Snyder Unit Hydrograph):**

| Subbasin | Tp (hr) | Cp |
|----------|---------|-----|
| Subbasin-1 | 0.20 | 0.16 |
| Subbasin-2 | 0.28 | 0.16 |
| Subbasin-3 | 0.20 | 0.16 |
| Subbasin-4 | 0.17 | 0.16 |

**Baseflow Parameters (Recession):**
- Recession Factor: 0.79
- Initial Flow/Area Ratio: 0.54
- Threshold Flow to Peak Ratio: 0.1

##### Reach Routing

| Reach | Description | Routing Method | Parameters |
|-------|-------------|----------------|------------|
| Reach-1 | Sub 4 to Outlet | Muskingum | K=0.6 hr, x=0.2, 7 steps |
| Reach-2 | Sub 2 to Outlet | Modified Puls | 4 subreaches, Storage-Outflow Table 1 |

#### Basin Model: Castro 2 (Future Conditions)

Similar structure to Castro 1, with modified impervious percentages and Snyder Tp values representing increased urbanization:

| Subbasin | Area (sq mi) | Impervious (%) | Snyder Tp |
|----------|--------------|----------------|-----------|
| Subbasin-1 | 0.86 | 2 | 0.20 |
| Subbasin-2 | 1.52 | **17** | **0.19** |
| Subbasin-3 | 2.17 | 10 | 0.20 |
| Subbasin-4 | 0.96 | 15 | 0.17 |

### Meteorologic Model: GageWts

| Attribute | Value |
|-----------|-------|
| **Description** | Thiessen weights; 10-min data |
| **Precipitation Method** | Weighted Gages |
| **Evapotranspiration Method** | No Evapotranspiration |
| **Use HEC1 Weighting Scheme** | Yes |

**Gage Weights by Subbasin:**

| Subbasin | Proctor School | Fire Dept. | Sidney School |
|----------|----------------|------------|---------------|
| Subbasin-1 | 1.0 | 0 (temporal only) | - |
| Subbasin-2 | 0.2 | 0.8 | - |
| Subbasin-3 | 0.33 | 0.33 | 0.33 |
| Subbasin-4 | - | 0.8 | 0.2 |

### Control Specification: Jan73

| Attribute | Value |
|-----------|-------|
| **Description** | Storm of 16 January 1973 |
| **Start Date/Time** | 16 January 1973, 03:00 |
| **End Date/Time** | 16 January 1973, 12:55 |
| **Time Interval** | 5 minutes |

### Run Configurations

| Run Name | Basin Model | Met Model | Control | Description |
|----------|-------------|-----------|---------|-------------|
| Current | Castro 1 | GageWts | Jan73 | Current conditions for storm of 16 January 1973 |
| Future | Castro 2 | GageWts | Jan73 | Future conditions for storm of 16 January 1973 |

### Gage Data

| Gage Name | Type | Description | DSS Path |
|-----------|------|-------------|----------|
| Fire Dept. | Precipitation (Recording) | Recording precipitation gage | /CASTRO VALLEY/FIRE DEPT./PRECIP-INC//10MIN/OBS/ |
| Out | Flow | Recording gage at outlet | /CASTRO VALLEY/OUTLET/FLOW//10MIN/OBS/ |

**Precipitation Totals (for Total Storm gages):**
- Proctor School: 1.92 inches
- Sidney School: 1.37 inches

---

## 2. River Bend Project

### Project Overview

| Attribute | Value |
|-----------|-------|
| **Project Name** | river_bend |
| **Description** | Interior Watershed model for the Green River |
| **Location** | Green River area (coordinates near Tennessee) |
| **Purpose** | Detention basin and pump station analysis for flood management |
| **Unit System** | English |
| **Coordinate System** | NAD83 / UTM zone 16N |

### Basin Models

The project contains three basin models comparing different detention basin configurations:

#### Basin Model: Minimum Facility

| Component Type | Count | Names |
|----------------|-------|-------|
| Subbasins | 2 | Upper, Local |
| Reaches | 1 | Local Route |
| Junctions | 1 | J1 |
| Reservoirs | 1 | Detention Basin |

##### Subbasin Parameters

| Subbasin | Area (sq mi) | Impervious (%) | Loss Method | Transform Method | Baseflow |
|----------|--------------|----------------|-------------|------------------|----------|
| Upper | 7.5 | 15 | Deficit Constant | SCS Unit Hydrograph | None |
| Local | 5.0 | 20 | Deficit Constant | SCS Unit Hydrograph | None |

**Loss Rate Parameters (Deficit and Constant):**
- Initial Deficit: 0 inches
- Maximum Deficit: 0.5 inches
- Percolation Rate: 0.02 in/hr
- Recovery Factor: 1.0

**Transform Parameters (SCS Unit Hydrograph):**

| Subbasin | Lag (min) | Unitgraph Type |
|----------|-----------|----------------|
| Upper | 252 | Standard |
| Local | 210 | Standard |

##### Reach Routing

| Reach | Routing Method | Parameters |
|-------|----------------|------------|
| Local Route | Muskingum | K=5 hr, x=0.4, 5 steps |

##### Detention Basin (Reservoir)

| Attribute | Value |
|-----------|-------|
| **Routing Method** | Controlled Outflow |
| **Routing Curve** | Elevation-Storage |
| **Initial Elevation** | 95 ft |
| **Tailwater Condition** | Specified Stage (Green River gage) |

**Conduit (Culvert):**

| Parameter | Value |
|-----------|-------|
| Shape | Box |
| Rise | 4 ft |
| Span | 4 ft |
| Number of Barrels | 1 |
| Length | 200 ft |
| Entrance Loss Coefficient | 0.4 |
| Exit Loss Coefficient | 1.0 |
| Manning's n | 0.012 |
| Inlet Invert Elevation | 91 ft |
| Outlet Invert Elevation | 89 ft |

#### Basin Model: Minimum Facility + Pump

Same as Minimum Facility, with addition of **1 pump**:

| Parameter | Value |
|-----------|-------|
| Number of Pumps | 1 |
| Intake Elevation | 97 ft |
| Discharge Elevation | 101.5 ft |
| Switch-On Elevation | 100 ft |
| Switch-Off Elevation | 98 ft |
| Equipment Head Loss | 1.15 ft |

#### Basin Model: Minimum Facility + 4Pumps

Same as Minimum Facility + Pump, with **4 pumps** instead of 1.

### Meteorologic Model: Historic Precipitation

| Attribute | Value |
|-----------|-------|
| **Precipitation Method** | Specified Average |
| **Evapotranspiration Method** | Monthly Evaporation |

**Monthly Pan Evaporation (inches per month):**
| Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| 3.1 | 2.8 | 3.1 | 3.0 | 3.1 | 3.0 | 3.1 | 3.1 | 3.0 | 3.1 | 3.0 | 3.1 |

Evapotranspiration Coefficient: 1.0 (all months)

### Control Specification: 1951

| Attribute | Value |
|-----------|-------|
| **Start Date/Time** | 1 January 1951, 01:00 |
| **End Date/Time** | 31 December 1951, 23:00 |
| **Time Interval** | 60 minutes |
| **Duration** | Full year simulation |

### Run Configurations

| Run Name | Basin Model | Met Model | Control |
|----------|-------------|-----------|---------|
| Minimum Facility | Minimum Facility | Historic Precipitation | 1951 |
| Minimum Facility + Pump | Minimum Facility + Pump | Historic Precipitation | 1951 |
| Minimum Facility + 4Pumps | Minimum Facility + 4Pumps | Historic Precipitation | 1951 |

### Gage Data

| Gage Name | Type | DSS Path |
|-----------|------|----------|
| Local | Precipitation | //GAGE2/PRECIP-INC/01OCT1950/1HOUR/OBS/ |
| Upper | Precipitation | //GAGE1/PRECIP-INC/01OCT1950/1HOUR/OBS/ |
| Green River | Stage | //GREEN RIVER/STAGE/01JAN1951/1DAY/COMP/ |

---

## 3. Tenk Project (Tenkiller Lake)

### Project Overview

| Attribute | Value |
|-----------|-------|
| **Project Name** | tenk |
| **Description** | Illinois River Watershed above Tenkiller Lake |
| **Location** | Oklahoma/Arkansas border region |
| **Purpose** | Gridded precipitation modeling using NWS Stage III radar data with ModClark transform |
| **Unit System** | English |

### Basin Model: Tenk 1

| Component Type | Count | Names |
|----------------|-------|-------|
| Subbasins | 4 | 86, 85, 113, 127 |
| Reaches | 5 | R-1, R-2, R-3, R-4, R-5 |
| Junctions | 5 | Watts, Tahlequah, Eldon, conf, Tenkiller |

**Description:** 4 ModClark Subbasins with gridded HRAP precipitation cells

##### Subbasin Parameters

| Subbasin | Area (sq mi) | Impervious (%) | Loss Method | Transform Method | Baseflow Method |
|----------|--------------|----------------|-------------|------------------|-----------------|
| 86 | 635 | 0 | Initial+Constant | Modified Clark | Recession |
| 85 | 324 | 0 | Initial+Constant | Modified Clark | Recession |
| 113 | 307 | 0 | Initial+Constant | Modified Clark | Recession |
| 127 | 345 | 10 | Initial+Constant | Modified Clark | Recession |

**Discretization:** File-Specified (regions\hrapcells) for gridded precipitation

**Loss Rate Parameters (Initial+Constant):**

| Subbasin | Initial Loss (in) | Constant Rate (in/hr) |
|----------|-------------------|----------------------|
| 86 | 1.0 | 0.20 |
| 85 | 1.0 | 0.20 |
| 113 | 1.3 | 0.04 |
| 127 | 1.15 | 0.15 |

**Transform Parameters (Modified Clark):**

| Subbasin | Time of Concentration (hr) | Storage Coefficient (hr) |
|----------|---------------------------|-------------------------|
| 86 | 24 | 11.6 |
| 85 | 30 | 15.5 |
| 113 | 18 | 8.7 |
| 127 | 1 | 7.0 |

**Baseflow Parameters (Recession):**

| Subbasin | Recession Factor | Initial Baseflow (cfs) | Threshold Ratio |
|----------|-----------------|----------------------|-----------------|
| 86 | 0.79 | 290 | 0.20 |
| 85 | 0.79 | 100 | 0.15 |
| 113 | 0.79 | 150 | 0.15 |
| 127 | 0.79 | 80 | 0.15 |

##### Reach Routing

| Reach | Description | Routing Method | Parameters |
|-------|-------------|----------------|------------|
| R-1 | Watts to Flint Creek | Modified Puls | 6 subreaches, Table 4 |
| R-2 | Flint Creek to Tahlequah | Modified Puls | 20 subreaches, Table 3 |
| R-3 | Tahlequah to Barron Fork confluence | Modified Puls | 4 subreaches, Table 1 |
| R-4 | Eldon to Illinois River confluence | Modified Puls | 4 subreaches, Table 2 |
| R-5 | Barron Fork confluence to dam | Lag | 120 min lag |

##### Computation Points (with Observed Data)

| Junction | Observed Gage |
|----------|---------------|
| Watts | WATT |
| Tahlequah | TAHL |
| Eldon | ELDN |
| Tenkiller | TENK |

### Meteorologic Model: Stage3-HRAP

| Attribute | Value |
|-----------|-------|
| **Description** | NWS Stage III radar rainfall data |
| **Precipitation Method** | Gridded Precipitation |
| **Evapotranspiration Method** | No Evapotranspiration |
| **Grid Name** | Grid 1 |

### Control Specification: Jan 96

| Attribute | Value |
|-----------|-------|
| **Description** | Storm of 17 January 1996 |
| **Start Date/Time** | 16 January 1996, 24:00 |
| **End Date/Time** | 21 January 1996, 23:00 |
| **Time Interval** | 60 minutes |

### Run Configuration

| Run Name | Basin Model | Met Model | Control | Description |
|----------|-------------|-----------|---------|-------------|
| Jan 96 storm | Tenk 1 | Stage3-HRAP | Jan 96 | Base conditions for January 1996 |

### Gage Data

| Gage Name | Type | Description | DSS Path |
|-----------|------|-------------|----------|
| TAHL | Flow | Illinois River near Tahlequah | /ILLINOIS/TAHL/FLOW-LOC CUM//1HOUR/OBS/ |
| TENK | Flow | Computed inflow to Lake Tenkiller | /ILLINOIS/TENK/FLOW-RES IN//1HOUR/OBS/ |
| ELDN | Flow | Baron Fork near Eldon | /ILLINOIS/ELDN/FLOW-LOC CUM//1HOUR/OBS/ |
| WATT | Flow | Illinois River near Watts | /ILLINOIS/WATT/FLOW-LOC CUM//1HOUR/OBS/ |

### Gridded Data

| Grid Name | Type | Description | DSS Path |
|-----------|------|-------------|----------|
| Grid 1 | Precipitation | Stage3-HRAP | /HRAP/ABRFC/PRECIP//// |

**DSS File:** hrap.dss

---

## 4. Tifton Project

### Project Overview

| Attribute | Value |
|-----------|-------|
| **Project Name** | tifton |
| **Description** | Little River Watershed near Tifton, Georgia |
| **Location** | Tifton, Georgia (ARS Watershed 74006) |
| **Purpose** | Continuous simulation with soil moisture accounting and multi-layer groundwater |
| **Unit System** | English |

### Basin Model: Tifton

| Component Type | Count | Names |
|----------------|-------|-------|
| Subbasins | 1 | 74006 |
| Junctions | 1 | Station I |

**Description:** ARS Watershed 74006 - Agricultural Research Service experimental watershed

##### Subbasin Parameters

| Subbasin | Area (sq mi) | Impervious (%) | Loss Method | Transform Method | Baseflow Method |
|----------|--------------|----------------|-------------|------------------|-----------------|
| 74006 | 19.27 | 0 | Soil Moisture Account | Clark Unit Hydrograph | Linear Reservoir |

**Canopy Layer (Simple):**
- Initial Canopy Storage: 0%
- Canopy Storage Capacity: 0.2 inches
- Crop Coefficient: 1.0

**Surface Layer (Simple):**
- Initial Surface Storage: 0%
- Surface Storage Capacity: 0.0 inches
- Surface Albedo: 0.20

**Loss Rate Parameters (Soil Moisture Accounting):**

| Parameter | Value |
|-----------|-------|
| Initial Soil Storage Percent | 80% |
| Soil Maximum Infiltration | 2.0 in/hr |
| Soil Storage Capacity | 9.0 inches |
| Soil Tension Capacity | 8.5 inches |
| Soil Maximum Percolation | 0.02 in/hr |
| Initial GW1 Storage Percent | 0% |
| GW1 Storage Capacity | 10.0 inches |
| GW1 Routing Coefficient | 100 hr |
| GW1 Maximum Percolation | 0.02 in/hr |
| Initial GW2 Storage Percent | 2% |
| GW2 Storage Capacity | 24.0 inches |
| GW2 Routing Coefficient | 500 hr |
| GW2 Maximum Percolation | 0.0 in/hr |

**Transform Parameters (Clark Unit Hydrograph):**
- Time of Concentration: 20 hours
- Storage Coefficient: 20 hours
- Time-Area Method: Default

**Baseflow Parameters (Linear Reservoir):**

| Layer | Number of Reservoirs | Routing Coefficient (hr) | Initial Baseflow (cfs) |
|-------|---------------------|-------------------------|----------------------|
| GW-1 | 1 | 140 | 0.0 |
| GW-2 | 1 | 240 | 20.0 |

### Meteorologic Model: Tifton Hyetograph

| Attribute | Value |
|-----------|-------|
| **Precipitation Method** | Specified Average |
| **Evapotranspiration Method** | Monthly Evaporation |
| **Precipitation Gage** | Gage 38 |

**Monthly Pan Evaporation (inches):**

| Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| 2.22 | 2.78 | 4.53 | 6.00 | 7.08 | 6.97 | 6.81 | 6.32 | 5.12 | 4.24 | 2.80 | 2.17 |

**Evapotranspiration Coefficient:** 0.7 (all months)

### Control Specification: Jan1-Jun30 1970

| Attribute | Value |
|-----------|-------|
| **Start Date/Time** | 1 January 1970, 01:00 |
| **End Date/Time** | 30 June 1970, 01:00 |
| **Time Interval** | 60 minutes |
| **Duration** | 6-month continuous simulation |

### Run Configuration

| Run Name | Basin Model | Met Model | Control | Description |
|----------|-------------|-----------|---------|-------------|
| 1970 simulation | Tifton | Tifton Hyetograph | Jan1-Jun30 1970 | Jan to Jun 1970 |

### Gage Data

| Gage Name | Type | DSS Path |
|-----------|------|----------|
| Gage 74006 | Flow (Observed) | /ARS/74006/FLOW//15MIN/OBS/ |
| Gage 38 | Precipitation | /ARS/000038/PRECIP-CUM/01APR1968/15MIN/OBS/ |

---

## 5. Summary of Hydrologic Methods

### Loss Rate Methods

| Method | Projects Using | Key Parameters |
|--------|---------------|----------------|
| **Initial+Constant** | Castro, Tenk | Initial loss (in), Constant rate (in/hr), % Impervious |
| **Deficit Constant** | River Bend | Max deficit (in), Percolation rate (in/hr), Recovery factor |
| **Soil Moisture Accounting** | Tifton | Multi-layer: Soil, GW1, GW2 with capacities, percolation rates |

### Transform Methods

| Method | Projects Using | Key Parameters |
|--------|---------------|----------------|
| **Snyder Unit Hydrograph** | Castro | Tp (time to peak), Cp (peaking coefficient) |
| **SCS Unit Hydrograph** | River Bend | Lag time (min), Standard/PRF505 |
| **Clark Unit Hydrograph** | Tifton | Time of Concentration (hr), Storage Coefficient (hr) |
| **Modified Clark** | Tenk | Tc (hr), Storage Coefficient (hr), Gridded cell discretization |

### Baseflow Methods

| Method | Projects Using | Key Parameters |
|--------|---------------|----------------|
| **Recession** | Castro, Tenk | Recession factor, Initial flow, Threshold ratio |
| **Linear Reservoir** | Tifton | Number reservoirs, Routing coefficient, Initial baseflow |
| **None** | River Bend | No baseflow simulation |

### Routing Methods

| Method | Projects Using | Key Parameters |
|--------|---------------|----------------|
| **Muskingum** | Castro (Reach-1), River Bend | K (hr), x (weighting), Number of steps |
| **Modified Puls** | Castro (Reach-2), Tenk | Storage-Outflow table, Number of subreaches |
| **Lag** | Tenk (R-5) | Lag time (min) |
| **Controlled Outflow** | River Bend (Reservoir) | Elevation-Storage curve, Conduits, Pumps |

### Precipitation Methods

| Method | Projects Using | Description |
|--------|---------------|-------------|
| **Weighted Gages** | Castro | Thiessen polygon weighting with multiple gages |
| **Specified Average** | River Bend, Tifton | Single gage per subbasin |
| **Gridded Precipitation** | Tenk | NWS Stage III radar (HRAP grid) |

### Evapotranspiration Methods

| Method | Projects Using | Description |
|--------|---------------|-------------|
| **No Evapotranspiration** | Castro, Tenk | Event-based simulation |
| **Monthly Evaporation** | River Bend, Tifton | Pan evaporation with crop coefficients |

### Special Features by Project

| Project | Special Features |
|---------|------------------|
| **Castro** | Urban hydrology, existing vs. future conditions comparison |
| **River Bend** | Detention basin routing, pump station analysis (1 vs 4 pumps), tailwater effects |
| **Tenk** | Gridded precipitation (ModClark), multiple computation points with observed data |
| **Tifton** | Continuous simulation, multi-layer groundwater, canopy/surface interception |

---

## File Structure Summary

```
hms413_test/
├── castro/
│   └── castro/
│       ├── castro.hms          # Project file
│       ├── Castro_1.basin      # Existing conditions basin
│       ├── Castro_2.basin      # Future conditions basin
│       ├── GageWts.met         # Weighted gages meteorology
│       ├── Jan73.control       # Control specification
│       ├── castro.run          # Run configurations
│       ├── castro.gage         # Gage definitions
│       └── castro.dss          # DSS data file
├── river_bend/
│   └── river_bend/
│       ├── river_bend.hms
│       ├── Minimum_Facility.basin
│       ├── Minimum_Facility_+_Pump.basin
│       ├── Minimum_Facility_+_4Pumps.basin
│       ├── Historic_Precipitation.met
│       ├── 1951.control
│       ├── river_bend.run
│       ├── river_bend.gage
│       └── green_river.dss
├── tenk/
│   └── tenk/
│       ├── tenk.hms
│       ├── Tenk_1.basin
│       ├── Stage3_HRAP.met
│       ├── Jan_96.control
│       ├── tenk.run
│       ├── tenk.gage
│       ├── tenk.grid           # Grid definitions
│       ├── hrap.dss            # HRAP radar data
│       └── regions/hrapcells   # Grid cell definitions
└── tifton/
    └── tifton/
        ├── tifton.hms
        ├── Tifton.basin
        ├── Tifton_Hyetograph.met
        ├── Jan1_Jun30_1970.control
        ├── tifton.run
        ├── tifton.gage
        └── tifton.dss
```

---

*Documentation generated for HEC-HMS 4.13 example projects*
