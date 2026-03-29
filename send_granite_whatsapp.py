import os
import re
import time
import pandas as pd
import pywhatkit as pwk

# 1) CONFIG
INPUT_CSV = "granite_dealers_rajasthan_clean.csv"
MESSAGE_TEMPLATE = (
    "Hello {name},\n"
    "This is Vijay from Granite Traders.\n"
    "Today price for Premium Black Granite is ₹{rate}/sqft.\n"
    "Location: {city}\n\n"
    "Reply here to book delivery or get sample photos."
)
DELAY_BETWEEN_MESSAGES_SEC = 30
PHONE_PREFIX = "+91"

def normalize_phone(phone: str) -> str:
    s = str(phone).strip()
    s = re.sub(r"[^\d+]", "", s)
    s = s.lstrip("0")
    if s.startswith("91") and not s.startswith("+"):
        s = "+" + s
    if not s.startswith("+"):
        s = PHONE_PREFIX + s
    return s

def is_blocked_phone(phone: str) -> bool:
    return not bool(re.match(r"^\+\d{10,14}$", phone))

def main():
    cwd = os.path.dirname(os.path.abspath(__file__))
    path_in = os.path.join(cwd, INPUT_CSV)
    if not os.path.exists(path_in):
        raise FileNotFoundError("Input file missing: " + path_in)

    df = pd.read_csv(path_in, dtype=str, keep_default_na=False)
    df["contact_number"] = df["contact_number"].apply(normalize_phone)

    already = 0
    sent = 0
    skipped = 0

    print("Open WhatsApp Web once and login; then press Enter to continue...")
    input()

    for idx, row in df.iterrows():
        name = row.get("store_name", "Sir/Madam")
        phone = row.get("contact_number", "")
        city = row.get("city", "")
        address = row.get("address", "")
        rate = row.get("rate", "negotiable")
        stock = row.get("stock", "available")

        if is_blocked_phone(phone):
            print(f"SKIP invalid number: {phone} (row {idx+1})")
            skipped += 1
            continue

        msg = MESSAGE_TEMPLATE.format(name=name, rate=rate, city=city, stock=stock)

        try:
            print(f"SEND {idx+1} -> {phone} : {name}")
            pwk.sendwhatmsg_instantly(phone_no=phone, message=msg, wait_time=10, tab_close=False)
            sent += 1
            time.sleep(8)   # small gap to reduce throttling risk
        except Exception as exc:
            print(f"ERROR {phone}: {exc}")
            skipped += 1
            time.sleep(5)

    print(f"Done: total={len(df)}, sent={sent}, skipped={skipped}, already={already}")

if __name__ == "__main__":
    main()