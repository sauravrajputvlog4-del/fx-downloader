import os
import sys
from huggingface_hub import HfApi

def deploy(token, repo_name="fx-downloader"):
    api = HfApi(token=token)
    user = api.whoami()['name']
    repo_id = f"{user}/{repo_name}"
    
    print(f"[*] Creating Free 24/7 Cloud Space: {repo_id}...")
    try:
        api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="docker", private=False)
        print("[+] Space created successfully!")
    except Exception as e:
        print(f"[i] Space might already exist: {e}")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    print("[*] Uploading app files to Cloud Server...")
    
    # Upload essential cloud files
    for filename in ["app.py", "Dockerfile", "requirements.txt", "Procfile"]:
        fpath = os.path.join(script_dir, filename)
        if os.path.exists(fpath):
            api.upload_file(path_or_fileobj=fpath, path_in_repo=filename, repo_id=repo_id, repo_type="space")
            print(f"  - Uploaded {filename}")
            
    # Upload directories
    for foldername in ["templates", "static"]:
        dpath = os.path.join(script_dir, foldername)
        if os.path.exists(dpath):
            api.upload_folder(folder_path=dpath, path_in_repo=foldername, repo_id=repo_id, repo_type="space")
            print(f"  - Uploaded {foldername}/")

    space_url = f"https://{user.lower()}-{repo_name.lower()}.hf.space"
    print("\n=======================================================")
    print(f"🎉 24/7 PERMANENT LINK IS READY: {space_url}")
    print("=======================================================")
    return space_url

if __name__ == "__main__":
    if len(sys.argv) > 1:
        deploy(sys.argv[1])
    else:
        t = input("Enter HuggingFace Token: ").strip()
        if t:
            deploy(t)
