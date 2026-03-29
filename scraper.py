#!/usr/bin/env python3
"""
Granite Shop Scraper — Small & Mid Dealers in Rajasthan
• Saves each record to CSV IMMEDIATELY (never loses data)
• Filters out big players / exporters / industries
"""

import atexit
import csv
import os
import re
import signal
import sys
import time
import traceback

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:
    print("Run:  pip install undetected-chromedriver selenium")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════

CITIES = [  

]

# Focused on granite retail shops only
SEARCH_QUERIES = [
    "granite shop in {city}",
    "granite dealer in {city}",
    "granite store in {city}",
    "granite supplier in {city}",
]

# Filter out big players — if store name contains any of these, skip it
BIG_PLAYER_KEYWORDS = [
    "export", "exporter", "international", "global",
    "industries", "industry", "limited", "ltd",
    "pvt", "private limited", "corporation",
    "group of companies", "mining", "quarry",
    "manufacturer", "manufacturing", "infra",
    "construction company", "builders",
    "multinational", "enterprise",  # keep "enterprises" — often small
]

# If a store has more than this many Google reviews, skip it (likely big player)
MAX_REVIEWS = 50

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE   = os.path.join(SCRIPT_DIR, "granite_dealers_rajasthan.csv")

FIELDS = [
    "store_name", "owner_name", "contact_number",
    "address", "city", "rating" , "total_reviews", "category",
    "website", "google_maps_url",
]

# ══════════════════════════════════════════════════════════════
#  CSV — IMMEDIATE SAVE (append each row as we find it)
# ══════════════════════════════════════════════════════════════

class LiveCSV:
    """Appends each row to CSV the moment it's found.
       Even Ctrl+C / crash / kill won't lose data."""

    def __init__(self, path, fields):
        self.path   = path
        self.fields = fields
        self.count  = 0

        # If file doesn't exist or is empty, write header
        write_header = (not os.path.exists(path) or os.path.getsize(path) == 0)
        self._file   = open(path, "a", newline="", encoding="utf-8-sig")
        self._writer = csv.DictWriter(self._file, fieldnames=fields)
        if write_header:
            self._writer.writeheader()
            self._file.flush()

    def add(self, row: dict):
        self._writer.writerow(row)
        self._file.flush()              # flush to disk IMMEDIATELY
        os.fsync(self._file.fileno())   # force OS to write to disk
        self.count += 1

    def close(self):
        try:
            self._file.close()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════
#  SCRAPER
# ══════════════════════════════════════════════════════════════

