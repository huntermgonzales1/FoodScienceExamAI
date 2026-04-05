CREATE TYPE chat_status AS ENUM (
    'active',
    'completed',
    'graded'
);

CREATE TYPE message_role AS ENUM (
    'system',
    'user',
    'assistant'
);

CREATE TABLE allowed_emails (
    email TEXT PRIMARY KEY,
    expiration_date DATE,
    is_instructor BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE user_profile (
    user_id UUID PRIMARY KEY
        REFERENCES auth.users(id) ON DELETE CASCADE,

    email TEXT UNIQUE NOT NULL,
    is_instructor BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE prompt_question (
    prompt_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_text TEXT NOT NULL,
    info_text TEXT NOT NULL,
    system_instruction TEXT NOT NULL,
    available_date DATE NOT NULL,
    expire_date DATE,
    order_index INTEGER,
    is_practice BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE chat (
    chat_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL
        REFERENCES auth.users(id) ON DELETE CASCADE,

    initial_prompt_id UUID NOT NULL
        REFERENCES prompt_question(prompt_id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status chat_status NOT NULL,
    final_grade NUMERIC(5,2),
    grade_justification TEXT
);

CREATE TABLE chat_message (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id UUID NOT NULL
        REFERENCES chat(chat_id) ON DELETE CASCADE,

    role message_role NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);