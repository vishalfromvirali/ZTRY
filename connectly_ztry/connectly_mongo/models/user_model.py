"""
User document structure in MongoDB:
{
  _id: ObjectId,
  username: str (unique),
  email: str,
  password_hash: str,
  gender: str,
  bio: str,
  profile_picture: str,   # filename
  banner_picture: str,    # filename
  location: str,
  relationship_goal: str,
  study_field: str,
  website: str,
  interests: [str],       # list of interest names
  followers: [str],       # list of user_id strings
  following: [str],
  is_online: bool,
  last_seen: datetime,
  created_at: datetime
}
