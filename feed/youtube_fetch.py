#!/usr/bin/env python3
"""Holt die aktuell meistgesehenen YouTube-Videos und Shorts je Rubrik.

Aufruf:
    YOUTUBE_API_KEY=... python3 feed/youtube_fetch.py
    python3 feed/youtube_fetch.py --out /tmp/test.json          # anderes Ziel
    YOUTUBE_API_KEY=... python3 feed/youtube_fetch.py --dump roh.json   # Rohdaten zusätzlich sichern
    python3 feed/youtube_fetch.py --aus-dump roh.json           # ohne API neu bewerten (Filter testen)

Ergebnis: youtube/aktuell.json (nur der aktuelle Stand, wird jedes Mal überschrieben).
Der Schlüssel kommt ausschließlich aus der Umgebungsvariable YOUTUBE_API_KEY und wird
nie ausgegeben oder gespeichert. Suchbegriffe, Filter und Grenzwerte stehen in feed/youtube_config.json.

Ablauf: Je Rubrik mehrere Suchen (sortiert nach Aufrufen, nur Videos der letzten Tage),
danach Statistik und Metadaten aller Treffer abrufen. Dann werden Treffer aussortiert, die nicht
zu den Rubriken passen (YouTube-Kategorie, Sprache, Stichwörter), nach Aufrufen pro Tag
bewertet und die besten je Rubrik und Format behalten. Kosten: etwa 100 Quota-Einheiten pro
Suche, das Tageslimit liegt bei 10 000. Das Filtern selbst kostet nichts.
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
ISO_ZEIT = "%Y-%m-%dT%H:%M:%SZ"

METHODE = (
    "Gesucht wird je Rubrik nach den meistgesehenen Videos der letzten {tage} Tage. Aussortiert werden Treffer, "
    "die thematisch nicht zur Rubrik passen (Stichwörter in Titel und Tags, YouTube-Kategorie, Sprache). "
    "Die Rangfolge richtet sich nach Aufrufen pro Tag seit der Veröffentlichung, damit neue Videos "
    "mit schnellem Zulauf vor älteren stehen. Als Short gilt ein Video bis {kurz} Sekunden Länge. "
    "Die Zuordnung zu Rubriken ist automatisch und kann danebenliegen."
)


class QuotaFehler(Exception):
    pass


# ---------------------------------------------------------------- API

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
    """Statistik, Dauer, Titel und Tags für beliebig viele Video-IDs (50 pro Abruf)."""
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


# ---------------------------------------------------------------- Filter

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


def muster(woerter):
    """Wortliste -> Regex. Ein '*' am Ende erlaubt beliebige Endungen (camera* trifft cameras)."""
    teile = []
    for w in woerter:
        w = w.strip().lower()
        if not w:
            continue
        stern = w.endswith("*")
        teile.append(r"(?<!\w)" + re.escape(w.rstrip("*")) + ("" if stern else r"(?!\w)"))
    return re.compile("|".join(teile)) if teile else None


def lateinisch(text):
    """Anteil lateinischer Buchstaben im Titel (filtert Titel in Devanagari, Tamil, Bengali usw.)."""
    buchstaben = [c for c in text if c.isalpha()]
    if not buchstaben:
        return 1.0
    return sum(1 for c in buchstaben if ord(c) < 0x250) / len(buchstaben)


class Filter:
    def __init__(self, cfg):
        self.kat_ok = set(cfg.get("kategorien_erlaubt", []))
        self.sprachen = {s.lower() for s in cfg.get("sprachen", [])}
        self.global_aus = muster(cfg.get("ausschliessen", []))
        self.rub = {}
        for kat, c in cfg["rubriken"].items():
            self.rub[kat] = {
                "muss": muster(c.get("muss_enthalten", [])),
                "und": muster(c.get("und_enthalten", [])),
                "aus": muster(c.get("ausschliessen", [])),
            }

    def allgemein(self, sn):
        """Prüfungen, die nicht von der Rubrik abhängen. Gibt einen Grund zurück oder None."""
        if self.kat_ok and sn.get("categoryId") not in self.kat_ok:
            return "kategorie"
        sprache = (sn.get("defaultAudioLanguage") or sn.get("defaultLanguage") or "").split("-")[0].lower()
        if self.sprachen and sprache and sprache not in self.sprachen:
            return "sprache"
        if lateinisch(sn.get("title", "")) < 0.7:
            return "schrift"
        return None

    def passt(self, kat, text, voll):
        """text: Titel ohne Hashtags (bei Videos plus Tags) für die Stichwörter,
        voll: Titel mit Hashtags plus Tags für die Ausschlüsse."""
        r = self.rub[kat]
        if r["muss"] and not r["muss"].search(text):
            return False
        if r["und"] and not r["und"].search(text):
            return False
        if r["aus"] and r["aus"].search(voll):
            return False
        return True


def bewerten(cfg, gefunden, info, jetzt):
    """Filtert und bewertet die Rohdaten. Gibt (items, Statistik der aussortierten) zurück."""
    kurz_max = int(cfg.get("short_max_sekunden", 180))
    reihenfolge = list(cfg["rubriken"].keys())
    flt = Filter(cfg)
    grund = collections.Counter()
    kandidaten = collections.defaultdict(list)
    schw_cfg = cfg.get("schwerpunkte", {})
    schw_muster = {sid: muster(c.get("begriffe", [])) for sid, c in schw_cfg.items()}
    schw_pool = collections.defaultdict(list)

    for vid, kats in gefunden.items():
        v = info.get(vid)
        if not v:
            grund["nicht abrufbar"] += 1
            continue
        sn, st, cd = v.get("snippet", {}), v.get("statistics", {}), v.get("contentDetails", {})
        if sn.get("liveBroadcastContent", "none") != "none":
            grund["live"] += 1
            continue
        aufrufe = zahl(st.get("viewCount"))
        sek = dauer_sekunden(cd.get("duration"))
        if aufrufe is None or sek <= 0:
            grund["ohne Zahlen"] += 1
            continue
        fmt = "short" if sek <= kurz_max else "video"
        g = flt.allgemein(sn)
        if g:
            grund[g] += 1
            continue
        titel = html.unescape(sn.get("title", "")).strip()
        tags = " ".join(sn.get("tags", []))
        ohne_hashtags = re.sub(r"#\w+", " ", titel)
        # Shorts: nur der Titel zählt (Hashtag- und Tag-Spam ist dort üblich), Videos: Titel plus Tags
        text = (ohne_hashtags if fmt == "short" else ohne_hashtags + " " + tags).lower()
        voll = (titel + " " + tags).lower()
        if flt.global_aus and flt.global_aus.search(voll):
            grund["ausschluss"] += 1
            continue
        # nur Rubriken, in deren Suchen das Video aufgetaucht ist, in der Reihenfolge der Konfiguration
        passend = [k for k in reihenfolge if k in kats and flt.passt(k, text, voll)]
        if not passend:
            grund["Stichwörter"] += 1
            continue
        mindest = {**cfg["min_aufrufe"], **cfg["rubriken"][passend[0]].get("min_aufrufe", {})}
        flaggen = [sid for sid, m in schw_muster.items() if m and m.search(voll)]
        normal_ok = aufrufe >= int(mindest[fmt])
        schw_ok = [sid for sid in flaggen if aufrufe >= int(schw_cfg[sid].get("min_aufrufe", 0))]
        if not normal_ok and not schw_ok:
            grund["zu wenig Aufrufe"] += 1
            continue
        try:
            veroeff = dt.datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            grund["ohne Datum"] += 1
            continue
        alter_h = max((jetzt - veroeff).total_seconds() / 3600, 0)
        trend = aufrufe / ((alter_h + 12) / 24)  # Aufrufe pro Tag, neue Videos nicht überbewertet
        kat = passend[0]
        eintrag = {
            "id": vid,
            "kat": kat,
            "format": fmt,
            "titel": titel,
            "kanal": html.unescape(sn.get("channelTitle", "")).strip(),
            "veroeffentlicht": veroeff.strftime(ISO_ZEIT),
            "dauer_s": sek,
            "aufrufe": aufrufe,
            "likes": zahl(st.get("likeCount")),
            "kommentare": zahl(st.get("commentCount")),
            "trend": round(trend, 1),
        }
        if flaggen:
            eintrag["schwerpunkt"] = flaggen[0]
        if normal_ok:
            kandidaten[(kat, fmt)].append(eintrag)
        for sid in schw_ok:
            schw_pool[sid].append(eintrag)

    items = []
    max_kanal = int(cfg.get("max_pro_kanal", 2))
    gesehen = set()  # gleiche Titel (oft mehrfach hochgeladen) nur einmal
    for kat in reihenfolge:
        for fmt in ("video", "short"):
            liste = sorted(kandidaten.get((kat, fmt), []), key=lambda x: x["trend"], reverse=True)
            ziel = int({**cfg["treffer_pro_rubrik"], **cfg["rubriken"][kat].get("treffer", {})}[fmt])
            je_kanal = collections.Counter()
            gewaehlt = []
            for it in liste:
                schluessel = re.sub(r"\W+", " ", it["titel"].lower()).strip()
                if schluessel in gesehen:
                    grund["Dublette"] += 1
                    continue
                if je_kanal[it["kanal"]] >= max_kanal:
                    grund["Kanal-Limit"] += 1
                    continue
                gesehen.add(schluessel)
                je_kanal[it["kanal"]] += 1
                gewaehlt.append(it)
                if len(gewaehlt) >= ziel:
                    break
            items += gewaehlt
    # Schwerpunkte: die besten Treffer kommen auch dann hinein, wenn sie in ihrer Rubrik nicht unter die ersten fallen
    drin = {it["id"] for it in items}
    for sid, pool in schw_pool.items():
        pool = sorted(pool, key=lambda x: x["trend"], reverse=True)[: int(schw_cfg[sid].get("treffer", 8))]
        for it in pool:
            if it["id"] in drin:
                continue
            schluessel = re.sub(r"\W+", " ", it["titel"].lower()).strip()
            if schluessel in gesehen:
                continue
            gesehen.add(schluessel)
            drin.add(it["id"])
            items.append(it)
    return items, grund


# ---------------------------------------------------------------- Ablauf

def sammeln(cfg, key, seit):
    """Alle Suchen ausführen. Gibt (gefunden, Anzahl Suchen, Hinweis) zurück."""
    pro_suche = int(cfg.get("ergebnisse_pro_suche", 25))
    gefunden = collections.OrderedDict()
    n = 0
    hinweis = None
    quellen = [(kat, c) for kat, c in cfg["rubriken"].items()]
    quellen += [(c.get("rubrik", "ki"), c) for c in cfg.get("schwerpunkte", {}).values()]
    try:
        for kat, c in quellen:
            for kurz, liste in ((False, c.get("suchen", [])), (True, c.get("shorts_suchen", []))):
                for begriff in liste:
                    n += 1
                    try:
                        for vid in suchen(key, begriff, seit, pro_suche, kurz):
                            gefunden.setdefault(vid, [])
                            if kat not in gefunden[vid]:
                                gefunden[vid].append(kat)
                    except RuntimeError as e:
                        print(f"Warnung: Suche '{begriff}' ({kat}) übersprungen: {e}", file=sys.stderr)
    except QuotaFehler as e:
        hinweis = "Tageslimit der YouTube-API erreicht, die Liste ist unvollständig."
        print(f"Quota erschöpft nach {n} Suchen: {e}", file=sys.stderr)
    return gefunden, n, hinweis


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=OUT, help="Zieldatei (Standard: youtube/aktuell.json)")
    ap.add_argument("--config", type=pathlib.Path, default=CONFIG)
    ap.add_argument("--dump", type=pathlib.Path, help="Rohdaten der API-Abrufe zusätzlich in diese Datei schreiben")
    ap.add_argument("--aus-dump", type=pathlib.Path, help="Rohdaten aus dieser Datei lesen statt die API abzurufen")
    args = ap.parse_args()

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    tage = int(cfg.get("tage", 14))
    kurz_max = int(cfg.get("short_max_sekunden", 180))
    hinweis = None
    suchen_n = 0

    if args.aus_dump:
        roh = json.loads(args.aus_dump.read_text(encoding="utf-8"))
        jetzt = dt.datetime.strptime(roh["jetzt"], ISO_ZEIT).replace(tzinfo=dt.timezone.utc)
        gefunden, info = roh["gefunden"], roh["info"]
        suchen_n = roh.get("suchen", 0)
        hinweis = roh.get("hinweis")
    else:
        key = os.environ.get("YOUTUBE_API_KEY", "").strip()
        if not key:
            print("YOUTUBE_API_KEY ist nicht gesetzt.", file=sys.stderr)
            return 1
        jetzt = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        seit = (jetzt - dt.timedelta(days=tage)).strftime(ISO_ZEIT)
        gefunden, suchen_n, hinweis = sammeln(cfg, key, seit)
        if hinweis:
            print("Abbruch: unvollständige Daten werden nicht veröffentlicht, youtube/aktuell.json bleibt unverändert. "
                  "Das Tageslimit setzt sich täglich um 9 Uhr Zürcher Zeit (Mitternacht Pazifikzeit) zurück.", file=sys.stderr)
            return 1
        if not gefunden:
            print("Keine Treffer gefunden, youtube/aktuell.json bleibt unverändert.", file=sys.stderr)
            return 1
        try:
            info = details(key, gefunden.keys())
        except QuotaFehler as e:
            print(f"Quota erschöpft beim Abruf der Statistik: {e}", file=sys.stderr)
            return 1
        if args.dump:
            args.dump.parent.mkdir(parents=True, exist_ok=True)
            args.dump.write_text(json.dumps({
                "jetzt": jetzt.strftime(ISO_ZEIT), "suchen": suchen_n, "hinweis": hinweis,
                "gefunden": gefunden, "info": info,
            }, ensure_ascii=False), encoding="utf-8")

    items, grund = bewerten(cfg, gefunden, info, jetzt)
    print(f"{len(gefunden)} Kandidaten aus {suchen_n} Suchen. Aussortiert: " +
          (", ".join(f"{k} {n}" for k, n in grund.most_common()) or "nichts"))
    if not items:
        print("Nach dem Filtern blieb kein Video übrig, youtube/aktuell.json bleibt unverändert.", file=sys.stderr)
        return 1

    ausgabe = {
        "stand": jetzt.astimezone(ZEIT).strftime("%Y-%m-%d"),
        "erzeugt": jetzt.strftime(ISO_ZEIT),
        "tage": tage,
        "quelle": "YouTube Data API v3",
        "methode": METHODE.format(tage=tage, kurz=kurz_max),
        "items": items,
    }
    if cfg.get("schwerpunkte"):
        ausgabe["schwerpunkte"] = {sid: c["label"] for sid, c in cfg["schwerpunkte"].items()}
    if hinweis:
        ausgabe["hinweis"] = hinweis
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(ausgabe, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    je = collections.Counter((i["kat"], i["format"]) for i in items)
    for sid in cfg.get("schwerpunkte", {}):
        print(f"  Schwerpunkt {sid}: {sum(1 for i in items if i.get('schwerpunkt') == sid)} Einträge")
    print(f"{len(items)} Einträge geschrieben (etwa {suchen_n * 100 + 1 + len(gefunden) // 50} Quota-Einheiten)")
    for kat in cfg["rubriken"]:
        print(f"  {kat:10s} {je[(kat, 'video')]} Videos, {je[(kat, 'short')]} Shorts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
