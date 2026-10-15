#!/usr/bin/env python3
"""Baut die Wochenblick-Seite aus den JSON-Ausgaben.

Aufruf:
    python3 feed/build.py            # prüft ausgaben/*.json und schreibt dist/
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
KEEP = 12  # so viele Ausgaben stecken in der Seite

KATEGORIEN = {"broadcast", "kamera", "drohnen", "schnitt", "ki", "foto"}
TYPEN = {"news", "update", "geruecht"}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
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


def main():
    nur_pruefen = "--check" in sys.argv[1:]
    ausgaben, fehler = laden()
    if fehler:
        print("Fehler in den Ausgaben:", file=sys.stderr)
        for f in fehler:
            print(f"  - {f}", file=sys.stderr)
        return 1
    if not ausgaben:
        print("Keine Ausgabe in ausgaben/*.json gefunden.", file=sys.stderr)
        return 1
    if nur_pruefen:
        print(f"OK: {len(ausgaben)} Ausgabe(n), neueste {ausgaben[-1]['key']} mit {len(ausgaben[-1]['items'])} Meldungen")
        return 0

    vorlage = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in vorlage:
        print(f"Platzhalter {PLACEHOLDER} fehlt in {TEMPLATE}", file=sys.stderr)
        return 1
    # '</' maskieren, damit Inhalte das <script>-Element nicht beenden können
    daten = json.dumps(ausgaben[-KEEP:], ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    artifact = vorlage.replace(PLACEHOLDER, daten)

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
    print(f"Gebaut: {neueste['key']} ({len(neueste['items'])} Meldungen), {min(len(ausgaben), KEEP)} Ausgabe(n) in docs/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
