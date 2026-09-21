"""Every factory module must be importable first, in any order (no import cycles)."""

from __future__ import annotations

import importlib
import subprocess
import sys

import pytest

MODULES = [
    "assemble", "bank", "captions", "cli", "music", "procedural", "prompts", "timeline", "tts",
]


@pytest.mark.parametrize("first", MODULES)
def test_module_imports_cleanly_first(first):
    code = f"import factory.{first}; " + "; ".join(f"import factory.{m}" for m in MODULES)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_reimport_in_process():
    for m in MODULES:
        importlib.import_module(f"factory.{m}")
