# newsfeed

Sammlung und Wochenrückblick der wichtigsten Meldungen.

## Struktur

```
newsfeed/
├── README.md
├── vorlagen/
│   └── wochenrueckblick.md     # Vorlage für jede Woche
├── rueckblicke/
│   └── <Jahr>/
│       └── KW<NN>.md           # ein Rückblick pro Kalenderwoche
└── scripts/
    └── neuer-rueckblick.sh     # erzeugt den Rückblick für eine Woche aus der Vorlage
```

## Neuen Wochenrückblick anlegen

```bash
# aktuelle Kalenderwoche
./scripts/neuer-rueckblick.sh

# bestimmte Woche (ISO-Jahr und Kalenderwoche)
./scripts/neuer-rueckblick.sh 2026 42
```

Das Skript legt `rueckblicke/<Jahr>/KW<NN>.md` an, trägt Kalenderwoche und
Datumsbereich (Montag bis Sonntag) ein und überschreibt keine bestehende Datei.

## Ablauf

1. Während der Woche Meldungen unter „Meldungen" sammeln.
2. Am Ende der Woche Highlights, Einordnung und Ausblick ergänzen.
3. Committen und pushen.
