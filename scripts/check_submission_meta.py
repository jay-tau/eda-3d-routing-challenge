#!/usr/bin/env python3
"""Check that submission directories carry the required runtime metadata.

Every submission must report how long it took: `runtime.json` maps each case of
the tier to the wall-clock seconds of the one run that produced that case's
route file, and `meta.json` names the `hardware` it ran on and the `threads` it
used. CI runs this on the submission directories a PR adds or changes.

Usage: python scripts/check_submission_meta.py submissions/<tier>/<name> [...]
"""
import json
import math
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from m3d.cli import _tier_dir_map, _load_manifest  # noqa: E402


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def problems(sub_dir: str):
    """List what is missing or malformed for one submission directory."""
    tier = os.path.basename(os.path.dirname(os.path.normpath(sub_dir)))
    suite_dir = _tier_dir_map().get(tier)
    if not suite_dir:
        return [f"unknown tier {tier!r}"]
    if not os.path.isabs(suite_dir):
        suite_dir = os.path.join(REPO_ROOT, suite_dir)
    cases = [c["name"] for c in _load_manifest(suite_dir)["cases"]]
    out = []
    rt_path = os.path.join(sub_dir, "runtime.json")
    try:
        rt = _load(rt_path)
    except FileNotFoundError:
        rt = None
        out.append("runtime.json is missing (wall-clock seconds of one run per case)")
    except ValueError as exc:
        rt = None
        out.append(f"runtime.json is not valid JSON ({exc})")
    if rt is not None:
        if not isinstance(rt, dict):
            out.append("runtime.json must be an object {\"<case>\": seconds}")
        else:
            bad = [c for c in cases
                   if not (isinstance(rt.get(c), (int, float)) and not isinstance(rt.get(c), bool)
                           and math.isfinite(rt[c]) and rt[c] >= 0)]
            if bad:
                out.append(f"runtime.json needs a non-negative number of seconds for "
                           f"every case; missing or invalid: {', '.join(bad)}")
    try:
        meta = _load(os.path.join(sub_dir, "meta.json"))
    except (OSError, ValueError):
        meta = None
        out.append("meta.json is missing or not valid JSON")
    if meta is not None:
        if not isinstance(meta, dict):
            out.append("meta.json must be an object")
        else:
            if not (isinstance(meta.get("hardware"), str) and meta["hardware"].strip()):
                out.append('meta.json needs "hardware" (e.g. "AMD Ryzen 9 7950X, 64 GB" '
                           'or "1x RTX 4090 + i7-13700K")')
            th = meta.get("threads")
            if not (type(th) is int and th > 0):
                out.append('meta.json needs "threads": the number of CPU threads the '
                           'timed run used (a positive integer)')
    return out


def main(dirs) -> int:
    failed = False
    for d in dirs:
        for p in problems(d):
            print(f"{d}: {p}")
            failed = True
    if failed:
        print("\nSee CONTRIBUTING.md, 'Runtime'.")
        return 1
    print(f"runtime metadata ok for {len(dirs)} submission dir(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
