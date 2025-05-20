from fastapi import FastAPI, Request
import requests

app = FastAPI()

# === THÔNG TIN APP ===
APP_ID = "7506424810470277121"
APP_SECRET = "08b8c695d62828af9e2d6dc42f177f99159a9e1e"
REDIRECT_URI = "https://mammy-oauth.onrender.com/oauth/callback"  # Đúng route đã đăng ký

@app.get("/")
def get_auth_url():
    scope = "ads.read,report.read"
    auth_url = (
        f"https://business-api.tiktok.com/portal/auth?"
        f"app_id={APP_ID}&state=test123&redirect_uri={REDIRECT_URI}&scope={scope}"
    )
    return {"auth_url": auth_url}

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
    try:
        return res.json()
    except:
        return {"error": "Invalid response", "raw": res.text}

@app.get("/campaigns/{advertiser_id}")
def get_all_campaigns(advertiser_id: str):
    access_token = "8ef7508b6aaea9361bdedf663a3f91df19b2f616"  # 👉 token bạn đã lấy
    url = "https://business-api.tiktok.com/open_api/v1.3/campaign/get/"

    headers = {
        "Access-Token": access_token
    }

    # TikTok API phân trang nên cần gọi nhiều lần
    all_campaigns = []
    page = 1
    page_size = 50

    while True:
        params = {
            "advertiser_id": advertiser_id,
            "page": page,
            "page_size": page_size
        }

        res = requests.get(url, headers=headers, params=params)
        if res.status_code != 200:
            return {"error": "TikTok API error", "status_code": res.status_code, "raw": res.text}

        data = res.json()
        campaigns = data.get("data", {}).get("list", [])

        all_campaigns.extend(campaigns)

        # Kiểm tra có trang tiếp không
        pagination = data.get("data", {}).get("page_info", {})
        if pagination.get("total_page", 1) <= page:
            break

        page += 1

    return {
        "total": len(all_campaigns),
        "campaigns": all_campaigns
    }
