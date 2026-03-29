# Marble & Granite Store Scraper — Rajasthan

## Quick Start (Selenium Scraper)

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Make sure Google Chrome is installed on your system

# 3. Run the scraper
python scraper.py
```

The browser will open, search Google Maps for each city, scroll through results, click into each listing, and extract the data.

**Output** → `marble_granite_rajasthan_LATEST.csv` (running backup) + a timestamped final CSV when finished.

## Configuration

### Run headless (no visible browser)
In `scraper.py` change:
```python
scraper = GoogleMapsScraper(headless=True)
```

### Scrape only specific cities
```python
scraper.run(["Jaipur", "Bhilwara", "Udaipur"])
```

## Alternative: Google Places API

```bash
pip install -r requirements.txt
```

1. Get a Google Cloud API key → enable **Places API**
2. Paste it in `scraper_places_api.py`:
   ```python
   API_KEY = "YOUR_GOOGLE_PLACES_API_KEY"
   ```
3. Run:
   ```bash
   python scraper_places_api.py
   ```

This is the official, reliable method. Google gives ~$200 free credit/month which covers thousands of lookups.

## CSV Columns

| Column | Description |
|--------|-------------|
| `store_name` | Business name |
| `owner_name` | Owner (rarely available on Maps) |
| `contact_number` | Phone number |
| `address` | Full address |
| `city` | City searched |
| `rating` | Google rating (1-5) |
| `total_reviews` | Number of Google reviews |
| `website` | Business website |
| `category` | Google Maps category |
| `google_maps_url` | Direct link to Maps listing |

## Notes

- **Owner names** are rarely listed on Google Maps; this field will often be blank.
- The Selenium scraper saves a backup CSV after every city, so if it crashes you don't lose data.
- Press **Ctrl+C** to stop early — it saves a partial CSV.
- Google may occasionally show CAPTCHAs; if the scraper stalls, solve it manually in the browser window.

## Cities Covered

The scraper includes all 36 districts of Rajasthan:

**Tier-1 cities:** Jaipur, Jodhpur, Udaipur, Kota, Ajmer, Bikaner

**Marble-belt cities:** Bhilwara, Rajsamand, Makrana, Kishangarh

**Other major cities:** Alwar, Bharatpur, Sikar, Pali, Tonk, Chittorgarh, Nagaur, Barmer, Jaisalmer, Sri Ganganagar, Hanumangarh, Jhunjhunu, Churu, Sawai Madhopur, Bundi, Dholpur, Karauli, Dausa, Jhalawar, Baran, Sirohi, Jalore, Banswara, Dungarpur, Pratapgarh, Beawar
