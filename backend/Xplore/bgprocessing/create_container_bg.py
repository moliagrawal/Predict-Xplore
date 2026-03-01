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
from predictor.models import Task, Container

def process_container_creation(task_id, zip_path, name, description, allowed_users, created_by_id):
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
            print(f"Failed to remove temp zip file: {e}")

        # Validate required files
        required_files = ["inference.py", "requirements.txt", "model.pth", "dockerfile"]
        missing_files = []
        for rf in required_files:
            file_path = os.path.join(upload_dir, rf)
            if not os.path.exists(file_path):
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

        # Cleanup Build Dir
        shutil.rmtree(upload_dir, ignore_errors=True)
        
        # Save Container Entry details in DB
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=created_by_id)
        Container.objects.create(
            name=name,
            description=description,
            allowed_users=allowed_users,
            created_by=user
        )

        # Complete Task
        log("Task Processing Complete! Container stored in database.")
        task.status = 'Completed'
        task.end_time = datetime.now()
        task.save()
        
    except Exception as e:
        error_msg = f"Error in container bg creation processing: {e}"
        print(error_msg)
        try:
            log(error_msg)
            task = Task.objects.get(task_id=task_id)
            task.status = 'Failed'
            task.end_time = datetime.now()
            task.save()
        except:
            pass

if __name__ == "__main__":
    import json
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
        payload_str = sys.argv[2]
        payload = json.loads(payload_str)
        
        process_container_creation(
            task_id, 
            payload['zip_path'], 
            payload['name'], 
            payload['description'], 
            payload['allowed_users'], 
            payload['created_by_id']
        )
    else:
        print("Required arguments not provided.")