class GraniteScraper:

    def __init__(self, headless=False):
        self.seen_names = set()
        self.seen_urls  = set()
        self.csv        = LiveCSV(CSV_FILE, FIELDS)
        self.driver     = None
        self.wait       = None
        self._start_browser(headless)

        # ── ensure cleanup on ANY exit ──
        atexit.register(self._cleanup)
        signal.signal(signal.SIGINT,  self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        # Load already-scraped names (if resuming)
        self._load_existing()

    def _load_existing(self):
        """If CSV already has data (from previous run), load seen names
           so we don't duplicate."""
        if not os.path.exists(CSV_FILE):
            return
        try:
            with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("store_name", "").lower().strip()
                    if name:
                        self.seen_names.add(name)
                        self.csv.count += 1
            if self.seen_names:
                print(f"📂  Resuming — {len(self.seen_names)} stores already in CSV")
        except Exception:
            pass

    def _handle_signal(self, sig, frame):
        print(f"\n\n⛔  Stopped! {self.csv.count} records already saved to:")
        print(f"    📁  {CSV_FILE}")
        self._cleanup()
        sys.exit(0)

    def _cleanup(self):
        self.csv.close()
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    # ── browser ──────────────────────────────────────────────

    def _start_browser(self, headless):
        print("🚀  Starting Chrome …")
        opts = uc.ChromeOptions()
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--lang=en-US")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        if headless:
            opts.add_argument("--headless=new")

        self.driver = uc.Chrome(options=opts, version_main=None)
        self.wait   = WebDriverWait(self.driver, 15)
        print("✅  Chrome ready\n")

    # ── navigation ───────────────────────────────────────────

    def _search(self, query):
        url = "https://www.google.com/maps/search/" + query.replace(" ", "+")
        self.driver.get(url)
        time.sleep(6)

        # dismiss consent
        for xp in ["//button[contains(.,'Accept all')]",
                    "//button[contains(.,'Accept')]"]:
            try:
                btns = self.driver.find_elements(By.XPATH, xp)
                for b in btns:
                    if b.is_displayed():
                        b.click()
                        time.sleep(2)
                        break
            except Exception:
                continue
        time.sleep(2)

    # ── scroll ───────────────────────────────────────────────

    def _scroll_feed(self):
        feed = None
        for sel in ['div[role="feed"]', 'div.m6QErb.DxyBCb.kA9KIf.dS8AEf']:
            try:
                feed = self.driver.find_element(By.CSS_SELECTOR, sel)
                break
            except Exception:
                continue
        if not feed:
            return False

        prev = 0
        stale = 0
        for _ in range(40):
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", feed
            )
            time.sleep(2.5)

            cur = self.driver.execute_script(
                "return arguments[0].scrollHeight", feed
            )

            try:
                if "end of the list" in feed.get_attribute("innerHTML"):
                    break
            except Exception:
                pass

            if cur == prev:
                stale += 1
                if stale >= 3:
                    break
            else:
                stale = 0
            prev = cur
        return True

    # ── collect URLs ─────────────────────────────────────────

    def _listing_urls(self):
        urls = []
        try:
            anchors = self.driver.find_elements(
                By.CSS_SELECTOR, 'a[href*="/maps/place/"]'
            )
            for a in anchors:
                h = a.get_attribute("href")
                if h:
                    urls.append(h)
        except Exception:
            pass

        if not urls:
            try:
                for a in self.driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc"):
                    h = a.get_attribute("href")
                    if h:
                        urls.append(h)
            except Exception:
                pass

        seen, unique = set(), []
        for u in urls:
            k = u.split("/@")[0]
            if k not in seen:
                seen.add(k)
                unique.append(u)
        return unique

    # ── extract detail ───────────────────────────────────────

    def _txt(self, css):
        try:
            return self.driver.find_element(By.CSS_SELECTOR, css).text.strip()
        except Exception:
            return ""

    def _get_name(self):
        for sel in ["h1.DUwDvf", "h1.fontHeadlineLarge", "h1"]:
            t = self._txt(sel)
            if t and "google" not in t.lower():
                return t
        return ""

    def _get_phone(self):
        # method 1: data-item-id
        try:
            el = self.driver.find_element(
                By.CSS_SELECTOR, 'button[data-item-id^="phone:tel:"]'
            )
            did = el.get_attribute("data-item-id") or ""
            phone = did.replace("phone:tel:", "").strip()
            if phone:
                return phone
        except Exception:
            pass

        # method 2: aria-label
        for sel in ['button[aria-label*="Phone"]',
                     'button[aria-label*="phone"]',
                     'button[data-tooltip="Copy phone number"]']:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, sel)
                aria = el.get_attribute("aria-label") or ""
                phone = re.sub(r"^.*?:\s*", "", aria).strip()
                if phone:
                    return phone
            except Exception:
                continue

        # method 3: all CsEnBe buttons
        try:
            for btn in self.driver.find_elements(By.CSS_SELECTOR, "button.CsEnBe"):
                did  = btn.get_attribute("data-item-id") or ""
                aria = btn.get_attribute("aria-label") or ""
                if "phone" in did.lower() or "phone" in aria.lower():
                    phone = did.replace("phone:tel:", "") or re.sub(r"^.*?:\s*", "", aria)
                    if phone.strip():
                        return phone.strip()
        except Exception:
            pass

        # method 4: regex
        try:
            body = self.driver.find_element(By.TAG_NAME, "body").text
            for pat in [r"\+91[\s-]?\d{5}[\s-]?\d{5}",
                        r"0\d{2,4}[\s-]?\d{6,8}",
                        r"[6-9]\d{4}[\s-]?\d{5}"]:
                m = re.search(pat, body)
                if m:
                    return m.group().strip()
        except Exception:
            pass

        return ""

    def _get_address(self):
        for sel in ['button[data-item-id="address"]',
                     'button[aria-label^="Address"]']:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, sel)
                aria = el.get_attribute("aria-label") or ""
                addr = re.sub(r"^Address:\s*", "", aria).strip()
                if addr:
                    return addr
            except Exception:
                continue
        return ""

    def _get_reviews_count(self):
        try:
            el = self.driver.find_element(
                By.CSS_SELECTOR, 'span[aria-label*="review"]'
            )
            m = re.search(r"([\d,]+)", el.get_attribute("aria-label") or "")
            if m:
                return m.group(1).replace(",", "")
        except Exception:
            pass
        return ""

    def _get_rating(self):
        t = self._txt('div.F7nice span[aria-hidden="true"]')
        if t:
            return t
        return ""

    def _get_website(self):
        try:
            el = self.driver.find_element(
                By.CSS_SELECTOR, 'a[data-item-id="authority"]'
            )
            return (el.get_attribute("href") or "").strip()
        except Exception:
            return ""

    def _get_category(self):
        for sel in ["button.DkEaL", "span.DkEaL"]:
            t = self._txt(sel)
            if t:
                return t
        return ""

    # ── big player filter ────────────────────────────────────

    def _is_big_player(self, name, reviews_str, category):
        """Return True if this looks like a big / irrelevant business."""
        name_lower = name.lower()

        # keyword filter
        for kw in BIG_PLAYER_KEYWORDS:
            if kw in name_lower:
                return True

        # too many reviews → big player
        try:
            rev = int(reviews_str.replace(",", "")) if reviews_str else 0
            if rev > MAX_REVIEWS:
                return True
        except (ValueError, AttributeError):
            pass

        # wrong category entirely
        cat_lower = category.lower()
        skip_cats = ["quarry", "mining", "construction company",
                     "real estate", "architect", "interior designer"]
        for sc in skip_cats:
            if sc in cat_lower:
                return True

        return False

    # ── extract one listing ──────────────────────────────────

    def _extract(self, url, city):
        self.driver.get(url)
        time.sleep(3)

        # wait for h1
        try:
            self.wait.until(
                lambda d: any(e.text.strip() for e in d.find_elements(By.CSS_SELECTOR, "h1"))
            )
        except Exception:
            pass
        time.sleep(1)

        name = self._get_name()
        if not name:
            return None

        reviews = self._get_reviews_count()
        category = self._get_category()

        if self._is_big_player(name, reviews, category):
            return "BIG_PLAYER"

        return {
            "store_name":      name,
            "owner_name":      "",
            "contact_number":  self._get_phone(),
            "address":         self._get_address(),
            "city":            city,
            "rating":          self._get_rating(),
            "total_reviews":   reviews,
            "website":         self._get_website(),
            "category":        category,
            "google_maps_url": url,
        }

    # ── scrape one city ──────────────────────────────────────

    def _scrape_city(self, city):
        added = 0

        for tmpl in SEARCH_QUERIES:
            query = tmpl.format(city=city)
            print(f"\n  🔍  {query}")

            try:
                self._search(query)
                found = self._scroll_feed()

                if found:
                    links = self._listing_urls()
                    print(f"      📋  {len(links)} listings")

                    for i, link in enumerate(links, 1):
                        if link in self.seen_urls:
                            continue
                        self.seen_urls.add(link)

                        try:
                            row = self._extract(link, city)

                            if row == "BIG_PLAYER":
                                print(f"      🚫  [{i}/{len(links)}] big player, skipped")
                                continue

                            if row and row["store_name"]:
                                key = row["store_name"].lower().strip()
                                if key in self.seen_names:
                                    print(f"      ⏭️  [{i}/{len(links)}] dup")
                                    continue

                                self.seen_names.add(key)
                                self.csv.add(row)          # ← SAVED IMMEDIATELY
                                added += 1

                                ph = row["contact_number"] or "N/A"
                                print(f"      ✅  [{i}/{len(links)}] "
                                      f"{row['store_name']}  📞 {ph}")

                            time.sleep(1)
                        except Exception as e:
                            print(f"      ❌  [{i}/{len(links)}] {e}")
                else:
                    row = self._extract(self.driver.current_url, city)
                    if row and row != "BIG_PLAYER":
                        key = row["store_name"].lower().strip()
                        if key not in self.seen_names:
                            self.seen_names.add(key)
                            self.csv.add(row)
                            added += 1
                            print(f"      ✅  {row['store_name']}")

                time.sleep(2)
            except Exception as e:
                print(f"      ⚠️  {e}")

        return added

    # ── main ─────────────────────────────────────────────────

    def run(self, cities=None):
        cities = cities or CITIES

        print("=" * 60)
        print("  🪨  GRANITE DEALER SCRAPER — RAJASTHAN")
        print(f"  🎯  Small & mid shops only (filtering out big players)")
        print(f"  📁  Saving to: {CSV_FILE}")
        print(f"  💡  You can stop anytime — data is saved instantly")
        print("=" * 60)

        for idx, city in enumerate(cities, 1):
            print(f"\n{'━' * 55}")
            print(f"  🏙️  [{idx}/{len(cities)}]  {city.upper()}")
            print(f"{'━' * 55}")

            try:
                added = self._scrape_city(city)
                print(f"\n  📊  {city}: +{added} shops  "
                      f"(total saved: {self.csv.count})")
            except Exception:
                print(f"  💥  error for {city}")
                traceback.print_exc()

            time.sleep(3)

        print(f"\n{'=' * 60}")
        print(f"  ✅  DONE — {self.csv.count} granite shops saved")
        print(f"  📁  {CSV_FILE}")
        print(f"{'=' * 60}")


# ══════════════════════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════════════════════

def main():
    scraper = GraniteScraper(headless=False)
    try:
        scraper.run()
        # or specific cities:
        # scraper.run(["Jaipur", "Bhilwara", "Jodhpur"])
    except Exception:
        traceback.print_exc()
    finally:
        print(f"\n💾  {scraper.csv.count} records saved to {CSV_FILE}")
        scraper._cleanup()


if __name__ == "__main__":
    main()