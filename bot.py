Python 3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license()" for more information.
>>> import requests
... import time
... import json
... import os
... from datetime import datetime
... 
... # ================= CONFIG =================
... FEDEX_TOKEN = os.getenv("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiI2NzhlNThmZGM5Njc2ZjAwMDkwZmNiNTciLCJleHAiOjE3NzgyNDcyOTIsInRlbmFudElkIjoiRkRYRlJHSFRfMSIsInVzZXJUeXBlIjoiY2Fycmllcl9kaXNwYXRjaGVyIiwic2Vzc2lvbklkIjoiOTk2OTk3OGItYWNiOC00M2M5LWJlNjMtMjdhZWVlYjUyNGU3In0.LdYoFPhjYRWggZnW489Kc--XqDiOOqtqsCIGZbtWFNM")
... TELEGRAM_BOT_TOKEN = os.getenv("8636504764:AAEp1adhodIBE1_qZ391R7EO5j3eh4SoJ5w")
... 
... CHANNEL_ID = "-1003750550317"
... OFFERS_GROUP_ID = "-1003651639921"
... 
... KEY = "AlzaSyAHpKsviDxi4Rcp8YU9zX1RryymAsAaUKo"
... USER_ID = "678e58fdc9676f00090fcb57"
... TENANT_ID = "FDXFRGHT_1"
... COMPANY_ID = "6584b5a7c839a80009a7a41f"
... 
... URL = f"https://es-fedex.zuumapp.com/v1/search/shipments/format-for-carriers?key={KEY}"
... 
... HEADERS = {
...     "Authorization": FEDEX_TOKEN,
...     "X-Access-Token": FEDEX_TOKEN,
...     "Content-Type": "application/json"
... }
... 
... STATE = {
...     "cache": {},
...     "posted": {},
...     "offset": 0
... }
... 
... # ================= TELEGRAM =================
def tg(method, data):
    return requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}",
        json=data
    ).json()

def send(chat, text, kb=None):
    return tg("sendMessage", {
        "chat_id": chat,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": kb
    })

def edit(chat, msg_id, text, kb=None):
    return tg("editMessageText", {
        "chat_id": chat,
        "message_id": msg_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": kb
    })

def answer(id, text):
    tg("answerCallbackQuery", {
        "callback_query_id": id,
        "text": text
    })

# ================= FEDEX =================
def get_loads():
    payload = {
        "pickupFromDate": datetime.now().strftime("%Y-%m-%d"),
        "searchType": "lanes",
        "size": 50,
        "currentUserIds": [USER_ID],
        "tenantIds": [TENANT_ID],
        "pickup": {"type": "anywhere"},
        "dropoff": {"type": "anywhere"},
        "truckType": ["Any"],
        "companyIds": [COMPANY_ID],
        "includeMyBids": True,
        "includeNewOffers": True,
        "calculateDeadheads": True
    }

    r = requests.post(URL, json=payload, headers=HEADERS)
    print("STATUS:", r.status_code)

    if r.status_code != 200:
        return []

    return r.json().get("data", {}).get("bidding", [])

# ================= HELPERS =================
def sort_offers(offers):
    return sorted(offers, key=lambda x: float(str(x.get("price", 0)).replace(",", "")))

def winner(offers):
    for o in offers:
        if "accepted" in str(o.get("status")).lower():
            return o
    return None

def build_text(load):
    offers = sort_offers(load.get("offers", []))
    lowest = offers[0]["price"] if offers else "N/A"
    win = winner(offers)

    return f"""🚛 <b>LOAD</b>

ID: {load.get("longId")}
Price: {load.get("price")}
Offers: {len(offers)}
Lowest: {lowest}
Winner: {win.get("price") if win else "None"}"""

def build_offers(load):
    offers = sort_offers(load.get("offers", []))

    if not offers:
        return "❌ No offers"

    txt = "📊 <b>OFFERS</b>\n\n"

    for i, o in enumerate(offers, 1):
        user = o.get("createdByUser", {})
        txt += f"{i}. {o.get('price')} | {user.get('firstName')} {user.get('lastName')}\n"

    return txt

def keyboard(load):
    return {
        "inline_keyboard": [[
            {"text": "📊 View Offers", "callback_data": f"offers|{load.get('longId')}"}
        ]]
    }

# ================= CORE =================
def sync():
    loads = get_loads()

    for l in loads:
        id = l.get("longId")
        STATE["cache"][id] = l

        text = build_text(l)

        if id not in STATE["posted"]:
            r = send(CHANNEL_ID, text, keyboard(l))
            if r.get("ok"):
                STATE["posted"][id] = r["result"]["message_id"]
        else:
            edit(CHANNEL_ID, STATE["posted"][id], text, keyboard(l))

def handle_callback(cb):
    data = cb["data"]
    cid = cb["id"]

    if "|" not in data:
        return

    action, id = data.split("|")

    load = STATE["cache"].get(id)

    if not load:
        return

    if action == "offers":
        answer(cid, "Yuborildi")
        send(OFFERS_GROUP_ID, build_offers(load))

def updates():
    r = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={STATE['offset']}"
    ).json()

    for u in r.get("result", []):
        STATE["offset"] = u["update_id"] + 1

        if "callback_query" in u:
            handle_callback(u["callback_query"])

# ================= RUN =================
print("BOT STARTED")

while True:
    try:
        sync()
        updates()
    except Exception as e:
        print("ERR:", e)

