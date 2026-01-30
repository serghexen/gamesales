import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import ssl

import psycopg
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env.dev", override=True)

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

REGION_BY_COUNTRY_QID = {
    "Q30": "US",
    "Q159": "RU",
    "Q43": "TR",
}
EU_CONTINENT_QID = "Q46"


def fetch_wikidata_count(platform_qid: str, insecure: bool) -> int:
    query = f"""
    SELECT (COUNT(DISTINCT ?game) AS ?count) WHERE {{
      ?game wdt:P31 wd:Q7889;
            wdt:P400 wd:{platform_qid}.
    }}
    """
    params = urlencode({"query": query, "format": "json"})
    url = f"{SPARQL_ENDPOINT}?{params}"
    req = Request(url, headers={"User-Agent": "gamesales-import/1.0"})
    context = None
    if insecure:
        context = ssl._create_unverified_context()
    with urlopen(req, timeout=30, context=context) as resp:
        payload = json.load(resp)
    bindings = payload.get("results", {}).get("bindings", [])
    if not bindings:
        return 0
    return int(bindings[0]["count"]["value"])


def fetch_wikidata_games(
    platform_qid: str,
    insecure: bool,
    limit: int | None,
    offset: int,
) -> list[dict]:
    query = f"""
    SELECT ?gameLabel ?shortName ?country ?continent WHERE {{
      ?game wdt:P31 wd:Q7889;
            wdt:P400 wd:{platform_qid};
            rdfs:label ?gameLabel.
      FILTER(LANG(?gameLabel) = "en")
      OPTIONAL {{ ?game wdt:P1813 ?shortName. }}
      OPTIONAL {{
        ?game wdt:P495 ?country.
        OPTIONAL {{ ?country wdt:P30 ?continent. }}
      }}
      FILTER(!REGEX(STR(?gameLabel), "^Q[0-9]+$"))
    }}
    ORDER BY ?gameLabel
    """
    if limit is not None:
        query += f"\nLIMIT {limit}\n"
    if offset:
        query += f"\nOFFSET {offset}\n"
    params = urlencode({"query": query, "format": "json"})
    url = f"{SPARQL_ENDPOINT}?{params}"
    req = Request(url, headers={"User-Agent": "gamesales-import/1.0"})
    context = None
    if insecure:
        context = ssl._create_unverified_context()
    with urlopen(req, timeout=30, context=context) as resp:
        payload = json.load(resp)
    bindings = payload.get("results", {}).get("bindings", [])
    games = []
    for item in bindings:
        label = item.get("gameLabel", {}).get("value", "").strip()
        if not label:
            continue
        short_name = item.get("shortName", {}).get("value", "").strip() or None
        country_uri = item.get("country", {}).get("value", "")
        continent_uri = item.get("continent", {}).get("value", "")
        country_qid = country_uri.rsplit("/", 1)[-1] if country_uri else None
        continent_qid = continent_uri.rsplit("/", 1)[-1] if continent_uri else None
        region_code = None
        if country_qid in REGION_BY_COUNTRY_QID:
            region_code = REGION_BY_COUNTRY_QID[country_qid]
        elif continent_qid == EU_CONTINENT_QID:
            region_code = "EU"
        games.append(
            {
                "title": label,
                "short_title": short_name,
                "region_code": region_code,
            }
        )
    return games


def get_platform_id(conn, platform_code: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT platform_id FROM app.platforms WHERE code = %s",
            (platform_code,),
        )
        row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Platform code not found: {platform_code}")
    return row[0]


def load_region_ids(conn) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute("SELECT code, region_id FROM app.regions")
        rows = cur.fetchall()
    return {code: region_id for code, region_id in rows}


def upsert_games(conn, games: list[dict], platform_id: int, region_ids: dict[str, int]):
    with conn.cursor() as cur:
        for game in games:
            title = game["title"]
            short_title = game["short_title"]
            region_code = game["region_code"]
            region_id = region_ids.get(region_code) if region_code else None

            cur.execute(
                "SELECT game_id, short_title, region_id FROM app.game_titles WHERE title = %s",
                (title,),
            )
            row = cur.fetchone()
            if row:
                game_id = row[0]
                existing_short_title = row[1]
                existing_region_id = row[2]
                if short_title and not existing_short_title:
                    cur.execute(
                        "UPDATE app.game_titles SET short_title = %s WHERE game_id = %s",
                        (short_title, game_id),
                    )
                if region_id and not existing_region_id:
                    cur.execute(
                        "UPDATE app.game_titles SET region_id = %s WHERE game_id = %s",
                        (region_id, game_id),
                    )
            else:
                cur.execute(
                    """
                    INSERT INTO app.game_titles (title, short_title, region_id)
                    VALUES (%s, %s, %s)
                    RETURNING game_id
                    """,
                    (title, short_title, region_id),
                )
                game_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO app.game_platforms (game_id, platform_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (game_id, platform_id),
            )


def main():
    parser = argparse.ArgumentParser(description="Import PS4 games from Wikidata.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--platform-qid",
        default="Q5014725",
        help="Wikidata QID for platform (default: PS4 Q5014725).",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification (not recommended).",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Only print the total number of games for the platform.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all games without a LIMIT (uses batching).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch size for --all mode (default: 500).",
    )
    args = parser.parse_args()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is required to connect to Postgres.")

    with psycopg.connect(dsn) as conn:
        platform_id = get_platform_id(conn, "ps4")
        region_ids = load_region_ids(conn)
        if args.count:
            count = fetch_wikidata_count(args.platform_qid, args.insecure)
            print(f"Wikidata games count: {count}")
            return

        if args.all:
            offset = 0
            total = 0
            while True:
                games = fetch_wikidata_games(
                    args.platform_qid,
                    args.insecure,
                    args.batch_size,
                    offset,
                )
                if not games:
                    break
                upsert_games(conn, games, platform_id, region_ids)
                conn.commit()
                total += len(games)
                offset += args.batch_size
            print(f"Imported {total} games.")
        else:
            games = fetch_wikidata_games(
                args.platform_qid,
                args.insecure,
                args.limit,
                0,
            )
            if not games:
                print("No games collected from Wikidata.")
                return
            upsert_games(conn, games, platform_id, region_ids)
            conn.commit()
            print(f"Imported {len(games)} games.")


if __name__ == "__main__":
    main()
