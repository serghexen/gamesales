FIELDS = (
    "agent_transaction_id", "service_id", "service_title", "nominal", "nominal_title",
    "price", "gift_code", "created_at", "deal_id", "order_number", "customer_nickname",
    "region_code", "created_by",
)


def iter_crm_purchase_export(*, psycopg, dsn, date_from, date_to):
    # Читаем весь оплаченный архив одним запросом: повторный COUNT и OFFSET замедляют месячную выгрузку.
    clauses = ["t.state='paid'"]
    params = []
    if date_from:
        clauses.append("t.created_at >= (%s::date::timestamp AT TIME ZONE 'Europe/Moscow')")
        params.append(date_from)
    if date_to:
        clauses.append("t.created_at < ((%s::date + 1)::timestamp AT TIME ZONE 'Europe/Moscow')")
        params.append(date_to)
    query = f"""
        WITH service_titles AS (
            SELECT DISTINCT ON (service_id) service_id, service_title
            FROM app.supplier_catalog_labels WHERE success=true
            ORDER BY service_id, calculated_at DESC, id DESC
        ), nominal_titles AS (
            SELECT DISTINCT ON (service_id, nominal_id) service_id, nominal_id, nominal_title
            FROM app.supplier_catalog_labels WHERE success=true
            ORDER BY service_id, nominal_id, calculated_at DESC, id DESC
        )
        SELECT t.agent_transaction_id, t.service_id, COALESCE(s.service_title, ''),
               COALESCE(t.request_params->>'nominal', ''),
               COALESCE(NULLIF(t.request_params->>'nominal_title', ''), n.nominal_title, ''),
               t.amount, t.gift_code, t.created_at, t.deal_id,
               COALESCE(d.order_number, ''), COALESCE(c.nickname, ''),
               COALESCE(r.region_code, ''), COALESCE(t.created_by, '')
        FROM app.interhub_transactions t
        LEFT JOIN service_titles s ON s.service_id=t.service_id
        LEFT JOIN nominal_titles n ON n.service_id=t.service_id
            AND n.nominal_id::text=COALESCE(t.request_params->>'nominal', '')
        LEFT JOIN app.deals d ON d.deal_id=t.deal_id
        LEFT JOIN app.customers c ON c.customer_id=d.customer_id
        LEFT JOIN LATERAL (
            SELECT COALESCE(direct_region.code, account_region.code) AS region_code
            FROM app.deal_items di
            LEFT JOIN app.accounts a ON a.account_id=di.account_id
            LEFT JOIN app.regions direct_region ON direct_region.region_id=d.region_id
            LEFT JOIN app.regions account_region ON account_region.region_id=a.region_id
            WHERE di.deal_id=d.deal_id
            ORDER BY di.deal_item_id LIMIT 1
        ) r ON true
        WHERE {' AND '.join(clauses)}
        ORDER BY t.created_at ASC, t.agent_transaction_id ASC
    """
    # Выбираем последние подписи один раз на услугу и номинал, а строки отдаём сборщику небольшими пачками.
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            while batch := cur.fetchmany(500):
                for row in batch:
                    yield dict(zip(FIELDS, row))
