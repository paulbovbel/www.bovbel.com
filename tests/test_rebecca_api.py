import json
from unittest.mock import Mock

import pytest

from bovbel_site.websites.local import lambda_event
from sites.rebecca.api import catalog, checkout


@pytest.mark.pre_deploy
def test_catalog_filters_unavailable_items(monkeypatch):
    objects = [
        {"type": "IMAGE", "id": "photo", "image_data": {"url": "https://example.com/piece.jpg"}},
    ]
    for name, visibility in [("Available", "VISIBLE"), ("Sold", "VISIBLE"), ("Hidden", "HIDDEN")]:
        objects.extend([
            {"type": "ITEM", "id": name, "item_data": {
                "name": name, "image_ids": ["photo"], "ecom_visibility": visibility,
            }},
            {"type": "ITEM_VARIATION", "id": name + "-variation", "item_variation_data": {
                "item_id": name, "price_money": {"amount": 1200, "currency": "CAD"},
            }},
        ])
    monkeypatch.setattr(catalog, "square_catalog_objects", lambda: objects)
    monkeypatch.setattr(catalog, "inventory_counts", lambda ids: {
        "Available-variation": 2, "Sold-variation": 0, "Hidden-variation": 1,
    })
    result = catalog.handler(lambda_event("GET"), None)
    assert result["statusCode"] == 200
    assert json.loads(result["body"])["items"] == [{
        "name": "Available", "description": "", "price": "CAD 12.00", "buy_url": "",
        "variation_id": "Available-variation", "quantity_available": 2,
        "image_url": "https://example.com/piece.jpg",
    }]


@pytest.mark.pre_deploy
def test_checkout_merges_quantities_and_uses_square_prices(monkeypatch):
    monkeypatch.setattr(checkout, "inventory_counts", lambda ids: {"piece": 3})
    monkeypatch.setattr(checkout, "square_location_id", lambda: "location")
    post = Mock(return_value={"payment_link": {"url": "https://square.link/example"}})
    monkeypatch.setattr(checkout, "square_post", post)
    result = checkout.handler(lambda_event("POST", json.dumps({"items": [
        {"variation_id": "piece", "quantity": 1, "price": 1},
        {"variation_id": "piece", "quantity": 2},
    ]})), None)
    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == {"url": "https://square.link/example"}
    path, payload = post.call_args.args
    assert path == "/v2/online-checkout/payment-links"
    assert payload["order"] == {
        "location_id": "location", "line_items": [{"catalog_object_id": "piece", "quantity": "3"}],
    }


@pytest.mark.pre_deploy
@pytest.mark.parametrize("items", [[], [{"variation_id": "invalid/id"}], [{"variation_id": "piece", "quantity": 3}]])
def test_checkout_rejects_bad_or_unavailable_cart(items, monkeypatch):
    monkeypatch.setattr(checkout, "inventory_counts", lambda ids: {"piece": 1})
    post = Mock()
    monkeypatch.setattr(checkout, "square_post", post)
    result = checkout.handler(lambda_event("POST", json.dumps({"items": items})), None)
    assert result["statusCode"] == 400
    post.assert_not_called()


@pytest.mark.pre_deploy
def test_api_handles_square_failure(monkeypatch):
    monkeypatch.setattr(catalog, "catalog_items", Mock(side_effect=RuntimeError("secret details")))
    result = catalog.handler(lambda_event("GET"), None)
    assert result["statusCode"] == 502
    assert json.loads(result["body"]) == {"error": "Unable to load catalog"}
