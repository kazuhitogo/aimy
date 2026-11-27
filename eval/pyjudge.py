"""Run a Python solution against hidden tests; print JSON lines like `aimy test`.

usage: python eval/pyjudge.py sol.py tests.py
A solution that fails to compile or to run at import is reported as an error with
severity "error" (the counterpart of an aimy compile error). Each test_* function then
yields {"test", "status", ...}; a final {"summary": {"passed", "failed"}} line follows.
"""
import json, sys, traceback

sol, tests = (open(p).read() for p in sys.argv[1:3])
ns: dict = {"__name__": "sol"}
try:
    exec(compile(sol, "sol.py", "exec"), ns)
except BaseException as e:
    line = getattr(e, "lineno", None)
    if line is None:
        tb = [f for f in traceback.extract_tb(e.__traceback__) if f.filename == "sol.py"]
        line = tb[-1].lineno if tb else None
    print(json.dumps({"code": type(e).__name__, "msg": str(e), "line": line, "severity": "error"}))
    sys.exit(1)
exec(compile(tests, "tests.py", "exec"), ns)
passed = failed = 0
for name in [n for n in ns if n.startswith("test_")]:
    try:
        ns[name]()
        passed += 1
        print(json.dumps({"test": name, "status": "pass"}))
    except BaseException as e:
        failed += 1
        tb = traceback.extract_tb(e.__traceback__)
        ln = next((f.lineno for f in reversed(tb) if f.filename == "tests.py"), None)
        src = tests.splitlines()[ln - 1].strip() if ln else None
        row = {"test": name, "status": "fail", "kind": type(e).__name__, "msg": str(e), "src": src}
        if isinstance(e, AssertionError) and src and src.startswith("assert ") and " == " in src:
            try:  # show the actual value, as aimy does for a failed '=='
                tb_, frame = e.__traceback__, None
                while tb_:  # the test's own frame, so its local variables resolve
                    if tb_.tb_frame.f_code.co_filename == "tests.py":
                        frame = tb_.tb_frame
                    tb_ = tb_.tb_next
                row["got"] = repr(eval(src[7:].split(" == ")[0], ns, frame.f_locals if frame else {}))
            except BaseException as e2:
                row["got"] = f"{type(e2).__name__}: {e2}"
        else:
            row["trace"] = [l for l in traceback.format_exception(e) if "pyjudge.py" not in l][-4:]
        print(json.dumps(row))
print(json.dumps({"summary": {"passed": passed, "failed": failed}}))
sys.exit(1 if failed else 0)
