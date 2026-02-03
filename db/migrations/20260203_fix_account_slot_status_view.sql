BEGIN;

CREATE OR REPLACE VIEW app.v_account_slot_status AS
SELECT
  a.account_id,
  st.code AS slot_type_code,
  st.platform_code,
  st.mode,
  st.capacity,
  COALESCE(
    SUM(
      CASE
        WHEN asa.assignment_id IS NOT NULL AND asa.released_at IS NULL THEN 1
        ELSE 0
      END
    ),
    0
  ) AS occupied,
  GREATEST(
    st.capacity - COALESCE(
      SUM(
        CASE
          WHEN asa.assignment_id IS NOT NULL AND asa.released_at IS NULL THEN 1
          ELSE 0
        END
      ),
      0
    ),
    0
  ) AS free
FROM app.accounts a
CROSS JOIN app.slot_types st
LEFT JOIN app.account_slot_assignments asa
  ON asa.account_id = a.account_id AND asa.slot_type_code = st.code
GROUP BY a.account_id, st.code, st.platform_code, st.mode, st.capacity;

COMMIT;
