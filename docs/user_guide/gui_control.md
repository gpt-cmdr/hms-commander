# GUI Control

`HmsGui` controls a running HEC-HMS Swing GUI through Java Access Bridge. Use it
for GUI-only workflows, GUI verification, reports, dialogs, and Component Editor
state. Prefer `HmsPrj`, `HmsBasin`, `HmsMet`, `HmsControl`, `HmsRun`,
`HmsCmdr`, and `HmsJython` for durable project edits and computation.

## Requirements

- Windows
- A running HEC-HMS GUI process
- Java Access Bridge enabled before HEC-HMS starts
- The `windowsaccessbridge-64.dll` from the same JRE bundled with that HMS version

```powershell
& "C:\Program Files\HEC\HEC-HMS\4.13\jre\bin\jabswitch.exe" /enable
```

You can also enable it from Python:

```python
from hms_commander import HmsGui

HmsGui.enable_access_bridge(hms_path=r"C:\Program Files\HEC\HEC-HMS\4.13")
```

After enabling JAB, restart HEC-HMS. Enabling it while HMS is already running
does not attach the bridge to that existing Java process.

## Basic Use

```python
from hms_commander import HmsGui

# Walk the current GUI tree.
nodes = HmsGui.walk(max_depth=6)

# Click a menu item by accessible name. Scope names that can collide with tabs,
# labels, or submenu entries. This uses a worker process so modal dialogs do not
# hang the caller.
result = HmsGui.invoke(
    "Program Settings...",
    role_filter="menu item",
    ancestor_name="Tools",
)
manager_results = HmsGui.invoke_many([
    "Basin Model Manager...",
    "Meteorologic Model Manager...",
])

# Focus context-dependent views before invoking disabled menu items.
HmsGui.focus("Basin Model [A100_1PCT]")
HmsGui.invoke("Map Layers...")

# Read Component Editor fields by their visible labels.
unit_system = HmsGui.read_component_field("Unit System:")
message_log = HmsGui.read_message_log()
HmsGui.write_text("Name:", "Updated Name", label_sibling=True)
HmsGui.select_combo_by_label("Unit System:", "U.S. Customary")

# Always safe to run after exploratory GUI actions.
HmsGui.close_dialogs()
```

## Deterministic Startup

Passing a `.hms` file to `HEC-HMS.exe` is not reliable in all HMS versions. For
GUI validation, seed HMS's `projects*.hms` state file so startup opens the
target project through HMS's own "Open Last Project" path.

```python
from hms_commander import HmsGui

project = r"C:\Users\ajith\Downloads\Truckee_River\Truckee_River\Truckee_River.hms"
hms_path = r"C:\Program Files\HEC\HEC-HMS\4.12"

with HmsGui.startup_project_seed(project, hms_path=hms_path, version="4.12") as seed:
    process, _ = HmsGui.launch_project(
        project,
        hms_path=hms_path,
        version="4.12",
        seed_project_state=False,
    )
    window = HmsGui.wait_for_project_open(project, hms_path=hms_path)

    print(seed.state_file)
    print(seed.backup_file)
    print(window.title)
```

This writes the `Project:` and `Recent Projects:` blocks and sets
`Open Last Project: Yes`. A timestamped backup is created by default, and the
context manager restores the prior HMS startup-state file on exit. If you need
manual control, call `HmsGui.seed_startup_project()` and later
`HmsGui.restore_startup_project(seed)`.

HMS 4.12 may show a `New Version Available` modal before automation can
continue. Dismiss it through JAB:

```python
HmsGui.dismiss_update_prompt(
    jre_bin=r"C:\Program Files\HEC\HEC-HMS\4.12\jre\bin"
)
```

## Sessions

Use a session when doing several operations against the same HMS window.

```python
from hms_commander import HmsGui

with HmsGui.attach() as gui:
    gui.focus("Basin Model [A100_1PCT]")
    gui.select("Components", role_filter="page tab")
    gui.select("A100C", role_filter=None)
    area = gui.read_component_field("Area:")
```

## Known Workflows

Some HMS menus are disabled until the relevant basin model is active. Use
`activate_basin_model()` before global editors such as `Parameters > Subbasin Area`.

```python
with HmsGui.attach(jre_bin=r"C:\Program Files\HEC\HEC-HMS\4.12\jre\bin") as gui:
    gui.activate_basin_model("Jan_1997")
    result = gui.safe_invoke_action(
        "Subbasin Area",
        role_filter="menu item",
        ancestor_name="Parameters",
        close_dialogs=False,
        keep_dialog_open=True,
    )
    gui.close_dialogs()
```

Report dialogs can be opened directly by menu item name. Their combo boxes often
accept direct accessible selection:

```python
result = HmsGui.invoke(
    "Standard Report...",
    jre_bin=r"C:\Program Files\HEC\HEC-HMS\4.12\jre\bin",
    role_filter="menu item",
    ancestor_name="Reports",
    close_dialogs=False,
    keep_dialog_open=True,
)

with HmsGui.attach(
    hwnd=result.dialogs[0].hwnd,
    jre_bin=r"C:\Program Files\HEC\HEC-HMS\4.12\jre\bin",
) as dialog:
    dialog.select_combo_by_label_ex("Compute", "RUN: Jan_1997")
```

Some Swing combos report a selected child through JAB without updating the
visible application value. Use the keyboard fallback for those known cases and
verify an application-visible effect.

```python
HmsGui.select_combo_by_label(
    "Sorting:",
    "Alphabetic",
    force_keyboard_fallback=True,
    hwnd=editor_hwnd,
    jre_bin=r"C:\Program Files\HEC\HEC-HMS\4.12\jre\bin",
)
```

Report dialogs and top-level global editors can leave the main HMS frame
minimized or positioned off-screen after they close. `close_dialogs()` restores
the main frame automatically; `restore_main_window()` is available when a
workflow needs an explicit restore before coordinate-based fallback.

## Live Regression Tests

The default GUI tests do not require HMS. Live HMS/JAB regression tests are
available behind the `requires_hms_gui` marker:

```powershell
$env:HMS_GUI_PROJECT = "C:\Users\ajith\Downloads\Truckee_River\Truckee_River\Truckee_River.hms"
$env:HMS_GUI_PATH = "C:\Program Files\HEC\HEC-HMS\4.12"
$env:HMS_GUI_BASIN = "Jan_1997"
$env:HMS_GUI_RUN = "RUN: Jan_1997"
python -m pytest -m requires_hms_gui tests/test_gui_live.py
```

Set `HMS_GUI_LAUNCH=1` when the tests should seed startup state and launch HMS.
Without it, the tests attach to an already-open project and verify the title
before exercising the GUI workflows.

## Control Boundaries

`HmsGui` is not the preferred compute interface. Simulation runs should go
through `HmsCmdr` or `HmsJython`; project file edits should go through the
existing parser-backed APIs. GUI control is for cases where HMS exposes useful
state only through the Swing interface or where a GUI-verifiable workflow is
needed.

Some HMS menu items run immediately and may mutate project state. Keep GUI
exploration read-only unless the workflow is explicitly intended to change a
cloned project.
