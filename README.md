# Vacation Planner

Dieses Projekt stellt einen einfachen Urlaubsplaner zur Verfügung, mit dem mehrere Mitarbeitende
selbstständig Urlaubsanträge erstellen können. Gleichzeitig werden individuelle und allgemeine
Restriktionen eingehalten, um Überschneidungen und Überbuchungen zu vermeiden.

## Funktionsumfang

- **Benutzerprofile** mit Jahresurlaubskontingent, Sperrzeiten und optionaler Vorlaufzeit.
- **Globale Regeln** wie allgemeine Sperrzeiten oder erlaubte Monate.
- **Gruppenrestriktionen**, die festlegen, wie viele Personen einer Gruppe gleichzeitig im Urlaub
  sein dürfen.
- Verwaltung und Abfrage bestehender Urlaubsanträge.
- Ermittlung der Restkapazität je Gruppe für einen bestimmten Zeitraum.

## Installation

1. Erstelle ein virtuelles Python-Umfeld (optional):

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Installiere die Test-Abhängigkeiten:

   ```bash
   pip install -r requirements-dev.txt
   ```

   > Hinweis: Die Datei `requirements-dev.txt` enthält lediglich `pytest`.

## Nutzung

Das Modul `vacation_planner` kann direkt aus Python heraus verwendet werden:

```python
from datetime import date

from vacation_planner import GroupRestriction, UserProfile, VacationPlanner

planner = VacationPlanner()
planner.add_user(UserProfile(name="Alice", group="Engineering", annual_quota=30))
planner.add_group_restriction(GroupRestriction(group="Engineering", max_simultaneous=2))

planner.request_vacation("Alice", date(2024, 7, 1), date(2024, 7, 5))
```

Weitere Beispiele finden sich in den Tests unter `vacation_planner/tests/test_planner.py`.

## Tests ausführen

```bash
pytest
```
