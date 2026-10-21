"""Daily retention maintenance. Run from backend with the production DATABASE_URL."""
import json
from datetime import datetime,timezone,timedelta
from sqlalchemy import select,delete
from sqlalchemy.orm import Session
from app.main import engine,SocialVideo,Hotspot,RateBucket
now=datetime.now(timezone.utc)
with Session(engine) as s:
    expired=[v.id for v in s.scalars(select(SocialVideo)) if datetime.fromisoformat(json.loads(v.payload)['collected_at'])<now-timedelta(days=30)]
    if expired:
        s.execute(delete(Hotspot).where(Hotspot.id.in_(expired)))
        s.execute(delete(SocialVideo).where(SocialVideo.id.in_(expired)))
    s.execute(delete(RateBucket).where(RateBucket.expires<int(now.timestamp())))
    s.commit()
print('Expired social evidence and request buckets removed')
