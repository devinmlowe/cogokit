"""Fetch all NAD83 SPCS zone definitions from epsg.io and write JSON.

Run once: python scripts/fetch_spcs_zones.py
Output: src/cogokit/data/spcs_zones.json
"""

import json
import time
import urllib.request

# NAD83 SPCS EPSG codes — meters-based canonical definitions
# Sources: EPSG registry, epsg.io
SPCS_EPSG_CODES = [
    # Alabama
    26929, 26930,
    # Alaska
    26931, 26932, 26933, 26934, 26935, 26936, 26937, 26938, 26939, 26940,
    # Arizona
    26948, 26949, 26950,
    # Arkansas
    26951, 26952,
    # California
    26941, 26942, 26943, 26944, 26945, 26946,
    # Colorado
    26953, 26954, 26955,
    # Connecticut
    26956,
    # Delaware
    26957,
    # Florida
    26958, 26959, 26960,
    # Georgia
    26966, 26967,
    # Hawaii
    26961, 26962, 26963, 26964, 26965,
    # Idaho
    26968, 26969, 26970,
    # Illinois
    26971, 26972,
    # Indiana
    26973, 26974,
    # Iowa
    26975, 26976,
    # Kansas
    26977, 26978,
    # Kentucky
    26979, 26980,
    # Louisiana
    26981, 26982,
    # Maine
    26983, 26984,
    # Maryland
    26985,
    # Massachusetts
    26986, 26987,
    # Michigan
    26988, 26989, 26990,
    # Minnesota
    26991, 26992, 26993,
    # Mississippi
    26994, 26995,
    # Missouri
    26996, 26997, 26998,
    # Montana
    32100,
    # Nebraska
    32104,
    # Nevada
    32107, 32108, 32109,
    # New Hampshire
    32110,
    # New Jersey
    32111,
    # New Mexico
    32112, 32113, 32114,
    # New York
    32115, 32116, 32117, 32118,
    # North Carolina
    32119,
    # North Dakota
    32120, 32121,
    # Ohio
    32122, 32123,
    # Oklahoma
    32124, 32125,
    # Oregon
    32126, 32127,
    # Pennsylvania
    32128, 32129,
    # Rhode Island
    32130,
    # South Carolina
    32133,
    # South Dakota
    32134, 32135,
    # Tennessee
    32136,
    # Texas
    32137, 32138, 32139, 32140, 32141,
    # Utah
    32142, 32143, 32144,
    # Vermont
    32145,
    # Virginia
    32146, 32147,
    # Washington
    32148, 32149,
    # West Virginia
    32150, 32151,
    # Wisconsin
    32152, 32153, 32154,
    # Wyoming
    32155, 32156, 32157, 32158,
    # Puerto Rico / US Virgin Islands
    32161,
]

# State abbreviation mapping from EPSG name
# Pattern: "NAD83 / <State> <Zone>" or "NAD83 / <Territory>"
STATE_ABBREVS = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE",
    "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
    "Puerto Rico": "PR", "Guam": "GU", "Virgin Islands": "VI",
}


def _urlopen(url: str) -> bytes:
    """Open a URL with a proper User-Agent header."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "cogokit-spcs-fetcher/1.0 (surveying library)"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()


def fetch_zone(epsg: int) -> dict | None:
    """Fetch a single zone definition from epsg.io."""
    proj4_url = f"https://epsg.io/{epsg}.proj4"
    json_url = f"https://epsg.io/{epsg}.json"

    try:
        proj4 = _urlopen(proj4_url).decode().strip()
        data = json.loads(_urlopen(json_url).decode())

        name = data.get("name", "")

        # Extract state and zone from name
        # Pattern: "NAD83 / <State> <zone info>"
        # Sort by length descending so "West Virginia" matches before "Virginia"
        state_abbrev = ""
        zone_name = ""
        for state_full, abbrev in sorted(
            STATE_ABBREVS.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if state_full in name:
                state_abbrev = abbrev
                # Zone is everything after the state name
                after = name.split(state_full, 1)[1].strip()
                zone_name = after
                break

        return {
            "name": name,
            "state": state_abbrev,
            "zone": zone_name,
            "proj4": proj4,
        }
    except Exception as exc:
        print(f"  FAILED {epsg}: {exc}")
        return None


def main():
    zones = {}
    failed = []
    for code in SPCS_EPSG_CODES:
        print(f"Fetching EPSG:{code}...")
        result = fetch_zone(code)
        if result:
            zones[str(code)] = result
        else:
            failed.append(code)
        time.sleep(0.3)  # rate limit

    # Retry failed codes once
    if failed:
        print(f"\nRetrying {len(failed)} failed codes...")
        time.sleep(2)
        for code in failed:
            print(f"  Retrying EPSG:{code}...")
            result = fetch_zone(code)
            if result:
                zones[str(code)] = result
            time.sleep(0.5)

    out_path = "src/cogokit/data/spcs_zones.json"
    with open(out_path, "w") as f:
        json.dump(zones, f, indent=2, sort_keys=True)

    print(f"\nWrote {len(zones)} zones to {out_path}")


if __name__ == "__main__":
    main()
