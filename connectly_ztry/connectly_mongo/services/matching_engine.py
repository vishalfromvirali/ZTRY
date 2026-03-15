from flask import current_app
def _db():
    return current_app.mongo.db
from models.db_utils import oid

def compute_match_score(user1_doc, user2_doc):
    score = 0.0
    i1 = set(user1_doc.get('interests', []))
    i2 = set(user2_doc.get('interests', []))
    if i1 and i2:
        shared = i1 & i2
        union  = i1 | i2
        score += (len(shared)/len(union))*60 if union else 0
    if user1_doc.get('study_field') and user2_doc.get('study_field'):
        if user1_doc['study_field'].lower() == user2_doc['study_field'].lower():
            score += 20
    if user1_doc.get('relationship_goal') and user1_doc.get('relationship_goal') == user2_doc.get('relationship_goal'):
        score += 20
    if user1_doc.get('location') and user2_doc.get('location'):
        if user1_doc['location'].lower() == user2_doc['location'].lower():
            score += 10
    return min(round(score, 1), 100.0)

def get_suggestions(user_id, limit=10):
    from bson import ObjectId
    matched = _db().matches.find({'$or':[{'user1_id':user_id},{'user2_id':user_id}]})
    skip = {m['user2_id'] if m['user1_id']==user_id else m['user1_id'] for m in matched}
    skip.add(user_id)
    me = _db().users.find_one({'_id': oid(user_id)})
    if not me: return []
    candidates = _db().users.find({'_id':{'$nin':[oid(s) for s in skip if s]}})
    scored = []
    for c in candidates:
        s = compute_match_score(me, c)
        if s > 10:
            from models.db_utils import str_id
            scored.append((str_id(c), s))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
