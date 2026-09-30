# INNOVXTHON — Exact UI + One Challenge Per Round

## Flow
1. Team enters 01–40.
2. Round 1: select exactly ONE challenge.
3. Admin clicks RESET PARTICIPANT SCREEN.
4. Round 2: select exactly ONE challenge.
5. Admin resets again.
6. Round 3: select exactly ONE challenge.
7. Admin resets again.
8. Round 4: select exactly ONE challenge.
9. DONE — 4 challenges assigned.

The same team cannot select the same challenge twice. Refreshing the participant page does not create another selection. SQLite persists all selections.

## Run
```bash
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000/
Admin: http://127.0.0.1:5000/admin
Admin password: `innovxadmin`

## Admin
- RESET PARTICIPANT SCREEN advances only the active participant team to the next round. It does NOT delete history.
- RESET ALL DATA clears all team selections and starts the system fresh.
- EXPORT CSV downloads the recorded selections.
