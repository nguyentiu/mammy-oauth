from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
import json
import os

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
@app.get("/oauth/callback")
def oauth_callback(request: Request):
    auth_code = request.query_params.get("auth_code")
    if not auth_code:
        return {"error": "No auth_code received"}

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
        with open(TOKEN_FILE, "w") as f:
            json.dump(data["data"], f, indent=2)

    return data

# ==== HIỂN THỊ CHIẾN DỊCH DẠNG HTML BẢNG ====
@app.get("/campaigns", response_class=HTMLResponse)
def get_all_campaigns(
    request: Request,
    access_token: str = Query(default=None),
    advertiser_id: str = Query(default=None)
):
    if not access_token or not advertiser_id:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                token_data = json.load(f)
                access_token = access_token or token_data.get("access_token")
                advertiser_id = advertiser_id or token_data.get("advertiser_id")

    if not access_token or not advertiser_id:
        return HTMLResponse("<h3>⚠️ Thiếu access_token hoặc advertiser_id</h3>", status_code=400)

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
