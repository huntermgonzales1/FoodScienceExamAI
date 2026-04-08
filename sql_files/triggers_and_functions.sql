-- CLEANUP: Remove old variations to prevent conflicts
DROP TRIGGER IF EXISTS ensure_email_is_whitelisted ON auth.users;
DROP TRIGGER IF EXISTS create_profile_after_signup ON auth.users;
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP TRIGGER IF EXISTS on_auth_user_synced ON auth.users;

DROP FUNCTION IF EXISTS check_allowed_email();
DROP FUNCTION IF EXISTS create_user_profile();
DROP FUNCTION IF EXISTS handle_metadata_only();
DROP FUNCTION IF EXISTS sync_user_profile();

----------------------------------------------------------------                
-- 1. BEFORE INSERT: Tag the JWT Metadata (The Auth Gate)
----------------------------------------------------------------
CREATE OR REPLACE FUNCTION handle_metadata_only()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if email exists in our whitelist and is not expired
    IF EXISTS (
        SELECT 1 FROM public.allowed_emails 
        WHERE email = NEW.email 
        AND (expiration_date IS NULL OR expiration_date >= CURRENT_DATE)
    ) THEN
        -- Tag as authorized so the App can allow entry
        NEW.raw_app_meta_data = jsonb_build_object('is_authorized', true);
    ELSE
        -- Tag as unauthorized so the App can block entry
        NEW.raw_app_meta_data = jsonb_build_object('is_authorized', false);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
BEFORE INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION handle_metadata_only();

----------------------------------------------------------------
-- 2. AFTER INSERT: Create Public Profile (The Data Sync)
----------------------------------------------------------------
CREATE OR REPLACE FUNCTION sync_user_profile()
RETURNS TRIGGER AS $$
BEGIN
    -- Only create a profile if they passed the whitelist check above
    IF (NEW.raw_app_meta_data->>'is_authorized')::boolean = true THEN
        INSERT INTO public.user_profile (user_id, email, is_instructor)
        SELECT 
            NEW.id, 
            NEW.email, 
            COALESCE(is_instructor, FALSE)
        FROM public.allowed_emails
        WHERE email = NEW.email;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_synced
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION sync_user_profile();

-- Grant permissions so the Auth service can run these functions
GRANT SELECT ON TABLE public.allowed_emails TO supabase_auth_admin;
GRANT INSERT ON TABLE public.user_profile TO supabase_auth_admin;