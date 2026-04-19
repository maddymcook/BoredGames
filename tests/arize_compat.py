"""Helpers for tests across arize 7.x (legacy api.Client) and 8.x (ArizeClient)."""

from __future__ import annotations

import importlib.util


def arize_client_patch_target() -> str:
    """Return the patch path for the concrete client class installed in the environment."""
    if importlib.util.find_spec("arize.api") is not None:
        return "arize.api.Client"
    return "arize.ArizeClient"


def import_environments_and_model_types():
    try:
        from arize.utils.types import Environments, ModelTypes
    except ImportError:
        from arize.ml.types import Environments, ModelTypes
    return Environments, ModelTypes


def import_environments():
    try:
        from arize.utils.types import Environments
    except ImportError:
        from arize.ml.types import Environments
    return Environments
