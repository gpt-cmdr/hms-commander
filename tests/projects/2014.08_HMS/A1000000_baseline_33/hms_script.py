"""
HEC-HMS Jython Script (Python 2 compatible)
"""

from hms.model import JythonHms
import sys

project_path = r"test_project\2014.08_HMS\A1000000_baseline_33"
project_name = "A1000000"

try:
    JythonHms.OpenProject(project_name, project_path)
    print "Project opened successfully: " + project_name
except Exception, e:
    print "Error opening project: " + str(e)
    JythonHms.Exit(1)

# Try to open the basin model
try:
    JythonHms.OpenBasinModel("Pre_1PCT")
    print "Basin model opened"
except Exception, e:
    print "Could not open basin: " + str(e)

# Compute the simulation run
run_name = "Pre_1PCT_Run"
try:
    JythonHms.Compute(run_name)
    print "Computation completed for: " + run_name
except Exception, e:
    print "Error during computation: " + str(e)
    JythonHms.Exit(1)

JythonHms.Exit(0)
