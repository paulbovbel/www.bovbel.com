import base64
import json
import os
import re
from functools import cache
from uuid import uuid4

try:
    from api.common import inventory_counts, response, square_get, square_post
except ModuleNotFoundError:
    from sites.rebecca.api.common import inventory_counts, response, square_get, square_post


CATALOG_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
MAX_LINE_ITEMS = 20


@cache
def square_location_id():
    if os.environ.get("SQUARE_LOCATION_ID"):
        return os.environ["SQUARE_LOCATION_ID"]

    locations = square_get("/v2/locations").get("locations", [])
    for location in locations:
        if location.get("status") == "ACTIVE":
            return location["id"]

    raise RuntimeError("No active Square location found")


def request_body(event):
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode()
    return json.loads(body)


def validate_line_items(items):
    if not isinstance(items, list) or not items:
        raise ValueError("Cart is empty")
    if len(items) > MAX_LINE_ITEMS:
        raise ValueError(f"Cart is limited to {MAX_LINE_ITEMS} line items")

    quantities = {}
    for item in items:
        variation_id = str(item.get("variation_id", ""))
        quantity = int(item.get("quantity", 1))
        if not CATALOG_ID_RE.match(variation_id):
            raise ValueError("Invalid item variation")
        if quantity < 1 or quantity > 99:
            raise ValueError("Quantity must be between 1 and 99")

        quantities[variation_id] = quantities.get(variation_id, 0) + quantity

    return [
        {
            "catalog_object_id": variation_id,
            "quantity": str(quantity),
        }
        for variation_id, quantity in quantities.items()
    ]


def enforce_stock(line_items):
    requested = {
        line_item["catalog_object_id"]: int(line_item["quantity"])
        for line_item in line_items
    }
    stock_counts = inventory_counts(list(requested))

    for variation_id, quantity in requested.items():
        available = stock_counts.get(variation_id, 0)
        if quantity > available:
            raise ValueError(f"Only {available} available for item {variation_id}")


def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method")
    if method == "OPTIONS":
        return response(204, {})
    if method != "POST":
        return response(405, {"error": "Method not allowed"})

    try:
        body = request_body(event)
        line_items = validate_line_items(body.get("items"))
        enforce_stock(line_items)
        checkout = square_post(
            "/v2/online-checkout/payment-links",
            {
                "idempotency_key": str(uuid4()),
                "order": {
                    "location_id": square_location_id(),
                    "line_items": line_items,
                },
            },
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        return response(400, {"error": str(error)})
    except Exception:
        return response(502, {"error": "Unable to create checkout"})

    url = checkout.get("payment_link", {}).get("url")
    if not url:
        return response(502, {"error": "Square did not return a checkout URL"})

    return response(200, {"url": url})
