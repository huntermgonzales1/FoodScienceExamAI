CREATE OR REPLACE FUNCTION check_allowed_email()
RETURNS TRIGGER AS $$
DECLARE
    v_expiration_date DATE;
BEGIN
    SELECT expiration_date
    INTO v_expiration_date
    FROM allowed_emails
    WHERE email = NEW.email;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Email % is not on the whitelist.',
            NEW.email;
    END IF;

    IF v_expiration_date IS NOT NULL
       AND v_expiration_date < CURRENT_DATE
    THEN
        RAISE EXCEPTION
            'Whitelist entry for % expired on %.',
            NEW.email,
            v_expiration_date;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER ensure_email_is_whitelisted
BEFORE INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION check_allowed_email();



CREATE OR REPLACE FUNCTION create_user_profile()
RETURNS TRIGGER AS $$
DECLARE
    v_is_instructor BOOLEAN;
BEGIN
    -- Get the instructor status from the whitelist
    SELECT is_instructor INTO v_is_instructor
    FROM allowed_emails
    WHERE email = NEW.email;

    -- 1. Sync to user_profile table
    INSERT INTO user_profile (user_id, email, is_instructor)
    VALUES (NEW.id, NEW.email, COALESCE(v_is_instructor, FALSE));

    -- 2. Sync to auth.users metadata so it's available in the JWT
    UPDATE auth.users
    SET raw_app_metadata = 
        raw_app_metadata || jsonb_build_object('is_instructor', COALESCE(v_is_instructor, FALSE))
    WHERE id = NEW.id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER create_profile_after_signup
AFTER INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION create_user_profile();