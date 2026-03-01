import sys
import os
import time
import django
from datetime import datetime

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xplore.settings')
django.setup()

from predictor.models import Task

def run_test_bg(task_id):
    try:
        task = Task.objects.get(task_id=task_id)
        task.status = 'Running'
        task.subprocess_id = os.getpid()
        task.save()
        
        # Simulate processing time
        time.sleep(10)
        
        task.status = 'Completed'
        task.end_time = datetime.now()
        task.save()
        
    except Exception as e:
        print(f"Error in background task: {e}")
        try:
            task = Task.objects.get(task_id=task_id)
            task.status = 'Failed'
            task.end_time = datetime.now()
            task.save()
        except:
            pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
        run_test_bg(task_id)
    else:
        print("Please provide a task ID.")
