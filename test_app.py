import pytest

import app as app_module
from app import create_app
from splitter import split_evenly


@pytest.fixture
def client():
    # The store is module-level, so reset it between tests rather than letting
    # one test's expenses leak into the next one's balances.
    app_module._expenses.clear()
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_health_reports_the_configured_currency(client):
    body = client.get("/health").get_json()
    assert body["status"] == "ok"
    assert body["currency"]


def test_split_three_ways():
    assert split_evenly(900, ["ana", "ben", "cal"]) == {
        "ana": 300,
        "ben": 300,
        "cal": 300,
    }


def test_payer_is_credited_the_others_shares(client):
    client.post(
        "/expenses",
        json={
            "amount_cents": 900,
            "paid_by": "ana",
            "participants": ["ana", "ben", "cal"],
        },
    )
    body = client.get("/balances").get_json()
    assert body["balances"]["ana"] == 600
    assert body["balances"]["ben"] == -300


VALID_EXPENSE = {
    "amount_cents": 900,
    "paid_by": "ana",
    "participants": ["ana", "ben", "cal"],
}


def test_valid_expense_is_accepted(client):
    resp = client.post("/expenses", json=VALID_EXPENSE)
    assert resp.status_code == 201


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount_cents": 9.0},
        {"amount_cents": "900"},
        {"amount_cents": True},
        {"amount_cents": 0},
        {"amount_cents": -100},
        {"paid_by": ""},
        {"paid_by": 42},
        {"participants": []},
        {"participants": "ana"},
        {"participants": ["ana", ""]},
        {"participants": ["ana", "ana", "ben"]},
    ],
)
def test_invalid_expense_is_rejected(client, overrides):
    resp = client.post("/expenses", json={**VALID_EXPENSE, **overrides})
    assert resp.status_code == 400
    assert resp.get_json()["errors"]
    assert app_module._expenses == []


@pytest.mark.parametrize("field", ["amount_cents", "paid_by", "participants"])
def test_missing_field_is_rejected(client, field):
    body = {k: v for k, v in VALID_EXPENSE.items() if k != field}
    resp = client.post("/expenses", json=body)
    assert resp.status_code == 400
    assert any(field in e for e in resp.get_json()["errors"])


def test_non_json_body_is_rejected(client):
    resp = client.post("/expenses", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_json_array_body_is_rejected(client):
    resp = client.post("/expenses", json=[VALID_EXPENSE])
    assert resp.status_code == 400
