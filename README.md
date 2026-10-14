# Wochenblick Bild & Ton

Wöchentlicher, interaktiver Newsfeed zu Broadcast und Audio, Kameras (inklusive Gerüchte), Drohnen und FPV,
Gyroflow, DaVinci Resolve, Adobe, KI-Vereinfachung in Kamera und Schnitt sowie Video- und Fotobearbeitung.

**Online:** https://jbproductions1986.github.io/newsfeed/

Neue Ausgabe jeden Montag. Die Seite hat Themenfilter (der Farbbalken oben ist ebenfalls klickbar),
Suche, Filter nach News, Updates und Gerüchten, eine Gerüchte-Einstufung, Schlagzeilen, einen
Terminplan und Markierung gelesener Meldungen.

## Aufbau

```
newsfeed/
├── ausgaben/            # eine JSON-Datei pro Woche, z. B. 2026-KW42.json
├── docs/                # fertige Seite (index.html), wird per GitHub Pages veröffentlicht
├── feed/
│   ├── template.html    # Layout und Bedienung der Seite
│   └── build.py         # prüft die JSON-Dateien und baut docs/index.html
└── REDAKTION.md         # Themen, Qualitätsregeln, Schema, Ablauf jeder Ausgabe
```

## Lokal bauen

```bash
python3 feed/build.py          # prüfen und docs/index.html schreiben
python3 feed/build.py --check  # nur prüfen
```

Der wöchentliche Lauf folgt den Regeln in `REDAKTION.md`.
