
ALTER TABLE allowed_emails ENABLE ROW LEVEL SECURITY;

ALTER TABLE chat ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_message ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_question ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profile ENABLE ROW LEVEL SECURITY;

-- Students view own
CREATE POLICY "students can view own chats"
ON chat FOR SELECT
USING (user_id = auth.uid());

-- Instructors view all (No subquery!)
CREATE POLICY "instructors can view all chats"
ON chat FOR SELECT
USING ((auth.jwt() -> 'app_metadata' ->> 'is_instructor')::boolean = true);

-- Users create own
CREATE POLICY "users create their own chats"
ON chat FOR INSERT
WITH CHECK (user_id = auth.uid());



-- Students view own
CREATE POLICY "students view own messages"
ON chat_message FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM chat 
        WHERE chat.chat_id = chat_message.chat_id 
        AND chat.user_id = auth.uid()
    )
);

-- Instructors view all
CREATE POLICY "instructors view all messages"
ON chat_message FOR SELECT
USING ((auth.jwt() -> 'app_metadata' ->> 'is_instructor')::boolean = true);

-- Role-restricted insert (Prevents students from faking assistant messages)
CREATE POLICY "users insert own messages"
ON chat_message FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM chat 
        WHERE chat.chat_id = chat_message.chat_id 
        AND chat.user_id = auth.uid()
    ) 
    AND (
        -- If not an instructor
        (auth.jwt() -> 'app_metadata' ->> 'is_instructor')::boolean = true 
    )
);

CREATE POLICY "students read prompts"
ON prompt_question
FOR SELECT
USING (TRUE);

CREATE POLICY "instructors manage prompts"
ON prompt_question FOR ALL
USING ((auth.jwt() -> 'app_metadata' ->> 'is_instructor')::boolean = true);


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

CREATE POLICY "instructors manage allowed_emails"
ON allowed_emails FOR ALL
USING ((auth.jwt() -> 'app_metadata' ->> 'is_instructor')::boolean = true);