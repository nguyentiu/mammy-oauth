from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
import json
import os
import time

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# ==== CẤU HÌNH APP ====
APP_ID = "7506424810470277121"
APP_SECRET = "08b8c695d62828af9e2d6dc42f177f99159a9e1e"
REDIRECT_URI = "https://mammy-oauth.onrender.com/oauth/callback"
TOKEN_FILE = "token.json"

# ==== LẤY LINK OAUTH TIKTOK ====
@app.get("/")
def get_auth_url():
    scope = "ads.read,report.read"
    auth_url = (
        f"https://business-api.tiktok.com/portal/auth?"
        f"app_id={APP_ID}&state=test123&redirect_uri={REDIRECT_URI}&scope={scope}"
    )
    return {"auth_url": auth_url}

# ==== CALLBACK: LƯU TOKEN VÀO FILE ====
@app.get("/oauth/callback", response_class=HTMLResponse)
def oauth_callback(request: Request):
    auth_code = request.query_params.get("auth_code")
    if not auth_code:
        return "<h3>❌ Không có auth_code</h3>"

    token_url = "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/"
    payload = {
        "app_id": APP_ID,
        "secret": APP_SECRET,
        "auth_code": auth_code,
        "grant_type": "authorization_code"
    }
    res = requests.post(token_url, json=payload)
    data = res.json()

    if data.get("code") == 0:
        d = data["data"]
        d["advertiser_id"] = d["advertiser_ids"][0]
        d["expires_at"] = int(time.time()) + d.get("expires_in", 3600)
        with open(TOKEN_FILE, "w") as f:
            json.dump(d, f, indent=2)
        return f"""
        <h2>✅ Lấy token thành công</h2>
        <ul>
            <li><b>Access Token:</b> {d['access_token']}</li>
            <li><b>Advertiser ID:</b> {d['advertiser_id']}</li>
        </ul>
        <p>Truy cập: 
        <a href='/campaigns'>Xem campaigns</a>
        </p>
        """
    return f"<pre>{data}</pre>"

# ==== HÀM TỰ ĐỘNG REFRESH TOKEN ====
def get_valid_token():
    if not os.path.exists(TOKEN_FILE):
        return None

    with open(TOKEN_FILE, "r") as f:
        token_data = json.load(f)

    if token_data.get("expires_at", 0) > time.time():
        return token_data  # still valid

    # Token expired → refresh
    payload = {
        "app_id": APP_ID,
        "secret": APP_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": token_data["refresh_token"]
    }
    res = requests.post("https://business-api.tiktok.com/open_api/v1.3/oauth2/refresh_token/", json=payload)
    data = res.json()
    if data.get("code") == 0:
        new_data = data["data"]
        new_data["advertiser_id"] = token_data["advertiser_id"]
        new_data["expires_at"] = int(time.time()) + new_data.get("expires_in", 3600)
        with open(TOKEN_FILE, "w") as f:
            json.dump(new_data, f, indent=2)
        return new_data
    return None

# ==== HIỂN THỊ CHIẾN DỊCH DẠNG HTML BẢNG ====
@app.get("/campaigns", response_class=HTMLResponse)
def get_campaigns(request: Request):
    token_data = get_valid_token()
    if not token_data:
        return HTMLResponse("<h3>⚠️ Không có token hợp lệ, vui lòng auth lại</h3>", status_code=403)

    access_token = token_data["access_token"]
    advertiser_id = token_data["advertiser_id"]

    url = "https://business-api.tiktok.com/open_api/v1.3/campaign/get/"
    headers = {"Access-Token": access_token}

    all_campaigns = []
    page = 1
    while True:
        params = {
            "advertiser_id": advertiser_id,
            "page": page,
            "page_size": 50
        }
        res = requests.get(url, headers=headers, params=params)
        if res.status_code != 200:
            return HTMLResponse(f"<h3>❌ Lỗi TikTok API</h3><pre>{res.text}</pre>", status_code=500)

        data = res.json()
        campaigns = data.get("data", {}).get("list", [])
        all_campaigns.extend(campaigns)

        page_info = data.get("data", {}).get("page_info", {})
        if page >= page_info.get("total_page", 1):
            break
        page += 1

    return templates.TemplateResponse("campaigns.html", {
        "request": request,
        "campaigns": all_campaigns,
        "advertiser_id": advertiser_id
    })
