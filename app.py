from flask import Flask, request, jsonify
from flask_cors import CORS
from rq.job import Job
from worker import feedback_queue, redis_conn
from feedback_automation import run_feedback_automation
import time

app = Flask(__name__)

# CORS configuration for your Vercel frontend
CORS(app, resources={r"/api/*": {"origins": "https://easy-college.vercel.app"}})


@app.route("/api/run-feedback", methods=["POST"])
def start_feedback_task():
    """
    API endpoint to start a new feedback automation task.
    Enqueues the task to Redis Queue instead of running it directly.
    """
    data = request.get_json()
    
    # Validate required fields
    if not all(key in data for key in ['rollno', 'password', 'feedback_type']):
        return jsonify({
            "error": "Missing required data: rollno, password, and feedback_type"
        }), 400

    rollno = data['rollno']
    password = data['password']
    feedback_type = int(data['feedback_type'])
    
    try:
        # Enqueue the task to Redis Queue
        job = feedback_queue.enqueue(
            run_feedback_automation,
            feedback_type,
            rollno,
            password,
            None,  # status_queue not needed with RQ
            job_timeout='10m',  # Max 10 minutes per task
            result_ttl=3600,    # Keep result for 1 hour
            failure_ttl=3600    # Keep failed job info for 1 hour
        )
        
        return jsonify({
            "status": "Task queued successfully",
            "task_id": job.id,
            "position": len(feedback_queue)  # Queue position
        }), 202
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to queue task: {str(e)}"
        }), 500


@app.route("/api/status/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """
    API endpoint to check the status of a queued task.
    """
    try:
        job = Job.fetch(task_id, connection=redis_conn)
        
        # Map RQ job status to your frontend's expected format
        if job.is_finished:
            return jsonify({
                "task_id": task_id,
                "status": "done",
                "progress": 100,
                "message": "Feedback submitted successfully!",
                "result": job.result
            })
        
        elif job.is_failed:
            return jsonify({
                "task_id": task_id,
                "status": "error",
                "progress": 0,
                "message": f"Task failed: {job.exc_info}",
                "error": str(job.exc_info)
            })
        
        elif job.is_started:
            # Job is currently being processed
            return jsonify({
                "task_id": task_id,
                "status": "running",
                "progress": 50,  # Mid-progress since we can't track granularly
                "message": "Processing feedback automation..."
            })
        
        elif job.is_queued:
            # Job is waiting in queue
            position = job.get_position()
            return jsonify({
                "task_id": task_id,
                "status": "queued",
                "progress": 10,
                "message": f"Waiting in queue (position: {position + 1 if position is not None else 'N/A'})",
                "queue_position": position + 1 if position is not None else None
            })
        
        else:
            # Job is scheduled or deferred
            return jsonify({
                "task_id": task_id,
                "status": "pending",
                "progress": 0,
                "message": "Task is scheduled"
            })
    
    except Exception as e:
        return jsonify({
            "error": f"Task not found or invalid task ID: {str(e)}"
        }), 404


@app.route("/api/health", methods=["GET"])
def health_check():
    """
    Health check endpoint to verify Redis connection.
    """
    try:
        redis_conn.ping()
        return jsonify({
            "status": "healthy",
            "redis": "connected",
            "timestamp": time.time()
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "redis": str(e),
            "timestamp": time.time()
        }), 500


@app.route("/api/keep-alive", methods=["GET"])
def keep_alive():
    """
    Keep-alive endpoint for cron jobs to prevent Render free tier from sleeping.
    Also provides system status information.
    """
    try:
        # Check Redis connection
        redis_conn.ping()
        
        # Get queue statistics
        queue_stats = {
            "queued": len(feedback_queue),
            "failed": len(feedback_queue.failed_job_registry),
            "finished": len(feedback_queue.finished_job_registry),
            "started": len(feedback_queue.started_job_registry)
        }
        
        return jsonify({
            "status": "alive",
            "message": "Service is running",
            "redis": "connected",
            "queue_stats": queue_stats,
            "timestamp": time.time()
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "degraded",
            "message": f"Service running but Redis unreachable: {str(e)}",
            "timestamp": time.time()
        }), 200  # Still return 200 to keep service awake


@app.route("/api/queue-stats", methods=["GET"])
def get_queue_stats():
    """
    Optional endpoint to check queue health and statistics.
    """
    try:
        return jsonify({
            "queued_jobs": len(feedback_queue),
            "failed_jobs": len(feedback_queue.failed_job_registry),
            "finished_jobs": len(feedback_queue.finished_job_registry),
            "started_jobs": len(feedback_queue.started_job_registry)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
