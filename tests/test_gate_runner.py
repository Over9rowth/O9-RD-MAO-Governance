import unittest
import tempfile
import subprocess
import sys
import os
from pathlib import Path

RUNNER = str(Path(__file__).resolve().parent.parent / "gate_runner.py")

class TestGateRunner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, RUNNER, *args],
            cwd=self.cwd, text=True, capture_output=True
        )

    def test_1_fail_closed_without_baseline(self):
        """1. 无基线时 check 必须 Fail-Closed 并返回非零退出码"""
        self.run_cli("init")
        res = self.run_cli("check", ".")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Fail-Closed", res.stdout)

    def test_2_tampering_detected_and_freeze_protection(self):
        """2. 基线篡改必须被检出，且重复 freeze 无 --force 必须被阻断"""
        self.run_cli("init")
        res1 = self.run_cli("freeze")
        self.assertEqual(res1.returncode, 0)
        self.assertIn("BL-001", res1.stdout)

        # 重复 freeze 无 --force 应被拒绝
        res_dup = self.run_cli("freeze")
        self.assertNotEqual(res_dup.returncode, 0)

        # 篡改 spec 文件后 check 应报错阻断
        spec = self.cwd / "o9_workspace" / "spec_and_contracts.md"
        spec.write_text(spec.read_text(encoding="utf-8") + "\nTampered line!", encoding="utf-8")
        res_chk = self.run_cli("check", ".")
        self.assertNotEqual(res_chk.returncode, 0)
        self.assertIn("Tampering Detected", res_chk.stdout)

    def test_3_anti_stub_and_vacuous_assert_and_path_parts(self):
        """3. 必须抓出 TODO 和 assert True，且不能误跳过名叫 my_docs_app 的业务目录"""
        self.run_cli("init")
        self.run_cli("freeze")
        self.run_cli("approve", "Tester")

        # 创建名叫 my_docs_app 的子目录（测试 Path.parts 不会因为包含 'docs' 子串而误跳过）
        src_dir = self.cwd / "my_docs_app"
        src_dir.mkdir()
        bad_file = src_dir / "app.ts"
        bad_file.write_text("function login() {\n  // TODO: implement auth\n}\n", encoding="utf-8")

        res = self.run_cli("check", ".", "--require-approval")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("ANTI-STUB BLOCKER", res.stdout)

        # 换成 assert True 作弊代码
        bad_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
        (src_dir / "test_fake.py").write_text("def test_x():\n    assert 1 # fake\n", encoding="utf-8")
        bad_file.unlink()
        res2 = self.run_cli("check", ".", "--require-approval")
        self.assertNotEqual(res2.returncode, 0)
        self.assertIn("FAKE-ASSERT BLOCKER", res2.stdout)

if __name__ == "__main__":
    unittest.main()
