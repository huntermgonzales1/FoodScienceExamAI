CREATE INDEX idx_chat_user_id ON chat(user_id);
CREATE INDEX idx_chat_message_chat_id ON chat_message(chat_id);
CREATE INDEX idx_user_profile_is_instructor ON user_profile(is_instructor) WHERE is_instructor IS TRUE;