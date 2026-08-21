import requests
import json
import os
import sys

def deploy_to_render(api_key, service_name="fx-downloader"):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Get user / owner info
    print("[*] Verifying Render API Key...")
    res = requests.get("https://api.render.com/v1/owners", headers=headers)
    if res.status_code != 200:
        print(f"[-] Error verifying key: {res.text}")
        return False
        
    owners = res.json()
    if not owners:
        print("[-] No owner found for this account.")
        return False
        
    owner_id = owners[0]['owner']['id']
    print(f"[+] Connected to Render Account (Owner ID: {owner_id})")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        deploy_to_render(sys.argv[1])
    else:
        print("Usage: python deploy_render.py <RENDER_API_KEY>")
