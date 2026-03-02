from django.apps import AppConfig


class PredictorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'predictor'

    def ready(self):
        import sys
        # the ready() method gets called multiple times, sometimes for migrations.
        # we only want to interact with the database if we are running the server
        if 'runserver' not in sys.argv and 'gunicorn' not in sys.argv[0]:
            return

        import threading

        def check_orphaned_tasks():
            try:
                import time
                time.sleep(3) # Wait for Django apps to finish loading to avoid RuntimeWarning
                from .models import Task
                import os
                # Identify orphaned tasks
                tasks_to_check = list(Task.objects.filter(status__in=['Pending', 'Running']))
                for task in tasks_to_check:
                    if task.subprocess_id:
                        try:
                            # sending signal 0 checks if the process exists
                            os.kill(task.subprocess_id, 0)
                        except ProcessLookupError:
                            # Process died unexpectedly
                            task.status = 'Failed'
                            task.save()
                            target_log = task.log_file
                            
                            if target_log and os.path.exists(target_log):
                                with open(target_log, 'a') as f:
                                    f.write('\n[System] Server rebooted. Task failed: Process died unexpectedly.\n')
            except Exception:
                pass

        # Run the check in a separate thread so it doesn't execute during app init lifecycle directly
        threading.Thread(target=check_orphaned_tasks, daemon=True).start()
