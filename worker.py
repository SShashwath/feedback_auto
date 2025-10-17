import os
from redis import Redis
from rq import Queue

# Connect to Upstash Redis using the URL from environment variables
redis_url = os.getenv('UPSTASH_REDIS_URL', 'redis://localhost:6379')
redis_conn = Redis.from_url(
    redis_url,
    decode_responses=False,  # Important for RQ compatibility
    socket_connect_timeout=5,
    socket_keepalive=True,
    health_check_interval=30
)

# Create the queue for feedback tasks
feedback_queue = Queue('feedback', connection=redis_conn, default_timeout=600)
