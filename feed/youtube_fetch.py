#!/usr/bin/env python3
"""Holt die aktuell meistgesehenen YouTube-Videos und Shorts je Rubrik.

Aufruf:
    YOUTUBE_API_KEY=... python3 feed/youtube_fetch.py
    python3 feed/youtube_fetch.py --out /tmp/test.json   # anderes Ziel

Ergebnis: youtube/aktuell.json (nur der aktuelle Stand, wird jedes Mal überschrieben).
Der Schlüssel kommt ausschließlich aus der Umgebungsvariable YOUTUBE_API_KEY und wird
nie ausgegeben oder gespeichert. Suchbegriffe und Grenzwerte stehen in feed/youtube_config.json.

Ablauf: Je Rubrik mehrere Suchen (sortiert nach Aufrufen, nur Videos der letzten Tage),
danach die Statistik aller Treffer abrufen, nach Aufrufen pro Tag (Trend) bewerten und
die besten je Rubrik und Format behalten. Kosten: etwa 100 Quota-Einheiten pro Suche,
das Tageslimit liegt bei 10 000.
"""

import argparse
import collections
import datetime as dt
import html
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zoneinfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "feed" / "youtube_config.json"
OUT = ROOT / "youtube" / "aktuell.json"
API = "https://www.googleapis.com/youtube/v3"
ZEIT = zoneinfo.ZoneInfo("Europe/Zurich")
DAUER = re.compile(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")

METHODE = (
    "Gesucht wird je Rubrik nach den meistgesehenen Videos der letzten {tage} Tage. "
    "Die Rangfolge richtet sich nach Aufrufen pro Tag seit der Veröffentlichung, damit neue Videos "
    "mit schnellem Zulauf vor älteren stehen. Als Short gilt ein Video bis {kurz} Sekunden Länge. "
    "Die Zuordnung zu Rubriken folgt den Suchbegriffen und kann danebenliegen."
)


class QuotaFehler(Exception):
    pass


def api_get(endpunkt, params, key):
    """Ein GET gegen die YouTube Data API. Gibt nie die URL (mit Schlüssel) aus."""
    url = f"{API}/{endpunkt}?" + urllib.parse.urlencode({**params, "key": key})
    letzter = None
    for versuch in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            try:
                err = json.load(e).get("error", {})
            except Exception:
                err = {}
            gruende = [x.get("reason") for x in err.get("errors", [])]
            if e.code == 403 and ("quotaExceeded" in gruende or "rateLimitExceeded" in gruende):
                raise QuotaFehler(err.get("message", "Quota erschöpft"))
            if e.code >= 500 and versuch < 2:
                letzter = f"HTTP {e.code}"
                time.sleep(2 * (versuch + 1))
                continue
            raise RuntimeError(f"{endpunkt}: HTTP {e.code} {err.get('message', '')} {gruende}".strip())
        except (urllib.error.URLError, TimeoutError) as e:
            letzter = type(e).__name__
            time.sleep(2 * (versuch + 1))
    raise RuntimeError(f"{endpunkt}: Netzwerkfehler ({letzter})")


def dauer_sekunden(iso):
    m = DAUER.match(iso or "")
    if not m:
        return 0
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s


def zahl(wert):
    try:
        return int(wert)
    except (TypeError, ValueError):
        return None


def suchen(key, begriff, seit, anzahl, kurz=False):
    params = {
        "part": "id",
        "type": "video",
        "q": begriff,
        "order": "viewCount",
        "publishedAfter": seit,
        "maxResults": anzahl,
        "safeSearch": "moderate",
    }
    if kurz:
        params["videoDuration"] = "short"
    daten = api_get("search", params, key)
    return [i["id"]["videoId"] for i in daten.get("items", []) if i.get("id", {}).get("videoId")]


def details(key, ids):
    """Statistik, Dauer und Titel für beliebig viele Video-IDs (50 pro Abruf)."""
    erg = {}
    ids = list(ids)
    for i in range(0, len(ids), 50):
        daten = api_get(
            "videos",
            {"part": "snippet,statistics,contentDetails", "id": ",".join(ids[i:i + 50]), "maxResults": 50},
            key,
        )
        for v in daten.get("items", []):
            erg[v["id"]] = v
    return erg


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=OUT, help="Zieldatei (Standard: youtube/aktuell.json)")
    ap.add_argument("--config", type=pathlib.Path, default=CONFIG)
    args = ap.parse_args()

    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        print("YOUTUBE_API_KEY ist nicht gesetzt.", file=sys.stderr)
        return 1
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    tage = int(cfg.get("tage", 14))
    kurz_max = int(cfg.get("short_max_sekunden", 180))
    pro_suche = int(cfg.get("ergebnisse_pro_suche", 25))
    jetzt = dt.datetime.now(dt.timezone.utc)
    seit = (jetzt - dt.timedelta(days=tage)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1) Kandidaten sammeln: Video-ID -> Rubriken, in denen sie gefunden wurde
    gefunden = collections.OrderedDict()
    suchen_n = 0
    hinweis = None
    try:
        for kat, c in cfg["rubriken"].items():
            for kurz, liste in ((False, c.get("suchen", [])), (True, c.get("shorts_suchen", []))):
                for begriff in liste:
                    suchen_n += 1
                    try:
                        for vid in suchen(key, begriff, seit, pro_suche, kurz):
                            gefunden.setdefault(vid, [])
                            if kat not in gefunden[vid]:
                                gefunden[vid].append(kat)
                    except RuntimeError as e:
                        print(f"Warnung: Suche '{begriff}' ({kat}) übersprungen: {e}", file=sys.stderr)
    except QuotaFehler as e:
        hinweis = "Tageslimit der YouTube-API erreicht, die Liste ist unvollständig."
        print(f"Quota erschöpft nach {suchen_n} Suchen: {e}", file=sys.stderr)

    if not gefunden:
        print("Keine Treffer gefunden, youtube/aktuell.json bleibt unverändert.", file=sys.stderr)
        return 1

    # 2) Statistik holen
    try:
        info = details(key, gefunden.keys())
    except QuotaFehler as e:
        print(f"Quota erschöpft beim Abruf der Statistik: {e}", file=sys.stderr)
        return 1

    # 3) Bewerten und je Rubrik/Format die besten wählen
    reihenfolge = list(cfg["rubriken"].keys())
    kandidaten = collections.defaultdict(list)
    for vid, kats in gefunden.items():
        v = info.get(vid)
        if not v:
            continue
        sn, st, cd = v.get("snippet", {}), v.get("statistics", {}), v.get("contentDetails", {})
        if sn.get("liveBroadcastContent", "none") != "none":
            continue
        aufrufe = zahl(st.get("viewCount"))
        sek = dauer_sekunden(cd.get("duration"))
        if aufrufe is None or sek <= 0:
            continue
        fmt = "short" if sek <= kurz_max else "video"
        if aufrufe < int(cfg["min_aufrufe"][fmt]):
            continue
        try:
            veroeff = dt.datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        alter_h = max((jetzt - veroeff).total_seconds() / 3600, 0)
        trend = aufrufe / ((alter_h + 12) / 24)  # Aufrufe pro Tag, neue Videos nicht überbewertet
        kat = min(kats, key=reihenfolge.index)
        kandidaten[(kat, fmt)].append({
            "id": vid,
            "kat": kat,
            "format": fmt,
            "titel": html.unescape(sn.get("title", "")).strip(),
            "kanal": html.unescape(sn.get("channelTitle", "")).strip(),
            "veroeffentlicht": veroeff.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "dauer_s": sek,
            "aufrufe": aufrufe,
            "likes": zahl(st.get("likeCount")),
            "kommentare": zahl(st.get("commentCount")),
            "trend": round(trend, 1),
        })

    items = []
    for kat in reihenfolge:
        for fmt in ("video", "short"):
            liste = sorted(kandidaten.get((kat, fmt), []), key=lambda x: x["trend"], reverse=True)
            items += liste[: int(cfg["treffer_pro_rubrik"][fmt])]

    if not items:
        print("Nach dem Filtern blieb kein Video übrig, youtube/aktuell.json bleibt unverändert.", file=sys.stderr)
        return 1

    ausgabe = {
        "stand": jetzt.astimezone(ZEIT).strftime("%Y-%m-%d"),
        "erzeugt": jetzt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tage": tage,
        "quelle": "YouTube Data API v3",
        "methode": METHODE.format(tage=tage, kurz=kurz_max),
        "items": items,
    }
    if hinweis:
        ausgabe["hinweis"] = hinweis
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(ausgabe, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    je = collections.Counter((i["kat"], i["format"]) for i in items)
    print(f"{len(items)} Einträge aus {len(gefunden)} Kandidaten ({suchen_n} Suchen, etwa {suchen_n * 100 + 1 + len(gefunden) // 50} Quota-Einheiten)")
    for kat in reihenfolge:
        print(f"  {kat:10s} {je[(kat, 'video')]} Videos, {je[(kat, 'short')]} Shorts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
