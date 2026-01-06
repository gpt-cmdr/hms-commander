# Next Steps: Release v0.2.0

**Current Status**: Implementation 100% complete, all tests passing, ready for release
**Remaining**: Version bump, git commit, PyPI release (~10 minutes)

---

## Quick Commands (Copy/Paste Ready)

### Step 1: Verify Everything Still Works

```bash
cd C:\GH\hms-commander

# Run full test suite
python -m pytest tests/test_atlas14_multiduration.py tests/test_scs_type.py -v

# Expected: 77 passed in ~0.5s
```

### Step 2: Update Version Number

**Edit `setup.py`** line ~5:

```python
# CHANGE FROM:
version="0.1.0",

# CHANGE TO:
version="0.2.0",  # Breaking change: DataFrame API
```

### Step 3: Git Commit

```bash
git add .

git commit -m "BREAKING: Return DataFrame from precipitation hyetograph methods

Changes:
- Atlas14Storm.generate_hyetograph() returns pd.DataFrame
- FrequencyStorm.generate_hyetograph() returns pd.DataFrame
- ScsTypeStorm.generate_hyetograph() returns pd.DataFrame
- FrequencyStorm parameter renamed: total_depth → total_depth_inches

DataFrame columns: ['hour', 'incremental_depth', 'cumulative_depth']

Enables seamless HMS→RAS integration without manual conversion.

Test Results: 77/77 passing
Notebooks: 4/4 validated
HMS Equivalence: Verified at 10^-6 precision

See CHANGELOG.md for complete migration guide.

Files modified:
- hms_commander/Atlas14Storm.py
- hms_commander/FrequencyStorm.py
- hms_commander/ScsTypeStorm.py
- tests/test_atlas14_multiduration.py
- tests/test_scs_type.py
- examples/08_atlas14_hyetograph_generation.ipynb
- examples/09_frequency_storm_variable_durations.ipynb
- examples/10_scs_type_validation.ipynb
- examples/11_atlas14_multiduration_validation.ipynb
- README.md
- CHANGELOG.md (new)

Co-Authored-By: 4 Opus Subagents (notebook specialists)

🤖 Generated with Claude Code (https://claude.com/claude-code)
Co-Authored-By: Claude Sonnet 4.5 (1M context) <noreply@anthropic.com>"
```

### Step 4: Tag Release

```bash
git tag -a v0.2.0 -m "Release v0.2.0: DataFrame API for precipitation methods

Breaking change: All hyetograph generation methods return DataFrame.
See CHANGELOG.md for migration guide."

git push origin main
git push origin v0.2.0
```

### Step 5: Build and Publish to PyPI

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build distribution
python -m build

# Upload to PyPI
python -m twine upload dist/hms-commander-0.2.0*
```

---

## Verification Checklist

Before release:

- [ ] Version updated in setup.py
- [ ] All tests pass: `pytest tests/test_atlas14_multiduration.py tests/test_scs_type.py -v`
- [ ] Notebooks execute: All 4 validation notebooks run without errors
- [ ] Git commit created
- [ ] Git tag created (v0.2.0)
- [ ] Build successful: `python -m build`
- [ ] PyPI upload successful

After release:

- [ ] Install from PyPI: `pip install hms-commander==0.2.0`
- [ ] Test basic import: `from hms_commander import Atlas14Storm`
- [ ] Test DataFrame return: Verify `isinstance(hyeto, pd.DataFrame)`
- [ ] Notify ras-commander team

---

## Cross-Repo Notification

**Send to ras-commander**:

```
Subject: hms-commander v0.2.0 Released - DataFrame API Ready

The precipitation DataFrame API standardization is complete and released:

- Version: hms-commander v0.2.0
- PyPI: https://pypi.org/project/hms-commander/
- Status: All tests passing (77/77), all notebooks validated

What's Available:
✅ Atlas14Storm.generate_hyetograph() returns DataFrame
✅ FrequencyStorm.generate_hyetograph() returns DataFrame (param: total_depth_inches)
✅ ScsTypeStorm.generate_hyetograph() returns DataFrame
✅ Columns: ['hour', 'incremental_depth', 'cumulative_depth']

ras-commander can now:
1. Update dependency: hms-commander>=0.2.0
2. Remove manual DataFrame conversion code
3. Implement RasUnsteady.set_precipitation_hyetograph() directly
4. Update notebooks (720, 721, 722)

Migration guide: See CHANGELOG.md in hms-commander repo
```

---

## Documentation Reference

**For Users**:
- Migration Guide: `CHANGELOG.md` (comprehensive)
- Quick Guide: `README.md` (breaking change section)

**For Developers**:
- Implementation Plan: `agent_tasks/cross-repo/IMPLEMENTATION_PLAN_precipitation_dataframe_api.md`
- Completion Report: `agent_tasks/cross-repo/IMPLEMENTATION_COMPLETE_precipitation_dataframe_api.md`
- Final Summary: `agent_tasks/cross-repo/FINAL_SUMMARY_precipitation_dataframe_api.md`

**For Future Sessions**:
- Current Status: `.agent/CURRENT_STATUS.md`
- This File: `.agent/TASK_PRECIPITATION_DATAFRAME_API.md`

---

**Created**: 2026-01-05
**Ready For**: Immediate release (just version bump and commit)
