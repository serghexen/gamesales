"""Общие SQL-правила пересчёта закупа для финансов и аналитики."""


# Оплаченная покупка, связанная со сделкой, подтверждает рублёвый закуп ваучеров.
# EXISTS не размножает строки отчёта, когда у сделки несколько покупок.
PAID_VOUCHER_COST_SQL = """(
    d.deal_type_code = 'sale'
    AND upper(rd.code) IN ('TR', 'PL')
    AND EXISTS (
        SELECT 1
        FROM app.interhub_transactions cost_tx
        WHERE cost_tx.deal_id = d.deal_id AND cost_tx.state = 'paid'
    )
)"""


def purchase_cost_rate_sql(legacy_rate_sql: str = "COALESCE(rd.purchase_cost_rate, 1.0)") -> str:
    # Для оплаченных ваучеров берём 1, а старым сделкам оставляем прежний пересчёт.
    # Аргумент содержит только SQL из кода отчёта, пользовательские значения сюда не передаются.
    return f"(CASE WHEN {PAID_VOUCHER_COST_SQL} THEN 1.0 ELSE {legacy_rate_sql} END)"
