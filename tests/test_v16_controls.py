# O9-RD-OFFICIAL-CONFORMANCE-TEST
"""V1.6 control-plane conformance tests.

Every mechanism claimed as `tool-enforced` in docs/CONTROL-MATRIX.md is exercised
here against the real CLI, so the matrix cannot drift away from the implementation:
  G1-01  non-empty spec + structured AC-xxx rows
  G3-01  composite manifest_sha256 (spec + o9_workspace/contracts/**)
  G3-02  detached approval bound to the manifest
  G3-03  .o9_project_id + ~/.o9-trust/index.tsv registry + trust-reset escape hatch
  G5-02  repo-root-confined evidence + latest run selected by recorded_at
  G5-03  order-independent YAML item parsing
"""
import unittest
import re
import datetime
import tempfile
import subprocess
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

RUNNER = str(Path(__file__).resolve().parent.parent / "gate_runner.py")
TEST_SECRET = {"O9_APPROVAL_SECRET": "UNITTEST-HUMAN-SECRET-KEY-2026-V16"}
PROJECT_ID = "PRJ-2026-001"


class TestGateRunnerV16(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        self.ws = self.cwd / "o9_workspace"
        # V1.6.1: the zero-file scan guard now applies to `check .` as well, so every
        # temp repo gets one ordinary source file to scan (test_11 removes it on purpose).
        (self.cwd / "app_main.py").write_text("def main():\n    return 0\n", encoding="utf-8")

    def tearDown(self):
        apr_log = self.ws / "approvals.jsonl"
        if apr_log.exists():
            try:
                os.chmod(apr_log, 0o666)
            except Exception:
                pass
        ws_abs = str(self.ws.resolve())
        ws_id = hashlib.sha256(ws_abs.encode("utf-8")).hexdigest()[:16]
        trust_dir = Path.home() / ".o9-trust"
        for stale in list(trust_dir.glob(f"anchor_{ws_id}.sha256*")):
            try:
                os.chmod(stale, 0o666)
                stale.unlink()
            except Exception:
                pass
        self.tmp.cleanup()

    def run_cli(self, *args, env_override=TEST_SECRET, unset_secret=False):
        env = os.environ.copy()
        env.pop("O9_EXPECTED_KEY_FP", None)
        if unset_secret:
            env.pop("O9_APPROVAL_SECRET", None)
        else:
            env.update(env_override or {})
        return subprocess.run(
            [sys.executable, RUNNER, *args],
            cwd=self.cwd, text=True, capture_output=True, env=env,
        )

    def bootstrap(self):
        self.assertEqual(self.run_cli("init").returncode, 0)
        self.assertEqual(self.run_cli("freeze").returncode, 0)
        self.assertEqual(self.run_cli("approve", "station_master").returncode, 0)

    def read_review(self):
        return (self.ws / "review_and_defects.yaml").read_text(encoding="utf-8")

    def make_g5_passable(self):
        import datetime, re
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        rev_file = self.ws / "review_and_defects.yaml"
        content = rev_file.read_text(encoding="utf-8")
        content = content.replace("source_code_hidden_verified: false", "source_code_hidden_verified: true")
        content = content.replace("exit_code: -1", "exit_code: 0")
        content = re.sub(r"""recorded_at:\s*["'][^"']*["']""", f'recorded_at: "{now_iso}"', content)
        rev_file.write_text(content, encoding="utf-8")
        ev_file = self.ws / "evidence" / "run-bb-001.log"
        ev_file.parent.mkdir(parents=True, exist_ok=True)
        ev_file.write_text("[PASS EVIDENCE]\n", encoding="utf-8")

    def make_g6_passable(self):
        self.make_g5_passable()
        rtm_file = self.ws / "rtm_acceptance.md"
        content = rtm_file.read_text(encoding="utf-8")
        content = content.replace("| not-covered | not-run |", "| covered | passed |")
        rtm_file.write_text(content, encoding="utf-8")

    def make_g7_passable(self):
        self.make_g6_passable()
        rtm_file = self.ws / "rtm_acceptance.md"
        content = rtm_file.read_text(encoding="utf-8")
        content = content.replace("Decision 1 (Sign-Off)**: `pending`", "Decision 1 (Sign-Off)**: `approved`")
        content = content.replace("Decision 1 (Sign-Off): pending", "Decision 1 (Sign-Off): approved")
        rtm_file.write_text(content, encoding="utf-8")
        self.run_cli("approve", "station_master", "--gate=G7")


    # ---------------- VERSION ----------------
    def test_00_version_is_v16(self):
        res = self.run_cli("--version")
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "O9-RD-Next-V1.6.4")

    # ---------------- G1-01 ----------------
    def test_01_g1_01_blocks_empty_or_acless_spec(self):
        self.run_cli("init")
        spec = self.ws / "spec_and_contracts.md"

        spec.write_text("", encoding="utf-8")
        res_empty = self.run_cli("freeze")
        self.assertNotEqual(res_empty.returncode, 0)
        self.assertIn("G1-01", res_empty.stdout)

        spec.write_text("# Spec\n- **In-Scope**: nothing\n", encoding="utf-8")
        res_no_ac = self.run_cli("freeze")
        self.assertNotEqual(res_no_ac.returncode, 0)
        self.assertIn("no structured `AC-xxx`", res_no_ac.stdout)

        # A prose mention of an AC id does not count as a structured row.
        spec.write_text("# Spec\nWe will cover AC-001 later.\n", encoding="utf-8")
        res_prose = self.run_cli("freeze")
        self.assertNotEqual(res_prose.returncode, 0)
        self.assertIn("no structured `AC-xxx`", res_prose.stdout)

        spec.write_text(
            "# Spec\n| AC-ID | REQ-ID | Expected Result |\n| :--- | :--- | :--- |\n"
            "| `AC-001` | `REQ-001` | Returns 200 OK |\n",
            encoding="utf-8",
        )
        self.assertEqual(self.run_cli("freeze").returncode, 0)

    # ---------------- G3-01 / G3-02 ----------------
    def test_02_g3_01_manifest_covers_contract_files_and_breaks_on_tamper(self):
        self.run_cli("init")
        contracts = self.ws / "contracts"
        contracts.mkdir()
        (contracts / "api.yaml").write_text("endpoint: /v1/health\n", encoding="utf-8")
        (contracts / "schema.sql").write_text("CREATE TABLE t(id INT);\n", encoding="utf-8")

        self.assertEqual(self.run_cli("freeze").returncode, 0)

        rec = json.loads((self.ws / "approvals.jsonl").read_text(encoding="utf-8").splitlines()[0])
        self.assertIn("manifest_sha256", rec)
        self.assertEqual(len(rec["files"]), 3)  # spec + 2 contract files
        self.assertTrue(any(f["path"].endswith("contracts/api.yaml") for f in rec["files"]))

        self.assertEqual(self.run_cli("check", ".").returncode, 0)

        # Tampering a NON-spec baseline file must still circuit-break via manifest_sha256.
        (contracts / "api.yaml").write_text("endpoint: /v1/admin\n", encoding="utf-8")
        res = self.run_cli("check", ".")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Baseline Manifest Tampering", res.stdout)
        self.assertIn("modified: ", res.stdout)

        # Approval must also refuse to bind a mutated baseline.
        res_apr = self.run_cli("approve", "station_master")
        self.assertNotEqual(res_apr.returncode, 0)
        self.assertIn("manifest modified after freeze", res_apr.stdout)

    def test_03_g3_01_added_contract_file_after_freeze_is_blocked(self):
        self.bootstrap()
        contracts = self.ws / "contracts"
        contracts.mkdir()
        (contracts / "late.yaml").write_text("added: after-freeze\n", encoding="utf-8")
        res = self.run_cli("check", ".")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Baseline Manifest Tampering", res.stdout)
        self.assertIn("unregistered: ", res.stdout)

    # ---------------- G3-03 ----------------
    def test_04_g3_03_project_id_and_registry_pin_the_binding(self):
        self.run_cli("init")
        pid_file = self.ws / ".o9_project_id"
        self.assertTrue(pid_file.exists())
        meta = json.loads(pid_file.read_text(encoding="utf-8"))
        self.assertEqual(meta["project_id"], PROJECT_ID)

        index = Path.home() / ".o9-trust" / "index.tsv"
        self.assertTrue(index.exists())
        ws_abs = str(self.ws.resolve())
        rows = [l.split("\t") for l in index.read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")]
        mine = [r for r in rows if len(r) >= 3 and r[1] == ws_abs]
        self.assertTrue(mine, "workspace row missing from index.tsv")
        self.assertEqual(mine[0][2], PROJECT_ID)

        # Silently re-binding the workspace to another project must be refused.
        meta["project_id"] = "PRJ-EVIL-999"
        os.chmod(pid_file, 0o666)
        pid_file.write_text(json.dumps(meta), encoding="utf-8")
        res = self.run_cli("init")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Refusing accidental re-binding", res.stdout)

    def test_05_g3_03_trust_reset_is_the_sanctioned_escape_hatch(self):
        self.run_cli("init")
        self.assertEqual(self.run_cli("freeze").returncode, 0)

        # Simulate the R11b dead-end: ledger wiped while the external anchor survives.
        apr = self.ws / "approvals.jsonl"
        os.chmod(apr, 0o666)
        apr.write_text("", encoding="utf-8")
        res_blocked = self.run_cli("init")
        self.assertNotEqual(res_blocked.returncode, 0)
        self.assertIn("Security Violation (C-01/A16)", res_blocked.stdout)

        # A wrong confirmation token cannot reset trust.
        res_bad = self.run_cli("trust-reset", "PRJ-WRONG")
        self.assertNotEqual(res_bad.returncode, 0)
        self.assertIn("Confirmation token mismatch", res_bad.stdout)

        # No signing secret -> fail-closed.
        res_nosecret = self.run_cli("trust-reset", PROJECT_ID, unset_secret=True)
        self.assertNotEqual(res_nosecret.returncode, 0)
        self.assertIn("No valid signing key configured", res_nosecret.stdout)

        # The sanctioned path archives the old state and unblocks the project.
        res_ok = self.run_cli("trust-reset", PROJECT_ID)
        self.assertEqual(res_ok.returncode, 0)
        self.assertIn("TRUST RESET", res_ok.stdout)
        trust_dir = Path.home() / ".o9-trust"
        ws_id = hashlib.sha256(str(self.ws.resolve()).encode("utf-8")).hexdigest()[:16]
        self.assertTrue(
            list(trust_dir.glob(f"anchor_{ws_id}.sha256.bak.*")), "anchor was not archived"
        )

        # Project is usable again.
        self.assertEqual(self.run_cli("freeze").returncode, 0)
        self.assertEqual(self.run_cli("check", ".").returncode, 0)

        # A reset over a NON-empty ledger archives the ledger as well (never deletes it).
        self.assertEqual(self.run_cli("trust-reset", PROJECT_ID).returncode, 0)
        self.assertTrue(list(self.ws.glob("approvals.jsonl.bak.*")), "ledger was not archived")

    def test_09_g3_03_trust_reset_recovers_a_fully_wiped_workspace(self):
        self.run_cli("init")
        self.assertEqual(self.run_cli("freeze").returncode, 0)

        # Total loss (the R11b worst case): the entire o9_workspace/ directory is gone.
        apr = self.ws / "approvals.jsonl"
        if apr.exists():
            os.chmod(apr, 0o666)  # the tool keeps it read-only by design
        shutil.rmtree(self.ws)
        self.assertFalse(self.ws.exists())

        res_init = self.run_cli("init")
        self.assertNotEqual(res_init.returncode, 0)
        self.assertIn("Security Violation (C-01/A16)", res_init.stdout)

        # Recovery works through the local registry, which survives the workspace wipe.
        res_reset = self.run_cli("trust-reset", PROJECT_ID)
        self.assertEqual(res_reset.returncode, 0)
        self.assertIn("TRUST RESET", res_reset.stdout)

        self.assertEqual(self.run_cli("init").returncode, 0)
        self.assertEqual(self.run_cli("freeze").returncode, 0)
        self.assertEqual(self.run_cli("check", ".").returncode, 0)

    def test_10_g3_03_trust_reset_works_on_an_empty_readonly_ledger(self):
        # `init` leaves an empty, read-only approvals.jsonl; trust-reset must still work.
        self.run_cli("init")
        self.assertEqual(self.run_cli("trust-reset", PROJECT_ID).returncode, 0)
        self.assertEqual(self.run_cli("freeze").returncode, 0)
        self.assertEqual(self.run_cli("check", ".").returncode, 0)

    # ---------------- G5-02 ----------------

    def test_06_g5_02_evidence_must_live_inside_repo_root(self):
        self.bootstrap()
        self.make_g5_passable()
        outside = Path(tempfile.mkdtemp()) / "run.log"
        outside.write_text("evidence outside the repo\n", encoding="utf-8")
        try:
            review = self.read_review().replace(
                "o9_workspace/evidence/run-bb-001.log", str(outside)
            )
            (self.ws / "review_and_defects.yaml").write_text(review, encoding="utf-8")
            res = self.run_cli("check", ".", "--gate=G5")
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("escapes the repository root", res.stdout)
        finally:
            outside.unlink(missing_ok=True)
            outside.parent.rmdir()

    def test_07_g5_02_latest_run_is_chosen_by_recorded_at_not_file_order(self):
        self.bootstrap()
        self.make_g5_passable()
        base = self.read_review()
        start = base.index("g5_test_runs:")
        end = base.index("defects:")
        records = [json.loads(line) for line in (self.ws / "approvals.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        freeze_rec = [r for r in records if r.get("type") == "FREEZE"][-1]
        import datetime
        f_dt = datetime.datetime.fromisoformat(freeze_rec["at"].replace("Z", "+00:00"))
        t_old = (f_dt + datetime.timedelta(seconds=1)).isoformat()
        t_mid = (f_dt + datetime.timedelta(seconds=2)).isoformat()
        two_runs = (
            "g5_test_runs:\n"
            "  - run_id: RUN-NEW-FAIL\n"
            f"    recorded_at: \"{t_mid}\"\n"
            "    exit_code: 1\n"
            "    source_code_hidden_verified: true\n"
            "    evidence_log_ref: \"o9_workspace/evidence/run-bb-001.log\"\n"
            "  - run_id: RUN-OLD-PASS\n"
            f"    recorded_at: \"{t_old}\"\n"
            "    exit_code: 0\n"
            "    source_code_hidden_verified: true\n"
            "    evidence_log_ref: \"o9_workspace/evidence/run-bb-001.log\"\n"
        )
        (self.ws / "review_and_defects.yaml").write_text(
            base[:start] + two_runs + base[end:], encoding="utf-8"
        )

        # Document order ends with a PASSING run, but the newest `recorded_at` FAILED.
        res = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("RUN-NEW-FAIL", res.stdout)

        # Flip the timestamps: the newest run now passes, so the gate opens.
        flipped = two_runs.replace(t_mid, t_old).replace(f'run_id: RUN-OLD-PASS\n    recorded_at: "{t_old}"', f'run_id: RUN-OLD-PASS\n    recorded_at: "{t_mid}"')
        (self.ws / "review_and_defects.yaml").write_text(
            base[:start] + flipped + base[end:], encoding="utf-8"
        )
        self.assertEqual(self.run_cli("check", ".", "--gate=G5").returncode, 0)

    # ---------------- G5-03 ----------------
    def test_08_g5_03_defect_keys_may_appear_in_any_order(self):
        self.bootstrap()
        self.make_g5_passable()
        base = self.read_review()
        # `bug_id` deliberately LAST inside the item.
        unordered = (
            "defects:\n"
            "  - status: closed\n"
            "    closed_by_tester: qa_lead\n"
            "    bug_id: BUG-ORD-1\n"
        )
        (self.ws / "review_and_defects.yaml").write_text(
            base.replace("defects: []", unordered), encoding="utf-8"
        )

        res = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("BUG-ORD-1", res.stdout)
        self.assertIn("BUG_CLOSE", res.stdout)

        # close-bug must also see the existing defect regardless of key order.
        res_close = self.run_cli("close-bug", "BUG-ORD-1", "qa_lead")
        self.assertEqual(res_close.returncode, 0)
        self.assertNotIn("Phantom Bug Prevention", res_close.stdout)

        self.assertEqual(self.run_cli("check", ".", "--gate=G5").returncode, 0)

    # ---------------- V1.6.1 closure tests ----------------
    def test_11_g4_01_zero_file_scan_is_blocked_even_for_dot(self):
        """G4-01: `scanned_files > 0` must hold regardless of how the target is spelled.

        v1.6 exempted `check .` from the zero-file guard, which made the G4-01 row of
        CONTROL-MATRIX false. Both spellings must now block, and --allow-empty-scan must
        still pass but announce that it saw nothing.
        """
        self.bootstrap()
        (self.cwd / "app_main.py").unlink()          # the repo now has zero code files

        res_dot = self.run_cli("check", ".")
        self.assertNotEqual(res_dot.returncode, 0)
        self.assertIn("Zero code files scanned", res_dot.stdout)

        res_path = self.run_cli("check", str(self.cwd))
        self.assertNotEqual(res_path.returncode, 0)
        self.assertIn("Zero code files scanned", res_path.stdout)

        res_override = self.run_cli("check", ".", "--allow-empty-scan")
        self.assertEqual(res_override.returncode, 0)
        self.assertIn("[WARNING] empty scan accepted", res_override.stdout)

    def test_12_r04_renamed_file_cannot_evade_the_scan(self):
        """R04: the old SELF_TEST_FILES basename whitelist let `mv cheat.py confirm.py` pass."""
        self.bootstrap()
        cheat = self.cwd / "cheat.py"
        cheat.write_text("# TODO: unimplemented\n", encoding="utf-8")
        self.assertNotEqual(self.run_cli("check", ".").returncode, 0)

        for decoy in ("confirm.py", "redteam.py", "test_gate_runner.py"):
            cheat.rename(self.cwd / decoy)
            res = self.run_cli("check", ".")
            self.assertNotEqual(res.returncode, 0, f"renaming to {decoy} evaded the scan")
            self.assertIn("ANTI-STUB BLOCKER", res.stdout)
            (self.cwd / decoy).rename(cheat)

    def test_13_r09c_g5_run_without_recorded_at_is_inadmissible(self):
        """R09c: omitting `recorded_at` must not restore document-order fallback."""
        self.bootstrap()
        self.make_g5_passable()
        base = self.read_review()
        start = base.index("g5_test_runs:")
        end = base.index("defects:")
        unstamped = (
            "g5_test_runs:\n"
            "  - run_id: RUN-OK\n"
            "    exit_code: 0\n"
            "    source_code_hidden_verified: true\n"
            "    evidence_log_ref: \"o9_workspace/evidence/run-bb-001.log\"\n"
        )
        (self.ws / "review_and_defects.yaml").write_text(
            base[:start] + unstamped + base[end:], encoding="utf-8"
        )
        res = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("recorded_at", res.stdout)

    def test_14_t2_trust_reset_leaves_a_signed_trace_and_archive_must_match(self):
        """T2: the reset must be a signed, chained record -- and an unexplained archive blocks."""
        self.run_cli("init")
        self.assertEqual(self.run_cli("freeze").returncode, 0)
        self.assertEqual(self.run_cli("trust-reset", PROJECT_ID).returncode, 0)

        ledger = (self.ws / "approvals.jsonl").read_text(encoding="utf-8")
        records = [json.loads(l) for l in ledger.splitlines() if l.strip()]
        self.assertEqual(records[0]["type"], "TRUST_RESET")
        self.assertEqual(records[0]["seq"], 1)
        self.assertIn("archived_ledger_sha256", records[0])
        self.assertIn("previous_key_fp", records[0])

        self.assertEqual(self.run_cli("freeze").returncode, 0)
        self.assertEqual(self.run_cli("check", ".").returncode, 0)

        # Forge an extra archive the ledger knows nothing about -> must be refused.
        bogus = self.ws / "approvals.jsonl.bak.19700101T000000Z"
        bogus.write_text('{"type":"FREEZE"}\n', encoding="utf-8")
        res = self.run_cli("check", ".")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Unrecorded trust-root reset", res.stdout)
        bogus.unlink()

        # Delete the archive that TRUST_RESET points at -> the erased history must be refused.
        archives = list(self.ws.glob("approvals.jsonl.bak.*"))
        self.assertTrue(archives, "expected the pre-reset ledger to be archived")
        for archive in archives:
            os.chmod(archive, 0o666)
            archive.unlink()
        res_missing = self.run_cli("check", ".")
        self.assertNotEqual(res_missing.returncode, 0)
        self.assertIn("Missing trust-root archive", res_missing.stdout)

    def test_15_r01_deleting_the_anchor_is_no_longer_a_way_to_start_over(self):
        """R01: the append-only registry must catch an anchor deletion that the ledger forgot."""
        self.bootstrap()
        trust_dir = Path.home() / ".o9-trust"
        ws_id = hashlib.sha256(str(self.ws.resolve()).encode("utf-8")).hexdigest()[:16]
        for anchor in list(trust_dir.glob(f"anchor_{ws_id}.sha256")):
            os.chmod(anchor, 0o666)
            anchor.unlink()
        apr = self.ws / "approvals.jsonl"
        os.chmod(apr, 0o666)
        apr.write_text("", encoding="utf-8")

        res_init = self.run_cli("init")
        self.assertNotEqual(res_init.returncode, 0)
        self.assertIn("Unrecorded trust-root reset (R01)", res_init.stdout)

        res_check = self.run_cli("check", ".")
        self.assertNotEqual(res_check.returncode, 0)
        self.assertIn("Fail-Closed (R01)", res_check.stdout)



    # ---------------- V1.6.2 additions ----------------

    def test_00_zero_work_factory_init_must_fail_g5_g6_g7(self):
        """P0-1: init factory state is default-red; G5/G6/G7 fail without actual testing work."""
        self.bootstrap()
        res_g5 = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res_g5.returncode, 0)

        res_g6 = self.run_cli("check", ".", "--gate=G6")
        self.assertNotEqual(res_g6.returncode, 0)

        res_g7 = self.run_cli("check", ".", "--gate=G7")
        self.assertNotEqual(res_g7.returncode, 0)

    def test_16_future_timestamp_detected_in_recorded_at(self):
        """1.2: Future timestamp in recorded_at (> 5s) must be blocked."""
        self.bootstrap()
        self.make_g5_passable()
        base = self.read_review()
        futuristic = re.sub(r"""recorded_at:\s*["'][^"']*["']""", 'recorded_at: "2099-12-31T23:59:59Z"', base)
        (self.ws / "review_and_defects.yaml").write_text(futuristic, encoding="utf-8")
        res = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Future timestamp detected in recorded_at!", res.stdout)

    def test_17_flow_style_yaml_forbidden(self):
        """1.3: Flow-style YAML ('{' or '}') in review_and_defects.yaml must be blocked."""
        self.bootstrap()
        self.make_g5_passable()
        base = self.read_review()
        flow = base.replace("defects: []", "defects:\n  - {bug_id: BUG-FLOW, status: open}")
        (self.ws / "review_and_defects.yaml").write_text(flow, encoding="utf-8")
        res = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Flow-style YAML ('{' or '}') is forbidden", res.stdout)

    def test_18_duplicate_yaml_key_detected(self):
        """1.5: Duplicate YAML key within an item must be blocked."""
        self.bootstrap()
        self.make_g5_passable()
        base = self.read_review()
        dup = base.replace("defects: []", "defects:\n  - bug_id: BUG-DUP\n    status: open\n    status: closed")
        (self.ws / "review_and_defects.yaml").write_text(dup, encoding="utf-8")
        res = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Duplicate YAML key 'status' detected in item!", res.stdout)

    def test_19_comment_spoofing_hidden_source_blocked(self):
        """1.6: Comment spoofing source_code_hidden_verified must be blocked after comment stripping."""
        self.bootstrap()
        self.make_g5_passable()
        base = self.read_review()
        spoofed = base.replace(
            "source_code_hidden_verified: true",
            "# source_code_hidden_verified: true\n    source_code_hidden_verified: false"
        )
        (self.ws / "review_and_defects.yaml").write_text(spoofed, encoding="utf-8")
        res = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Missing 'source_code_hidden_verified: true'", res.stdout)

    def test_20_tampering_after_bug_close_blocked(self):
        """1.7: Tampering with review_and_defects.yaml after BUG_CLOSE signature must be blocked."""
        self.bootstrap()
        self.make_g5_passable()
        base = self.read_review()
        bug_entry = "defects:\n  - bug_id: BUG-TAMPER\n    status: closed\n    closed_by_tester: qa_lead\n"
        (self.ws / "review_and_defects.yaml").write_text(base.replace("defects: []", bug_entry), encoding="utf-8")
        self.assertEqual(self.run_cli("close-bug", "BUG-TAMPER", "qa_lead").returncode, 0)
        self.assertEqual(self.run_cli("check", ".", "--gate=G5").returncode, 0)

        # Post-signing tamper: modify review_and_defects.yaml
        tampered = (self.ws / "review_and_defects.yaml").read_text(encoding="utf-8") + "\n# sneak edit\n"
        (self.ws / "review_and_defects.yaml").write_text(tampered, encoding="utf-8")
        res = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("review_and_defects.yaml was modified after BUG_CLOSE signature!", res.stdout)

    def test_21_rtm_must_cover_all_frozen_acs(self):
        """1.8: RTM must 100% cover all frozen ACs and forbid not-run/failed/blocked/not-covered/skipped/pending."""
        self.bootstrap()
        self.make_g6_passable()
        rtm_file = self.ws / "rtm_acceptance.md"
        rtm_orig = rtm_file.read_text(encoding="utf-8")

        # 1. Missing AC-001
        rtm_file.write_text(rtm_orig.replace("`AC-001`", "`AC-999`"), encoding="utf-8")
        res_missing = self.run_cli("check", ".", "--gate=G6")
        self.assertNotEqual(res_missing.returncode, 0)
        self.assertIn("does not cover all frozen ACs", res_missing.stdout)

        # 2. Forbidden status 'pending'
        rtm_file.write_text(rtm_orig.replace("`passed`", "`pending`"), encoding="utf-8")
        res_pending = self.run_cli("check", ".", "--gate=G6")
        self.assertNotEqual(res_pending.returncode, 0)
        self.assertIn("Unverified or failed AC row", res_pending.stdout)

        # 3. Forbidden status 'skipped'
        rtm_file.write_text(rtm_orig.replace("`passed`", "`skipped`"), encoding="utf-8")
        res_skipped = self.run_cli("check", ".", "--gate=G6")
        self.assertNotEqual(res_skipped.returncode, 0)
        self.assertIn("Unverified or failed AC row", res_skipped.stdout)

    def test_22_missing_g7_gate_approval_blocked(self):
        """1.9: G7 check requires dedicated 'approve station_master --gate=G7'."""
        self.bootstrap()
        self.make_g6_passable()
        rtm_file = self.ws / "rtm_acceptance.md"
        rtm_content = rtm_file.read_text(encoding="utf-8")
        rtm_content = rtm_content.replace("Decision 1 (Sign-Off)**: `pending`", "Decision 1 (Sign-Off)**: `approved`")
        rtm_content = rtm_content.replace("Decision 1 (Sign-Off): pending", "Decision 1 (Sign-Off): approved")
        rtm_file.write_text(rtm_content, encoding="utf-8")

        # Only G3 approved so far -> G7 check must block
        res = self.run_cli("check", ".", "--gate=G7")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Missing detached G7 approval in approvals.jsonl!", res.stdout)

        # After approving G7 -> passes
        self.assertEqual(self.run_cli("approve", "station_master", "--gate=G7").returncode, 0)
        res_ok = self.run_cli("check", ".", "--gate=G7")
        self.assertEqual(res_ok.returncode, 0)

    def test_23_target_path_escapes_repo_root_blocked(self):
        """1.10: target_path escaping repo root must be blocked."""
        self.bootstrap()
        outside = Path(tempfile.mkdtemp())
        try:
            res = self.run_cli("check", str(outside))
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("escapes the repository root", res.stdout)
        finally:
            outside.rmdir()

    def test_24_skip_dirs_only_at_root_scans_sub_docs(self):
        """1.11: SKIP_DIRS (docs, templates, prompts) only skipped at target root; subdirectories like src/docs/ are scanned."""
        self.bootstrap()
        evil_dir = self.cwd / "src" / "docs"
        evil_dir.mkdir(parents=True, exist_ok=True)
        evil_file = evil_dir / "evil.py"
        evil_file.write_text("# TODO: sneak stub\n", encoding="utf-8")
        res = self.run_cli("check", ".")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("ANTI-STUB BLOCKER", res.stdout)

    def test_25_lock_regular_file_reclaimed(self):
        """1.14: Lock path being a regular file is safely unlinked to prevent DoS."""
        self.bootstrap()
        ws_abs = str(self.ws.resolve())
        ws_id = hashlib.sha256(ws_abs.encode("utf-8")).hexdigest()[:16]
        lock_dir = Path.home() / ".o9-trust" / "locks" / f"lock_{ws_id}"
        lock_dir.parent.mkdir(parents=True, exist_ok=True)
        lock_dir.write_text("malicious ordinary file dos attempt\n", encoding="utf-8")
        self.assertTrue(lock_dir.is_file())

        # freeze should successfully unlink the regular file and acquire lock
        res = self.run_cli("freeze", "--force")
        self.assertEqual(res.returncode, 0)
        self.assertFalse(lock_dir.is_file())

    def test_26_round6_top2_top3_fixes(self):
        """Top 2 & Top 3 regression tests covering 1.6b/c, N2, N3, N6, 1.11b, 1.12, 1.13, 1.14b, 1.16."""
        # 1. 1.6b/c: source_code_hidden_verified in command string cannot spoof the checker
        self.bootstrap()
        self.make_g5_passable()
        rev_f = self.ws / "review_and_defects.yaml"
        content = rev_f.read_text(encoding="utf-8")
        spoofed = content.replace("source_code_hidden_verified: true", "source_code_hidden_verified: false")
        spoofed = spoofed.replace('command_executed: "pytest tests/"', 'command_executed: "pytest ; source_code_hidden_verified: true"')
        rev_f.write_text(spoofed, encoding="utf-8")
        res = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Missing 'source_code_hidden_verified: true'", res.stdout)

        # 2. N2: Quote-aware YAML comment stripper does not truncate '#' inside quotes
        from gate_runner import strip_yaml_comments
        stripped = strip_yaml_comments('command: "pytest -k \'login or #123\'" # this is a comment')
        self.assertIn("#123", stripped)
        self.assertNotIn("this is a comment", stripped)

        # 3. N3: RTM referencing non-existent or failed run_id is blocked
        self.make_g5_passable()
        self.make_g6_passable()
        rtm_f = self.ws / "rtm_acceptance.md"
        rtm_txt = rtm_f.read_text(encoding="utf-8")
        rtm_f.write_text(rtm_txt.replace("RUN-BB-001", "RUN-FAKE-999"), encoding="utf-8")
        res_fake_run = self.run_cli("check", ".", "--gate=G6")
        self.assertNotEqual(res_fake_run.returncode, 0)
        self.assertIn("RTM references non-existent or failed G5 run_id 'RUN-FAKE-999'", res_fake_run.stdout)
        rtm_f.write_text(rtm_txt, encoding="utf-8")

        # 4. N6: recorded_at earlier than baseline freeze timestamp is blocked
        rev_txt = rev_f.read_text(encoding="utf-8")
        stale_rev = re.sub(r"""recorded_at:\s*["'][^"']*["']""", 'recorded_at: "2020-01-01T00:00:00Z"', rev_txt)
        rev_f.write_text(stale_rev, encoding="utf-8")
        res_stale = self.run_cli("check", ".", "--gate=G5")
        self.assertNotEqual(res_stale.returncode, 0)
        self.assertIn("Stale or back-dated timestamp in recorded_at!", res_stale.stdout)
        rev_f.write_text(rev_txt, encoding="utf-8")

        # 5. 1.11b: code under docs/ root is scanned
        docs_dir = self.cwd / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        docs_code = docs_dir / "prod_logic.py"
        docs_code.write_text("# TODO: code in docs\n", encoding="utf-8")
        res_docs = self.run_cli("check", ".")
        self.assertNotEqual(res_docs.returncode, 0)
        self.assertIn("ANTI-STUB BLOCKER", res_docs.stdout)
        docs_code.unlink()

        # 6. 1.12: new extensions and new vacuous asserts & pass-only docstrings
        # 6a. .mjs extension
        mjs_file = self.cwd / "component.mjs"
        mjs_file.write_text("// TODO: js module\n", encoding="utf-8")
        res_mjs = self.run_cli("check", ".")
        self.assertNotEqual(res_mjs.returncode, 0)
        self.assertIn("ANTI-STUB BLOCKER", res_mjs.stdout)
        mjs_file.unlink()

        # 6b. assertTrue(1 == 1)
        test_py = self.cwd / "test_fake.py"
        test_py.write_text("def test_it():\n    assertTrue(1 == 1)\n", encoding="utf-8")
        res_assert = self.run_cli("check", ".")
        self.assertNotEqual(res_assert.returncode, 0)
        self.assertIn("FAKE-ASSERT BLOCKER", res_assert.stdout)

        # 6c. raise NotImplementedError is permitted per P8
        test_py.write_text("def prod_func():\n    raise NotImplementedError\n", encoding="utf-8")
        res_nie = self.run_cli("check", ".")
        self.assertEqual(res_nie.returncode, 0)

        # 6d. docstring-aware pass body
        test_py.write_text('def empty_func():\n    """Docstring explanation"""\n    pass\n', encoding="utf-8")
        res_pass = self.run_cli("check", ".")
        self.assertNotEqual(res_pass.returncode, 0)
        self.assertIn("Contains pass-only stub function body!", res_pass.stdout)
        test_py.unlink()

        # 7. 1.14b: readonly lock file handling
        ws_abs = str(self.ws.resolve())
        ws_id = hashlib.sha256(ws_abs.encode("utf-8")).hexdigest()[:16]
        lock_dir = Path.home() / ".o9-trust" / "locks" / f"lock_{ws_id}"
        lock_dir.parent.mkdir(parents=True, exist_ok=True)
        lock_dir.write_text("readonly lock test\n", encoding="utf-8")
        os.chmod(lock_dir, 0o444)
        res_ro_lock = self.run_cli("freeze", "--force")
        self.assertEqual(res_ro_lock.returncode, 0)

        # 8. 1.16: directory replacing approvals.jsonl prints blocker without unhandled traceback
        apr_log = self.ws / "approvals.jsonl"
        if apr_log.exists():
            try:
                apr_log.chmod(0o666)
            except Exception:
                pass
            apr_log.unlink()
        apr_log.mkdir()
        res_dir = self.run_cli("check", ".")
        self.assertNotEqual(res_dir.returncode, 0)
        self.assertIn("[BLOCKER] Expected regular file but found directory", res_dir.stdout)
        self.assertNotIn("Traceback", res_dir.stderr)
        apr_log.rmdir()

    def test_18_v164_same_second_freeze_abc_abstractmethod_and_n3b_run_id(self):
        """v1.6.4 regression: P13 same-second freeze & check, P8 ABC compatibility, N3b RTM run_id enforcement."""
        # 1. P13: Same-second freeze & check (sub-second precision truncation tolerance)
        self.bootstrap()
        self.make_g5_passable()
        self.make_g6_passable()
        self.make_g7_passable()

        res_frz = self.run_cli("freeze", "--force")
        self.assertEqual(res_frz.returncode, 0)

        records = [json.loads(l) for l in (self.ws / "approvals.jsonl").read_text(encoding="utf-8").splitlines()]
        freeze_rec = [r for r in records if r.get("type") == "FREEZE"][-1]
        now_sec = freeze_rec["at"][:19] + "Z"

        rev_f = self.ws / "review_and_defects.yaml"
        rev_txt = rev_f.read_text(encoding="utf-8")
        rev_txt = re.sub(r"""recorded_at:\s*["'][^"']*["']""", f'recorded_at: "{now_sec}"', rev_txt)
        rev_f.write_text(rev_txt, encoding="utf-8")

        res_apr3 = self.run_cli("approve", "station_master")
        self.assertEqual(res_apr3.returncode, 0)
        res_apr7 = self.run_cli("approve", "station_master", "--gate=G7")
        self.assertEqual(res_apr7.returncode, 0)

        res_chk = self.run_cli("check", ".", "--gate=G7")
        self.assertEqual(res_chk.returncode, 0)
        self.assertIn("[PASSED] Gate G7 checks passed", res_chk.stdout)

        # 2. P8: ABC with @abstractmethod and raise NotImplementedError is not blocked
        abc_file = self.cwd / "src" / "base_interface.py"
        abc_file.parent.mkdir(parents=True, exist_ok=True)
        abc_code = '''import abc

class BaseEngine(abc.ABC):
    """Abstract base engine."""

    @abc.abstractmethod
    def start(self) -> None:
        raise NotImplementedError("Subclasses must implement start")

    @abc.abstractmethod
    def stop(self) -> None:
        raise NotImplementedError
'''
        abc_file.write_text(abc_code, encoding="utf-8")
        res_abc = self.run_cli("check", ".")
        self.assertEqual(res_abc.returncode, 0)
        abc_file.unlink()

        # 3. N3b: RTM row omitting RUN-xxx ID is blocked
        rtm_f = self.ws / "rtm_acceptance.md"
        rtm_orig = rtm_f.read_text(encoding="utf-8")
        rtm_no_run = rtm_orig.replace("RUN-BB-001", "N/A")
        rtm_f.write_text(rtm_no_run, encoding="utf-8")
        res_n3b = self.run_cli("check", ".", "--gate=G6")
        self.assertNotEqual(res_n3b.returncode, 0)
        self.assertIn("N3b Violation", res_n3b.stdout)
        rtm_f.write_text(rtm_orig, encoding="utf-8")

        # 4. N3c: AC declared 'automated' in frozen spec cannot use manual 'no-run-required' exemption in RTM
        rtm_manual_spoof = rtm_orig.replace("RUN-BB-001", "no-run-required | manual")
        rtm_f.write_text(rtm_manual_spoof, encoding="utf-8")
        res_n3c = self.run_cli("check", ".", "--gate=G6")
        self.assertNotEqual(res_n3c.returncode, 0)
        self.assertIn("N3c Violation", res_n3c.stdout)
        rtm_f.write_text(rtm_orig, encoding="utf-8")

if __name__ == "__main__":
    unittest.main()
