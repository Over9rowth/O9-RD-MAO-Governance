import unittest
import tempfile
import subprocess
import shutil
import json
import sys
import os
import hashlib
import concurrent.futures
from pathlib import Path

RUNNER = str(Path(__file__).resolve().parent.parent / "gate_runner.py")
TEST_SECRET = {"O9_APPROVAL_SECRET": "UNITTEST-HUMAN-SECRET-KEY-2026-V15"}

class TestGateRunnerV15(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        # V1.6.1: the zero-file scan guard now applies to `check .` as well, so every
        # temp repo gets one ordinary source file to scan.
        (self.cwd / "app_main.py").write_text("def main():\n    return 0\n", encoding="utf-8")

    def tearDown(self):
        apr_log = self.cwd / "o9_workspace" / "approvals.jsonl"
        if apr_log.exists():
            try:
                os.chmod(apr_log, 0o666)
            except Exception:
                pass
        ws = (self.cwd / "o9_workspace").resolve()
        ws_id = hashlib.sha256(str(ws).encode("utf-8")).hexdigest()[:16]
        anchor_file = Path.home() / ".o9-trust" / f"anchor_{ws_id}.sha256"
        if anchor_file.exists():
            try:
                os.chmod(anchor_file, 0o666)
                anchor_file.unlink()
            except Exception:
                pass
        self.tmp.cleanup()

    def run_cli(self, *args, env_override=TEST_SECRET, unset_secret=False):
        env = os.environ.copy()
        if unset_secret:
            env.pop("O9_APPROVAL_SECRET", None)
            env.pop("O9_EXPECTED_KEY_FP", None)
        elif env_override:
            env.update(env_override)
        return subprocess.run(
            [sys.executable, RUNNER, *args],
            cwd=self.cwd, text=True, capture_output=True, env=env
        )

    def test_1_r1_fail_closed_when_no_secret_configured(self):
        """R1 (Suggestion 1 & 3): 无密钥环境下 freeze / approve / check 必须全部拒绝执行"""
        self.run_cli("init", unset_secret=True)
        res_frz = self.run_cli("freeze", unset_secret=True)
        self.assertNotEqual(res_frz.returncode, 0)
        self.assertIn("No valid signing key configured", res_frz.stdout)

        res_chk = self.run_cli("check", ".", unset_secret=True)
        self.assertNotEqual(res_chk.returncode, 0)
        self.assertIn("No valid signing key configured", res_chk.stdout)

    def test_2_r2_r3_unconditional_freeze_hmac_and_external_anchor(self):
        """R2 & R3: 伪造 FREEZE 记录或 chmod 篡改 approvals.jsonl 必须被无条件 HMAC 与外部锚点阻断"""
        self.run_cli("init")
        self.run_cli("freeze")

        apr_log = self.cwd / "o9_workspace" / "approvals.jsonl"
        os.chmod(apr_log, 0o666)
        fake_rec = {
            "type": "FREEZE", "baseline_id": "BL-999", "parent_baseline_id": "BL-001",
            "spec_sha256": "deadbeef" * 8, "forced": True, "prev_hmac": "FAKE", "at": "2026-11-03", "hmac": "forged_mac"
        }
        with open(apr_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(fake_rec) + "\n")

        res = self.run_cli("check", ".")
        self.assertNotEqual(res.returncode, 0)
        self.assertTrue("Tampering" in res.stdout or "HMAC verification failed" in res.stdout or "hash-chain broken" in res.stdout)

    def test_3_r4_block_self_closed_bugs_by_ai_or_coder(self):
        """R4 (Suggestion 5): 缺陷状态虽为 closed，但关闭者是 AI自己 或 Coder-A 时必须阻断"""
        self.run_cli("init")
        self.run_cli("freeze")
        self.run_cli("approve", "station_master")

        review_file = self.cwd / "o9_workspace" / "review_and_defects.yaml"
        base_txt = review_file.read_text(encoding="utf-8")

        # AI 自关 Bug -> 必须拦截
        bad_bug = "defects:\n  - bug_id: BUG-1\n    status: closed\n    closed_by_tester: AI_Self_Closer\n"
        review_file.write_text(base_txt.replace("defects: []", bad_bug), encoding="utf-8")
        res_bad = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res_bad.returncode, 0)
        self.assertTrue("unauthorized role" in res_bad.stdout or "unauthorized identity" in res_bad.stdout)

        # 独立 QA (qa_lead) 使用 close-bug 签名后关闭 Bug -> 允许通过
        self.run_cli("close-bug", "BUG-1", "qa_lead")
        good_bug = "defects:\n  - bug_id: BUG-1\n    status: closed\n    closed_by_tester: qa_lead\n"
        review_file.write_text(base_txt.replace("defects: []", good_bug), encoding="utf-8")
        res_good = self.run_cli("check", ".", "--gate=G5")
        self.assertEqual(res_good.returncode, 0)

    def test_4_r5_block_fake_or_dev_null_test_evidence(self):
        """R5 (Suggestion 6): evidence_log_ref 指向 /dev/null 或不存在文件时必须阻断"""
        self.run_cli("init")
        self.run_cli("freeze")
        self.run_cli("approve", "station_master")

        review_file = self.cwd / "o9_workspace" / "review_and_defects.yaml"
        base_txt = review_file.read_text(encoding="utf-8")
        review_file.write_text(
            base_txt.replace("o9_workspace/evidence/run-bb-001.log", "/dev/null"),
            encoding="utf-8"
        )
        res = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res.returncode, 0)
        self.assertTrue("Invalid device/null test evidence path" in res.stdout or "missing test evidence file" in res.stdout.lower())

    def test_5_g7_all_three_decisions_and_ipynb_scan(self):
        """Suggestion 7 & 9: G7 三项决定完整校验 + .ipynb 扫描拦截"""
        self.run_cli("init")
        self.run_cli("freeze")
        self.run_cli("approve", "station_master")

        # G7 默认模板三项决定齐全，应通过
        res_g7 = self.run_cli("check", ".", "--gate=G7")
        self.assertEqual(res_g7.returncode, 0)

        # 写入含 TODO 的 .ipynb 文件 -> 必须拦截
        nb_file = self.cwd / "analysis.ipynb"
        nb_file.write_text('{"cells": [{"source": ["# TODO: fake notebook result"]}]}', encoding="utf-8")
        res_nb = self.run_cli("check", ".", "--gate=G7")
        self.assertNotEqual(res_nb.returncode, 0)
        self.assertIn("ANTI-STUB BLOCKER", res_nb.stdout)

    def test_6_legacy_t1_to_t15_regressions(self):
        """T1-T15 回归保护：无基线阻断、单文件部署、非法参数拦截"""
        standalone = self.cwd / "gate_runner.py"
        shutil.copyfile(RUNNER, standalone)
        res_init = subprocess.run([sys.executable, str(standalone), "init"], cwd=self.cwd, text=True, capture_output=True)
        self.assertEqual(res_init.returncode, 0)

        # 无基线时 check 阻断
        res_no_bl = self.run_cli("check", ".")
        self.assertNotEqual(res_no_bl.returncode, 0)

        # 非法参数阻断
        self.assertNotEqual(self.run_cli("check", ".", "--gate=G9").returncode, 0)
        self.assertNotEqual(self.run_cli("approve", "--force").returncode, 0)

    def test_7_s3_block_unauthenticated_yaml_bug_close_and_verify_signed_close(self):
        """S3: 拦截未经 close-bug 签名绑定的手写 YAML 关单，经签名后方可放行"""
        self.run_cli("init")
        self.run_cli("freeze")
        self.run_cli("approve", "station_master")

        review_file = self.cwd / "o9_workspace" / "review_and_defects.yaml"
        base_txt = review_file.read_text(encoding="utf-8")

        # 场景 A: AI 在 YAML 中自称 closed，但未在 approvals.jsonl 中进行 BUG_CLOSE 签名
        unverified_bug = "defects:\n  - bug_id: BUG-101\n    status: closed\n    closed_by_tester: qa_lead\n"
        review_file.write_text(base_txt.replace("defects: []", unverified_bug), encoding="utf-8")

        res_unauth = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res_unauth.returncode, 0)
        self.assertTrue("BUG_CLOSE" in res_unauth.stdout)

        # 场景 B: 运行 close-bug 写入加密签名记录后，再次校验应顺利通过
        res_close = self.run_cli("close-bug", "BUG-101", "qa_lead")
        self.assertEqual(res_close.returncode, 0)
        self.assertIn("BUG_CLOSE", res_close.stdout)

        res_ok = self.run_cli("check", ".", "--gate=G5")
        self.assertEqual(res_ok.returncode, 0)

    def test_8_s1_block_ai_self_invented_secret_via_pinned_key_fingerprint(self):
        """S1: 外部锚点钉死密钥指纹后，AI 试图使用自造假密钥重签或核验必须被当场阻断"""
        human_secret = {"O9_APPROVAL_SECRET": "HUMAN-PINNED-SECRET-987654"}
        ai_secret = {"O9_APPROVAL_SECRET": "AI-SELF-INVENTED-SECRET-FAKE"}

        self.run_cli("init", env_override=human_secret)
        self.run_cli("freeze", env_override=human_secret)

        # AI 尝试使用自造假密钥执行 check -> 必须被指纹钉死拦截
        res_ai_chk = self.run_cli("check", ".", env_override=ai_secret)
        self.assertNotEqual(res_ai_chk.returncode, 0)
        self.assertIn("Signing key fingerprint mismatch", res_ai_chk.stdout)

        # AI 尝试使用自造假密钥执行 freeze --force -> 同样必须被当场拦截
        res_ai_frz = self.run_cli("freeze", "--force", env_override=ai_secret)
        self.assertNotEqual(res_ai_frz.returncode, 0)
        self.assertIn("Signing key fingerprint mismatch", res_ai_frz.stdout)

        # 人类使用原密钥核验 -> 正常通过
        res_human_chk = self.run_cli("check", ".", env_override=human_secret)
        self.assertEqual(res_human_chk.returncode, 0)

    def test_9_redteam_a1_a4_a5_a6_a7_a9b_a11b_a12_a16_a18_defenses(self):
        """Red-Team Defenses: A1, A4, A5, A6, A7, A9b, A11b, A12, A16, A18 & C-04 G6 prose note"""
        self.run_cli("init")
        self.run_cli("freeze")
        self.run_cli("approve", "station_master")

        apr_log = self.cwd / "o9_workspace" / "approvals.jsonl"
        saved_ledger = apr_log.read_text(encoding="utf-8")
        ws = (self.cwd / "o9_workspace").resolve()
        ws_id = hashlib.sha256(str(ws).encode("utf-8")).hexdigest()[:16]
        anchor_file = Path.home() / ".o9-trust" / f"anchor_{ws_id}.sha256"
        saved_anchor = anchor_file.read_text(encoding="utf-8")

        # 1. A1 & A16: Truncate approvals.jsonl -> init blocked
        os.chmod(apr_log, 0o666)
        apr_log.write_text("", encoding="utf-8")
        res_init_blocked = self.run_cli("init")
        self.assertNotEqual(res_init_blocked.returncode, 0)
        self.assertIn("Security Violation (C-01/A16)", res_init_blocked.stdout)

        # Restore ledger, delete anchor -> check fail-closed (C-02)
        apr_log.write_text(saved_ledger, encoding="utf-8")
        if anchor_file.exists():
            os.chmod(anchor_file, 0o666)
            anchor_file.unlink()
        res_chk_no_anchor = self.run_cli("check", ".")
        self.assertNotEqual(res_chk_no_anchor.returncode, 0)
        self.assertIn("Fail-Closed", res_chk_no_anchor.stdout)
        # V1.6.1: with the append-only registry in the verification path, a deleted anchor
        # is now caught one layer earlier (R01) instead of by C-02 -- either block is valid.
        self.assertTrue(
            "Fail-Closed (R01)" in res_chk_no_anchor.stdout
            or "Fail-Closed (C-02)" in res_chk_no_anchor.stdout
        )

        # Restore anchor
        anchor_file.write_text(saved_anchor, encoding="utf-8")
        os.chmod(anchor_file, 0o444)

        # 2. A4 & A6: Empty dir check blocked; stub in tests/bad.py blocked
        empty_d = self.cwd / "empty_dir"
        empty_d.mkdir()
        res_empty = self.run_cli("check", "empty_dir")
        self.assertNotEqual(res_empty.returncode, 0)
        self.assertIn("Zero code files scanned", res_empty.stdout)

        bad_py = self.cwd / "tests" / "bad.py"
        bad_py.parent.mkdir(exist_ok=True)
        bad_py.write_text("# TODO: fix me\n", encoding="utf-8")
        res_bad_py = self.run_cli("check", ".")
        self.assertNotEqual(res_bad_py.returncode, 0)
        self.assertIn("ANTI-STUB BLOCKER", res_bad_py.stdout)
        bad_py.unlink()

        # 3. A5 & A12: Case-insensitive, TODO_1, fake assert, pass-only, UTF-16
        src_d = self.cwd / "src"
        src_d.mkdir(exist_ok=True)
        test_f = src_d / "mod.py"

        # Case-insensitive # todo:
        test_f.write_text("# todo: lower\n", encoding="utf-8")
        self.assertIn("ANTI-STUB BLOCKER", self.run_cli("check", ".").stdout)

        # TODO_1
        test_f.write_text("x = 'TODO_1'\n", encoding="utf-8")
        self.assertIn("ANTI-STUB BLOCKER", self.run_cli("check", ".").stdout)

        # assert True, "msg"
        test_f.write_text("assert True, 'msg'\n", encoding="utf-8")
        self.assertIn("FAKE-ASSERT BLOCKER", self.run_cli("check", ".").stdout)

        # assert x == x
        test_f.write_text("assert val == val\n", encoding="utf-8")
        self.assertIn("FAKE-ASSERT BLOCKER", self.run_cli("check", ".").stdout)

        # pass-only function
        test_f.write_text("def dummy():\n    pass\n", encoding="utf-8")
        self.assertIn("pass-only", self.run_cli("check", ".").stdout)

        # UTF-16 BOM with TODO
        test_f.write_bytes("# TODO utf16 stub\n".encode("utf-16"))
        self.assertIn("ANTI-STUB BLOCKER", self.run_cli("check", ".").stdout)
        test_f.unlink()

        # 4. A7 & A18: open_defects caught; phantom bug close-bug blocked
        rev_f = self.cwd / "o9_workspace" / "review_and_defects.yaml"
        base_rev = rev_f.read_text(encoding="utf-8")

        rev_f.write_text(base_rev + "\nopen_defects:\n  - bug_id: BUG-SECRET\n    status: open\n", encoding="utf-8")
        res_a7 = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res_a7.returncode, 0)
        self.assertIn("BUG-SECRET", res_a7.stdout)
        self.assertIn("open", res_a7.stdout)
        rev_f.write_text(base_rev, encoding="utf-8")

        res_a18 = self.run_cli("close-bug", "BUG-9999", "qa_lead")
        self.assertNotEqual(res_a18.returncode, 0)
        self.assertIn("Phantom Bug Prevention (A18)", res_a18.stdout)

        # 5. A9b & A11b: Non-object JSON in approvals.jsonl; concurrent close-bug
        os.chmod(apr_log, 0o666)
        with open(apr_log, "a", encoding="utf-8") as f:
            f.write("[]\n")
        res_a9b = self.run_cli("check", ".")
        self.assertNotEqual(res_a9b.returncode, 0)
        self.assertIn("Non-object JSON record", res_a9b.stdout)

        lines = [l for l in apr_log.read_text(encoding="utf-8").splitlines() if l.strip() != "[]"]
        apr_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

        bug_entries = "\ndefects:\n" + "\n".join([
            f"  - bug_id: BUG-CONC-{i}\n    status: closed\n    closed_by_tester: qa_lead"
            for i in range(5)
        ]) + "\n"
        rev_f.write_text(base_rev.replace("defects: []", bug_entries), encoding="utf-8")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            futures = [
                pool.submit(self.run_cli, "close-bug", f"BUG-CONC-{i}", "qa_lead")
                for i in range(5)
            ]
            results = [fut.result() for fut in futures]

        for r in results:
            self.assertEqual(r.returncode, 0)

        rec_txt = apr_log.read_text(encoding="utf-8")
        for i in range(5):
            self.assertIn(f"BUG-CONC-{i}", rec_txt)

        # 6. C-04 & G6 prose note verification
        rtm_f = self.cwd / "o9_workspace" / "rtm_acceptance.md"
        rtm_txt = rtm_f.read_text(encoding="utf-8")
        rtm_f.write_text(rtm_txt + "\n\nNote: All items passed after a previously failed build on staging.\n", encoding="utf-8")
        (self.cwd / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
        res_rtm = self.run_cli("check", ".", "--gate=G6")
        self.assertEqual(res_rtm.returncode, 0)

if __name__ == "__main__":
    unittest.main()
