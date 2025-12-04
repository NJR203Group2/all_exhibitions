import requests
import json
import pandas as pd

API_KEY = "YOUR API KEY"  # 請替換成你的 Google Places API Key

BASE_URL = "https://places.googleapis.com/v1/places:searchText"

# 要回傳的欄位（注意：要保留 places.types 才能判斷是不是博物館）
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.types",                           
    "places.websiteUri",
    "places.internationalPhoneNumber",
    "places.rating",
    "places.regularOpeningHours.weekdayDescriptions"
])

HEADERS = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": API_KEY,
    "X-Goog-FieldMask": FIELD_MASK,
}

# 雙北博物館 / 美術館關鍵字
KEYWORDS = [
    # 台北市
    "台北市 博物館",
    "台北市 美術館",
    "museum in Taipei City",
    "art museum Taipei",

    # 新北市
    "新北市 博物館",
    "新北市 美術館",
    "museum in New Taipei City",
    "art museum New Taipei",
]

# 額外一定要查詢的文化園區關鍵字
EXTRA_QUERIES = [
    "華山1914文化創意產業園區",
    "松山文創園區",
]

# 只保留這兩個主園區的 place_id
KEEP_PARK_IDS = {
    "ChIJbSTgI2WpQjQRcVwWB2cnyfE",   # 華山
    "ChIJO0vOI7-rQjQR3Pl9_4cPK8g",   # 松菸
}

# 視為博物館 / 美術館的 types
MUSEUM_TYPES = {"museum", "art_gallery"}


# ==========================
#  API 呼叫與工具函式
# ==========================

def search_text_all_pages(text_query: str):
    """用 Places API (New) 搜尋關鍵字，支援翻頁"""
    all_places = []
    page_token = None

    while True:
        body = {
            "textQuery": text_query,
            "languageCode": "zh-TW",  # 繁體中文
            "pageSize": 20,
        }
        if page_token:
            body["pageToken"] = page_token

        resp = requests.post(BASE_URL, headers=HEADERS, json=body)
        print(f"[searchText] {text_query} -> {resp.status_code}")
        data = resp.json()

        if "error" in data:
            print("❌ API 錯誤：", data["error"].get("message"))
            break

        places = data.get("places", [])
        all_places.extend(places)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return all_places


def is_museum_like(place: dict) -> bool:
    """判斷此地點是否為博物館 / 美術館"""
    types = set(place.get("types", []) or [])
    return bool(types & MUSEUM_TYPES)


def extract_row(place: dict) -> dict:
    """整理輸出欄位（不輸出類型 types）"""
    pid = place.get("id")
    name = place.get("displayName", {}).get("text")
    addr = place.get("formattedAddress")
    loc = place.get("location", {}) or {}
    lat = loc.get("latitude")
    lng = loc.get("longitude")
    website = place.get("websiteUri")
    phone = place.get("internationalPhoneNumber")
    rating = place.get("rating")
    opening_list = place.get("regularOpeningHours", {}).get("weekdayDescriptions", [])

    opening_str = "|".join(opening_list) if opening_list else None

    return {
        "place_id": pid,
        "館名": name,
        "地址": addr,
        "緯度": lat,
        "經度": lng,
        "網站": website,
        "電話": phone,
        "評分": rating,
        "營業時間": opening_str,
    }


# ==========================
#  主流程
# ==========================

def main():
    all_places_by_id = {}

    # 1) 抓雙北博物館、美術館
    for kw in KEYWORDS:
        places = search_text_all_pages(kw)
        for p in places:
            pid = p.get("id")
            if pid:
                all_places_by_id[pid] = p

    # 2) 抓華山 & 松菸（避免 types 不符時被漏掉）
    for q in EXTRA_QUERIES:
        places = search_text_all_pages(q)
        for p in places:
            pid = p.get("id")
            if pid:
                all_places_by_id[pid] = p

    print("🔢 抓到（去重後） place 數量：", len(all_places_by_id))

    # 3) 保留博物館、美術館 + 華山、松菸主園區
    selected_places = []
    for p in all_places_by_id.values():
        pid = p.get("id")
        if is_museum_like(p) or pid in KEEP_PARK_IDS:
            selected_places.append(p)

    print("✅ 最終保留的 place 數量：", len(selected_places))

    # 4) 輸出 CSV（不含類型欄位）
    rows = [extract_row(p) for p in selected_places]
    df = pd.DataFrame(rows)
    df.to_csv("taipei_museums_info.csv", encoding="utf-8-sig", index=False)

    print("📁 已輸出：taipei_museums_info.csv")


if __name__ == "__main__":
    main()