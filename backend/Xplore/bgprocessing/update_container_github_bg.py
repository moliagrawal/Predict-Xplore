import sys
import os
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
    
    folder = folder_path.strip("/")
    
    commit_resp = requests.get(f"{api_base}/commits/{default_branch}", timeout=10)
    if commit_resp.status_code != 200:
        raise Exception("Failed to fetch default branch commit info")
    root_tree_sha = commit_resp.json()["commit"]["tree"]["sha"]
    folder_hash = root_tree_sha
    
    if folder:
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
                
        tree_resp = requests.get(f"{api_base}/git/trees/{folder_hash}?recursive=1", timeout=10)
    else:
        tree_resp = requests.get(f"{api_base}/git/trees/{default_branch}?recursive=1", timeout=10)
        
    if tree_resp.status_code != 200:
        raise Exception(f"Failed to fetch tree for {folder if folder else 'root'}")
        
    tree_data = tree_resp.json().get("tree", [])
    files = [item for item in tree_data if item["type"] == "blob"]
    
    log_func(f"Found {len(files)} files in remote GitHub folder.")
    
    changed_files = []
    
    for item in files:
        file_path = item["path"]
        download_url = f"https://raw.githubusercontent.com/{api_base.split('repos/')[1]}/{default_branch}/{folder + '/' if folder else ''}{file_path}"
        
        target_path = os.path.join(dest_dir, file_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        resp = requests.get(download_url, timeout=10)
        if resp.status_code == 200:
            new_content = resp.content
            
            is_changed = True
            if os.path.exists(target_path):
                with open(target_path, "rb") as f:
                    old_content = f.read()
                if old_content == new_content:
                    is_changed = False
            
            if is_changed:
                with open(target_path, "wb") as f:
                    f.write(new_content)
                changed_files.append(file_path)
        else:
            raise Exception(f"Failed to download file {file_path}")
            
    return folder_hash, changed_files


def process_container_update(task_id, payload):
    container_id = payload.get('container_id')
    target_hash = payload.get('target_hash')
    
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
        
        container = Container.objects.get(id=container_id)
        gh_info = container.github_info
        
        log(f"Task started. Updating Container: {container.name} from GitHub")

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'containers', 'uploads', container.name)
        os.makedirs(upload_dir, exist_ok=True)
        
        import re, requests
        pattern = r'https://github\.com/([^/]+)/([^/]+)'
        match = re.match(pattern, gh_info.repo_url)
        if not match:
            raise Exception("Invalid GitHub URL format stored in DB")
        user, repo = match.groups()
        
        api_base = f"https://api.github.com/repos/{user}/{repo}"
        repo_info_resp = requests.get(api_base, timeout=10)
        if repo_info_resp.status_code != 200:
            raise Exception("Failed to fetch repository information from GitHub")
            
        default_branch = repo_info_resp.json().get("default_branch", "main")
        
        folder_hash, changed_files = download_github_folder(api_base, default_branch, gh_info.github_folder, upload_dir, log)
        
        if not changed_files:
            log("No files were actually changed locally despite hash difference. Update complete.")
        else:
            log(f"The following {len(changed_files)} files changed:")
            for cf in changed_files:
                log(f" - {cf}")
            
            # Check if dockerfile changed
            dockerfile_changed = any(f.lower() == 'dockerfile' for f in changed_files)
            requirements_changed = any(f.lower() == 'requirements.txt' for f in changed_files)
            
            image_name = f"user_{container.name}:latest"
            
            if dockerfile_changed:
                log("Dockerfile was modified. Falling back to a full 'docker build' to ensure layer correctness...")
                with open(log_path, "a") as f:
                    result = subprocess.run(["docker", "build", "-t", image_name, upload_dir], stdout=f, stderr=subprocess.STDOUT)
                    if result.returncode != 0:
                        raise Exception("Docker rebuild failed. Check logs.")
                log(f"Full Docker build completed successfully.")
            else:
                log("Dockerfile not changed. Proceeding with dynamic container patching (docker cp + commit)...")
                
                # Find container WorkingDir
                workdir_result = subprocess.run(["docker", "inspect", "-f", "{{.Config.WorkingDir}}", image_name], capture_output=True, text=True)
                workdir = workdir_result.stdout.strip()
                if not workdir:
                    workdir = "/"
                
                log(f"Extracted image WorkDir: {workdir}")
                
                temp_container = f"temp_updater_{task_id}"
                
                # Spin up a daemonized container with simple entrypoint to keep it alive
                log(f"Spinning up temporary container {temp_container}...")
                subprocess.run([
                    "docker", "run", "-d", "--name", temp_container, "--entrypoint", "sleep", image_name, "3600"
                ], check=True, capture_output=True)
                
                try:
                    for cf in changed_files:
                        local_target = os.path.join(upload_dir, cf)
                        docker_target = f"{workdir}/{cf}"
                        
                        log(f"Copying {cf} into container...")
                        # Ensure parent directory exists inside the container
                        dest_dir = os.path.dirname(docker_target)
                        subprocess.run(["docker", "exec", temp_container, "mkdir", "-p", dest_dir], check=False, capture_output=True)
                        
                        subprocess.run(["docker", "cp", local_target, f"{temp_container}:{docker_target}"], check=True, capture_output=True)
                        
                    if requirements_changed:
                        log("requirements.txt changed! Running 'pip install -r requirements.txt' inside container...")
                        with open(log_path, "a") as f:
                            res = subprocess.run([
                                "docker", "exec", temp_container, "pip", "install", "-r", f"{workdir}/requirements.txt"
                            ], stdout=f, stderr=subprocess.STDOUT)
                            if res.returncode != 0:
                                raise Exception("pip install failed inside the container.")
                    
                    log("Committing patched container back to image...")
                    subprocess.run(["docker", "commit", temp_container, image_name], check=True, capture_output=True)
                    log("Patch committed successfully.")
                finally:
                    log("Cleaning up temporary container...")
                    subprocess.run(["docker", "rm", "-f", temp_container], capture_output=True)
        
        # Update DB hash
        gh_info.folder_hash = folder_hash
        gh_info.save()

        # Complete Task
        log("Update Task Processing Complete!")
        task.status = 'Completed'
        task.save()
        
    except Exception as e:
        error_msg = f"Error in container bg update processing: {e}"
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
        process_container_update(task_id, payload)
    else:
        print("Required arguments not provided.")
