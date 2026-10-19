# Wochenblick Bild & Ton

Wöchentlicher, interaktiver Newsfeed zu Broadcast (Schwerpunkt IP-Technik und Automatisierung, dazu Stream Deck, Companion und Ubiquiti), Kameras und Audio (inklusive Gerüchte), Drohnen und FPV
(Gyroflow bei Relevanz), Schnitt mit DaVinci Resolve und Premiere, KI-Vereinfachung in Kamera und Schnitt sowie Foto.

**Online:** https://jbproductions1986.github.io/newsfeed/

Neue Ausgabe jeden Montag. Der zweite Reiter **Best of YouTube** zeigt, was in denselben Rubriken auf YouTube
gerade am meisten läuft (Videos und Shorts, Rangfolge nach Aufrufen pro Tag). Die Seite hat Themenfilter (der Farbbalken oben ist ebenfalls klickbar),
Suche, Filter nach News, Updates und Gerüchten, eine Gerüchte-Einstufung, Schlagzeilen, einen
Terminplan und Markierung gelesener Meldungen.

## Aufbau

```
newsfeed/
├── ausgaben/            # eine JSON-Datei pro Woche, z. B. 2026-KW42.json
├── docs/                # fertige Seite (index.html), wird per GitHub Pages veröffentlicht
├── feed/
│   ├── template.html    # Layout und Bedienung der Seite (beide Reiter)
│   ├── build.py         # prüft die JSON-Dateien und baut docs/index.html
│   ├── youtube_fetch.py # holt Best of YouTube über die YouTube Data API
│   └── youtube_config.json  # Suchbegriffe je Rubrik und Grenzwerte
├── youtube/
│   └── aktuell.json     # aktueller Stand von Best of YouTube (wird überschrieben)
├── .github/workflows/
│   └── best-of-youtube.yml  # Montag früh: abrufen, bauen, veröffentlichen
└── REDAKTION.md         # Themen, Qualitätsregeln, Schema, Ablauf jeder Ausgabe
```

## Lokal bauen

```bash
python3 feed/build.py          # prüfen und docs/index.html schreiben
python3 feed/build.py --check  # nur prüfen
```

Der wöchentliche Lauf folgt den Regeln in `REDAKTION.md`.

Best of YouTube läuft getrennt davon in GitHub Actions und braucht das Repository-Secret `YOUTUBE_API_KEY`
(Settings, Secrets and variables, Actions). Von Hand starten: Actions, „Best of YouTube“, Run workflow.
Lokal: `YOUTUBE_API_KEY=… python3 feed/youtube_fetch.py` und danach `python3 feed/build.py`.
