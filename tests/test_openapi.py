from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
validator = pytest.importorskip("openapi_spec_validator")

SPEC = Path(__file__).resolve().parents[1] / "docs" / "api" / "openapi.yaml"


def test_openapi_document_is_valid():
    validator.validate(yaml.safe_load(SPEC.read_text()))


def test_work_order_statuses_match_the_domain_model():
    from eam.work_orders import Status

    spec = yaml.safe_load(SPEC.read_text())
    assert spec["components"]["schemas"]["WorkOrderStatus"]["enum"] == [s.value for s in Status]
