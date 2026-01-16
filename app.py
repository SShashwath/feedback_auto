from flask import Flask, request, jsonify
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import queue
import uuid
import time

# Import the core automation logic
from feedback_automation import run_feedback_automation

app = Flask(__name__)

# IMPORTANT: Configured CORS to allow requests from your Vercel frontend.
CORS(app, resources={r"/api/*": {"origins": "https://easy-college.vercel.app"}})

# --- QUEUE SYSTEM ---
# Single worker to prevent memory issues on Render's free tier
executor = ThreadPoolExecutor(max_workers=1)

# In-memory storage for task statuses.
tasks = {}
tasks_lock = Lock()

# Track queue position
pending_queue = []  # List of task_ids in order
queue_lock = Lock()


def cleanup_old_tasks():
    """Remove completed tasks older than 5 minutes to prevent memory leaks."""
    current_time = time.time()
    with tasks_lock:
        to_delete = [
            tid for tid, task in tasks.items()
            if task.get("completed_at") and (current_time - task["completed_at"]) > 300
        ]
        for tid in to_delete:
            del tasks[tid]


@app.route("/api/run-feedback", methods=["POST"])
def start_feedback_task():
    """
    API endpoint to start a new feedback automation task.
    Tasks are queued and processed one at a time to prevent memory issues.
    """
    # Clean up old tasks periodically
    cleanup_old_tasks()

    data = request.get_json()
    if not all(key in data for key in ['rollno', 'password', 'feedback_type']):
        return jsonify({"error": "Missing required data: rollno, password, and feedback_type"}), 400

    rollno = data['rollno']
    password = data['password']
    feedback_type = int(data['feedback_type'])
    
    # Generate a unique ID for this task
    task_id = str(uuid.uuid4())
    
    # Create a queue to get progress updates from the Selenium script
    status_queue = queue.Queue()
    
    # Add to pending queue to track position
    with queue_lock:
        pending_queue.append(task_id)
        queue_position = len(pending_queue)
    
    with tasks_lock:
        tasks[task_id] = {
            "status": "queued",
            "progress": 0,
            "message": f"Queued. Position in queue: {queue_position}",
            "queue": status_queue,
            "queue_position": queue_position,
            "created_at": time.time(),
            "completed_at": None
        }

    def automation_task():
        """Wrapper that runs the automation and handles cleanup."""
        try:
            # Update status to running
            with tasks_lock:
                if task_id in tasks:
                    tasks[task_id]["status"] = "running"
                    tasks[task_id]["message"] = "Starting automation..."
            
            # Remove from pending queue since we're now running
            with queue_lock:
                if task_id in pending_queue:
                    pending_queue.remove(task_id)
                # Update queue positions for remaining tasks
                for i, tid in enumerate(pending_queue):
                    with tasks_lock:
                        if tid in tasks:
                            tasks[tid]["queue_position"] = i + 1
                            tasks[tid]["message"] = f"Queued. Position in queue: {i + 1}"
            
            # Run the actual automation
            run_feedback_automation(feedback_type, rollno, password, status_queue)
            
        except Exception as e:
            status_queue.put({"status": "error", "message": f"A critical error occurred: {e}"})
        finally:
            # Mark completion time for cleanup
            with tasks_lock:
                if task_id in tasks:
                    tasks[task_id]["completed_at"] = time.time()

    # Submit to the executor (will queue if another task is running)
    executor.submit(automation_task)

    return jsonify({
        "status": "Task queued successfully",
        "task_id": task_id,
        "queue_position": queue_position
    }), 202


@app.route("/api/status/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """
    API endpoint for the client to poll for status updates.
    Includes queue position for waiting tasks.
    """
    with tasks_lock:
        if task_id not in tasks:
            return jsonify({"error": "Invalid task ID"}), 404
        task = tasks[task_id]
    
    try:
        # Check for the latest update from the queue without blocking
        update = task["queue"].get_nowait()
        with tasks_lock:
            task["status"] = update["status"]
            if "progress" in update:
                task["progress"] = update["progress"]
            if "message" in update:
                task["message"] = update["message"]

    except queue.Empty:
        # No new update, return last known status
        pass

    # Get current queue position for queued tasks
    queue_position = 0
    if task["status"] == "queued":
        with queue_lock:
            if task_id in pending_queue:
                queue_position = pending_queue.index(task_id) + 1
                with tasks_lock:
                    task["message"] = f"Queued. Position in queue: {queue_position}"

    return jsonify({
        "task_id": task_id,
        "status": task["status"],
        "progress": task.get("progress", 0),
        "message": task.get("message", ""),
        "queue_position": queue_position
    })


@app.route("/api/queue-info", methods=["GET"])
def get_queue_info():
    """Get current queue status - how many tasks are waiting."""
    with queue_lock:
        queue_length = len(pending_queue)
    
    return jsonify({
        "queue_length": queue_length,
        "max_concurrent": 1,
        "estimated_wait_minutes": queue_length * 2  # Rough estimate: ~2 min per task
    })


if __name__ == "__main__":
    # Use 0.0.0.0 to make it accessible within the Docker container
    app.run(host="0.0.0.0", port=8080)