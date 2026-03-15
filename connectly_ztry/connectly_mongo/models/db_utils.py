from bson import ObjectId
from datetime import datetime

def oid(id_str):
    try: return ObjectId(str(id_str))
    except: return None

def str_id(doc):
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def str_ids(docs):
    return [str_id(d) for d in docs]

def now():
    return datetime.utcnow()
