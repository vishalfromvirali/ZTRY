"""
Post document:
{
  _id: ObjectId,
  user_id: str,
  username: str,
  user_pic: str,
  content: str,
  media_url: str,          # filename in static/uploads/posts/
  media_type: str,         # image | video | None
  likes: [str],            # list of user_id strings
  comments: [{
    _id: str, user_id: str, username: str,
    user_pic: str, content: str, timestamp: datetime
  }],
  post_type: str,          # text | image | video
  timestamp: datetime
}
