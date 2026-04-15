# Food Science Exam AI

Streamlit web app for a food-science case-study style exam. Students sign in with email (one-time code), work through timed scenarios in a chat UI backed by **Google Gemini**, and can finalize attempts so the model assigns a numeric grade stored in **Supabase**. Instructors manage the email allowlist, prompts, and can review chats.

**Roadmap (not in the codebase yet):** The course design originally targeted **IFT CoDeveloper**—an AI stack tuned on Institute of Food Technologists (IFT) literature—for grading support. Today’s deployment uses Gemini instead. A planned next step is to connect the exam flow to a **vector store of published food-science journals** (IFT-curated or aligned corpora) **through model tool calls**, so answers can be grounded in that literature. That retrieval layer is not implemented yet, but it is a priority for future work.

## What it does

- **Auth**: Supabase Auth with email OTP; only addresses listed in `allowed_emails` (and not past `expiration_date`) are treated as authorized.
- **Data**: Chats and messages live in Postgres (Supabase); grading updates use the service role key so finalized grades can be written reliably under RLS.
- **AI**: Live tutoring and grading use the Gemini API (`google-genai`).

## Prerequisites

- Python **3.10+** (3.11 or 3.12 recommended)
- A [Supabase](https://supabase.com/) project
- A [Google AI Studio](https://aistudio.google.com/) API key for Gemini

## Local setup

1. Clone the repository and create a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Add Streamlit secrets at `.streamlit/secrets.toml` (this path is gitignored). Use the template in [Secrets](#secrets) below.

3. Run the app from the project root:

   ```bash
   streamlit run app.py
   ```

   Entrypoint is `app.py`; it registers hidden navigation routes (`login`, `exam`, `instructor`, etc.).

## Supabase setup

### 1. Create a project

Create a new Supabase project and wait for the database to finish provisioning.

### 2. Run SQL in order

In the Supabase dashboard, open **SQL Editor** and execute each file **once**, in this order (later files depend on earlier ones):

| Order | File | Purpose |
| --- | --- | --- |
| 1 | `sql_files/Schema.sql` | Tables, enums, foreign keys |
| 2 | `sql_files/triggers_and_functions.sql` | Auth triggers on `auth.users`: whitelist gate + `user_profile` row |
| 3 | `sql_files/RLS_policies.sql` | Row Level Security policies |
| 4 | `sql_files/indexes.sql` | Supporting indexes |

Copy the full contents of each file into a new query, run it, then move to the next.

### 3. Enable email (magic link / OTP) sign-in

Under **Authentication → Providers → Email**, enable the email provider. Configure **Authentication → URL Configuration** with your site URL (for local dev, `http://localhost:8501` is typical for Streamlit). Add any redirect URLs your host will use (for example your Streamlit Community Cloud URL, such as `https://food-science-ai.streamlit.app` for this project’s current deployment).

### 4. Bootstrap the first users

Before students can sign in, insert allowed addresses (lowercase emails match the app):

```sql
INSERT INTO public.allowed_emails (email, expiration_date, is_instructor)
VALUES
  ('you@example.edu', NULL, TRUE),
  ('student@example.edu', '2026-12-31', FALSE);
```

- `expiration_date` may be `NULL` for no expiry.
- Set `is_instructor` to `TRUE` for accounts that should use the instructor pages.

**RLS note:** Instructor policies in `RLS_policies.sql` check `is_instructor` in the JWT `app_metadata`. The bundled trigger sets `is_authorized` from the whitelist when a user is first created. If instructor-only actions fail with permission errors after redeploying, add a [Custom Access Token Hook](https://supabase.com/docs/guides/auth/auth-hooks/custom-access-token-hook) (or extend the signup trigger) so `is_instructor` from `allowed_emails` is present in `app_metadata` for new sessions.

## Secrets

Create `.streamlit/secrets.toml` locally. For **Streamlit Community Cloud**, paste the same keys in **App settings → Secrets**.

```toml
SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "your-anon-public-key"
SUPABASE_SECRET_KEY = "your-service-role-key"
GEMINI_API_KEY = "your-google-genai-api-key"

# Optional — auth cookie names and lifetime (defaults shown)
# COOKIE_PREFIX = "fsea"
# AUTH_COOKIE_MAX_AGE = 604800
```

- `SUPABASE_PUBLISHABLE_KEY`: Supabase **anon** `public` key (safe for browser-facing clients; still keep it out of public repos if you can).
- `SUPABASE_SECRET_KEY`: **service_role** key — treat as root access; only on the server / Streamlit secrets, never in client-only code.
- `COOKIE_PREFIX` (optional): Prefix for browser cookie names that store Supabase tokens (`{prefix}_sb_access`, `{prefix}_sb_refresh`). Default `fsea`.
- `AUTH_COOKIE_MAX_AGE` (optional): Cookie lifetime in seconds for those tokens. Default `604800` (7 days). Tokens are **not** `HttpOnly` (Streamlit component limitation); use a duration you are comfortable with.

Auth persistence uses [streamlit-cookies-controller](https://discuss.streamlit.io/t/new-component-streamlit-cookies-controller/64251) so a full page refresh can restore the Supabase session without putting secrets in the URL.

## Deploy to Streamlit Community Cloud

**Primary target:** [Streamlit Community Cloud](https://streamlit.io/cloud) (GitHub-connected). You can run the same app elsewhere (for example your own VM or a container platform), but this README only walks through Community Cloud.

A reference deployment for this codebase is **https://food-science-ai.streamlit.app**; your own Community Cloud URL will match the app name you choose in Streamlit.

1. Push this repository to GitHub (no secrets committed; confirm `.streamlit/secrets.toml` is not tracked).
2. In Streamlit Cloud, **Create app** → pick the repo, branch, and set **Main file path** to `app.py`.
3. Under **Advanced settings**, choose a Python version compatible with your dependencies (3.11 is a good default if offered).
4. Open **App settings → Secrets** and add the same TOML block as in [Secrets](#secrets), with production Supabase URL and keys.
5. In Supabase **Authentication → URL Configuration**, set **Site URL** to your Streamlit app URL (for example `https://food-science-ai.streamlit.app`) and add it to **Redirect URLs** if required by your auth flow.

After deploy, complete a full login test with a whitelisted email.

## Repository layout (short)

| Path | Role |
| --- | --- |
| `app.py` | Streamlit entry + page router |
| `database.py` | Supabase client helpers and data access |
| `tools.py` | Gemini chat + structured grading |
| `streamlit_helpers.py` | Session, query params, navigation helpers |
| `cookie_auth.py` | Browser cookies for Supabase session restore after refresh |
| `pages/` | UI for home, login, exam, instructor tools |
| `sql_files/` | Database schema, triggers, RLS, indexes |

## License

See `LICENSE` in the repository root.
