"""End-to-end tests for intent-kit: real git repos in a temp folder, a fake home folder
for Claude's transcripts, and the tools run as the hooks and agents run them.

  python -m unittest discover -s kit/tests -v
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
BOOTSTRAP = KIT / "bootstrap.py"
SID_A = "aaaaaaaa-1111-2222-3333-444444444444"
SID_B = "bbbbbbbb-1111-2222-3333-444444444444"


def mangle(p) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", str(p))


class Env:
    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="intent-kit-test-")).resolve()
        self.home = self.tmp / "home"
        self.home.mkdir()
        gc = self.tmp / "gitconfig"
        gc.write_text("[init]\n\tdefaultBranch = main\n", encoding="utf-8")
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "GIT_"))}
        self.env.update({
            "HOME": str(self.home), "USERPROFILE": str(self.home), "GIT_CONFIG_GLOBAL": str(gc),
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@example.invalid",
        })

    def run(self, *args, cwd=None, input=None, sid=None, ok=True):
        env = dict(self.env)
        if sid:
            env["CLAUDE_CODE_SESSION_ID"] = sid
        r = subprocess.run([str(a) for a in args], cwd=str(cwd or self.tmp), env=env, input=input,
                           capture_output=True, text=True, encoding="utf-8")
        if ok and r.returncode != 0:
            raise AssertionError(f"{args} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
        return r

    def py(self, script, *args, **kw):
        return self.run(sys.executable, script, *args, **kw)

    def git(self, cwd, *args, **kw):
        return self.run("git", "-C", cwd, *args, **kw)

    def tool(self, checkout, name, *args, tools="tools", **kw):
        return self.py(Path(checkout) / tools / name, *args, cwd=checkout, **kw)

    def transcript(self, checkout, sid, records):
        d = self.home / ".claude" / "projects" / mangle(Path(checkout).resolve())
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{sid}.jsonl"
        with p.open("a", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps({"sessionId": sid, **r}, separators=(",", ":")) + "\n")  # as Claude writes
        return p

    def cleanup(self):
        def onerr(func, path, _):
            os.chmod(path, 0o700)
            func(path)
        shutil.rmtree(self.tmp, onerror=onerr)


def user(text, ts, **flags):
    return {"type": "user", "timestamp": ts, "message": {"role": "user", "content": text}, **flags}


class KitTest(unittest.TestCase):
    def setUp(self):
        self.e = Env()

    def tearDown(self):
        self.e.cleanup()

    def new_project(self, name="proj", *extra):
        root = self.e.tmp / name
        self.e.py(BOOTSTRAP, "init", root, "--name", "Proj", "--summary", "A test project.", *extra)
        return root

    def main_files(self, root, folder):
        return self.e.git(root, "ls-tree", "-r", "--name-only", "main", "--", folder).stdout.split()

    # ---------------------------------------------------------------------------------

    def test_new_project(self):
        root = self.new_project("proj", "--layers", "research,experiments", "--stances", "wide-search")
        for rel in ["CLAUDE.md", "README.md", "METHOD.md", "METHOD-RULES.md", "intent-kit.json",
                    "intent/vision.md", "plan/requirements.md", "research/README.md", "experiments/README.md",
                    "tools/to_main.py", ".githooks/prepare-commit-msg", ".claude/settings.json"]:
            self.assertTrue((root / rel).is_file(), rel)
        self.assertFalse((root / "concepts").exists())
        # the method ships; the kit's own record doesn't
        self.assertEqual(self.main_files(root, "intent/log"), [])
        self.assertEqual(self.main_files(root, "plan/lessons"), ["plan/lessons/README.md"])
        self.assertEqual(self.main_files(root, "plan/decisions"), ["plan/decisions/README.md"])
        self.assertEqual((root / "METHOD.md").read_bytes(), (KIT / "PHILOSOPHY.md").read_bytes())
        claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("\n@METHOD-RULES.md\n", claude)
        self.assertLess(len(claude), 900)
        rules = (root / "METHOD-RULES.md").read_text(encoding="utf-8")
        self.assertIn("Experiments close the loop", rules)
        self.assertIn("Don't narrow the search early", rules)
        self.assertNotIn("Judge plausibility", rules)
        self.assertIn("Confidential.", rules)
        self.assertTrue((root / "record" / ".git").is_dir())
        self.assertEqual(self.e.git(root, "status", "--porcelain").stdout.strip(), "")
        self.assertEqual(self.e.git(root, "ls-files", "record").stdout.strip(), "")
        self.e.tool(root, "kit.py", "check")

    def test_hooks_capture_and_trailer(self):
        root = self.new_project()
        t = self.e.transcript(root, SID_A, [user("hello", "2026-01-02T00:00:00Z")])
        hook = lambda ev: json.dumps({"hook_event_name": ev, "session_id": SID_A, "transcript_path": str(t)})
        r = self.e.tool(root, "capture_session.py", input=hook("SessionStart"))
        self.assertEqual(r.stdout.strip(), "")  # SessionStart stdout goes into the agent's context
        self.assertEqual((root / ".claude" / "current-session").read_text().strip(), SID_A)
        copied = root / "record" / "sessions" / f"2026-01-02_{SID_A}.jsonl"
        self.assertTrue(copied.is_file())
        log = lambda: self.e.git(root / "record", "log", "--format=%s").stdout
        self.assertIn("sync at start", log())
        for _ in range(9):
            self.e.tool(root, "capture_session.py", input=hook("Stop"))
        self.assertNotIn("turn 10", log())
        self.e.transcript(root, SID_A, [user("more", "2026-01-02T00:01:00Z")])
        self.e.tool(root, "capture_session.py", input=hook("Stop"))
        self.assertIn("turn 10", log())
        self.assertIn(mangle(root), (root / "record" / "transcript-dirs.txt").read_text())
        (root / "x.txt").write_text("x")
        self.e.git(root, "add", "x.txt")
        self.e.git(root, "commit", "-q", "-m", "x", sid=SID_A)
        self.assertIn(f"Session: {SID_A}", self.e.git(root, "log", "-1", "--format=%B").stdout)

    def test_extractor_filters(self):
        root = self.new_project()
        self.e.transcript(root, SID_A, [
            user("First real intent.", "2026-01-02T00:00:01Z"),
            user("<command-name>/clear</command-name>", "2026-01-02T00:00:02Z"),
            user("Meta thing", "2026-01-02T00:00:03Z", isMeta=True),
            user("Subagent prompt", "2026-01-02T00:00:04Z", isSidechain=True),
            user("This session is being continued from a previous conversation...", "2026-01-02T00:00:05Z",
                 isCompactSummary=True),
            {"type": "user", "timestamp": "2026-01-02T00:00:06Z", "message": {"content": [
                {"type": "tool_result", "content": "output"}]}},
            {"type": "user", "timestamp": "2026-01-02T00:00:07Z", "message": {"content": [
                {"type": "text", "text": "<system-reminder>x</system-reminder>"},
                {"type": "text", "text": "Second, with blocks."}]}},
            {"type": "queue-operation", "operation": "enqueue", "timestamp": "2026-01-02T00:00:08Z",
             "content": "Typed mid-turn."},
            {"type": "queue-operation", "operation": "remove", "timestamp": "2026-01-02T00:00:09Z",
             "content": "Typed mid-turn."},
            {"type": "queue-operation", "operation": "enqueue", "timestamp": "2026-01-02T00:00:10Z",
             "content": "Queued then delivered."},
            user("Queued then delivered.", "2026-01-02T00:00:11Z"),
        ])
        out = self.e.tool(root, "extract_human_messages.py", SID_A, "--list").stdout
        lines = [ln for ln in out.splitlines() if re.match(r"\s*\d+[ *] \d{4}-", ln)]
        texts = [ln[24:].strip() for ln in lines]
        self.assertEqual(texts, ["First real intent.", "Second, with blocks.", "Typed mid-turn.",
                                 "Queued then delivered."], out)
        self.e.tool(root, "extract_human_messages.py", SID_A, "--slug", "first", "--msg", "1", "3", sid=SID_A)
        self.assertEqual(self.main_files(root, "intent/log"), ["intent/log/I-0001-first.md"])
        body = (root / "intent/log/I-0001-first.md").read_text(encoding="utf-8")
        self.assertIn("First real intent.\n\n---\n\nTyped mid-turn.", body)
        self.assertIn(f"Session: {SID_A}", self.e.git(root, "log", "-1", "--format=%B").stdout)
        out = self.e.tool(root, "extract_human_messages.py", SID_A, "--list").stdout
        self.assertRegex(out, r"1\* .*First real intent")
        self.assertRegex(out, r"2  .*Second")
        self.assertIn("2 of 4", out)

    def test_worktrees_number_from_main(self):
        root = self.new_project()
        wa, wb = self.e.tmp / "wt-a", self.e.tmp / "wt-b"
        self.e.git(root, "worktree", "add", "-q", wa, "-b", "a")
        self.e.git(root, "worktree", "add", "-q", wb, "-b", "b")
        self.e.transcript(wa, SID_A, [user("Intent from A.", "2026-01-02T00:00:01Z")])
        self.e.transcript(wb, SID_B, [user("Intent from B.", "2026-01-02T00:00:02Z")])
        self.e.tool(wa, "extract_human_messages.py", SID_A, "--slug", "from-a", "--msg", "1", sid=SID_A)
        self.e.tool(wb, "extract_human_messages.py", SID_B, "--slug", "from-b", "--msg", "1", sid=SID_B)
        self.assertEqual(self.main_files(root, "intent/log"),
                         ["intent/log/I-0001-from-a.md", "intent/log/I-0002-from-b.md"])
        self.assertTrue((wa / "intent/log/I-0001-from-a.md").is_file())  # synced back into the thread
        self.assertTrue((root / "intent/log/I-0002-from-b.md").is_file())  # main checkout updated
        msg = self.e.git(root, "log", "-1", "--format=%B", "main").stdout
        self.assertIn(f"Session: {SID_B}", msg)
        # sweeping finds worktree sessions too
        self.e.tool(root, "capture_session.py", "--all")
        self.assertEqual(len(list((root / "record" / "sessions").glob("*.jsonl"))), 2)

        # current-view docs: A's edit goes to main; B's conflicting edit is refused
        v = "intent/vision.md"
        text = (wa / v).read_text(encoding="utf-8")
        (wa / v).write_text(text.replace("A test project.", "A test project, as A sees it."), encoding="utf-8")
        self.e.tool(wa, "to_main.py", "docs", "-m", "Vision from A", sid=SID_A)
        self.assertIn("as A sees it", self.e.git(root, "show", f"main:{v}").stdout)
        self.assertIn("as A sees it", (root / v).read_text(encoding="utf-8"))
        before = self.e.git(root, "rev-parse", "main").stdout
        (wb / v).write_text(text.replace("A test project.", "A test project, as B sees it."), encoding="utf-8")
        r = self.e.tool(wb, "to_main.py", "docs", "-m", "Vision from B", sid=SID_B, ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("conflicts", r.stderr + r.stdout)
        self.assertEqual(self.e.git(root, "rev-parse", "main").stdout, before)

        # a decision from a worktree
        draft = self.e.tmp / "d.md"
        draft.write_text("---\nid: {ID}\n---\n# Use X\n", encoding="utf-8")
        self.e.tool(wa, "to_main.py", "decision", "--slug", "use-x", "--file", draft)
        self.assertIn("plan/decisions/D-0001-use-x.md", self.main_files(root, "plan/decisions"))

        # code lands linearly
        (wa / "code.txt").write_text("code\n")
        self.e.git(wa, "add", "code.txt")
        self.e.git(wa, "commit", "-q", "-m", "code")
        self.e.tool(wa, "land.py")
        self.assertIn("code.txt", self.e.git(root, "ls-tree", "--name-only", "main").stdout)
        self.assertEqual(self.e.git(root, "rev-list", "--merges", "main").stdout.strip(), "")

    def test_main_not_checked_out(self):
        root = self.new_project("proj", "--layers", "experiments")
        self.e.git(root, "switch", "-q", "-c", "feat")
        (root / "wip.txt").write_text("wip")  # uncommitted work survives (autostash)
        self.e.transcript(root, SID_A, [user("Intent on a branch.", "2026-01-02T00:00:01Z")])
        self.e.tool(root, "extract_human_messages.py", SID_A, "--slug", "on-branch", "--msg", "1", sid=SID_A)
        self.assertEqual(self.main_files(root, "intent/log"), ["intent/log/I-0001-on-branch.md"])
        self.assertTrue((root / "intent/log/I-0001-on-branch.md").is_file())  # branch synced
        self.assertTrue((root / "wip.txt").is_file())
        self.assertIn(f"Session: {SID_A}", self.e.git(root, "log", "-1", "--format=%B", "main").stdout)
        draft = self.e.tmp / "e.md"
        draft.write_text("---\nid: {ID}\n---\n# Does it work?\n", encoding="utf-8")
        self.e.tool(root, "to_main.py", "experiment", "--slug", "does-it", "--file", draft)
        self.assertIn("experiments/E-0001-does-it/README.md", self.main_files(root, "experiments"))

    def test_merge_landing(self):
        root = self.new_project("proj", "--landing", "merge")
        self.e.git(root, "switch", "-q", "-c", "feat")
        (root / "a.txt").write_text("a\n")
        self.e.git(root, "add", "a.txt")
        self.e.git(root, "commit", "-q", "-m", "a")
        self.e.git(root, "switch", "-q", "main")
        (root / "b.txt").write_text("b\n")
        self.e.git(root, "add", "b.txt")
        self.e.git(root, "commit", "-q", "-m", "b")
        self.e.tool(root, "land.py", "feat")
        self.assertNotEqual(self.e.git(root, "rev-list", "--merges", "main").stdout.strip(), "")
        self.assertTrue((root / "a.txt").is_file())

    def test_adopt_existing(self):
        root = self.e.tmp / "old"
        root.mkdir()
        self.e.git(root, "init", "-q", "-b", "trunk")
        (root / "CLAUDE.md").write_text("# Old project\n\nKeep this.\n", encoding="utf-8")
        (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
        (root / ".claude").mkdir()
        (root / ".claude" / "settings.json").write_text(json.dumps(
            {"permissions": {"allow": ["Bash(ls)"]},
             "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo hi"}]}]}}), encoding="utf-8")
        (root / "tools").mkdir()
        (root / "tools" / "sync.py").write_text("# someone else's sync\n", encoding="utf-8")
        self.e.git(root, "add", "-A")
        self.e.git(root, "commit", "-q", "-m", "old")
        r = self.e.py(BOOTSTRAP, "init", root, "--name", "Old", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("tools/sync.py", r.stdout + r.stderr)
        self.assertEqual(self.e.git(root, "status", "--porcelain").stdout.strip(), "")  # nothing changed
        self.e.py(BOOTSTRAP, "init", root, "--name", "Old", "--tools-dir", "tools/kit", "--visibility", "publishable")
        claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertTrue(claude.startswith("# Old project\n\nKeep this."))
        self.assertTrue(claude.endswith("\n@METHOD-RULES.md\n"))
        rules = (root / "METHOD-RULES.md").read_text(encoding="utf-8")
        self.assertIn("python tools/kit/to_main.py docs", rules)
        self.assertIn("Publishable.", rules)
        s = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(s["permissions"], {"allow": ["Bash(ls)"]})
        self.assertEqual(len(s["hooks"]["Stop"]), 2)
        self.assertIn("node_modules/", (root / ".gitignore").read_text(encoding="utf-8"))
        self.assertEqual(json.loads((root / "intent-kit.json").read_text())["main_branch"], "trunk")
        self.e.git(root, "add", "-A")
        self.e.git(root, "commit", "-q", "-m", "adopt intent-kit")
        self.e.py(root / "tools/kit/kit.py", "check", cwd=root)
        self.e.transcript(root, SID_A, [user("Old project's new intent.", "2026-01-02T00:00:01Z")])
        self.e.py(root / "tools/kit/extract_human_messages.py", SID_A, "--slug", "first", "--msg", "1", cwd=root)
        self.assertEqual(self.e.git(root, "ls-tree", "-r", "--name-only", "trunk", "--", "intent/log").stdout.split(),
                         ["intent/log/I-0001-first.md"])

    def test_record_safety(self):
        root = self.new_project()
        gi = root / ".gitignore"
        gi.write_text(gi.read_text().replace("/record/\n", ""), encoding="utf-8")
        r = self.e.tool(root, "kit.py", "check", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("record/ is not ignored", r.stdout)
        t = self.e.transcript(root, SID_A, [user("hello", "2026-01-02T00:00:00Z")])
        r = self.e.tool(root, "capture_session.py", input=json.dumps(
            {"hook_event_name": "SessionStart", "session_id": SID_A, "transcript_path": str(t)}))
        self.assertIn("NOT being recorded", r.stdout)
        self.assertEqual(list((root / "record" / "sessions").glob("*.jsonl")), [])

    def test_upgrade(self):
        root = self.new_project()
        (root / "tools" / "sync.py").write_text("# drifted\n", encoding="utf-8")
        cfg = json.loads((root / "intent-kit.json").read_text())
        cfg["layers"] = ["concepts"]
        (root / "intent-kit.json").write_text(json.dumps(cfg), encoding="utf-8")
        r = self.e.py(BOOTSTRAP, "upgrade", root)
        self.assertIn("tools/sync.py", r.stdout)
        self.assertIn("concepts/README.md", r.stdout)
        self.assertEqual((root / "tools" / "sync.py").read_text(), "# drifted\n")
        self.e.py(BOOTSTRAP, "upgrade", root, "--apply")
        self.assertEqual((root / "tools" / "sync.py").read_bytes(),
                         (KIT / "template/managed/tools/sync.py").read_bytes())
        self.assertTrue((root / "concepts" / "README.md").is_file())
        self.assertIn("C-0001", (root / "METHOD-RULES.md").read_text(encoding="utf-8"))
        self.assertIn("up to date", self.e.py(BOOTSTRAP, "upgrade", root).stdout)

    def test_upgrade_moves_inlined_rules_out(self):
        root = self.new_project()
        old = ("# Proj\n\nOwn rules.\n\n<!-- intent-kit:begin -->\n## How this project keeps its record\n"
               "old generated text\n<!-- intent-kit:end -->\n\n## Later section\n\nKeep me too.\n")
        (root / "CLAUDE.md").write_text(old, encoding="utf-8")
        self.e.tool(root, "kit.py", "render")
        claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertNotIn("intent-kit:begin", claude)
        self.assertNotIn("old generated text", claude)
        self.assertIn("Own rules.", claude)
        self.assertIn("Keep me too.", claude)
        self.assertEqual(claude.count("@METHOD-RULES.md"), 1)
        self.e.tool(root, "kit.py", "render")  # idempotent
        self.assertEqual((root / "CLAUDE.md").read_text(encoding="utf-8"), claude)

    def test_onboarding_answers_are_cited_not_captured(self):
        root = self.new_project()
        self.e.transcript(root, SID_A, [
            user("Keep it confidential.", "2026-01-02T00:00:01Z"),
            user("It's a tool for sorting seeds.", "2026-01-02T00:00:02Z"),
        ])
        self.e.tool(root, "kit.py", "cite", SID_A, "--msg", "1", "--keys", "visibility")
        src = json.loads((root / "intent-kit.json").read_text())["sources"]
        self.assertEqual(src, {"visibility": [{"session": SID_A, "message": "2026-01-02T00:00:01Z"}]})
        self.e.tool(root, "to_main.py", "docs", "-m", "Cite onboarding")
        self.e.tool(root, "extract_human_messages.py", SID_A, "--slug", "what-it-is", "--msg", "2")
        out = self.e.tool(root, "extract_human_messages.py", SID_A, "--list").stdout
        self.assertRegex(out, r"1c .*confidential")
        self.assertRegex(out, r"2\* .*sorting seeds")
        self.assertEqual(self.main_files(root, "intent/log"), ["intent/log/I-0001-what-it-is.md"])
        r = self.e.tool(root, "kit.py", "cite", SID_A, "--msg", "1", "--keys", "nonsense", ok=False)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
