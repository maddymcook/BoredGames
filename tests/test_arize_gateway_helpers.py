"""Unit tests for arize_gateway module-level helpers (no live SDK calls)."""

from data5580_hw.gateways import arize_gateway as ag


def test_normalize_space_id_empty():
    assert ag._normalize_arize_space_id("") == ""


def test_map_arize_environment_staging_maps_to_validation():
    class E:
        PRODUCTION = 1
        VALIDATION = 2
        TRAINING = 3

    assert ag._map_arize_environment(E, "STAGING") == E.VALIDATION


def test_map_sdk_model_type_unknown_defaults_to_regression():
    class MT:
        REGRESSION = "reg"
        BINARY_CLASSIFICATION = "bc"
        SCORE_CATEGORICAL = "sc"
        NUMERIC = "num"

    assert ag._map_sdk_model_type("WEIRD", MT) == MT.REGRESSION


def test_safe_feature_tag_dicts_none_tags():
    feats, tags = ag._safe_feature_tag_dicts({"a": 1}, None)
    assert tags is None
    assert feats["a"] == 1.0


def test_schedule_log_followup_respects_wait_sync(monkeypatch):
    called = []

    def fn():
        called.append(1)

    monkeypatch.setenv("ARIZE_LOG_WAIT", "1")
    ag._schedule_log_followup(fn)
    assert called == [1]
