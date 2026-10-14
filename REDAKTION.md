# Redaktionsregeln Wochenblick Bild & Ton

Diese Datei beschreibt, wie jede Montagsausgabe entsteht. Sie ist die Arbeitsanweisung für den
wöchentlichen Lauf (Montag, 9 Uhr Zürcher Zeit) und gilt unverändert für jede Ausgabe, damit die
Struktur gleich bleibt.

## Themen

| id          | Thema             | Inhalt                                                                                     |
|-------------|-------------------|--------------------------------------------------------------------------------------------|
| `broadcast` | Broadcast & Audio | Broadcast-Technik, Live-Produktion, Audio, IP-Workflows (ST 2110, IPMX, NDI), Messen (NAB, IBC) |
| `kamera`    | Kameras           | Kameras, Objektive, Firmware, Tests, **Gerüchte zu neuen Kameras**                         |
| `drohnen`   | Drohnen & FPV     | DJI und Konkurrenz, FPV, Regulierung mit Einfluss auf Filmer, **Gerüchte zu neuen Drohnen** |
| `gyroflow`  | Gyroflow          | Releases und Neuigkeiten zu Gyroflow und Stabilisierung per Gyro-Daten                     |
| `resolve`   | DaVinci Resolve   | Resolve, Blackmagic Design, Fusion, Fairlight                                              |
| `adobe`     | Adobe             | Premiere, After Effects, Photoshop, Lightroom, Firefly, Creative Cloud                     |
| `ki`        | KI & Automation   | **Schwerpunkt:** Kamera und Video vereinfachen per KI (Assistenten, Rohschnitt, Automatisierung) |
| `schnitt`   | Schnitt & Foto    | Allgemeines zu Video- und Fotobearbeitung, Tools, Branche                                  |

Gerüchte sind keine eigene Kategorie, sondern der Typ `geruecht` innerhalb ihres Themas.

## Ablauf jeder Ausgabe

1. Letzte Ausgabe lesen (`ausgaben/`), damit nichts doppelt erscheint. Berichtszeitraum ist
   „seit dem Stand der letzten Ausgabe“, höchstens 8 Tage.
2. Pro Thema recherchieren (Websuche, Seiten abrufen). Jede Meldung braucht eine Quelle, die
   tatsächlich gelesen wurde.
3. Neue Datei `ausgaben/<Jahr>-KW<NN>.json` schreiben (Schema unten). `<NN>` ist die ISO-Kalenderwoche
   des Montags, an dem die Ausgabe erscheint.
4. `python3 feed/build.py` ausführen. Das prüft die Daten und schreibt `docs/index.html`.
5. `ausgaben/` und `docs/` committen und nach `main` pushen. GitHub Pages veröffentlicht automatisch.

## Qualitätsregeln

- **Eigene Worte.** Keine Sätze aus Quellen übernehmen, keine Zitate. Zusammenfassen und einordnen.
- **Nichts behaupten, was nicht gelesen wurde.** Wenn nur eine Überschrift verfügbar war, steht in
  `kurz` nur, was die Überschrift hergibt.
- **Datum prüfen.** `datum` ist das Veröffentlichungsdatum der Quelle. Ist es unbekannt: `null` und
  `datum_hinweis` setzen. Ältere, aber noch relevante Einträge bekommen `"hintergrund": true`.
- **Gerüchte einstufen** mit `sicherheit`: 1 = Spekulation oder Einzelquelle, 2 = glaubwürdig
  (mehrere Hinweise, bekannter Leaker, Teaser), 3 = so gut wie bestätigt (offizieller Teaser mit
  Produkt, Händlerlisten, Zulassungen).
- **Schnell lesbar.** `titel` höchstens eine Zeile, `kurz` zwei bis vier Sätze, `warum` ein Satz.
- **Umfang.** 20 bis 35 Meldungen, höchstens 5 Schlagzeilen (`"schlagzeile": true`).
- **Gesponserte Inhalte** als solche kennzeichnen.
- **Keine Meldung erfinden.** Gab es in einem Thema nichts Neues, steht dort nichts oder ein
  Hintergrund-Eintrag mit dem Hinweis „Keine neue Version in dieser Woche“.
- **Termine** (`termine`): Messen, Events, Launch-Daten, Fristen der nächsten Wochen. Vergangene
  Termine fallen in der nächsten Ausgabe heraus.

## Quellen, die sich bewährt haben

- Kameras und Video: CineD, Newsshooter, No Film School
- Gerüchte: Nikon Rumors, Sony Alpha Rumors, Canon Rumors, Fuji Rumors, Photo Rumors (DJI-Gerüchte), Notebookcheck
- Drohnen und FPV: DroneXL, DroneDJ, Oscar Liang
- Broadcast und Audio: TV Technology, NewscastStudio, TVBEurope
- Schnitt und KI: ProVideo Coalition, Blackmagic-Pressemitteilungen, Adobe-Blog
- Gyroflow: github.com/gyroflow/gyroflow/releases

Hinweis: Manche Startseiten (z. B. photorumors.com, fujirumors.com) liefern beim Abruf alte Inhalte.
Dann Kategorieseiten oder die Websuche nutzen und das Datum jedes Beitrags prüfen.

## Schema `ausgaben/<Jahr>-KW<NN>.json`

```json
{
  "jahr": 2026,
  "kw": 43,
  "von": "2026-10-15",
  "bis": "2026-10-19",
  "stand": "2026-10-19",
  "intro": "Zwei bis drei Sätze: Was bestimmt die Woche?",
  "hinweis": "optional, z. B. für Sonderausgaben",
  "termine": [
    { "datum": "2026-10-24", "label": "optional, z. B. 20.–21.10.", "text": "Sigma Produktevent", "geruecht": true }
  ],
  "items": [
    {
      "id": "kurzer-slug",
      "kat": "kamera",
      "typ": "news | update | geruecht",
      "sicherheit": 2,
      "schlagzeile": true,
      "hintergrund": false,
      "titel": "…",
      "kurz": "…",
      "warum": "…",
      "quelle": "CineD",
      "url": "https://…",
      "datum": "2026-10-16",
      "datum_hinweis": "nur wenn datum null ist"
    }
  ]
}
```

`sicherheit` ist nur bei `geruecht` Pflicht. Die Seite zeigt die letzten 12 Ausgaben in einem
Auswahlfeld; ältere Dateien bleiben im Repo erhalten.
