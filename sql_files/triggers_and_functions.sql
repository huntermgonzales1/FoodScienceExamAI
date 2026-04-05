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
BEGIN
    INSERT INTO user_profile (user_id, email, is_instructor)
    SELECT
        NEW.id,
        NEW.email,
        a.is_instructor
    FROM allowed_emails a
    WHERE a.email = NEW.email;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER create_profile_after_signup
AFTER INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION create_user_profile();