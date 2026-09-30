import json
import os
import sys
import time
import urllib.parse
import urllib.request

# iPhone 18 Pro Max 256GB Burgundy (Swiss/DACH part number)
PART = os.environ.get("PART_NUMBER", "MJXQ4ZD/A")
TOPIC = os.environ["NTFY_TOPIC"]
TEST = os.environ.get("TEST") == "1"

# Zurich, Basel, Geneva, Lausanne: together these cover all Swiss Apple Stores
LOCATIONS = ["8001", "4051", "1204", "1003"]
BASE = "https://www.apple.com/ch-de/shop/fulfillment-messages"
BUY_URL = "https://www.apple.com/ch-de/shop/buy-iphone"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/json",
    "Accept-Language": "de-CH,de;q=0.9",
    "Referer": BUY_URL,
}


def fetch(location):
    query = urllib.parse.urlencode({
        "pl": "true",
        "mts.0": "regular",
        "parts.0": PART,
        "location": location,
        "searchNearby": "true",
    })
    req = urllib.request.Request(f"{BASE}?{query}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def notify(title, message, priority="urgent"):
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title, "Priority": priority,
                 "Tags": "rotating_light", "Click": BUY_URL},
    )
    urllib.request.urlopen(req, timeout=20)


def main():
    stores, errors = {}, []
    for loc in LOCATIONS:
        try:
            data = fetch(loc)
            found = data.get("body", {}).get("content", {}).get("pickupMessage", {}).get("stores", [])
            for s in found:
                stores[s.get("storeNumber")] = s
        except Exception as e:
            errors.append(f"{loc}: {e}")
        time.sleep(2)

    if not stores:
        print("No store data received. Errors:", errors)
        sys.exit(1)

    lines, available, part_seen = [], [], False
    for s in stores.values():
        pa = s.get("partsAvailability", {}).get(PART)
        if pa:
            part_seen = True
        pa = pa or {}
        status = pa.get("pickupDisplay", "unknown")
        quote = pa.get("pickupSearchQuote", "")
        name = s.get("storeName", "?")
        lines.append(f"{name}: {status} {quote}".strip())
        if status == "available":
            available.append(name)

    print("\n".join(lines))

    if not part_seen:
        print(f"Part number {PART} not recognised by Apple CH. Check the part number.")
        sys.exit(1)

    if available:
        notify("iPhone 18 Pro Max Burgundy IN STOCK",
               "Pickup available at: " + ", ".join(available) +
               "\nOpen the Apple Store app and reserve NOW.")
    elif TEST:
        notify("Stock checker test", "Working. Current status:\n" + "\n".join(lines), priority="default")


if __name__ == "__main__":
    main()
