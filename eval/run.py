#!/usr/bin/env python3
"""Evaluation harness.

usage: uv run python eval/run.py [--lang aimy|py|rs] [--ref] [--rounds N] [--tasks a,b|@hard.txt] [--out FILE]

Default: for each task, send SPEC.md + task.md to the model command, compile, run the
hidden reference tests, feed errors back, up to N fix rounds. The model command is
$AIMY_EVAL_CMD (default: `kiro-cli chat --no-interactive --trust-tools= {prompt}`). The command takes
the prompt in place of a `{prompt}` argument, or on stdin if there is none, and prints code.
--ref: run the solutions in eval/refs.txt (refs-py.txt, refs-rs.txt) instead of a model.
--lang py / rs: the Python / Rust baseline. Same tasks (task.py.md + tests.py, task.rs.md + tests.rs),
no SPEC in the prompt, judged by eval/pyjudge.py / eval/rsjudge.py. For Python "compiled" means the module loads.
"""
import argparse, json, os, pathlib, re, shlex, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
AIMY = [sys.executable, "-m", "aimy.cli"]
ENV = {**os.environ, "PYTHONPATH": str(REPO / "src")}


def aimy(*args):
    return subprocess.run(AIMY + list(args), capture_output=True, text=True, env=ENV, timeout=120)


def extract(text):
    m = re.findall(r"```(?:aimy|aim|python|py|rust|rs)?\n(.*?)```", text, re.S)
    if not m:
        sys.exit("model command returned no code block:\n" + text[:300])
    return max(m, key=len).strip() + "\n"


LANGS = {  # task file, test file, refs file, code fence
    "aimy": ("task.md", "tests.aim", "refs.txt", "aimy"),
    "py": ("task.py.md", "tests.py", "refs-py.txt", "python"),
    "rs": ("task.rs.md", "tests.rs", "refs-rs.txt", "rust"),
}
JUDGES = {"py": ("pyjudge.py", "sol.py", "tests.py"), "rs": ("rsjudge.py", "sol.rs", "tests.rs")}


def judge(code, tests, tmp, lang="aimy"):
    try:
        if lang in JUDGES:
            script, sf, tf = JUDGES[lang]
            (tmp / sf).write_text(code)
            (tmp / tf).write_text(tests)
            r = subprocess.run([sys.executable, str(ROOT / script), str(tmp / sf), str(tmp / tf)],
                               capture_output=True, text=True, timeout=120)
        else:
            f = tmp / "sol.aim"
            f.write_text(code + "\n" + tests)
            r = aimy("test", str(f))
    except subprocess.TimeoutExpired:
        return False, True, json.dumps({"kind": "timeout", "status": "fail", "msg": "tests did not finish in time"})
    out = (r.stdout + r.stderr).strip()
    lines = []
    for l in out.splitlines():
        if l.startswith("{"):
            try:
                lines.append(json.loads(l))
            except ValueError:
                pass
    summ = next((l["summary"] for l in lines if "summary" in l), None)
    ok = bool(summ) and summ["failed"] == 0 and summ["passed"] > 0 and r.returncode == 0
    compiled = not any(l.get("severity") == "error" for l in lines)
    return ok, compiled, out


def ask(cmd, prompt):
    if "{prompt}" in cmd:  # prompt as an argument instead of stdin
        cmd, prompt = [prompt if c == "{prompt}" else c for c in cmd], None
    return subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=600).stdout


def load_refs(fname):
    refs, cur = {}, None
    for line in (ROOT / fname).read_text().splitlines(True):
        if line.startswith("### "):
            cur = line[4:].strip()
            refs[cur] = ""
        elif cur:
            refs[cur] += line
    return refs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", action="store_true")
    ap.add_argument("--lang", choices=sorted(LANGS), default="aimy")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--tasks")
    ap.add_argument("--out", default=str(ROOT / "results.jsonl"))
    a = ap.parse_args()
    cmd = shlex.split(os.environ.get("AIMY_EVAL_CMD", "kiro-cli chat --no-interactive --trust-tools= {prompt}"))
    task_f, tests_f, refs_f, fence = LANGS[a.lang]
    spec = (REPO / "SPEC.md").read_text() if a.lang == "aimy" else ""
    refs = load_refs(refs_f) if a.ref else {}
    if a.tasks and a.tasks.startswith("@"):  # @hard.txt: one task name per line
        a.tasks = ",".join((ROOT / a.tasks[1:]).read_text().split())
    names = a.tasks.split(",") if a.tasks else sorted(p.name for p in (ROOT / "tasks").iterdir())
    rows = []
    for name in names:
        d = ROOT / "tasks" / name
        task, tests = (d / task_f).read_text(), (d / tests_f).read_text()
        tmp = pathlib.Path(tempfile.mkdtemp())
        row = dict(task=name, first_compile=None, first_pass=None, rounds=None, passed=False, chars_out=0)
        if a.ref:
            ok, comp, out = judge(refs.get(name) or refs[name.removesuffix("_terse")], tests, tmp, a.lang)
            row.update(first_compile=comp, first_pass=ok, rounds=0, passed=ok)
            if not ok:
                row["log"] = out[-800:]
        else:
            head = (f"{spec}\n\n---\n" if spec else "") + f"Task. Reply with only one ```{fence} code block, no tests.\n\n{task}"
            prompt = head
            for rnd in range(a.rounds + 1):
                code = extract(ask(cmd, prompt))
                row["chars_out"] += len(code)
                ok, comp, out = judge(code, tests, tmp, a.lang)
                if rnd == 0:
                    row.update(first_compile=comp, first_pass=ok)
                    if not ok:  # why the first attempt failed: diagnostic codes or failing test lines
                        row["first_fail"] = [l.get("code") or l.get("src") or l.get("kind")
                                             for l in map(json.loads, (x for x in out.splitlines() if x.startswith("{")))
                                             if l.get("severity") == "error" or l.get("status") == "fail"][:5]
                if ok:
                    row.update(passed=True, rounds=rnd)
                    break
                prompt = (f"{head}\n\nYour previous attempt:\n```{fence}\n{code}```\n\n"
                          f"Compiler/test output (JSON lines):\n{out[-1500:]}\n\nFix it.")
            else:
                row["rounds"] = a.rounds
                row["log"] = out[-800:]
        rows.append(row)
        print(json.dumps(row), flush=True)
    n = len(rows)
    s = dict(tasks=n, first_compile=sum(bool(r["first_compile"]) for r in rows),
             first_pass=sum(bool(r["first_pass"]) for r in rows),
             passed=sum(r["passed"] for r in rows),
             avg_rounds=round(sum(r["rounds"] or 0 for r in rows) / n, 2),
             chars_out=sum(r["chars_out"] for r in rows))
    print(json.dumps({"summary": s}))
    pathlib.Path(a.out).write_text("\n".join(json.dumps(r) for r in rows + [{"summary": s}]) + "\n")


main()
