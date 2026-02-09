from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class GamesLookupService:
    find_game_title_platform_conflicts: Callable
    find_game_id_by_title_platforms: Callable


def build_games_lookup_service(*, q1, qall, normalize_platform_codes) -> GamesLookupService:
    def find_game_title_platform_conflicts(conn, title: str, platform_codes: list[str], exclude_game_id: Optional[int] = None) -> list[str]:
        if not title or not platform_codes:
            return []
        normalized_codes = normalize_platform_codes(platform_codes)
        params = [title, normalized_codes]
        extra = ""
        if exclude_game_id is not None:
            extra = "AND g.game_id <> %s"
            params.append(exclude_game_id)
        rows = qall(
            conn,
            f"""
            SELECT DISTINCT p.code
            FROM app.game_titles g
            JOIN app.game_platforms gp ON gp.game_id = g.game_id
            JOIN app.platforms p ON p.platform_id = gp.platform_id
            WHERE lower(g.title) = lower(%s)
              AND g.is_archived IS NOT TRUE
              AND lower(p.code) = ANY(%s)
              {extra}
            ORDER BY p.code
            """,
            params,
        )
        return [r[0] for r in rows]

    def find_game_id_by_title_platforms(conn, title: str, platform_codes: list[str]) -> Optional[int]:
        if not title or not platform_codes:
            return None
        normalized_codes = normalize_platform_codes(platform_codes)
        target_count = len(normalized_codes)
        row = q1(
            conn,
            """
            SELECT g.game_id
            FROM app.game_titles g
            JOIN app.game_platforms gp ON gp.game_id = g.game_id
            JOIN app.platforms p ON p.platform_id = gp.platform_id
            WHERE lower(g.title) = lower(%s)
              AND g.is_archived IS NOT TRUE
            GROUP BY g.game_id
            HAVING count(DISTINCT lower(p.code)) = %s
               AND bool_and(lower(p.code) = ANY(%s))
            ORDER BY g.game_id
            LIMIT 1
            """,
            (title, target_count, normalized_codes),
        )
        return int(row[0]) if row else None

    return GamesLookupService(
        find_game_title_platform_conflicts=find_game_title_platform_conflicts,
        find_game_id_by_title_platforms=find_game_id_by_title_platforms,
    )
