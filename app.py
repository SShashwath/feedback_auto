from flask import Flask, request, jsonify
from flask_cors import CORS
from threading import Thread
import queue
import uuid

# Import the core automation logic
from feedback_automation import run_feedback_automation

app = Flask(__name__)

# IMPORTANT: Configured CORS to allow requests from your Vercel frontend.
CORS(app, resources={r"/api/*": {"origins": "https://easy-college.vercel.app"}})


# In-memory storage for task statuses.
# For a larger application, you would replace this with a database like Redis.
tasks = {}

@app.route("/api/run-feedback", methods=["POST"])
def start_feedback_task():
    """
    API endpoint to start a new feedback automation task.
    It expects 'rollno', 'password', and 'feedback_type' in the JSON body.
    """
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
    
    tasks[task_id] = {"status": "starting", "progress": 0, "message": "Task is initializing...", "queue": status_queue}

    # Define the target function for our background thread
    def automation_task():
        try:
            run_feedback_automation(feedback_type, rollno, password, status_queue)
        except Exception as e:
            # If the script fails catastrophically, put an error in the queue
            status_queue.put({"status": "error", "message": f"A critical error occurred: {e}"})

    # Start the Selenium task in a background thread
    thread = Thread(target=automation_task)
    thread.daemon = True  # Allows main app to exit even if threads are running
    thread.start()

    # Immediately return the task_id so the client can start polling for status
    return jsonify({"status": "Task started successfully", "task_id": task_id}), 202

@app.route("/api/status/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """
    API endpoint for the client to poll for status updates.
    """
    if task_id not in tasks:
        return jsonify({"error": "Invalid task ID"}), 404

    task = tasks[task_id]
    
    try:
        # Check for the latest update from the queue without blocking
        update = task["queue"].get_nowait()
        task["status"] = update["status"]
        if "progress" in update:
            task["progress"] = update["progress"]
        if "message" in update:
            task["message"] = update["message"]

        # If the task is finished, remove it after a short delay
        # to ensure the client gets the final status.
        if update["status"] in ["done", "error"]:
             # In a real app, you might use a cleanup job for this
             pass


    except queue.Empty:
        # No new update from the queue, just return the last known status
        pass

    return jsonify({
        "task_id": task_id,
        "status": task["status"],
        "progress": task.get("progress", 0),
        "message": task.get("message", "")
    })

if __name__ == "__main__":
    # Use 0.0.0.0 to make it accessible within the Docker container
    app.run(host="0.0.0.0", port=8080)