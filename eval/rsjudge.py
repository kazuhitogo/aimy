"""Run a Rust solution against hidden tests; print JSON lines like `aimy test`.

usage: python eval/rsjudge.py sol.rs tests.rs
Builds sol.rs + tests.rs with `rustc --test`, overflow checks on (aimy also checks).
Compile errors are lines with severity "error" (rustc's own rendered text included);
each test yields {"test", "status", ...}; a final {"summary": {"passed", "failed"}} line follows.
"""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile

RUSTC = shutil.which("rustc") or os.path.expanduser("~/.cargo/bin/rustc")
sol, tests = (pathlib.Path(p).read_text() for p in sys.argv[1:3])
tmp = pathlib.Path(tempfile.mkdtemp())
src = tmp / "sol.rs"
src.write_text(sol + "\n" + tests)
exe = tmp / "t"
r = subprocess.run([RUSTC, "--edition", "2021", "--test", "-C", "overflow-checks=on", "-C", "opt-level=1",
                    "--error-format=json", "-o", str(exe), str(src)], capture_output=True, text=True)
errors = []
for l in r.stderr.splitlines():
    try:
        d = json.loads(l)
    except ValueError:
        continue
    if d.get("level") == "error" and d.get("spans"):
        errors.append({"code": (d.get("code") or {}).get("code") or "error", "msg": d["message"],
                       "line": d["spans"][0]["line_start"], "severity": "error", "rendered": d.get("rendered")})
if r.returncode != 0:
    for e in errors or [{"code": "error", "msg": r.stderr[-800:], "severity": "error"}]:
        print(json.dumps(e))
    sys.exit(1)
lines = src.read_text().splitlines()
t = subprocess.run([str(exe), "--test-threads=1"], capture_output=True, text=True, timeout=60)
out = t.stdout + t.stderr
fails = dict(re.findall(r"---- (\S+) stdout ----\n(.*?)(?=\n---- |\n\nfailures:|\Z)", out, re.S))
passed = failed = 0
for name, status in re.findall(r"^test (\S+) \.\.\. (ok|FAILED)", out, re.M):
    if status == "ok":
        passed += 1
        print(json.dumps({"test": name, "status": "pass"}))
        continue
    failed += 1
    msg = fails.get(name, "").strip()
    m = re.search(r"panicked at .*?sol\.rs:(\d+):", msg)
    print(json.dumps({"test": name, "status": "fail", "msg": msg[-600:],
                      "src": lines[int(m.group(1)) - 1].strip() if m else None}))
print(json.dumps({"summary": {"passed": passed, "failed": failed}}))
sys.exit(1 if failed or not passed else 0)
