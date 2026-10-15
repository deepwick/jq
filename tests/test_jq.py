import json
import re
import subprocess
from pathlib import Path

import pytest

from deepwick_spec.ansi import runs, style_of
from deepwick_spec.check_port import check_port
from deepwick_spec.palette import load_palette

REPO = Path(__file__).resolve().parents[1]
PALETTE = load_palette()
C = PALETTE.colors
JQ = Path("/usr/bin/jq")
FIELDS = ("blue", "blue", "blue", "sage", "orange", "foreground", "foreground", "lightBlue")
SAMPLE = {"name": "deepwick", "count": 3, "ok": True, "off": False, "none": None, "tags": ["a"]}


def sgr(name):
    r, g, b = (int(C[name][i : i + 2], 16) for i in (1, 3, 5))
    return f"38;2;{r};{g};{b}"


def style_containing(text, needle):
    for chunk, style in runs(text):
        if needle in chunk:
            return style
    raise AssertionError(f"no run contains {needle!r}")


def value(path):
    assert path.is_file(), f"{path.name} missing"
    return re.search(r'JQ_COLORS[= ]"([^"]*)"', path.read_text(encoding="utf-8")).group(1)


def test_sh_sets_all_eight_fields():
    fields = value(REPO / "deepwick.sh").split(":")
    assert len(fields) == 8
    assert all(fields), "an empty field means no color in jq"
    assert fields == [sgr(name) for name in FIELDS]


def test_fish_matches_sh():
    assert value(REPO / "deepwick.fish") == value(REPO / "deepwick.sh")


@pytest.mark.skipif(not JQ.is_file(), reason="requires /usr/bin/jq")
def test_jq_renders_roles():
    env = {"PATH": "/usr/bin:/bin", "JQ_COLORS": value(REPO / "deepwick.sh")}
    result = subprocess.run([str(JQ), "-C", "."], input=json.dumps(SAMPLE), env=env, capture_output=True, text=True, check=True)
    assert "Failed to set" not in result.stderr
    out = result.stdout
    assert style_of(out, '"deepwick"')["fg"] == C["orange"].lower()
    assert style_of(out, '"name"')["fg"] == C["lightBlue"].lower()
    assert style_of(out, "3")["fg"] == C["sage"].lower()
    for literal in ("true", "false", "null"):
        assert style_of(out, literal)["fg"] == C["blue"].lower(), literal
    assert style_containing(out, "{")["fg"] == C["foreground"].lower()
    assert not style_containing(out, "{")["bold"]


def test_port_conventions():
    assert check_port(REPO, PALETTE.allowed_hex()) == []
