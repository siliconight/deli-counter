#!/usr/bin/env python3
"""
install_hooks.py  --  install the Deli Counter git hooks
=========================================================
Copies hooks/pre-commit into .git/hooks/ and makes it executable, so the
catalog auto-refreshes and the validation gate runs before every commit.

    python install_hooks.py

Works on Windows, macOS, and Linux. Git on Windows runs the bash hook via the
bundled Git Bash, so the same script works everywhere. Re-run any time to
update the installed hook.
"""

import os
import shutil
import stat
import subprocess
import sys


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "hooks", "pre-commit")
    if not os.path.exists(src):
        print(f"error: {src} not found")
        return 1

    # locate the .git directory (handles worktrees / submodules too)
    try:
        git_dir = subprocess.check_output(
            ["git", "rev-parse", "--git-dir"], cwd=here, text=True).strip()
    except Exception as e:
        print(f"error: not a git repo (or git not found): {e}")
        return 1
    if not os.path.isabs(git_dir):
        git_dir = os.path.join(here, git_dir)

    hooks_dir = os.path.join(git_dir, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    dst = os.path.join(hooks_dir, "pre-commit")

    shutil.copyfile(src, dst)
    # make it executable (no-op effect on Windows, but harmless)
    st = os.stat(dst)
    os.chmod(dst, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    print(f"installed pre-commit hook -> {dst}")
    print("from now on, commits auto-refresh CATALOG.md and run the gate.")
    print("(bypass once with: git commit --no-verify)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
