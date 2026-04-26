from database import redis_client

# Delete one user's session

# Delete all sessions
for key in redis_client.scan_iter("session:*"):
    redis_client.delete(key)

# Nuclear option — wipe everything
redis_client.flushall()