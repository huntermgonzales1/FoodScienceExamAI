-- Enable RLS on all tables
ALTER TABLE allowed_emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_question ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_message ENABLE ROW LEVEL SECURITY;

----------------------------------------------------------------
-- ALLOWED EMAILS & PROMPTS
----------------------------------------------------------------
-- Allow the internal Auth service to read the whitelist
CREATE POLICY "service_can_read_whitelist" 
ON public.allowed_emails FOR SELECT USING (true);

-- Instructors manage the whitelist and exam prompts
CREATE POLICY "instructors_manage_whitelist" 
ON public.allowed_emails FOR ALL 
USING (COALESCE((auth.jwt() -> 'app_metadata' ->> 'is_instructor')::boolean, false));

CREATE POLICY "instructors_manage_prompts" 
ON public.prompt_question FOR ALL 
USING (COALESCE((auth.jwt() -> 'app_metadata' ->> 'is_instructor')::boolean, false));

-- Authorized students can read exam prompts
CREATE POLICY "authorized_read_prompts" 
ON public.prompt_question FOR SELECT 
USING (COALESCE((auth.jwt() -> 'app_metadata' ->> 'is_authorized')::boolean, false));

----------------------------------------------------------------
-- USER PROFILES & CHATS
----------------------------------------------------------------
-- Users see own profile; instructors see all.
-- Important: this policy must not query public.user_profile inside USING,
-- or PostgreSQL can raise "infinite recursion detected in policy".
CREATE POLICY "view_profiles" ON public.user_profile FOR SELECT 
USING (
    auth.uid() = user_id 
    OR COALESCE((auth.jwt() -> 'app_metadata' ->> 'is_instructor')::boolean, false)
);

-- Users manage own chats
CREATE POLICY "users_manage_own_chats" ON public.chat FOR ALL 
USING (auth.uid() = user_id);

-- Instructors view all chats
CREATE POLICY "instructors_view_all_chats" ON public.chat FOR SELECT 
USING (COALESCE((auth.jwt() -> 'app_metadata' ->> 'is_instructor')::boolean, false));

-- Messages are visible if you own the parent chat
CREATE POLICY "view_own_chat_messages" ON public.chat_message FOR SELECT 
USING (
    EXISTS (
        SELECT 1 FROM public.chat 
        WHERE chat.chat_id = chat_message.chat_id 
        AND chat.user_id = auth.uid()
    )
);

-- Instructors can read all chat messages (for review; no INSERT policy for them)
CREATE POLICY "instructors_view_all_chat_messages" ON public.chat_message FOR SELECT
USING (COALESCE((auth.jwt() -> 'app_metadata' ->> 'is_instructor')::boolean, false));

-- Users can only insert messages into their own active chats
CREATE POLICY "insert_own_messages" ON public.chat_message FOR INSERT 
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.chat 
        WHERE chat.chat_id = chat_message.chat_id 
        AND chat.user_id = auth.uid()
        AND chat.status = 'active'
    )
);
