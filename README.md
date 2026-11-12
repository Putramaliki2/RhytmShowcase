# RhythmShowcase

RhythmShowcase is a small full-stack rhythm-game music catalog MVP. It uses
HTML/CSS/JavaScript, a Python standard-library HTTP server, and SQLite; no
third-party packages are required.

## Project structure

- `user/` — public landing page, catalog, song detail, registration/login.
- `admin/` — admin login, review dashboard/editor, game management, settings.
- `assets/` — shared browser logic and styles.
- `server/app.py` — HTTP API, SQLite persistence, authentication, and seed data.
- `tests/` — five unit-test modules for business rules.
- `data/` — created automatically for the local SQLite database and ignored by Git.

## Main routes

- `/` — user landing page
- `/user/catalog.html` — searchable and filterable song catalog
- `/user/detail.html?id=1` — song details and community reviews
- `/user/register.html` and `/user/login.html` — user account flows
- `/admin/login.html` — administrator sign-in
- `/admin/dashboard.html` — editorial review dashboard
- `/admin/review.html` — create/edit a draft or published review
- `/admin/games.html` — activate/deactivate catalog games
- `/admin/settings.html` — persisted MVP preferences
