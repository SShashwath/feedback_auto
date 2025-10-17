import os
import sys
from redis import Redis
from rq import Queue

# Get Redis URL from environment variable
redis_url = os.getenv('UPSTASH_REDIS_URL')

# Validate that the Redis URL is set
if not redis_url:
    print("ERROR: UPSTASH_REDIS_URL environment variable is not set!")
    print("Please add it in your Render dashboard Environment settings.")
    print("Get your Redis URL from: https://console.upstash.com")
    sys.exit(1)

# Validate Redis URL format
if not redis_url.startswith(('redis://', 'rediss://', 'unix://')):
    print(f"ERROR: Invalid Redis URL format: {redis_url}")
    print("Redis URL must start with redis://, rediss://, or unix://")
    sys.exit(1)

# Connect to Upstash Redis
try:
    redis_conn = Redis.from_url(
        redis_url,
        decode_responses=False,  # Important for RQ compatibility
        socket_connect_timeout=5,
        socket_keepalive=True,
        health_check_interval=30
    )
    
    # Test connection
    redis_conn.ping()
    print(f"✅ Successfully connected to Redis at {redis_url.split('@')[1] if '@' in redis_url else 'localhost'}")
    
except Exception as e:
    print(f"❌ Failed to connect to Redis: {e}")
    print(f"Redis URL: {redis_url[:20]}..." if redis_url else "None")
    sys.exit(1)

# Create the queue for feedback tasks
feedback_queue = Queue('feedback', connection=redis_conn, default_timeout=600)
