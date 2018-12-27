Startet eine Umfrage die sichtbar für alle Nutzer in diesem Kanal ist. Der auf
den Text folgende Befehl wird als Nachricht für die Umfrage verwendet.

Standardmäßig wird eine Ja/Nein Umfrage erstellt:
```
{command} Mögt ihr Schokolade?
```
Die Nachricht kann mit Markdown formatierten Text enthalten.

Anstelle von Ja/Nein können auch eigene Auswahlmöglichkeiten angeben werden.
Die Auswahlmöglichkeiten müssen mit einem `--` getrennt werden:
```
{command} Was ist eure Lieblingsfarbe? --Rot --Grün --Blau
```
Zusätzlich gibt es einige spezielle Optionen, die das Erscheinungsbild oder
Verhalten der Umfrage ändern:

- `--progress`: Die Anzahl der Stimmen wird bereits während der Umfrage angezeigt.
- `--noprogress`: Die Anzahl der Stimmen wird nicht angezeigt bis die Umfrage beendet wurde.
- `--public`: Zeigt am Ende der Umfrage an welcher Benutzer für was gestimmt hat.
- `--anonym`: Zeigt am Ende der Umfrage nicht an welcher Benutzer für was gestimmt hat.
- `--votes=X`: Erlaubt Benutzern X Stimmen zu vergeben (Standardmäßig eine Stimme). Jede Auswahlmöglichkeiten kann trotzdem nur einmal gewählt werden.
- `--bars`: Zeigt das Ergebnis der Umfrage als Balkendiagramm an.
- `--nobars`: Das Balkendiagramm am Ende der Umfrage wird nicht angezeigt.
- `--locale=X`: Verwendet die angegebene Sprache für die Umfrage. Unterstützte Werte sind de und en. Standardmäßig wird die Sprache Ihres Kontos verwendet.

Jede dieser Optionen muss klein geschrieben werden und alleine auftauchen, zum Beispiel: 
```
{command} Bitte wählt eure Bestellung --Pizza --Burger --Fries --public --votes=3
```
