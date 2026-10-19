#!/usr/bin/env python3
"""Baut die Wochenblick-Seite aus den JSON-Ausgaben.

Aufruf:
    python3 feed/build.py            # prüft ausgaben/*.json (und youtube/aktuell.json) und schreibt docs/
    python3 feed/build.py --check    # nur prüfen, nichts schreiben

Ergebnis:
    docs/index.html      die komplette Seite als eigenständige HTML-Datei
                         (wird per GitHub Pages aus dem Ordner /docs veröffentlicht)
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "feed" / "template.html"
AUSGABEN = ROOT / "ausgaben"
DOCS = ROOT / "docs"
PLACEHOLDER = "/*__DATA__*/[]"
YOUTUBE = ROOT / "youtube" / "aktuell.json"  # Reiter "Best of YouTube", erzeugt von feed/youtube_fetch.py
PLACEHOLDER_YT = "/*__YT__*/null"
KEEP = 12  # so viele Ausgaben stecken in der Seite

KATEGORIEN = {"broadcast", "kamera", "licht", "drohnen", "schnitt", "ki", "foto"}
TYPEN = {"news", "update", "geruecht"}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_ZEIT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MAX_SCHLAGZEILEN = 5


def fehler_sammeln(pfad, ausgabe):
    f = []

    def fehlt(obj, feld, typ, wo):
        if feld not in obj or not isinstance(obj[feld], typ) or obj[feld] in ("", None):
            f.append(f"{pfad.name}: {wo}: Feld '{feld}' fehlt oder hat den falschen Typ")
            return True
        return False

    for feld, typ in (("jahr", int), ("kw", int), ("von", str), ("bis", str), ("stand", str), ("intro", str), ("items", list)):
        fehlt(ausgabe, feld, typ, "Kopf")
    for feld in ("von", "bis", "stand"):
        if isinstance(ausgabe.get(feld), str) and not ISO.match(ausgabe[feld]):
            f.append(f"{pfad.name}: '{feld}' ist kein Datum im Format JJJJ-MM-TT")

    ids = set()
    schlagzeilen = 0
    for i, it in enumerate(ausgabe.get("items", []), start=1):
        wo = f"Meldung {i}"
        for feld in ("id", "kat", "typ", "titel", "kurz", "quelle", "url"):
            fehlt(it, feld, str, wo)
        iid = it.get("id", "")
        if iid and not SLUG.match(iid):
            f.append(f"{pfad.name}: {wo}: id '{iid}' ist kein Slug (a-z, 0-9, -)")
        if iid in ids:
            f.append(f"{pfad.name}: {wo}: id '{iid}' kommt doppelt vor")
        ids.add(iid)
        if it.get("kat") not in KATEGORIEN:
            f.append(f"{pfad.name}: {wo}: unbekannte Kategorie '{it.get('kat')}'")
        if it.get("typ") not in TYPEN:
            f.append(f"{pfad.name}: {wo}: unbekannter Typ '{it.get('typ')}'")
        if not str(it.get("url", "")).startswith(("http://", "https://")):
            f.append(f"{pfad.name}: {wo}: url muss mit http(s):// beginnen")
        datum = it.get("datum")
        if datum is not None and not (isinstance(datum, str) and ISO.match(datum)):
            f.append(f"{pfad.name}: {wo}: datum muss JJJJ-MM-TT oder null sein")
        if datum is None and not it.get("datum_hinweis"):
            f.append(f"{pfad.name}: {wo}: ohne datum braucht die Meldung ein datum_hinweis")
        if it.get("typ") == "geruecht" and it.get("sicherheit") not in (1, 2, 3):
            f.append(f"{pfad.name}: {wo}: Gerücht braucht sicherheit 1, 2 oder 3")
        if it.get("schlagzeile"):
            schlagzeilen += 1
    if schlagzeilen > MAX_SCHLAGZEILEN:
        f.append(f"{pfad.name}: {schlagzeilen} Schlagzeilen, erlaubt sind höchstens {MAX_SCHLAGZEILEN}")

    for i, t in enumerate(ausgabe.get("termine", []), start=1):
        if not (isinstance(t.get("datum"), str) and ISO.match(t["datum"])) or not t.get("text"):
            f.append(f"{pfad.name}: Termin {i}: datum (JJJJ-MM-TT) und text sind Pflicht")
    return f


def laden():
    ausgaben = []
    fehler = []
    for pfad in sorted(AUSGABEN.glob("*.json")):
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            fehler.append(f"{pfad.name}: kein gültiges JSON ({e})")
            continue
        fehler += fehler_sammeln(pfad, daten)
        if isinstance(daten.get("jahr"), int) and isinstance(daten.get("kw"), int):
            daten["key"] = f"{daten['jahr']}-KW{daten['kw']:02d}"
            ausgaben.append(daten)
    ausgaben.sort(key=lambda a: a["key"])
    return ausgaben, fehler


def youtube_laden():
    """Liest youtube/aktuell.json. Gibt (daten oder None, Fehlerliste) zurück.

    Fehlt die Datei, ist das kein Fehler: Die Seite zeigt dann nur den Wochenblick.
    """
    if not YOUTUBE.exists():
        return None, []
    name = "youtube/aktuell.json"
    try:
        d = json.loads(YOUTUBE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return None, [f"{name}: kein gültiges JSON ({e})"]
    f = []
    if not (isinstance(d.get("stand"), str) and ISO.match(d["stand"])):
        f.append(f"{name}: 'stand' fehlt oder ist kein Datum im Format JJJJ-MM-TT")
    if not (isinstance(d.get("erzeugt"), str) and ISO_ZEIT.match(d["erzeugt"])):
        f.append(f"{name}: 'erzeugt' fehlt oder hat nicht das Format JJJJ-MM-TTThh:mm:ssZ")
    if not isinstance(d.get("tage"), int) or isinstance(d.get("tage"), bool):
        f.append(f"{name}: 'tage' fehlt oder ist keine ganze Zahl")
    if not isinstance(d.get("items"), list) or not d.get("items"):
        f.append(f"{name}: 'items' fehlt oder ist leer")
        return None, f

    def ganz(x):
        return isinstance(x, int) and not isinstance(x, bool) and x >= 0

    ids = set()
    for i, it in enumerate(d["items"], start=1):
        wo = f"{name}: Eintrag {i}"
        if not VIDEO_ID.match(str(it.get("id", ""))):
            f.append(f"{wo}: id ist keine gültige YouTube-Video-ID")
        if it.get("id") in ids:
            f.append(f"{wo}: id '{it.get('id')}' kommt doppelt vor")
        ids.add(it.get("id"))
        if it.get("kat") not in KATEGORIEN:
            f.append(f"{wo}: unbekannte Rubrik '{it.get('kat')}'")
        if it.get("format") not in ("video", "short"):
            f.append(f"{wo}: format muss 'video' oder 'short' sein")
        for feld in ("titel", "kanal"):
            if not isinstance(it.get(feld), str) or not it[feld]:
                f.append(f"{wo}: Feld '{feld}' fehlt")
        if not (isinstance(it.get("veroeffentlicht"), str) and ISO_ZEIT.match(it["veroeffentlicht"])):
            f.append(f"{wo}: veroeffentlicht fehlt oder hat nicht das Format JJJJ-MM-TTThh:mm:ssZ")
        if not ganz(it.get("dauer_s")) or it.get("dauer_s") == 0:
            f.append(f"{wo}: dauer_s muss eine positive ganze Zahl sein")
        if not ganz(it.get("aufrufe")):
            f.append(f"{wo}: aufrufe muss eine ganze Zahl sein")
        for feld in ("likes", "kommentare"):
            if it.get(feld) is not None and not ganz(it.get(feld)):
                f.append(f"{wo}: {feld} muss eine ganze Zahl oder null sein")
        if not isinstance(it.get("trend"), (int, float)) or isinstance(it.get("trend"), bool):
            f.append(f"{wo}: trend muss eine Zahl sein")
    return (None if f else d), f


def main():
    nur_pruefen = "--check" in sys.argv[1:]
    ausgaben, fehler = laden()
    yt, yt_fehler = youtube_laden()
    fehler += yt_fehler
    if fehler:
        print("Fehler in den Ausgaben:", file=sys.stderr)
        for f in fehler:
            print(f"  - {f}", file=sys.stderr)
        return 1
    if not ausgaben:
        print("Keine Ausgabe in ausgaben/*.json gefunden.", file=sys.stderr)
        return 1
    yt_info = f", Best of YouTube mit {len(yt['items'])} Einträgen (Stand {yt['stand']})" if yt else ", kein Best of YouTube"
    if nur_pruefen:
        print(f"OK: {len(ausgaben)} Ausgabe(n), neueste {ausgaben[-1]['key']} mit {len(ausgaben[-1]['items'])} Meldungen{yt_info}")
        return 0

    vorlage = TEMPLATE.read_text(encoding="utf-8")
    for platzhalter in (PLACEHOLDER, PLACEHOLDER_YT):
        if platzhalter not in vorlage:
            print(f"Platzhalter {platzhalter} fehlt in {TEMPLATE}", file=sys.stderr)
            return 1
    # '</' maskieren, damit Inhalte das <script>-Element nicht beenden können
    daten = json.dumps(ausgaben[-KEEP:], ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    yt_daten = json.dumps(yt, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    artifact = vorlage.replace(PLACEHOLDER, daten).replace(PLACEHOLDER_YT, yt_daten)

    standalone = (
        '<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>:root{color-scheme:light}body{margin:0}</style>\n</head>\n<body>\n'
        + artifact + "\n</body>\n</html>\n"
    )

    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(standalone, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    neueste = ausgaben[-1]
    print(f"Gebaut: {neueste['key']} ({len(neueste['items'])} Meldungen), {min(len(ausgaben), KEEP)} Ausgabe(n) in docs/index.html{yt_info}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
