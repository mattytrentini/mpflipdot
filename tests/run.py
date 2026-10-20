"""Run from the repository root: micropython tests/run.py."""

import sys

sys.path.insert(0, ".")
sys.path.insert(0, "tests")

count = 0
for module_name in ("test_mpflipdot", "test_draw", "test_text"):
    module = __import__(module_name)
    for name in sorted(dir(module)):
        if name.startswith("test_"):
            getattr(module, name)()
            print("PASS", module_name + "." + name)
            count += 1
print("%d tests passed (native framebuf)" % count)
