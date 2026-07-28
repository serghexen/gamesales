from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256
import os

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field


class MarketplaceManualKeyOut(BaseModel):
    id: int
    masked_code: str
    status: str
    expires_at: date | None = None
    issued_order_ref: str = ""
    issued_at: datetime | None = None
    created_at: datetime


class MarketplaceManualKeyPoolOut(BaseModel):
    marketplace: str
    store_code: str
    product_key: str
    free_count: int = 0
    reserved_count: int = 0
    delivered_count: int = 0
    expired_count: int = 0
    total: int = 0
    page: int = 1
    page_size: int = 20
    items: list[MarketplaceManualKeyOut] = Field(default_factory=list)


class MarketplaceManualKeysIn(BaseModel):
    codes: list[str] = Field(min_length=1, max_length=1000)
    expires_at: date | None = None


class MarketplaceManualKeysCreateOut(BaseModel):
    added: int
    duplicates: int


class MarketplaceManualKeyRevealOut(BaseModel):
    id: int
    code: str


def mount_marketplace_key_pool_routes(app, *, DB_DSN, psycopg, q1, qall, exec1, require_role):
    def normalized_marketplace(value: str) -> str:
        # Принимает только поддерживаемые витрины, чтобы ключи разных маркетплейсов не смешивались.
        marketplace = str(value or "").strip().lower()
        if marketplace not in {"ozon", "yandex_market"}:
            raise HTTPException(404, "Пул ключей для этого маркетплейса не поддерживается")
        return marketplace

    def normalized_product_key(value: str) -> str:
        # Проверяет идентификатор карточки до создания пула и не допускает пустой общий пул.
        product_key = str(value or "").strip()
        if not product_key or len(product_key) > 255:
            raise HTTPException(400, "Не удалось определить карточку товара для пула ключей")
        return product_key

    def normalized_store_code(value: str) -> str:
        # Держит пулы разных магазинов раздельно, даже если артикул у них совпадает.
        store_code = str(value or "asat").strip().lower()
        if not store_code or len(store_code) > 64:
            raise HTTPException(400, "Некорректный код магазина")
        return store_code

    def key_pool_secret() -> str:
        # Не позволяет записать читаемый ключ в базу: секрет задается отдельно от токенов маркетплейсов.
        secret = str(os.getenv("MARKETPLACE_KEY_POOL_SECRET", "")).strip()
        if len(secret) < 32:
            raise HTTPException(503, "Для ручного пула ключей задайте MARKETPLACE_KEY_POOL_SECRET длиной не менее 32 символов")
        return secret

    def code_hash(value: str) -> str:
        # Создает единый отпечаток, чтобы один ключ нельзя было загрузить в другой пул повторно.
        return sha256(f"marketplace-manual-key:v1:{value}".encode("utf-8")).hexdigest()

    def mask_code_suffix(value: str) -> str:
        # Показывает оператору только хвост ключа, не раскрывая содержимое из базы в браузер.
        suffix = str(value or "").strip()[-4:]
        return f"••••{suffix}" if suffix else "••••"

    def ensure_pool(conn, marketplace: str, store_code: str, product_key: str) -> int:
        # Создает изолированный пул карточки один раз и возвращает его постоянный идентификатор.
        row = q1(
            conn,
            """
            INSERT INTO app.marketplace_manual_key_pools(marketplace, store_code, product_key)
            VALUES (%s, %s, %s)
            ON CONFLICT (marketplace, store_code, product_key)
            DO UPDATE SET updated_at=now()
            RETURNING id
            """,
            (marketplace, store_code, product_key),
        )
        return int(row[0])

    def pool_out(conn, marketplace: str, store_code: str, product_key: str, page: int, page_size: int) -> MarketplaceManualKeyPoolOut:
        # Возвращает маскированный список и счетчики, не расшифровывая ключи для обычного просмотра.
        pool_id = ensure_pool(conn, marketplace, store_code, product_key)
        stats = q1(
            conn,
            """
            SELECT
              COUNT(*) FILTER (WHERE status='free'),
              COUNT(*) FILTER (WHERE status IN ('reserved', 'sending')),
              COUNT(*) FILTER (WHERE status='delivered'),
              COUNT(*) FILTER (WHERE status='expired'),
              COUNT(*)
            FROM app.marketplace_manual_keys
            WHERE pool_id=%s
            """,
            (pool_id,),
        ) or (0, 0, 0, 0, 0)
        rows = qall(
            conn,
            """
            SELECT id, code_suffix, status, expires_at, issued_order_ref, issued_at, created_at
            FROM app.marketplace_manual_keys
            WHERE pool_id=%s
            ORDER BY CASE status WHEN 'free' THEN 0 WHEN 'reserved' THEN 1 WHEN 'sending' THEN 2 ELSE 3 END, created_at DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            (pool_id, page_size, (page - 1) * page_size),
        )
        return MarketplaceManualKeyPoolOut(
            marketplace=marketplace,
            store_code=store_code,
            product_key=product_key,
            free_count=int(stats[0] or 0),
            reserved_count=int(stats[1] or 0),
            delivered_count=int(stats[2] or 0),
            expired_count=int(stats[3] or 0),
            total=int(stats[4] or 0),
            page=page,
            page_size=page_size,
            items=[
                MarketplaceManualKeyOut(
                    id=int(row[0]), masked_code=mask_code_suffix(row[1]), status=str(row[2]),
                    expires_at=row[3], issued_order_ref=str(row[4] or ""), issued_at=row[5], created_at=row[6],
                )
                for row in rows
            ],
        )

    @app.get("/marketplaces/key-pools/{marketplace}/{product_key}", response_model=MarketplaceManualKeyPoolOut)
    def get_marketplace_key_pool(
        marketplace: str,
        product_key: str,
        store_code: str = "asat",
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        user=Depends(require_role("owner")),
    ):
        # Открывает только пул одной карточки, поэтому список ключей не пересекается с соседними товарами.
        normalized = normalized_marketplace(marketplace)
        with psycopg.connect(DB_DSN) as conn:
            result = pool_out(conn, normalized, normalized_store_code(store_code), normalized_product_key(product_key), page, page_size)
            conn.commit()
        return result

    @app.post("/marketplaces/key-pools/{marketplace}/{product_key}/keys", response_model=MarketplaceManualKeysCreateOut)
    def add_marketplace_key_pool_keys(
        marketplace: str,
        product_key: str,
        payload: MarketplaceManualKeysIn,
        store_code: str = "asat",
        user=Depends(require_role("owner")),
    ):
        # Загружает пачку ключей в один пул и сразу отсеивает повторы, не передавая их маркетплейсам.
        normalized = normalized_marketplace(marketplace)
        prepared = []
        seen = set()
        duplicate_count = 0
        for raw_code in payload.codes:
            code = str(raw_code or "").strip()
            if not code or len(code) > 1024:
                continue
            if code in seen:
                duplicate_count += 1
                continue
            seen.add(code)
            prepared.append(code)
        if not prepared:
            raise HTTPException(400, "Добавьте хотя бы один непустой ключ")
        secret = key_pool_secret()
        added = 0
        with psycopg.connect(DB_DSN) as conn:
            pool_id = ensure_pool(conn, normalized, normalized_store_code(store_code), normalized_product_key(product_key))
            for code in prepared:
                row = q1(
                    conn,
                    """
                    INSERT INTO app.marketplace_manual_keys(pool_id, code_ciphertext, code_hash, code_suffix, expires_at)
                    VALUES (%s, pgp_sym_encrypt(%s, %s, 'cipher-algo=aes256, compress-algo=0'), %s, %s, %s)
                    ON CONFLICT (code_hash) DO NOTHING
                    RETURNING id
                    """,
                    (pool_id, code, secret, code_hash(code), code[-4:], payload.expires_at),
                )
                if row:
                    added += 1
            conn.commit()
        return MarketplaceManualKeysCreateOut(added=added, duplicates=duplicate_count + len(prepared) - added)

    @app.post("/marketplaces/key-pools/{marketplace}/{product_key}/keys/{key_id}/reveal", response_model=MarketplaceManualKeyRevealOut)
    def reveal_marketplace_key_pool_key(
        marketplace: str,
        product_key: str,
        key_id: int,
        store_code: str = "asat",
        user=Depends(require_role("owner")),
    ):
        # Раскрывает один ключ владельцу для сверки, включая уже выданные ключи, не меняя его статус.
        normalized = normalized_marketplace(marketplace)
        secret = key_pool_secret()
        with psycopg.connect(DB_DSN) as conn:
            pool_id = ensure_pool(conn, normalized, normalized_store_code(store_code), normalized_product_key(product_key))
            row = q1(
                conn,
                """
                SELECT pgp_sym_decrypt(code_ciphertext, %s)
                FROM app.marketplace_manual_keys
                WHERE id=%s AND pool_id=%s
                """,
                (secret, key_id, pool_id),
            )
            conn.commit()
        if not row or not str(row[0] or ""):
            raise HTTPException(404, "Ключ не найден в этом пуле")
        return MarketplaceManualKeyRevealOut(id=key_id, code=str(row[0]))

    @app.delete("/marketplaces/key-pools/{marketplace}/{product_key}/keys/{key_id}", status_code=204)
    def delete_marketplace_key_pool_key(
        marketplace: str,
        product_key: str,
        key_id: int,
        store_code: str = "asat",
        user=Depends(require_role("owner")),
    ):
        # Удаляет только свободный ключ выбранной карточки, сохраняя историю зарезервированных и выданных.
        normalized = normalized_marketplace(marketplace)
        with psycopg.connect(DB_DSN) as conn:
            pool_id = ensure_pool(conn, normalized, normalized_store_code(store_code), normalized_product_key(product_key))
            removed = exec1(conn, "DELETE FROM app.marketplace_manual_keys WHERE id=%s AND pool_id=%s AND status='free'", (key_id, pool_id))
            conn.commit()
        if not removed:
            raise HTTPException(409, "Можно удалить только свободный ключ из этого пула")

    @app.delete("/marketplaces/key-pools/{marketplace}/{product_key}/keys", status_code=204)
    def delete_all_free_marketplace_key_pool_keys(
        marketplace: str,
        product_key: str,
        store_code: str = "asat",
        user=Depends(require_role("owner")),
    ):
        # Очищает только свободный остаток пула и никогда не стирает ключи из истории заказов.
        normalized = normalized_marketplace(marketplace)
        with psycopg.connect(DB_DSN) as conn:
            pool_id = ensure_pool(conn, normalized, normalized_store_code(store_code), normalized_product_key(product_key))
            exec1(conn, "DELETE FROM app.marketplace_manual_keys WHERE pool_id=%s AND status='free'", (pool_id,))
            conn.commit()
