import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "master" / "tg_master.sh"
DB_LIB = ROOT / "master" / "lib_db.sh"
VALIDATE = ROOT / "scripts" / "validate.sh"
CI = ROOT / ".github" / "workflows" / "ci.yml"


class P3EngineeringHardeningTests(unittest.TestCase):
    def test_sqlite_helper_uses_bound_parameters(self):
        self.assertTrue(DB_LIB.exists(), "master/lib_db.sh must centralize SQLite access")
        content = DB_LIB.read_text(encoding="utf-8")
        self.assertIn(".parameter init", content)
        self.assertIn("temp.sqlite_parameters", content)
        self.assertRegex(content, r"db_query\s*\(\)")
        self.assertRegex(content, r"sqlite_literal\s*\(\)")

    def test_dynamic_sql_does_not_interpolate_shell_variables_in_db_exec(self):
        content = MASTER.read_text(encoding="utf-8")
        offenders = []
        for lineno, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if "db_exec" in stripped and "$" in stripped and not stripped.startswith("#"):
                offenders.append(f"{lineno}: {stripped}")
        self.assertEqual(offenders, [], "Dynamic SQL must use db_query placeholders, not db_exec interpolation:\n" + "\n".join(offenders[:20]))

    def test_master_uses_placeholders_for_runtime_sql(self):
        content = MASTER.read_text(encoding="utf-8")
        self.assertIn(". \"$SCRIPT_DIR/lib_db.sh\"", content)
        runtime_queries = re.findall(r'db_query\s+"([^"]+)"', content)
        self.assertGreaterEqual(len(runtime_queries), 10, "runtime SQL should be routed through db_query")
        for sql in runtime_queries:
            upper = sql.upper()
            if any(keyword in upper for keyword in ("WHERE", "VALUES", "SET")):
                self.assertRegex(sql, r"@p[0-9]+", f"runtime SQL missing placeholder: {sql}")

    def test_master_installer_deploys_database_helper(self):
        installer = (ROOT / "master" / "install_master.sh").read_text(encoding="utf-8")
        self.assertIn("master/lib_db.sh", installer)
        self.assertIn("${MASTER_DIR}/lib_db.sh", installer)

    def test_validation_script_covers_tests_json_shell_and_optional_linters(self):
        self.assertTrue(VALIDATE.exists(), "scripts/validate.sh must provide local dry-run validation")
        content = VALIDATE.read_text(encoding="utf-8")
        self.assertIn("python3 -m unittest discover -s tests -v", content)
        self.assertIn("json.load", content)
        self.assertIn("bash -n", content)
        self.assertIn("shellcheck", content)
        self.assertIn("shfmt", content)

    def test_ci_blocks_on_validation_script(self):
        self.assertTrue(CI.exists(), ".github/workflows/ci.yml must exist")
        content = CI.read_text(encoding="utf-8")
        self.assertIn("scripts/validate.sh", content)
        self.assertIn("pull_request", content)
        self.assertIn("push", content)


if __name__ == "__main__":
    unittest.main()
