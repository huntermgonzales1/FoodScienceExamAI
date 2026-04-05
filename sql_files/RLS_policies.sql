
-- Enable RLS so students can't edit the whitelist
ALTER TABLE allowed_emails ENABLE ROW LEVEL SECURITY;

ALTER TABLE chat ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_message ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_question ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profile ENABLE ROW LEVEL SECURITY;

CREATE POLICY "students can view own chats"
ON chat
FOR SELECT
USING (
    user_id = auth.uid()
);

CREATE POLICY "instructors can view all chats"
ON chat
FOR SELECT
USING (
    EXISTS (
        SELECT 1
        FROM user_profile p
        WHERE p.user_id = auth.uid()
        AND p.is_instructor
    )
);

CREATE POLICY "users create their own chats"
ON chat
FOR INSERT
WITH CHECK (
    user_id = auth.uid()
);

CREATE POLICY "students view own messages"
ON chat_message
FOR SELECT
USING (
    EXISTS (
        SELECT 1
        FROM chat c
        WHERE c.chat_id = chat_message.chat_id
        AND c.user_id = auth.uid()
    )
);

CREATE POLICY "instructors view all messages"
ON chat_message
FOR SELECT
USING (
    EXISTS (
        SELECT 1
        FROM user_profile p
        WHERE p.user_id = auth.uid()
        AND p.is_instructor
    )
);

CREATE POLICY "users insert own messages"
ON chat_message
FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM chat c
        WHERE c.chat_id = chat_message.chat_id
        AND c.user_id = auth.uid()
    )
);

CREATE POLICY "students read prompts"
ON prompt_question
FOR SELECT
USING (TRUE);

CREATE POLICY "instructors manage prompts"
ON prompt_question
FOR ALL
USING (
    EXISTS (
        SELECT 1
        FROM user_profile p
        WHERE p.user_id = auth.uid()
        AND p.is_instructor
    )
);

CREATE POLICY "users read own profile"
ON user_profile
FOR SELECT
USING (user_id = auth.uid());

CREATE POLICY "instructors read profiles"
ON user_profile
FOR SELECT
USING (
    EXISTS (
        SELECT 1
        FROM user_profile p
        WHERE p.user_id = auth.uid()
        AND p.is_instructor
    )
);