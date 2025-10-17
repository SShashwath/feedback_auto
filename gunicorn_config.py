import multiprocessing
import os
import signal
import sys
from rq import Worker
from worker import feedback_queue, redis_conn

# Worker process reference
worker_process = None


def start_rq_worker():
    """
    Function to run RQ worker in a separate process.
    This processes jobs from the Redis queue.
    """
    try:
        # Create worker with burst=False to keep it running
        worker = Worker(
            [feedback_queue],
            connection=redis_conn,
            name=f'worker-{os.getpid()}'
        )
        
        print(f"[RQ Worker] Started worker with PID {os.getpid()}")
        
        # Start working - this blocks until the worker is stopped
        worker.work(with_scheduler=False, logging_level='INFO')
        
    except Exception as e:
        print(f"[RQ Worker] Error: {e}")
        sys.exit(1)


def on_starting(server):
    """
    Called just before the master process is initialized.
    We start the RQ worker here as a separate process.
    """
    global worker_process
    
    print("[Gunicorn] Starting RQ worker process...")
    
    # Start RQ worker in a daemon process
    worker_process = multiprocessing.Process(
        target=start_rq_worker,
        daemon=True
    )
    worker_process.start()
    
    print(f"[Gunicorn] RQ worker started with PID {worker_process.pid}")


def worker_int(worker):
    """
    Called when a worker receives the INT or QUIT signal.
    """
    print(f"[Gunicorn] Worker {worker.pid} received INT signal")


def on_exit(server):
    """
    Called just before the master process exits.
    Clean up the RQ worker process.
    """
    global worker_process
    
    if worker_process and worker_process.is_alive():
        print(f"[Gunicorn] Terminating RQ worker (PID {worker_process.pid})...")
        worker_process.terminate()
        worker_process.join(timeout=5)
        
        if worker_process.is_alive():
            print(f"[Gunicorn] Force killing RQ worker...")
            worker_process.kill()


# Gunicorn configuration
bind = "0.0.0.0:8080"
workers = 1  # Single worker to save memory on 512MB
threads = 3  # Handle 3 concurrent API requests
worker_class = "gthread"
timeout = 300
keepalive = 5

# Memory optimization
max_requests = 200  # Recycle worker after 200 requests to prevent leaks
max_requests_jitter = 50
preload_app = True  # Share memory between workers

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
