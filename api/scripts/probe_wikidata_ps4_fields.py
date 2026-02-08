import argparse
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import ssl

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

QUERY_TEMPLATE = """
SELECT ?gameLabel ?developerLabel ?publisherLabel ?genreLabel ?releaseDate ?officialSite WHERE {{
  ?game wdt:P31 wd:Q7889;
        wdt:P400 wd:Q5014725.

  OPTIONAL {{ ?game wdt:P178 ?developer. }}
  OPTIONAL {{ ?game wdt:P123 ?publisher. }}
  OPTIONAL {{ ?game wdt:P136 ?genre. }}
  OPTIONAL {{ ?game wdt:P577 ?releaseDate. }}
  OPTIONAL {{ ?game wdt:P856 ?officialSite. }}

  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT {limit}
"""


def fetch_probe(limit: int, insecure: bool) -> dict:
    query = QUERY_TEMPLATE.format(limit=limit)
    params = urlencode({"query": query, "format": "json"})
    url = f"{SPARQL_ENDPOINT}?{params}"
    req = Request(url, headers={"User-Agent": "gamesales-probe/1.0"})
    context = ssl._create_unverified_context() if insecure else None
    with urlopen(req, timeout=30, context=context) as resp:
        return json.load(resp)


def main():
    parser = argparse.ArgumentParser(description="Probe PS4 game fields from Wikidata.")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification (not recommended).",
    )
    args = parser.parse_args()

    payload = fetch_probe(args.limit, args.insecure)
    bindings = payload.get("results", {}).get("bindings", [])
    rows = []
    for item in bindings:
        rows.append(
            {
                "game": item.get("gameLabel", {}).get("value"),
                "developer": item.get("developerLabel", {}).get("value"),
                "publisher": item.get("publisherLabel", {}).get("value"),
                "genre": item.get("genreLabel", {}).get("value"),
                "releaseDate": item.get("releaseDate", {}).get("value"),
                "officialSite": item.get("officialSite", {}).get("value"),
            }
        )

    print(json.dumps(rows, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
