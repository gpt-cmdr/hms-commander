# HMS Documentation Query Agent

This agent queries the official HEC-HMS documentation to answer technical questions about HEC-HMS features, file formats, methods, and workflows.

## Overview

HEC-HMS has extensive official documentation maintained by the U.S. Army Corps of Engineers (USACE) Hydrologic Engineering Center. This agent provides a programmatic interface to query that documentation for technical answers.

## Documentation Sources

### Primary Sources
1. **HEC-HMS User's Manual** - Comprehensive guide to using HEC-HMS
   - URL: https://www.hec.usace.army.mil/confluence/hmsdocs/hmsum/latest/
   - Coverage: UI, workflows, methods, file formats

2. **HEC-HMS Technical Reference Manual** - Detailed method descriptions
   - URL: https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/latest/
   - Coverage: Loss methods, transform methods, routing algorithms

3. **HEC-HMS Release Notes** - Version-specific changes
   - URL: https://www.hec.usace.army.mil/software/hec-hms/downloads.aspx
   - Coverage: New features, bug fixes, breaking changes

4. **HEC-HMS Downloads Page** - Software and documentation
   - URL: https://www.hec.usace.army.mil/software/hec-hms/downloads.aspx
   - Coverage: Installation, system requirements, example projects

### Secondary Sources
5. **HEC-HMS Training Materials** - Workshops and tutorials
6. **HEC-HMS Example Projects** - Included with installation

### Community Resources
7. **The RAS Solution Forum (Kleinschmidt)** - Professional HEC software community
   - URL: https://therassolution.kleinschmidtgroup.com/the-ras-solution-forum/
   - Coverage: HEC-RAS, HEC-HMS, practical applications, troubleshooting

8. **Hydro School Forums** - Water resources modeling community
   - URL: https://hydroschool.org/forums/
   - Coverage: Tutorials, modeling techniques, software discussions

9. **HEC-RAS Reddit (r/HECRAS)** - Informal community Q&A
   - URL: https://www.reddit.com/r/HECRAS/
   - Coverage: Quick questions, code snippets, general HEC discussions

10. **CWMS/HEC-RTS Online Resources** - Advanced data management
    - URL: https://www.hec.usace.army.mil/confluence/cwmsdocs/cmrkit/latest/online-resources-for-cwms-hec-rts
    - Coverage: CWMS database, HEC-RTS, time-series data systems

## Use Cases

### 1. Method Documentation
Query details about HMS methods (loss, transform, routing, etc.):
```python
from hms_agents.HMS_DocQuery import query_documentation

# Get details about SCS Curve Number method
result = query_documentation(
    "What are the parameters for the SCS Curve Number loss method?",
    focus_area="loss_methods"
)
```

### 2. File Format Questions
Understand HMS file formats:
```python
result = query_documentation(
    "What is the structure of a .basin file?",
    focus_area="file_formats"
)
```

### 3. Version-Specific Features
Check version compatibility:
```python
result = query_documentation(
    "What new features were added in HMS 4.11?",
    focus_area="release_notes"
)
```

### 4. Workflow Guidance
Get best practices:
```python
result = query_documentation(
    "How do I set up a gridded precipitation model?",
    focus_area="workflows"
)
```

### 5. Troubleshooting
Find solutions to common issues:
```python
result = query_documentation(
    "Why am I getting NullPointerException when computing?",
    focus_area="troubleshooting"
)
```

## Agent Functions

### query_documentation()
Main function to query HMS documentation.

**Parameters:**
- `question` (str): The technical question to answer
- `focus_area` (str, optional): Narrow search to specific area
  - "loss_methods", "transform_methods", "routing_methods"
  - "file_formats", "workflows", "release_notes"
  - "installation", "troubleshooting"
- `hms_version` (str, optional): Target HMS version (e.g., "4.11", "3.5")
- `verbose` (bool): Print search progress

**Returns:**
- `QueryResult` with answer, sources, and relevant URLs

### get_method_parameters()
Get parameter details for a specific HMS method.

**Parameters:**
- `method_type` (str): "loss", "transform", "baseflow", "routing"
- `method_name` (str): Name of the method (e.g., "SCS Curve Number")
- `hms_version` (str, optional): Target version

**Returns:**
- Dictionary with parameter names, types, defaults, descriptions

### search_release_notes()
Search HMS release notes for version-specific information.

**Parameters:**
- `query` (str): Search query
- `version` (str, optional): Specific version to search

**Returns:**
- List of relevant release note entries with version, date, description

### validate_method_name()
Check if a method name is valid in HMS.

**Parameters:**
- `method_name` (str): Method name to validate
- `method_type` (str): "loss", "transform", etc.
- `hms_version` (str, optional): Target version

**Returns:**
- Boolean and correction suggestion if invalid

## Query Examples

### Example 1: Loss Method Parameters
```python
from hms_agents.HMS_DocQuery import query_documentation

result = query_documentation(
    "What parameters does the Deficit and Constant loss method require?",
    focus_area="loss_methods"
)

print(result.answer)
# Output: The Deficit and Constant loss method requires:
# - Initial Deficit (mm or in)
# - Maximum Deficit (mm or in)
# - Constant Rate (mm/hr or in/hr)
# - Impervious (%)

print(result.sources)
# Output: ['HEC-HMS Technical Reference Manual - Section 3.2']
```

