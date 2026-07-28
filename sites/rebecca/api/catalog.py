try:
    from api.common import inventory_counts, response, square_post
except ModuleNotFoundError:
    from sites.rebecca.api.common import inventory_counts, response, square_post


def square_catalog_objects():
    objects = []
    cursor = None

    while True:
        payload = {
            "object_types": ["ITEM", "ITEM_VARIATION", "IMAGE"],
            "include_deleted_objects": False,
            "include_related_objects": True,
        }
        if cursor:
            payload["cursor"] = cursor

        data = square_post("/v2/catalog/search", payload)
        objects.extend(data.get("objects", []))
        objects.extend(data.get("related_objects", []))

        cursor = data.get("cursor")
        if not cursor:
            return objects


def money_label(money):
    if not money:
        return ""

    amount = money.get("amount")
    currency = money.get("currency", "USD")
    if amount is None:
        return ""

    return f"{currency} {amount / 100:.2f}"


def item_price(item_data):
    prices = []
    for variation in item_data.get("variations", []):
        variation_data = variation.get("item_variation_data", {})
        if variation_data.get("sellable") is False:
            continue
        price = money_label(variation_data.get("price_money"))
        if price:
            prices.append(price)

    return min(prices) if prices else ""


def variation_price(item_id, variations):
    prices = []
    for variation in variations:
        variation_data = variation.get("item_variation_data", {})
        if variation_data.get("item_id") != item_id:
            continue
        if variation_data.get("sellable") is False:
            continue

        price = money_label(variation_data.get("price_money"))
        if price:
            prices.append(price)

    return min(prices) if prices else ""


def item_variations(item_data, item_id, variations):
    embedded_variations = item_data.get("variations", [])
    if embedded_variations:
        return embedded_variations

    return [
        variation
        for variation in variations
        if variation.get("item_variation_data", {}).get("item_id") == item_id
    ]


def sellable_variation(item_data, item_id, variations):
    for variation in item_variations(item_data, item_id, variations):
        variation_data = variation.get("item_variation_data", {})
        if variation_data.get("sellable") is False:
            continue
        return variation

    return None


def catalog_items():
    catalog_objects = square_catalog_objects()
    items = []
    image_urls = {}
    variations = []

    for obj in catalog_objects:
        if obj.get("type") == "IMAGE":
            image_data = obj.get("image_data", {})
            if image_data.get("url"):
                image_urls[obj["id"]] = image_data["url"]
        elif obj.get("type") == "ITEM_VARIATION":
            variations.append(obj)

    stock_counts = inventory_counts([variation["id"] for variation in variations])

    for obj in catalog_objects:
        if obj.get("type") != "ITEM":
            continue

        item_data = obj.get("item_data", {})
        if item_data.get("ecom_visibility") == "HIDDEN":
            continue

        variation = sellable_variation(item_data, obj["id"], variations)
        if not variation:
            continue

        quantity_available = stock_counts.get(variation["id"], 0)
        if quantity_available < 1:
            continue

        image_url = ""
        for image_id in item_data.get("image_ids", []):
            if image_id in image_urls:
                image_url = image_urls[image_id]
                break

        items.append(
            {
                "name": item_data.get("name", "Untitled piece"),
                "description": item_data.get("description", ""),
                "price": item_price(item_data) or variation_price(obj["id"], variations),
                "buy_url": item_data.get("ecom_uri", ""),
                "variation_id": variation["id"],
                "quantity_available": quantity_available,
                "image_url": image_url,
            }
        )

    return sorted(items, key=lambda item: item["name"].lower())


def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method")
    if method not in (None, "GET"):
        return response(405, {"error": "Method not allowed"})

    try:
        return response(200, {"items": catalog_items()})
    except Exception:
        return response(502, {"error": "Unable to load catalog"})
