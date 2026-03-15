"""
Message document:
{
  _id: ObjectId,
  sender_id: str,
  receiver_id: str,
  content: str,
  is_read: bool,
  is_ai_intro: bool,
  timestamp: datetime
}

Match document:
{
  _id: ObjectId,
  user1_id: str,
  user2_id: str,
  match_score: float,
  status: str,
  ai_intro_sent: bool,
  created_at: datetime
}

Notification document:
{
  _id: ObjectId,
  user_id: str,
  type: str,
  content: str,
  related_id: str,
  is_read: bool,
  timestamp: datetime
}
"""