### Example 2: File Format Structure
```python
result = query_documentation(
    "How are subbasins defined in a .basin file?",
    focus_area="file_formats"
)

print(result.answer)
# Output: Subbasins in .basin files are defined with:
# Subbasin: <name>
#     Area: <value>
#     Downstream: <element_name>
#     Loss: <method_name>
#     Transform: <method_name>
#     [method parameters...]
# End:
```

### Example 3: Version Compatibility
```python
result = query_documentation(
    "Is the ModClark transform method available in HMS 3.5?",
    focus_area="release_notes",
    hms_version="3.5"
)

print(result.answer)
# Output: ModClark was introduced in HMS 3.0, so it is available in 3.5.
```

## Common Questions

### Precipitation Methods
- "What precipitation methods are available in HMS?"
- "How do I configure Specified Hyetograph precipitation?"
- "What's the difference between Inverse Distance and Gridded precipitation?"

### Loss Methods
- "What are the parameters for SCS Curve Number?"
- "How does the Green and Ampt loss method work?"
- "What's the difference between Deficit-Constant and Initial-Constant?"

### Transform Methods
- "What parameters does Clark Unit Hydrograph require?"
- "How do I calculate Time of Concentration for Snyder method?"
- "What's the difference between Clark and ModClark?"

### File Formats
- "What is the structure of a .control file?"
- "How are gages defined in .gage files?"
- "What DSS pathname format does HMS use?"

### Troubleshooting
- "Why is my compute failing with no error message?"
- "How do I fix 'Project not found' errors?"
- "What does 'WARNING 10020' mean?"

## Known Documentation URLs

The agent is pre-configured with these key URLs:

**User's Manual:**
- https://www.hec.usace.army.mil/confluence/hmsdocs/hmsum/latest/
- Sections: Getting Started, Data Entry, Computing, Results

**Technical Reference:**
- https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/latest/
- Sections: Precipitation, Loss, Transform, Baseflow, Routing

**Downloads:**
- https://www.hec.usace.army.mil/software/hec-hms/downloads.aspx

**Software Page:**
- https://www.hec.usace.army.mil/software/hec-hms/

## Image and Screenshot Support

**IMPORTANT LIMITATION DISCOVERED (2025-12-10)**:

HEC-HMS documentation heavily relies on screenshots and diagrams to explain:
- User interface workflows
- Parameter entry dialogs
- Result visualization
- File format examples
- Method configuration screens

**Current WebFetch Behavior:**
- WebFetch successfully retrieves text content from HMS documentation pages
- Images are REFERENCED in the HTML but NOT RENDERED in WebFetch responses
- Screenshots and diagrams exist in the documentation but are not visible to the agent
- WebFetch provides image file paths and captions but not the visual content itself

**What This Means:**
- The agent can answer questions using TEXTUAL documentation (equations, parameter lists, descriptions)
- The agent CANNOT describe UI screenshots or visual diagrams
- The agent CANNOT extract information from parameter tables shown as images
- The agent CAN identify when images are present and reference them by caption

**Example:** The Technical Reference Manual page for Clark Unit Hydrograph references:
- "Example Tc Computation Using TR-55 Procedures" (figure)
- "Using Multi-Linear Regression to Estimate Tc" (figure)

But WebFetch only sees the captions, not the actual diagrams.

**Workaround:**
- Agent provides URLs to documentation pages for manual viewing
- Agent extracts available textual information
- Users can view screenshots directly in browser when needed

## Limitations

1. **Documentation Format**: HMS docs are HTML, not API-accessible
2. **Version Variations**: Docs may not specify version differences clearly
3. **Community Content**: Forums and unofficial sources not included
4. **Local Installation Docs**: Cannot access docs from local HMS installation
5. **PDF Manuals**: Cannot directly access downloadable PDF manuals without URL

## Integration with hms-commander

This agent complements hms-commander by providing:
- Method validation before setting parameters
- File format guidance when parsing
- Version compatibility checks before upgrades
- Troubleshooting context for error messages

Example integration:
```python
from hms_commander import HmsBasin
from hms_agents.HMS_DocQuery import get_method_parameters

# Validate method before use
params = get_method_parameters("loss", "SCS Curve Number")
print(f"Required parameters: {list(params.keys())}")

# Set parameters with confidence
HmsBasin.set_loss_parameters(
    basin_path="model.basin",
    subbasin_name="Sub1",
    curve_number=80,
    impervious=10
)
```

## Files in This Agent

- `AGENT.md` - This documentation
- `doc_query.py` - Documentation query workflow
- `KNOWN_URLS.py` - Pre-configured documentation URLs
- `examples/` - Example queries and responses

## Future Enhancements

- [ ] Cache frequently accessed documentation pages
- [ ] Parse HMS help files from local installation
- [ ] Index release notes for all versions
- [ ] Extract parameter tables from technical reference
- [ ] Build HMS method decision tree (which method to use when)
