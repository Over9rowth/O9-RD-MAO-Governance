import unittest
import tempfile
import subprocess
import shutil
import json
import sys
import os
from pathlib import Path

RUNNER = str(Path(__file__).resolve().parent.parent / "gate_runner.py")

class TestGateRunnerV12(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)

    def tearDown(self):
        # Ensure read-only approvals.jsonl can be cleaned up on Windows
        apr_log = self.cwd / "o9_workspace" / "approvals.jsonl"
        if apr_log.exists():
            os.chmod(apr_log, 0o666)
        self.tmp.cleanup()

    def run_cli(self, *args, env_override=None):
        env = os.environ.copy()
        if env_override:
            env.update(env_override)
        return subprocess.run(
            [sys.executable, RUNNER, *args],
            cwd=self.cwd, text=True, capture_output=True, env=env
        )

    def test_1_fail_closed_without_baseline(self):
        """T3: 无基线时 check 必须 Fail-Closed"""
        self.run_cli("init")
        res = self.run_cli("check", ".")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Fail-Closed", res.stdout)

    def test_2_single_file_deployment_no_crash(self):
        """T14: 当单文件部署（无 templates/ 目录）时，init 绝不能 Crash"""
        standalone_runner = self.cwd / "gate_runner.py"
        shutil.copyfile(RUNNER, standalone_runner)
        res = subprocess.run([sys.executable, str(standalone_runner), "init"], cwd=self.cwd, text=True, capture_output=True)
        self.assertEqual(res.returncode, 0)
        self.assertTrue((self.cwd / "o9_workspace" / "project_state.json").exists())

    def test_3_block_state_json_tampering_and_forged_approval(self):
        """T6/T7/T8/T9: 防御 AI 直接篡改 project_state.json 或无密钥伪造 approve / freeze --force"""
        human_env = {"O9_APPROVAL_SECRET": "HUMAN-MASTER-SECRET-999"}
        ai_env = {"O9_APPROVAL_SECRET": "AI-GUESSED-WRONG-KEY"}

        self.run_cli("init")
        self.run_cli("freeze", env_override=human_env)
        self.run_cli("approve", "station_master", env_override=human_env)

        # 正常校验通过
        res_ok = self.run_cli("check", ".", "--require-approval", env_override=human_env)
        self.assertEqual(res_ok.returncode, 0)

        # 攻击路径 A: AI 篡改 spec 后，尝试自己跑 freeze --force（无人类密钥）-> 必须被拦截！
        spec = self.cwd / "o9_workspace" / "spec_and_contracts.md"
        spec.write_text(spec.read_text(encoding="utf-8") + "\nAI secret edit!", encoding="utf-8")
        res_force = self.run_cli("freeze", "--force", env_override=ai_env)
        self.assertNotEqual(res_force.returncode, 0)
        self.assertIn("Unauthorized 'freeze --force'", res_force.stdout)

        # 攻击路径 B: AI 直接手改 project_state.json 里的 spec_sha256 对齐篡改后的文件 -> 必须被 approvals.jsonl 拦截！
        state_file = self.cwd / "o9_workspace" / "project_state.json"
        state = json.loads(state_file.read_text(encoding="utf-8"))
        import hashlib
        fake_hash = hashlib.sha256(spec.read_bytes()).hexdigest()
        state["active_baseline"]["spec_sha256"] = fake_hash
        state_file.write_text(json.dumps(state), encoding="utf-8")

        res_tamper = self.run_cli("check", ".", "--require-approval", env_override=human_env)
        self.assertNotEqual(res_tamper.returncode, 0)
        self.assertIn("Tampering Detected", res_tamper.stdout)

    def test_4_strict_approver_role_and_flag_validation(self):
        """T7 & T15: 拒绝 SelfSignedAI 非法角色、拒绝 approve --force 与非法 --gate=G9"""
        self.run_cli("init")
        self.run_cli("freeze")

        res_role = self.run_cli("approve", "SelfSignedAI")
        self.assertNotEqual(res_role.returncode, 0)
        self.assertIn("Unauthorized approver role", res_role.stdout)

        res_flag = self.run_cli("approve", "--force")
        self.assertNotEqual(res_flag.returncode, 0)

        res_gate = self.run_cli("check", ".", "--gate=G9")
        self.assertNotEqual(res_gate.returncode, 0)
        self.assertIn("Invalid --gate=G9", res_gate.stdout)

    def test_5_g5_g6_fail_closed_on_deleted_ledger_or_open_variants(self):
        """T10 & T11: G5/G6 台账删除必须 Fail-Closed，且 status: Open / resolved 均被白名单拦截"""
        self.run_cli("init")
        self.run_cli("freeze")
        self.run_cli("approve", "station_master")

        review_file = self.cwd / "o9_workspace" / "review_and_defects.yaml"
        # 测试 status: Open (首字母大写) 及 status: resolved (非关闭白名单)
        for bad_status in ["Open", "resolved", "in-progress"]:
            txt = review_file.read_text(encoding="utf-8").replace("defects: []", f"defects:\n  - bug_id: BUG-1\n    status: {bad_status}\n")
            review_file.write_text(txt, encoding="utf-8")
            res = self.run_cli("check", ".", "--gate=G5")
            self.assertNotEqual(res.returncode, 0, f"Failed to block status: {bad_status}")
            # 恢复
            review_file.write_text(txt.replace(f"defects:\n  - bug_id: BUG-1\n    status: {bad_status}\n", "defects: []"), encoding="utf-8")

        # 测试直接删除 review_and_defects.yaml (T11) -> 必须阻断！
        review_file.unlink()
        res_del = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res_del.returncode, 0)
        self.assertIn("Missing", res_del.stdout)

    def test_6_anti_stub_and_vacuous_assert_and_path_parts(self):
        """T12 & T13: Path.parts 精确匹配与 TODO / assert True 拦截"""
        self.run_cli("init")
        self.run_cli("freeze")
        self.run_cli("approve", "station_master")

        src_dir = self.cwd / "my_docs_app"
        src_dir.mkdir()
        bad_file = src_dir / "service.rb"
        bad_file.write_text("# TODO: fix later\n", encoding="utf-8")
        res = self.run_cli("check", ".", "--require-approval")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("ANTI-STUB BLOCKER", res.stdout)

if __name__ == "__main__":
    unittest.main()
