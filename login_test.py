#!/usr/bin/env python3

import requests
import json
import time
import os

# === 基本設定 ===
tenant_id = ""
client_id = ""
client_secret = ""
token_file = "token.json"

def get_token():
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default"
    }

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        token_data = response.json()
        token_data["expires_at"] = int(time.time()) + token_data["expires_in"]
        with open(token_file, "w") as f:
            json.dump(token_data, f)
        print("✅ Token 已成功取得並儲存！")
        return token_data["access_token"]
    else:
        print("❌ 無法取得 token：", response.text)
        return None

def load_token():
    if not os.path.exists(token_file):
        return get_token()

    with open(token_file, "r") as f:
        token_data = json.load(f)

    if int(time.time()) >= token_data.get("expires_at", 0):
        print("⚠ Token 已過期，自動更新中...")
        return get_token()
    
    return token_data["access_token"]

# === 測試呼叫 API ===
def call_graph_api():
    access_token = load_token()
    if not access_token:
        return

    print("access_token : ", access_token)

    url = "https://graph.microsoft.com/v1.0/users?$select=displayName,userPrincipalName,id"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        users = response.json().get("value", [])
        for user in users:
            print(f"{user['displayName']} ({user['userPrincipalName']})")
    else:
        print("❌ API 呼叫失敗：", response.text)

# 執行
if __name__ == "__main__":
    call_graph_api()
