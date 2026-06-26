"""
Idempotent post-install patcher for PyJHora.

The PyPI build of PyJHora (4.8.7) does not run cleanly under Python 3.14 + the
pyswisseph 2.10.x C extension. Three fixes are required, and because they live
inside the installed package under site-packages they are wiped every time the
virtual environment is rebuilt or `pip install` re-runs. setup.sh calls this
script after installing dependencies so the environment is always reproducible.

Fixes applied (each detected before writing, so re-running is a no-op):

  1. jhora/utils.py  -- swe.fixstar_ut(..., flag = ...)  -> positional
  2. jhora/utils.py  -- swe.utc_to_jd(...,  flag = ...)  -> positional
       The compiled pyswisseph for 3.14 rejects the `flag=` keyword and crashes
       immediately on these calls.
  3. jhora/panchanga/drik.py -- inside planetary_positions(): planet_list is a
       dict, so planet_list.index(planet) raises AttributeError. Replace with the
       dict key lookup planet_list[planet]. (A separate .index() call in another
       function operates on a list and is intentionally left untouched.)

Run:  ./.venv/bin/python patch_pyjhora.py
"""
from __future__ import annotations

import os
import re
import sys


def _pkg_dir():
    import jhora
    return os.path.dirname(jhora.__file__)


def patch_swe_keyword(text: str) -> tuple[str, int]:
    """Drop the `flag = ` keyword from swe.fixstar_ut / swe.utc_to_jd calls on
    non-comment lines so they pass the flag positionally."""
    changes = 0
    out_lines = []
    pat = re.compile(r'(swe\.(?:fixstar_ut|utc_to_jd)\([^\n]*?),\s*flag\s*=\s*')
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            out_lines.append(line)
            continue
        new = pat.sub(r"\1, ", line)
        if new != line:
            changes += 1
        out_lines.append(new)
    return "".join(out_lines), changes


def patch_planetary_positions(text: str) -> tuple[str, int]:
    """Within planetary_positions(), swap planet_list.index(planet) for the dict
    lookup planet_list[planet]. Scoped to that one function only."""
    m = re.search(r"\ndef planetary_positions\(", text)
    if not m:
        return text, 0
    start = m.start()
    nxt = re.search(r"\ndef ", text[start + 1:])
    end = start + 1 + nxt.start() if nxt else len(text)
    body = text[start:end]
    new_body, n = re.subn(r"planet_list\.index\(planet\)", "planet_list[planet]", body)
    if n:
        text = text[:start] + new_body + text[end:]
    return text, n


def apply(path: str, fn) -> int:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    new_text, n = fn(text)
    if n and new_text != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
    return n


def main() -> int:
    try:
        pkg = _pkg_dir()
    except Exception as e:
        print(f"! Could not locate the jhora package: {e}")
        return 1

    utils_py = os.path.join(pkg, "utils.py")
    drik_py = os.path.join(pkg, "panchanga", "drik.py")

    total = 0
    total += apply(utils_py, patch_swe_keyword)
    total += apply(drik_py, patch_planetary_positions)

    if total:
        print(f"✓ PyJHora patched ({total} site(s) updated) at {pkg}")
    else:
        print(f"✓ PyJHora already patched — nothing to do ({pkg})")

    # Smoke-test the patched engine end to end.
    try:
        from jhora import utils, const
        from jhora.panchanga import drik
        from jhora.panchanga.drik import Date, Place
        const._INCLUDE_URANUS_TO_PLUTO = False
        drik.set_ayanamsa_mode("LAHIRI")
        jd = utils.julian_day_number((2026, 6, 20), (12, 0, 0))
        place = Place("loc", 53.5236, -7.3437, 1.0)
        pos = drik.planetary_positions(jd, place)
        drik.raahu_kaalam(jd, place)
        assert len(pos) >= 9
        print(f"✓ Smoke test passed: {len(pos)} planetary positions + Rahu-Kalam computed.")
    except Exception as e:
        print(f"! Smoke test failed (non-fatal): {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
