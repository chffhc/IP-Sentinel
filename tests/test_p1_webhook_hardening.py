from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


class P1WebhookHardeningTests(unittest.TestCase):
    def test_agent_generates_and_persists_independent_webhook_secret(self):
        install = read(ROOT / "core" / "install.sh")
        self.assertIn("WEBHOOK_SECRET", install)
        self.assertRegex(install, r"openssl\s+rand\s+-hex\s+32")
        self.assertIn('WEBHOOK_SECRET="$WEBHOOK_SECRET"', install)

    def test_agent_webhook_uses_webhook_secret_not_chat_id_for_hmac(self):
        daemon = read(ROOT / "core" / "agent_daemon.sh")
        self.assertIn("WEBHOOK_SECRET", daemon)
        self.assertNotIn("利用 CHAT_ID 作为 PSK", daemon)
        self.assertNotRegex(daemon, r"AUTH_TOKEN\s*=.*CHAT_ID")
        self.assertRegex(daemon, r"line\.startswith\('WEBHOOK_SECRET='\)")

    def test_master_stores_webhook_secret_and_uses_it_for_signed_urls(self):
        master = read(ROOT / "master" / "tg_master.sh")
        self.assertIn("webhook_secret TEXT", master)
        self.assertRegex(master, r"generate_signed_url\(\) \{[\s\S]*local webhook_secret=\$4")
        self.assertNotIn('openssl dgst -sha256 -hmac "$CHAT_ID"', master)
        self.assertIn('openssl dgst -sha256 -hmac "$webhook_secret"', master)
        self.assertIn("webhook_secret", master)

    def test_registration_payload_carries_webhook_secret(self):
        install = read(ROOT / "core" / "install.sh")
        master = read(ROOT / "master" / "tg_master.sh")
        self.assertIn('${WEBHOOK_SECRET}', install)
        self.assertIn("RAW_WEBHOOK_SECRET", master)
        self.assertRegex(master, r"tr -cd 'a-fA-F0-9'.*cut -c 1-64")

    def test_systemd_services_include_basic_hardening_directives(self):
        install = read(ROOT / "core" / "install.sh")
        master_install = read(ROOT / "master" / "install_master.sh")
        combined = install + "\n" + master_install
        for directive in [
            "NoNewPrivileges=true",
            "PrivateTmp=true",
            "ProtectSystem=full",
            "ProtectHome=true",
        ]:
            self.assertIn(directive, combined)


if __name__ == "__main__":
    unittest.main()
