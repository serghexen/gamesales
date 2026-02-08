BEGIN;

CREATE OR REPLACE FUNCTION app.log_deal_audit()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  v_user text;
BEGIN
  v_user := current_setting('app.user', true);
  IF TG_OP = 'UPDATE' THEN
    IF to_jsonb(OLD) IS DISTINCT FROM to_jsonb(NEW) THEN
      IF TG_TABLE_NAME = 'deal_items' THEN
        INSERT INTO app.deal_audit(
          deal_id,
          deal_item_id,
          table_name,
          action,
          changed_by,
          old_data,
          new_data
        )
        VALUES (
          NEW.deal_id,
          NEW.deal_item_id,
          TG_TABLE_NAME,
          TG_OP,
          v_user,
          to_jsonb(OLD),
          to_jsonb(NEW)
        );
      ELSE
        INSERT INTO app.deal_audit(
          deal_id,
          deal_item_id,
          table_name,
          action,
          changed_by,
          old_data,
          new_data
        )
        VALUES (
          NEW.deal_id,
          NULL,
          TG_TABLE_NAME,
          TG_OP,
          v_user,
          to_jsonb(OLD),
          to_jsonb(NEW)
        );
      END IF;
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

COMMIT;
