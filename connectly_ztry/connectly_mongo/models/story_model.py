"""
Story document (expires after 24h):
{
  _id: ObjectId,
  user_id: str,
  username: str,
  user_pic: str,
  media_url: str,    # filename
  media_type: str,   # image | video
  caption: str,
  viewers: [str],    # list of user_id strings
  expires_at: datetime,
  created_at: datetime
}
"""
