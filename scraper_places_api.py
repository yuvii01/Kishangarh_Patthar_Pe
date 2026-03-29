#!/usr/bin/env python3
"""
Alternative: Google Places API (Nearby Search + Place Details).
Requires a Google Cloud API key with Places API enabled.
Free tier: ~$200/month credit (≈ thousands of requests).
"""

import csv
import os
import time
from datetime import datetime

import requests

API_KEY = "YOUR_GOOGLE_PLACES_API_KEY"       # ← Replace this

CITIES_COORDS = {
    # city: (latitude, longitude)
    # "Jaipur":        (26.9124, 75.7873),
    "Bhilwara":      (25.3407, 74.6313),
    "Jodhpur":       (26.2389, 73.0243),
    "Udaipur":       (24.5854, 73.7125),
    "Kota":          (25.2138, 75.8648),
    # "Ajmer":         (26.4499, 74.6399),
    "Bikaner":       (28.0229, 73.3119),
    "Alwar":         (27.5530, 76.6346),
    # "Makrana":       (27.0434, 74.7237),
    # "Kishangarh":    (26.5921, 74.8593),
    "Rajsamand":     (25.0667, 73.8833),
    "Chittorgarh":   (24.8887, 74.6269),
    "Nagaur":        (27.2024, 73.7340),
    "Sikar":         (27.6094, 75.1399),
    "Pali":          (25.7711, 73.3234),
    "Barmer":        (25.7532, 71.3967),
    "Jaisalmer":     (26.9157, 70.9083),
    "Bharatpur":     (27.2152, 77.4890),
    "Sri Ganganagar": (29.9038, 73.8772),
    "Tonk":          (26.1505, 75.7898),
    "Beawar":        (26.1011, 74.3188),
    "Dungarpur":     (23.8437, 73.7143),
    "Banswara":      (23.5463, 74.4431),
}

SEARCH_KEYWORDS = [
    "granite store",
    "granite supplier",
    "granite dealer",
    "granite shop",
]

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def nearby_search(lat, lng, keyword, radius=15000, page_token=None):
    """Google Places Nearby Search."""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "keyword": keyword,
        "key": API_KEY,
    }
    if page_token:
        params["pagetoken"] = page_token

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def place_details(place_id):
    """Google Places Details — get phone, website, etc."""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,formatted_phone_number,"
                  "international_phone_number,website,rating,"
                  "user_ratings_total,types,url",
        "key": API_KEY,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("result", {})


def scrape_all():
    results = []
    seen_ids = set()

    for city, (lat, lng) in CITIES_COORDS.items():
        print(f"\n🏙️  {city}")
        for kw in SEARCH_KEYWORDS:
            print(f"   🔍 {kw}")
            page_token = None

            while True:
                data = nearby_search(lat, lng, kw, page_token=page_token)
                places = data.get("results", [])

                for place in places:
                    pid = place["place_id"]
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)

                    detail = place_details(pid)
                    row = {
                        "store_name":      detail.get("name", ""),
                        "owner_name":      "",
                        "contact_number":  detail.get("formatted_phone_number",
                                           detail.get("international_phone_number", "")),
                        "address":         detail.get("formatted_address", ""),
                        "city":            city,
                        "rating":          detail.get("rating", ""),
                        "total_reviews":   detail.get("user_ratings_total", ""),
                        "website":         detail.get("website", ""),
                        "google_maps_url": detail.get("url", ""),
                    }
                    results.append(row)
                    print(f"      ✅ {row['store_name']}  |  📞 {row['contact_number'] or '—'}")
                    time.sleep(0.1)

                page_token = data.get("next_page_token")
                if not page_token:
                    break
                time.sleep(2)   # Google requires ~2s before using next_page_token

    # Save CSV
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"marble_granite_places_api_{ts}.csv")
    fields = ["store_name", "owner_name", "contact_number", "address",
              "city", "rating", "total_reviews", "website", "google_maps_url"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)

    print(f"\n💾  Saved {len(results)} stores → {path}")


if __name__ == "__main__":
    scrape_all()
