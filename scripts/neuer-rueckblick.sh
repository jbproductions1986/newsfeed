#!/usr/bin/env bash
# Erzeugt einen neuen Wochenrückblick aus der Vorlage.
#
# Aufruf:
#   ./scripts/neuer-rueckblick.sh            # aktuelle ISO-Kalenderwoche
#   ./scripts/neuer-rueckblick.sh 2026 42    # ISO-Jahr und Kalenderwoche

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VORLAGE="$ROOT/vorlagen/wochenrueckblick.md"

if [[ $# -eq 0 ]]; then
  JAHR="$(date +%G)"
  KW="$(date +%V)"
elif [[ $# -eq 2 ]]; then
  JAHR="$1"
  KW="$(printf '%02d' "$((10#$2))")"
else
  echo "Aufruf: $0 [JAHR KW]" >&2
  exit 1
fi

if [[ ! -f "$VORLAGE" ]]; then
  echo "Vorlage nicht gefunden: $VORLAGE" >&2
  exit 1
fi

# Montag der ISO-Woche: Der 4. Januar liegt immer in KW 1.
JAN4="$JAHR-01-04"
WOCHENTAG_JAN4="$(date -d "$JAN4" +%u)"
MONTAG_KW1="$(date -d "$JAN4 -$((WOCHENTAG_JAN4 - 1)) days" +%F)"
MONTAG="$(date -d "$MONTAG_KW1 +$(( (10#$KW - 1) * 7 )) days" +%F)"
SONNTAG="$(date -d "$MONTAG +6 days" +%F)"

ZIEL_DIR="$ROOT/rueckblicke/$JAHR"
ZIEL="$ZIEL_DIR/KW$KW.md"

if [[ -e "$ZIEL" ]]; then
  echo "Existiert bereits: $ZIEL" >&2
  exit 1
fi

mkdir -p "$ZIEL_DIR"
sed \
  -e "s/{{JAHR}}/$JAHR/g" \
  -e "s/{{KW}}/$KW/g" \
  -e "s/{{VON}}/$(date -d "$MONTAG" +%d.%m.%Y)/g" \
  -e "s/{{BIS}}/$(date -d "$SONNTAG" +%d.%m.%Y)/g" \
  "$VORLAGE" > "$ZIEL"

echo "Angelegt: ${ZIEL#"$ROOT"/}"
