"""Regression tests for the self-reference allowlist in scan.py.

Background: PR #42 added ``is_self_reference_file`` so that canonical
dictionary files (``.claude/rules/advocacy-domain.md`` and
``.claude/rules/speciesist-language.md``) are not flagged when they mention
the prohibited phrases as examples. These files define the very phrases the
scanner enforces, so flagging them is a self-reference false positive.

These tests pin four behaviours that the adversarial review specified:

1. skip-by-path      - a dictionary file addressed by direct path is skipped
2. skip-via-walk     - the same file is skipped when discovered via os.walk
3. real-violations   - the same phrases in a normal file ARE still flagged
4. path-anchor       - a same-named file outside .claude/rules/ is still flagged

The tests import scan.py as a module and call its real entry points
(``iter_files`` + ``scan_file``) and also drive ``main()`` as a subprocess to
assert on exit behaviour end-to-end. They use the scanner's own RULES list,
so any rule change tracks automatically.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

# Make the repo root importable when pytest runs from anywhere (e.g. CI that
# cds into tests/). scan.py lives at the repo root, one level above tests/.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import scan  # noqa: E402  (path set up above)

# Phrases that the scanner must flag in a normal file. All of these are
# defined verbatim in scan.RULES, and also appear in the canonical dictionary
# file .claude/rules/advocacy-domain.md - which is precisely why that file
# must be allowlisted.
VIOLATIONS_BODY = """\
# Notes

We can kill two birds with one stone here.
No need to beat a dead horse about it.
There's more than one way to skin a cat.
"""

# A path that the allowlist must recognise under any parent directory.
ALLOWLISTED_REL = ".claude/rules/advocacy-domain.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scan_paths_for(scan_paths):
    """Run iter_files + scan_file over scan_paths and return the list of
    (path, findings) tuples with non-zero findings only."""
    ignore_patterns = []  # no .wokeignore in these fixtures
    flagged = []
    for file_path in scan.iter_files(scan_paths, ignore_patterns):
        findings = scan.scan_file(file_path, scan.RULES)
        if findings:
            flagged.append((file_path, findings))
    return flagged


def _run_scan_subprocess(input_paths, cwd):
    """Invoke scan.py as a subprocess the way action.yml does and return
    (returncode, stdout). INPUT_SEVERITY=error so only error-severity phrases
    move the exit code to 1 - matching the production CI invocation."""
    env = dict(os.environ)
    env["INPUT_PATHS"] = input_paths
    env["INPUT_SEVERITY"] = "error"
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scan.py")],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fixture_tree(tmp_path):
    """Build a tree with:
      - allowlisted dictionary file containing violations (under .claude/rules/)
      - a normal notes.md with the same violations
      - a root-level same-named file NOT under .claude/rules/
    Returns the tmp_path root.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "advocacy-domain.md").write_text(VIOLATIONS_BODY, encoding="utf-8")

    (tmp_path / "notes.md").write_text(VIOLATIONS_BODY, encoding="utf-8")

    # Root-level file with the SAME basename but NOT under .claude/rules/.
    # This must still be flagged - proves the regex is path-anchored.
    (tmp_path / "advocacy-domain.md").write_text(VIOLATIONS_BODY, encoding="utf-8")

    return tmp_path


# ---------------------------------------------------------------------------
# Test 1: skip-by-path (direct path arg)
# ---------------------------------------------------------------------------

def test_skip_by_direct_path(fixture_tree):
    """A dictionary file addressed by its direct path is NOT flagged."""
    dict_file = fixture_tree / ALLOWLISTED_REL
    flagged = _scan_paths_for([str(dict_file)])

    assert dict_file.is_file(), "fixture setup: dictionary file must exist"
    assert flagged == [], (
        f"allowlisted dictionary file was flagged as a real violation: {flagged}"
    )


# ---------------------------------------------------------------------------
# Test 2: skip-via-walk (discovered through os.walk)
# ---------------------------------------------------------------------------

def test_skip_via_directory_walk(fixture_tree):
    """The dictionary file is skipped when the whole tree is walked (not just
    passed as a direct path). This exercises the os.walk branch of iter_files,
    which is the branch that fires in production (INPUT_PATHS=. )."""
    flagged = _scan_paths_for([str(fixture_tree)])
    flagged_paths = {str(p) for p, _ in flagged}

    dict_file = str(fixture_tree / ALLOWLISTED_REL)
    assert dict_file not in flagged_paths, (
        f"dictionary file was flagged during full tree walk: {dict_file} in {flagged_paths}"
    )


# ---------------------------------------------------------------------------
# Test 3: real violations still flagged (allowlist is not over-hiding)
# ---------------------------------------------------------------------------

def test_real_violations_still_flagged(fixture_tree):
    """The same prohibited phrases in a normal file (notes.md) ARE flagged.
    This proves the allowlist hides only the dictionary files, not the rules
    themselves."""
    flagged = _scan_paths_for([str(fixture_tree)])
    flagged_paths = {str(p) for p, _ in flagged}

    notes = str(fixture_tree / "notes.md")
    assert notes in flagged_paths, (
        f"notes.md with real violations was NOT flagged; allowlist is over-hiding. "
        f"flagged={flagged_paths}"
    )

    # Coherence check: at least one finding per phrase (3 distinct error/warning/info
    # phrases). We don't pin the exact count so rule additions don't break it,
    # but there must be multiple findings - a single match would suggest
    # scanning stopped early.
    notes_findings = next(f for p, f in flagged if str(p) == notes)
    assert len(notes_findings) >= 3, (
        f"expected >=3 findings in notes.md, got {len(notes_findings)}: {notes_findings}"
    )


def test_real_violations_exit_nonzero(fixture_tree):
    """End-to-end: invoking scan.py as a subprocess on a tree with real
    violations exits 1 (matches the production CI invocation)."""
    rc, stdout = _run_scan_subprocess(str(fixture_tree), cwd=fixture_tree)
    assert rc == 1, (
        f"scan.py should exit 1 on real violations; got rc={rc}. stdout:\n{stdout}"
    )


# ---------------------------------------------------------------------------
# Test 4: path-anchor boundary
# ---------------------------------------------------------------------------

def test_path_anchor_root_level_same_name_flagged(fixture_tree):
    """A root-level advocacy-domain.md (NOT under .claude/rules/) with the
    same violations IS still flagged. This proves SKIP_FILES_PATTERNS is
    path-anchored, not matching any same-named file anywhere."""
    flagged = _scan_paths_for([str(fixture_tree)])
    flagged_paths = {str(p) for p, _ in flagged}

    root_same_name = str(fixture_tree / "advocacy-domain.md")
    assert root_same_name in flagged_paths, (
        f"root-level same-named file was NOT flagged; the allowlist regex is "
        f"matching by basename instead of by anchored path. flagged={flagged_paths}"
    )


def test_path_anchor_isolated_root_file(tmp_path):
    """Stronger form of test 4: even when the dictionary file is the ONLY file
    present and sits at the root (so no .claude/rules/ sibling can confuse
    the matcher), it is still flagged. Pinned by direct path and by walk."""
    root_file = tmp_path / "advocacy-domain.md"
    root_file.write_text(VIOLATIONS_BODY, encoding="utf-8")

    flagged = _scan_paths_for([str(tmp_path)])
    flagged_paths = {str(p) for p, _ in flagged}
    assert str(root_file) in flagged_paths, (
        f"isolated root-level file should be flagged; flagged={flagged_paths}"
    )
