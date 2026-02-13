from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class GamesLookupService:
    find_game_title_platform_conflicts: Callable
    find_game_product_id_by_title_platforms: Callable


def build_games_lookup_service(*, q1, qall, normalize_platform_codes) -> GamesLookupService:
    # Проверяет, есть ли уже game-товар с тем же title на выбранных платформах.
    def find_game_title_platform_conflicts(conn, title: str, platform_codes: list[str], exclude_product_id: Optional[int] = None) -> list[str]:
        if not title or not platform_codes:
            return []
        normalized_codes = normalize_platform_codes(platform_codes)
        params = [title, normalized_codes]
        extra = ""
        if exclude_product_id is not None:
            extra = "AND p.product_id <> %s"
            params.append(exclude_product_id)
        rows = qall(
            conn,
            f"""
            SELECT DISTINCT pl.code
            FROM app.products p
            JOIN app.product_platforms pp ON pp.product_id = p.product_id
            JOIN app.platforms pl ON pl.platform_id = pp.platform_id
            WHERE lower(p.title) = lower(%s)
              AND lower(p.type_code) = 'game'
              AND p.is_archived IS NOT TRUE
              AND lower(pl.code) = ANY(%s)
              {extra}
            ORDER BY pl.code
            """,
            params,
        )
        return [r[0] for r in rows]

    # Возвращает product_id для game-товара по title и точному набору платформ.
    def find_game_product_id_by_title_platforms(conn, title: str, platform_codes: list[str]) -> Optional[int]:
        if not title or not platform_codes:
            return None
        normalized_codes = normalize_platform_codes(platform_codes)
        target_count = len(normalized_codes)
        row = q1(
            conn,
            """
            SELECT p.product_id
            FROM app.products p
            JOIN app.product_platforms pp ON pp.product_id = p.product_id
            JOIN app.platforms pl ON pl.platform_id = pp.platform_id
            WHERE lower(p.title) = lower(%s)
              AND lower(p.type_code) = 'game'
              AND p.is_archived IS NOT TRUE
            GROUP BY p.product_id
            HAVING count(DISTINCT lower(pl.code)) = %s
               AND bool_and(lower(pl.code) = ANY(%s))
            ORDER BY p.product_id
            LIMIT 1
            """,
            (title, target_count, normalized_codes),
        )
        return int(row[0]) if row else None

    return GamesLookupService(
        find_game_title_platform_conflicts=find_game_title_platform_conflicts,
        find_game_product_id_by_title_platforms=find_game_product_id_by_title_platforms,
    )
