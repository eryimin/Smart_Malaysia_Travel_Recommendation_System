"""Generate demo reviews; optional utility, not required during normal application startup."""
import json
import random
from pathlib import Path
from datetime import datetime, timedelta
random.seed(42)
BASE_DIR = Path(__file__).resolve().parent
REVIEWS_FILE = BASE_DIR / "data" / "reviews.json"
comments = ["Beautiful place with amazing scenery.","A great destination for family and friends.","Really enjoyed the attractions here.","Nice place to relax during the weekend.","Worth visiting when travelling in Malaysia.","Good experience with many things to explore.","The environment was clean and comfortable.","Interesting attractions and beautiful views.","Enjoyable trip, but it was quite crowded.","A wonderful place for a short holiday.","Good location with plenty of activities.","The experience was better than expected.","Nice destination, but some facilities could improve.","A memorable travel experience.",""]
reviews = json.loads(REVIEWS_FILE.read_text(encoding="utf-8")) if REVIEWS_FILE.exists() else []
existing = {(r["destination_id"],r["user_id"]) for r in reviews}
start_date = datetime(2026,10,1,10,0,0)
added = 0
for destination_id in (f"DEST{i:03d}" for i in range(1,51)):
    for user_number in range(1,5):
        user_id=f"demo_traveller{user_number:02d}"
        if (destination_id,user_id) in existing: continue
        rating=random.choices([2,3,4,5],weights=[1,2,5,6])[0]
        comment=random.choice(comments)
        created_at=(start_date+timedelta(days=random.randint(0,40),hours=random.randint(0,12),minutes=random.randint(0,59))).isoformat()
        reviews.append({"destination_id":destination_id,"user_id":user_id,"rating":rating,"review":comment,"created_at":created_at,"is_demo":True})
        added+=1
REVIEWS_FILE.parent.mkdir(parents=True,exist_ok=True)
REVIEWS_FILE.write_text(json.dumps(reviews,indent=4,ensure_ascii=False),encoding="utf-8")
print(f"Successfully added {added} demo reviews.")
print(f"Total review records: {len(reviews)}")
