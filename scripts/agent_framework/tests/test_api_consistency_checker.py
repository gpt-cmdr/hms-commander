"""Contracts for the report-only HMS API consistency checker (no inference, no imports of checked code)."""
import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import textwrap
import unittest

REPO = Path(__file__).resolve().parents[3]
CHECKER = REPO / '.claude/skills/api-consistency-auditor/scripts/check_api_consistency.py'
spec = importlib.util.spec_from_file_location('check_api_consistency', CHECKER)
checker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)

CONFIG = textwrap.dedent('''\
    exception_classes:
      - class_name: StatefulPrj
        reason: holds project state
    classmethod_classes:
      - class_name: CachedCatalog
        reason: class-level cache
    log_call_exempt:
      - qualname: Quiet.helper
    path_str_exempt:
      - qualname: Runs.set_dss_file.dss_file
    ''')

VALID = textwrap.dedent('''\
    from pathlib import Path
    from typing import Union
    from .Decorators import log_call

    class HmsGood:
        """Static class -- do not instantiate."""

        @staticmethod
        @log_call
        def get_subbasins(basin_path: Union[str, Path], hms_object=None) -> dict:
            """Read subbasins.

            Args:
                basin_path: Basin model file.
                hms_object: Optional HmsPrj.

            Returns:
                dict: Subbasin parameters.
            """
            return {}

    class StatefulPrj:
        def __init__(self):
            self.folder = None

        def refresh(self, hms_object=None) -> None:
            """Refresh."""

    class CachedCatalog:
        @classmethod
        @log_call
        def load(cls) -> dict:
            """Load."""
            return {}

    class Quiet:
        @staticmethod
        def helper() -> None:
            """Exempt."""

    class Runs:
        @staticmethod
        @log_call
        def set_dss_file(run_name: str, dss_file: str, hms_object=None) -> bool:
            """Set DSS file name.

            Args:
                run_name: Run.
                dss_file: File name written into the run file.
                hms_object: Optional HmsPrj.
            """
            return True
    ''')

INVALID = textwrap.dedent('''\
    from pathlib import Path

    class HmsBad:
        def __init__(self):
            pass

        def instance_method(self) -> None:
            """Instance."""

        @log_call
        @staticmethod
        def wrong_order() -> None:
            """Order."""

        @staticmethod
        def no_log(basin_path: Path, project=None, run_num: int = 1) -> None:
            """Missing log_call.

            Parameters
            ----------
            basin_path : Path
            """

        @classmethod
        @log_call
        def cls_method(cls) -> None:
            """Unlisted classmethod."""

        @staticmethod
        @log_call
        def bad_default(hms_object="hms"):
            pass
    ''')


class ApiConsistencyChecker(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / '.auditor.yaml').write_text(CONFIG)
        self.config = checker.load_config(self.root / '.auditor.yaml')

    def run_on(self, source):
        module = self.root / 'pkg' / 'Module.py'
        module.parent.mkdir(exist_ok=True)
        module.write_text(source)
        return checker.check_file(module, self.root, self.config, include_private=False)

    def test_fallback_config_parser(self):
        self.assertEqual(self.config['exception_classes'], {'StatefulPrj'})
        self.assertEqual(self.config['classmethod_classes'], {'CachedCatalog'})
        self.assertEqual(self.config['log_call_exempt'], {'Quiet.helper'})
        self.assertEqual(self.config['path_str_exempt'], {'Runs.set_dss_file.dss_file'})

    def test_valid_patterns_have_no_findings(self):
        self.assertEqual(self.run_on(VALID), [])

    def test_invalid_patterns_are_reported(self):
        found = {(f.rule, f.symbol) for f in self.run_on(INVALID)}
        expected = {
            ('HMS-API-01', 'HmsBad.__init__'),
            ('HMS-API-02', 'HmsBad.instance_method'),
            ('HMS-API-02', 'HmsBad.cls_method'),
            ('HMS-API-03', 'HmsBad.wrong_order'),
            ('HMS-API-04', 'HmsBad.instance_method'),
            ('HMS-API-04', 'HmsBad.no_log'),
            ('HMS-API-05', 'HmsBad.no_log'),
            ('HMS-API-05', 'HmsBad.bad_default'),
            ('HMS-API-06', 'HmsBad.no_log'),
            ('HMS-API-07', 'HmsBad.no_log'),
            ('HMS-API-08', 'HmsBad.bad_default'),
            ('HMS-API-09', 'HmsBad.no_log'),
            ('HMS-API-09', 'HmsBad.bad_default'),
        }
        self.assertEqual(found, expected)

    def test_private_module_skips_public_api_rules(self):
        module = self.root / 'pkg' / '_internal.py'
        module.parent.mkdir(exist_ok=True)
        module.write_text(INVALID)
        rules = {f.rule for f in checker.check_file(module, self.root, self.config, include_private=False)}
        self.assertEqual(rules, {'HMS-API-01', 'HMS-API-02', 'HMS-API-03', 'HMS-API-05'})

    def test_report_only_exit_and_json(self):
        module = self.root / 'pkg' / 'Module.py'
        module.parent.mkdir(exist_ok=True)
        module.write_text(INVALID)
        args = [str(module), '--root', str(self.root), '--config', str(self.root / '.auditor.yaml')]
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(checker.main(args + ['--format', 'json']), 0)
        self.assertTrue(json.loads(out.getvalue())['findings'])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(checker.main(args + ['--fail-on', 'major']), 1)


if __name__ == '__main__':
    unittest.main()
