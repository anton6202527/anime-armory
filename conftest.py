"""Pytest collection helpers for the flat skills/ tree.

Many skill tests import helper scripts from their own directory with statements
like `import mechanical_check`. Several skills intentionally reuse the same
script/test filenames, so pytest's default import mode collides. The repository
uses `--import-mode=importlib`; this hook restores "test-local script imports"
without requiring every skill directory to become a Python package.
"""
import sys


def pytest_collect_file(file_path, parent):  # noqa: ARG001 - pytest hook API
    if file_path.suffix != ".py" or not file_path.name.startswith("test_"):
        return None

    test_dir = str(file_path.parent)
    if test_dir in sys.path:
        sys.path.remove(test_dir)
    sys.path.insert(0, test_dir)

    # If another skill already imported a same-named local script, clear it so
    # this test imports the sibling script in its own directory.
    for sibling in file_path.parent.glob("*.py"):
        if sibling.name == file_path.name or sibling.name == "__init__.py":
            continue
        sys.modules.pop(sibling.stem, None)

    return None
