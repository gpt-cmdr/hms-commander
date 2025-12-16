# Release Notes

Version history and changelog for HMS Commander.

## Version 0.1.0 (Current Development)

**Status:** Active development
**Release Date:** TBD

### Features

#### Core Functionality
- ✅ Project initialization and management (`HmsPrj`)
- ✅ Basin model operations (`HmsBasin`)
- ✅ Meteorologic model operations (`HmsMet`)
- ✅ Control specification operations (`HmsControl`)
- ✅ Gage operations (`HmsGage`)
- ✅ Run configuration (`HmsRun`)
- ✅ Geospatial operations (`HmsGeo`)

#### Execution
- ✅ Simulation execution (`HmsCmdr`)
- ✅ Jython script generation (`HmsJython`)
- ✅ HMS 3.x and 4.x support
- ✅ Parallel execution support
- ✅ Python 2/3 compatible script generation

#### Data Operations
- ✅ DSS file operations (`HmsDss`)
- ✅ Results extraction and analysis (`HmsResults`)
- ✅ GeoJSON export

#### Utilities
- ✅ File parsing utilities (`HmsFileParser`)
- ✅ Constants and conversions (`_constants`)
- ✅ Example project management (`HmsExamples`)

#### LLM Forward Features
- ✅ Clone workflows (basin, met, control, run)
- ✅ Non-destructive operations
- ✅ Traceable modifications
- ✅ GUI verification support

#### Atlas 14 Support
- ✅ TP-40 to Atlas 14 conversion
- ✅ Project centroid calculation
- ✅ Precipitation depth updates

### Documentation
- ✅ Complete API documentation (auto-generated)
- ✅ User guide (all sections)
- ✅ Example notebooks
- ✅ LLM Forward approach documentation
- ✅ CLAUDE.md for AI assistants

### Known Issues
- None currently tracked

---

## Planned Features

### Version 0.2.0 (Planned)

**Theme:** Enhanced Analysis and Reporting

#### Planned Features
- [ ] Automated calibration workflows
- [ ] Sensitivity analysis tools
- [ ] Enhanced comparison reports
- [ ] Export to PDF reports
- [ ] Web-based results viewer

### Version 0.3.0 (Planned)

**Theme:** Advanced Modeling

#### Planned Features
- [ ] Gridded precipitation support
- [ ] Reservoir operations
- [ ] Routing method utilities
- [ ] Snowmelt model support
- [ ] Soil moisture accounting

### Version 0.4.0 (Planned)

**Theme:** Integration and Automation

#### Planned Features
- [ ] QGIS plugin
- [ ] ArcGIS toolbox
- [ ] GitHub Actions integration
- [ ] Automated testing workflows
- [ ] CI/CD documentation builds

---

## Version History

### Development Milestones

#### 2024-12-11: Documentation Complete
- ✅ All 48 documentation pages created
- ✅ API reference auto-generation working
- ✅ User guide complete
- ✅ LLM Forward principles documented

#### 2024-12: Initial Development
- ✅ Core architecture established
- ✅ Static class pattern implemented
- ✅ File parsing utilities created
- ✅ HMS 3.x and 4.x support added

---

## Breaking Changes

### None Yet

As version 0.1.0 is still in development, no breaking changes have been introduced.

**Future Policy:**
- Breaking changes will follow semantic versioning
- Deprecation warnings before removal
- Migration guides provided
- Backward compatibility maintained when possible

---

## Upgrade Guide

### From Git Repository

```bash
# Pull latest changes
git pull origin main

# Reinstall in development mode
pip install -e .
```

### From PyPI (Future)

```bash
# Upgrade to latest version
pip install --upgrade hms-commander

# Upgrade with DSS support
pip install --upgrade hms-commander[dss]
```

---

## Contributing

See [Contributing Guide](contributing.md) for:
- Development workflow
- Pull request process
- Coding standards
- Testing requirements

---

## Versioning Policy

HMS Commander follows [Semantic Versioning](https://semver.org/):

**Format:** MAJOR.MINOR.PATCH

- **MAJOR** - Incompatible API changes
- **MINOR** - Backward-compatible functionality
- **PATCH** - Backward-compatible bug fixes

**Examples:**
- `0.1.0` → `0.2.0` - New features, backward compatible
- `0.2.0` → `0.2.1` - Bug fixes only
- `0.9.9` → `1.0.0` - First stable release, API locked
- `1.0.0` → `2.0.0` - Breaking changes

---

## Support

### Reporting Issues

Report bugs and request features on GitHub:
https://github.com/gpt-cmdr/hms-commander/issues

**Include:**
- HMS Commander version
- HEC-HMS version
- Python version
- Operating system
- Minimal reproducible example

### Getting Help

1. **Documentation** - Check user guide and API reference
2. **CLAUDE.md** - Complete API reference
3. **Examples** - Review example notebooks
4. **GitHub Issues** - Search existing issues
5. **New Issue** - Create detailed bug report

---

## Acknowledgments

**Inspired by:**
- [ras-commander](https://github.com/fema-ffrd/ras-commander) - Architecture patterns
- [CLB Engineering](https://clbengineering.com/) - LLM Forward approach

**Built with:**
- Python 3.10+
- pandas - Data manipulation
- pathlib - Path operations
- ras-commander - DSS operations

---

*This document is updated with each release. Check back for the latest changes.*
