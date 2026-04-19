"""Extra MLFlow gateway unit coverage."""

import pytest

from data5580_hw.gateways.mlflow_gateway import MLFlowGateway


def test_load_model_unsupported_flavor_raises():
    gw = MLFlowGateway()
    with pytest.raises(ValueError, match="Unsupported model flavor"):
        gw._load_model("models:/x/1", "unknown-flavor")
