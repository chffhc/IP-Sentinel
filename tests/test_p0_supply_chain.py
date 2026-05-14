from pathlib import Path
import hashlib
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHELL_FILES = [p for p in ROOT.rglob("*.sh") if ".git" not in p.parts]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


class P0SupplyChainTests(unittest.TestCase):
    def test_runtime_scripts_do_not_pin_upstream_hotyue_repo(self):
        offenders = []
        for path in SHELL_FILES:
            text = read(path)
            if "raw.githubusercontent.com/hotyue/IP-Sentinel" in text:
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_repo_raw_url_is_configurable_with_owner_repo_ref_defaults(self):
        install = read(ROOT / "core" / "install.sh")
        self.assertIn("REPO_OWNER=", install)
        self.assertIn("REPO_NAME=", install)
        self.assertIn("REPO_REF=", install)
        self.assertIn("raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${REPO_REF}", install)

    def test_agent_ota_verifies_sha256_before_executing_downloaded_installer(self):
        daemon = read(ROOT / "core" / "agent_daemon.sh")
        self.assertIn("sha256sum -c", daemon)
        self.assertIn("AGENT_INSTALL_SHA256", daemon)
        checksum_pos = daemon.index("sha256sum -c")
        exec_pos = daemon.index("bash /tmp/ota_agent.sh")
        self.assertLess(checksum_pos, exec_pos)

    def test_master_ota_verifies_sha256_before_executing_downloaded_installer(self):
        master = read(ROOT / "master" / "tg_master.sh")
        self.assertIn("sha256sum -c", master)
        self.assertIn("MASTER_INSTALL_SHA256", master)
        checksum_pos = master.index("sha256sum -c")
        exec_pos = master.index("bash /tmp/install_master.sh")
        self.assertLess(checksum_pos, exec_pos)

    def test_version_manifest_contains_install_script_checksums(self):
        version = read(ROOT / "version.txt")
        self.assertIsNotNone(re.search(r"^AGENT_INSTALL_SHA256=[0-9a-f]{64}$", version, re.M))
        self.assertIsNotNone(re.search(r"^MASTER_INSTALL_SHA256=[0-9a-f]{64}$", version, re.M))

    def test_version_manifest_checksums_match_installer_files(self):
        values = dict(line.split("=", 1) for line in read(ROOT / "version.txt").splitlines() if "=" in line)
        agent_hash = hashlib.sha256((ROOT / "core" / "install.sh").read_bytes()).hexdigest()
        master_hash = hashlib.sha256((ROOT / "master" / "install_master.sh").read_bytes()).hexdigest()
        self.assertEqual(values.get("AGENT_INSTALL_SHA256"), agent_hash)
        self.assertEqual(values.get("MASTER_INSTALL_SHA256"), master_hash)


if __name__ == "__main__":
    unittest.main()
