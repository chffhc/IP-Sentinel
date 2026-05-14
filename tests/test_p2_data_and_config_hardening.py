from pathlib import Path
import json
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


class P2DataAndConfigHardeningTests(unittest.TestCase):
    def test_map_references_existing_keyword_and_region_files(self):
        data_dir = ROOT / "data"
        map_data = json.loads((data_dir / "map.json").read_text(encoding="utf-8"))
        missing = []
        empty_keywords = []
        for continent in map_data["continents"]:
            for country in continent.get("countries", []):
                keyword_file = country.get("keyword_file")
                self.assertTrue(keyword_file, f"{country.get('id')} missing keyword_file")
                keyword_path = data_dir / "keywords" / keyword_file
                if not keyword_path.exists():
                    missing.append(str(keyword_path.relative_to(data_dir)))
                elif not keyword_path.read_text(encoding="utf-8", errors="ignore").strip():
                    empty_keywords.append(str(keyword_path.relative_to(data_dir)))
                for state in country.get("states", []):
                    for city in state.get("cities", []):
                        rel = Path(country["id"]) / state["id"] / f"{city['id']}.json"
                        region_path = data_dir / "regions" / rel
                        if not region_path.exists():
                            missing.append(str(region_path.relative_to(data_dir)))
                        else:
                            payload = json.loads(region_path.read_text(encoding="utf-8"))
                            self.assertIn("google_module", payload, str(rel))
                            self.assertIn("trust_module", payload, str(rel))
                            self.assertIn("static_urls", payload["trust_module"], str(rel))
                            self.assertIn("white_urls", payload["trust_module"], str(rel))
        self.assertEqual([], missing)
        self.assertEqual([], empty_keywords)

    def test_config_files_are_loaded_through_safe_kv_loader_not_shell_source(self):
        shell_files = [p for p in ROOT.rglob("*.sh") if ".git" not in p.parts]
        offenders = []
        unsafe_patterns = [
            re.compile(r"^\s*source\s+\"?\$CONFIG_FILE\"?"),
            re.compile(r"^\s*source\s+\"?\$CONF\"?"),
            re.compile(r"^\s*source\s+\"?\$\{MASTER_DIR\}/master\.conf\"?"),
            re.compile(r"^\s*source\s+/opt/ip_sentinel/config\.conf"),
        ]
        for path in shell_files:
            rel = path.relative_to(ROOT)
            if str(rel) in {"core/lib_config.sh", "master/lib_config.sh"}:
                continue
            for line_no, line in enumerate(read(path).splitlines(), start=1):
                if any(p.search(line) for p in unsafe_patterns):
                    offenders.append(f"{rel}:{line_no}:{line.strip()}")
        self.assertEqual([], offenders)

    def test_safe_config_loader_rejects_command_substitution_and_exports_allowed_keys_only(self):
        core_loader = read(ROOT / "core" / "lib_config.sh")
        master_loader = read(ROOT / "master" / "lib_config.sh")
        for loader in [core_loader, master_loader]:
            self.assertIn("safe_load_config()", loader)
            self.assertIn("case \"$key\" in", loader)
            self.assertIn("case \"$value\" in", loader)
            for unsafe_char in ["`", "$", "&", "|", "<", ">"]:
                self.assertIn(unsafe_char, loader)
            self.assertNotRegex(loader, r"source\s+\$")
            self.assertIn("export \"$key=$value\"", loader)

    def test_safe_config_loader_does_not_execute_malicious_config_values(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            marker = tmp / "pwned"
            config = tmp / "config.conf"
            config.write_text(
                f'NODE_NAME="safe-node"\nREGION_NAME="$(touch {marker})"\nUNKNOWN_KEY="ignored"\n',
                encoding="utf-8",
            )
            script = f'. "{ROOT / "core" / "lib_config.sh"}"\nsafe_load_config "{config}"\nprintf "%s\\n" "$NODE_NAME"\nprintf "%s\\n" "${{REGION_NAME-unset}}"\n'
            result = subprocess.run(["bash", "-c", script], text=True, capture_output=True, check=True)
            self.assertEqual("safe-node\nunset\n", result.stdout)
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
