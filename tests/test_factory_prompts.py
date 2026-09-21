"""Tests for the prompt catalog."""

from __future__ import annotations

import pytest

from factory import prompts


def test_all_prompts_counts_and_suffix():
    plist = prompts.all_prompts()
    assert len(plist) == sum(len(v) for v in prompts.CATEGORIES.values())
    assert all(p.text.endswith(prompts.STYLE_SUFFIX) for p in plist)


def test_subset_and_per_category():
    plist = prompts.all_prompts(["soap-cutting", "slime"], per_category=2)
    assert [p.category for p in plist] == ["soap-cutting"] * 2 + ["slime"] * 2


def test_unknown_category():
    with pytest.raises(ValueError, match="Unknown categories: nope"):
        prompts.all_prompts(["nope"])
