# Redaktionsregeln Wochenblick Bild & Ton

Diese Datei beschreibt, wie jede Montagsausgabe entsteht. Sie ist die Arbeitsanweisung für den
wöchentlichen Lauf (Montag, 9 Uhr Zürcher Zeit) und gilt unverändert für jede Ausgabe, damit die
Struktur gleich bleibt.

## Themen

| id          | Thema             | Inhalt                                                                                     |
|-------------|-------------------|--------------------------------------------------------------------------------------------|
| `broadcast` | Broadcast | **Schwerpunkt:** IP-Technik und Automatisierung in Broadcast und Live-Produktion (ST 2110, IPMX, NDI), Steuerung und Automatisierung (Bitfocus Companion, Stream Deck, ATEM, vMix), Netzwerk im Studio (Ubiquiti UniFi), Messen (NAB, IBC) |
| `kamera`    | Kameras & Audio   | Kameras, Objektive, Firmware, Tests, **Gerüchte zu neuen Kameras**, Audio (Mikrofone, Recorder, Tontechnik) |
| `licht`     | Licht & Beleuchtung | Beleuchtung für Film, Fernsehen und Video: neue Produkte und Firmware von Aputure, Nanlite, ARRI, Creamsource, Godox, Astera, Litepanels, Kino Flo u. a., Lichtsteuerung (DMX, CRMX, App), Lichtformer, Beleuchtung bei Produktionen, Tests und Gerüchte zu neuen Leuchten |
| `drohnen`   | Drohnen & FPV     | DJI und Konkurrenz, FPV, Regulierung mit Einfluss auf Filmer, **Gerüchte zu neuen Drohnen**; Gyroflow nur, wenn es etwas Relevantes gibt (Release, Neuerung) |
| `schnitt`   | Schnitt           | DaVinci Resolve (inkl. Blackmagic Design, Fusion, Fairlight) und Adobe Premiere (inkl. After Effects, Firefly im Videokontext), allgemeine Schnitt-Tools und -Branche |
| `ki`        | KI & Automation   | **Schwerpunkt:** Kamera und Video vereinfachen per KI (Assistenten, Rohschnitt, Automatisierung) |
| `foto`      | Foto              | Fotobearbeitung, Foto-Tools und -Branche, Adobe Photoshop und Lightroom. **Steht in der Ausgabe immer am Schluss.** |

Gerüchte sind keine eigene Kategorie, sondern der Typ `geruecht` innerhalb ihres Themas.
Gyroflow hat kein eigenes Thema mehr: Meldungen dazu erscheinen unter `drohnen`, aber nur bei echter Relevanz.
Audio-Meldungen erscheinen unter `kamera`.

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
- Licht und Beleuchtung: Herstellerseiten und Pressemitteilungen (Aputure, Nanlite, ARRI, Creamsource), CineD, Newsshooter, No Film School, ProVideo Coalition; Neuheiten kommen oft rund um NAB, IBC und Cine Gear
- Drohnen und FPV: DroneXL, DroneDJ, Oscar Liang
- Broadcast: TV Technology, NewscastStudio, TVBEurope; für Companion und Stream Deck bitfocus.io und github.com/bitfocus/companion/releases, für Ubiquiti die UniFi-Releases und community.ui.com
- Schnitt und KI: ProVideo Coalition, Blackmagic-Pressemitteilungen, Adobe-Blog
- Gyroflow (nur bei Relevanz, Thema Drohnen & FPV): github.com/gyroflow/gyroflow/releases

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

## Reiter „Best of YouTube“

Der zweite Reiter der Seite zeigt, was in denselben sieben Rubriken auf YouTube am meisten läuft. Er entsteht
nicht im Montagslauf der Redaktion, sondern automatisch in GitHub Actions (`.github/workflows/best-of-youtube.yml`,
montags 05:30 UTC, also vor der Ausgabe um 9 Uhr).

- **Quelle:** YouTube Data API v3, Schlüssel im Repository-Secret `YOUTUBE_API_KEY`. Der Schlüssel steht nie im Code oder im Chat.
- **Auswahl:** `feed/youtube_fetch.py` sucht je Rubrik mit den Begriffen aus `feed/youtube_config.json`, sortiert nach Aufrufen und
  wertet die Treffer nach Aufrufen pro Tag aus. Je Rubrik bleiben 6 Videos und 4 Shorts, bei Broadcast 4 und 2, weil das Thema
  auf YouTube eher beiläufig interessiert. Als Short gilt ein Video bis 180 Sekunden.
- **Aussortiert** wird, was nicht zur Rubrik passt: falsche YouTube-Kategorie (z. B. Musik), andere Sprache als Englisch, Deutsch,
  Französisch oder Italienisch, fehlende Stichwörter im Titel (bei Videos auch in den Tags), Spam-Hashtags und Fan-Edits.
  Je Kanal erscheinen höchstens 2 Einträge je Rubrik und Format.
- **Schwerpunkt „MCP & KI-Anbindung“:** Videos über MCP-Anbindungen von KI an Schnitt- und Creator-Programme (DaVinci Resolve,
  Lightroom, Premiere, Photoshop, Blender u. a.) stehen in einer eigenen Gruppe ganz oben, tragen die Marke MCP und lassen sich
  mit dem Schalter „Nur MCP & KI-Anbindung“ einzeln anzeigen. Dafür gelten niedrigere Mindestaufrufe, damit auch kleine Fachvideos erscheinen.
- **Anpassen:** Suchbegriffe, Zeitraum (`tage`), Stichwörter, Ausschlüsse, Grenzwerte und Trefferzahl stehen in
  `feed/youtube_config.json`, nicht im Code. Neu bewerten ohne neue API-Abrufe: Workflow mit „dump“ starten, das Artefakt
  `youtube-roh` laden und `python3 feed/youtube_fetch.py --aus-dump roh.json` ausführen.
- **Kontingent:** Ein Lauf kostet etwa 4 500 von 10 000 Einheiten pro Tag. Ist das Tageslimit erschöpft, bricht der Lauf ab und
  lässt `youtube/aktuell.json` unverändert. Das Limit setzt sich täglich um 9 Uhr Zürcher Zeit zurück.
- **Nur der aktuelle Stand:** `youtube/aktuell.json` wird jede Woche überschrieben. Es werden keine älteren Stände archiviert,
  weil die YouTube-Bedingungen das Aufbewahren von API-Daten zeitlich begrenzen.
- **Inhalte:** Es erscheinen nur Titel, Kanal, Kennzahlen und der Link, keine Beschreibungen und keine eigenen Zusammenfassungen.
- **Montagslauf der Redaktion:** Nichts zu tun. `python3 feed/build.py` übernimmt `youtube/aktuell.json` automatisch in die Seite.
  Fehlt die Datei, zeigt die Seite nur den Wochenblick.
