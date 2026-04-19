"""Branch coverage for tests.arize_compat."""

import importlib.util
from unittest.mock import MagicMock

from tests.arize_compat import arize_client_patch_target


def test_arize_client_patch_prefers_legacy_when_submodule_exists(monkeypatch):
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: MagicMock() if name == "arize.api" else None,
    )
    assert arize_client_patch_target() == "arize.api.Client"


def test_arize_client_patch_falls_back_to_arize_client(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert arize_client_patch_target() == "arize.ArizeClient"
