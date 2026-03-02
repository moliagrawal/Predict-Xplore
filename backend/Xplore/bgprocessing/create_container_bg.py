import sys
import os
import zipfile
import shutil
import subprocess
import django
from datetime import datetime

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xplore.settings')
django.setup()

from django.conf import settings
from predictor.models import Task, Container, ContainerGithub

def download_github_folder(api_base, default_branch, folder_path, dest_dir, log_func):
    import requests
    
    # Get the tree for the folder
    folder = folder_path.strip("/")
    
    # Get the commit hash for the root branch to find our folder's hash later
    commit_resp = requests.get(f"{api_base}/commits/{default_branch}", timeout=10)
    if commit_resp.status_code != 200:
        raise Exception("Failed to fetch default branch commit info")
    root_tree_sha = commit_resp.json()["commit"]["tree"]["sha"]
    folder_hash = root_tree_sha
    
    if folder:
        # We need to find the folder's SHA for storing in ContainerGithub
        parent_dir = os.path.dirname(folder)
        basename = os.path.basename(folder)
        
        if parent_dir == "":
            tree_url = f"{api_base}/git/trees/{default_branch}"
        else:
            tree_url = f"{api_base}/contents/{parent_dir}?ref={default_branch}"
            
        parent_resp = requests.get(tree_url, timeout=10)
        parent_data = parent_resp.json()
        items = parent_data.get("tree", parent_data) if isinstance(parent_data, dict) else parent_data
        
        for item in items:
            if item.get("name") == basename or item.get("path", "").endswith(basename):
                folder_hash = item.get("sha")
                break
                
        # Now fetch the target folder recursively
        tree_resp = requests.get(f"{api_base}/git/trees/{folder_hash}?recursive=1", timeout=10)
    else:
        # Fetch root folder tree recursively
        tree_resp = requests.get(f"{api_base}/git/trees/{default_branch}?recursive=1", timeout=10)
        
    if tree_resp.status_code != 200:
        raise Exception(f"Failed to fetch tree for {folder if folder else 'root'}")
        
    tree_data = tree_resp.json().get("tree", [])
    files = [item for item in tree_data if item["type"] == "blob"]
    
    log_func(f"Found {len(files)} files to download from GitHub.")
    
    for item in files:
        file_path = item["path"]
        download_url = f"https://raw.githubusercontent.com/{api_base.split('repos/')[1]}/{default_branch}/{folder + '/' if folder else ''}{file_path}"
        
        target_path = os.path.join(dest_dir, file_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        resp = requests.get(download_url, timeout=10)
        if resp.status_code == 200:
            with open(target_path, "wb") as f:
                f.write(resp.content)
        else:
            raise Exception(f"Failed to download file {file_path}")
            
    return folder_hash

def process_container_creation(task_id, payload):
    name = payload.get('name')
    description = payload.get('description')
    allowed_users = payload.get('allowed_users', [])
    created_by_id = payload.get('created_by_id')
    zip_path = payload.get('zip_path')
    repo_url = payload.get('repo_url')
    github_folder = payload.get('github_folder', '')
    
    log_dir = os.path.join(settings.MEDIA_ROOT, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{task_id}.log")
    
    def log(message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = f"[{timestamp}] {message}\n"
        print(record, end='')
        with open(log_path, "a") as f:
            f.write(record)

    try:
        task = Task.objects.get(task_id=task_id)
        task.status = 'Running'
        task.subprocess_id = os.getpid()
        task.log_file = log_path
        task.save()
        
        log(f"Task started. Processing Container: {name}")

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'containers', 'uploads', name)
        os.makedirs(upload_dir, exist_ok=True)
        
        folder_hash = None
        
        if zip_path:
            log(f"Extracting zip file: {zip_path}")
            # Extract files properly
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                members = [m for m in zip_ref.namelist() if not m.endswith("/")]
                if not members:
                    raise Exception("Empty zip file")
                
                root_folders = set(m.split("/")[0] for m in members if "/" in m)
                
                if len(root_folders) == 1:
                    root = list(root_folders)[0]
                    for member in members:
                        if member.startswith(root + "/"):
                            relative_path = member[len(root) + 1:]
                        else:
                            relative_path = member
                        if not relative_path:
                            continue
                        target_path = os.path.join(upload_dir, relative_path)
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with open(target_path, "wb") as f:
                            f.write(zip_ref.read(member))
                else:
                    zip_ref.extractall(upload_dir)

            # Remove the zip file after extraction
            try:
                os.remove(zip_path)
            except Exception as e:
                log(f"Warning: Failed to remove temp zip file: {e}")
                
        elif repo_url:
            log(f"Fetching from GitHub: {repo_url} / {github_folder}")
            import re, requests
            pattern = r'https://github\.com/([^/]+)/([^/]+)'
            match = re.match(pattern, repo_url)
            if not match:
                raise Exception("Invalid GitHub URL format")
            user, repo = match.groups()
            
            api_base = f"https://api.github.com/repos/{user}/{repo}"
            repo_info_resp = requests.get(api_base, timeout=10)
            if repo_info_resp.status_code != 200:
                raise Exception("Failed to fetch repository information from GitHub")
                
            default_branch = repo_info_resp.json().get("default_branch", "main")
            
            folder_hash = download_github_folder(api_base, default_branch, github_folder, upload_dir, log)
            log(f"Successfully downloaded GitHub folder. Folder SHA: {folder_hash}")
        else:
            raise Exception("No zip file or GitHub repo provided")

        # Validate required files
        # Check files case-insensitively for Dockerfile
        files_in_dir = [f.lower() for f in os.listdir(upload_dir)]
        required_files = ["inference.py", "requirements.txt", "model.pth", "dockerfile"]
        missing_files = []
        for rf in required_files:
            if rf.lower() not in files_in_dir:
                missing_files.append(rf)
                
        if missing_files:
            raise Exception(f"Missing required files: {missing_files}")

        # Build Container
        image_name = f"user_{name}:latest"
        log("Starting Docker build...")
        with open(log_path, "a") as f:
            result = subprocess.run(["docker", "build", "-t", image_name, upload_dir], stdout=f, stderr=subprocess.STDOUT)
            if result.returncode != 0:
                log("Docker build failed.")
                raise Exception(f"Docker build failed. Check logs for details.")
        
        log(f"Container built successfully: {image_name}")

        # Cleanup Build Dir if zip
        if zip_path:
            shutil.rmtree(upload_dir, ignore_errors=True)
        # If github, we keep the directory so that the patch script can use it later for reference/building
        
        # Save Container Entry details in DB
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=created_by_id)
        
        container = Container.objects.create(
            name=name,
            description=description,
            allowed_users=allowed_users,
            created_by=user
        )
        
        if repo_url and folder_hash:
            ContainerGithub.objects.create(
                container=container,
                repo_url=repo_url,
                github_folder=github_folder,
                folder_hash=folder_hash
            )

        # Complete Task
        log("Task Processing Complete! Container stored in database.")
        task.status = 'Completed'
        task.save()
        
    except Exception as e:
        error_msg = f"Error in container bg creation processing: {e}"
        print(error_msg)
        try:
            log(error_msg)
            task = Task.objects.get(task_id=task_id)
            task.status = 'Failed'
            task.save()
        except:
            pass

if __name__ == "__main__":
    import json
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
        payload_str = sys.argv[2]
        payload = json.loads(payload_str)
        process_container_creation(task_id, payload)
    else:
        print("Required arguments not provided.")
