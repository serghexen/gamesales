"""Узкий read-only контракт текущих остатков для Supplier Hub и Seller."""
from hmac import compare_digest
import os
from datetime import datetime, timezone
from fastapi import Header, HTTPException
from domains.interhub_stock_cache import detail_items


def stock_item(row):
    # Отдаём только наличие и тип ошибки: цены, ключи и сырые ответы за границу CRM не выходят.
    service_id, nominal_id, status, count, checked_at, error, response, peer_ok = row
    items, malformed = detail_items(response)
    scope = ''
    if error:
        # Невалидный/пустой ответ услуги нельзя принять за ошибку отдельного номинала.
        scope = 'item' if items and not malformed and peer_ok else 'common'
    return dict(service_id=str(service_id), nominal_id=str(nominal_id), status=status,
                stock_count=count, checked_at=checked_at, error_scope=scope)


def mount_supplier_stock_snapshot(app, *, db, dsn):
    # Отдельный машинный секрет разрешает только чтение уже сохранённых остатков.
    @app.get('/internal/supplier-stock/interhub', include_in_schema=False)
    def snapshot(x_supplier_stock_token: str = Header(default='')):
        expected = os.getenv('SUPPLIER_STOCK_SNAPSHOT_TOKEN', '')
        if len(expected) < 32 or not compare_digest(expected.encode(), x_supplier_stock_token.encode()):
            raise HTTPException(403, 'Snapshot access denied')
        with db.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute('''SELECT c.service_id,c.nominal_id,c.status,c.stock_count,
                CASE WHEN c.status<>'active' THEN (SELECT discovery_at FROM app.supplier_catalog_sync_state WHERE supplier_code='interhub')
                     ELSE c.stock_checked_at END,c.stock_error,c.stock_attempt_response,
                EXISTS(SELECT 1 FROM app.supplier_catalog_current peer
                  WHERE peer.supplier_code=c.supplier_code AND peer.service_id=c.service_id
                    AND peer.stock_checked_at=c.stock_checked_at AND peer.stock_error='' AND peer.stock_count IS NOT NULL)
                FROM app.supplier_catalog_current c
                WHERE c.supplier_code='interhub' AND c.service_type='VOUCHER'
                ORDER BY c.service_id,c.nominal_id''')
            items = [stock_item(row) for row in cur.fetchall()]
            cur.execute("SELECT checked_at,error FROM app.supplier_catalog_sync_state WHERE supplier_code='interhub'")
            state = cur.fetchone()
        return {'version': 1, 'generated_at': datetime.now(timezone.utc), 'items': items,
                'catalog_error': bool(state and state[1])}
