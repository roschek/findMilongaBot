"""One-time script to seed Redis with local sites_db.json"""
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from upstash_redis import Redis

r = Redis(url=os.environ["UPSTASH_REDIS_REST_URL"], token=os.environ["UPSTASH_REDIS_REST_TOKEN"])

data = json.loads(Path("sites_db.json").read_text(encoding="utf-8"))
r.set("sites_db", json.dumps(data, ensure_ascii=False))
print(f"Seeded {len(data)} cities to Redis: {', '.join(data.keys())}")
