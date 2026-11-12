from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import sys
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
SESSION_COOKIE = "rhythm_session"
SESSION_SECONDS = 60 * 60 * 24 * 7
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class APIError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_hex, digest_hex = encoded.split(":", 1)
        salt = bytes.fromhex(salt_hex)
    except (ValueError, TypeError):
        return False
    expected = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000).hex()
    return hmac.compare_digest(expected, digest_hex)


def validate_email(email: str) -> str:
    if not isinstance(email, str):
        raise APIError(400, "Masukkan alamat email yang valid.")
    email = email.strip().lower()
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        raise APIError(400, "Masukkan alamat email yang valid.")
    return email


def validate_text(value: object, label: str, minimum: int, maximum: int) -> str:
    if not isinstance(value, str):
        raise APIError(400, f"{label} wajib diisi.")
    value = value.strip()
    if not minimum <= len(value) <= maximum:
        raise APIError(400, f"{label} harus berisi {minimum}–{maximum} karakter.")
    return value


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, factory=ClosingConnection)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'admin')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    song_count INTEGER NOT NULL DEFAULT 0 CHECK(song_count >= 0),
                    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
                );
                CREATE TABLE IF NOT EXISTS songs (
                    id INTEGER PRIMARY KEY,
                    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE RESTRICT,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    bpm INTEGER NOT NULL CHECK(bpm BETWEEN 1 AND 999),
                    difficulty TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    duration TEXT NOT NULL DEFAULT '2:45',
                    cover_class TEXT NOT NULL DEFAULT 'cover-blue'
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY,
                    song_id INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
                    author_id INTEGER NOT NULL REFERENCES users(id),
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('draft', 'published')),
                    pros TEXT NOT NULL DEFAULT '[]',
                    cons TEXT NOT NULL DEFAULT '[]',
                    video_url TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS user_reviews (
                    id INTEGER PRIMARY KEY,
                    song_id INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
                    author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(song_id, author_id)
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            db.executemany(
                "INSERT OR IGNORE INTO games(name, song_count, active) VALUES (?, ?, 1)",
                [
                    ("Project Sekai", 34),
                    ("Arcaea", 28),
                    ("Cytus II", 22),
                    ("Muse Dash", 18),
                    ("BanG Dream!", 16),
                ],
            )
            existing = db.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
            if not existing:
                seeded_songs = [
                    ("Project Sekai", "Hatsune Miku Dance", "sasakure.UK", 185, "Veteran", "Enerjik dengan chart yang menantang.", "cover-pink"),
                    ("Arcaea", "Testify", "void (Mournfinale)", 200, "Hard", "Chart cepat dengan transisi tajam.", "cover-violet"),
                    ("Cytus II", "Quantum", "M2U", 175, "Challenge", "Pola ritme dinamis dan presisi.", "cover-blue"),
                    ("BanG Dream!", "U.N. Owen Was Her?", "ZUN", 165, "Normal", "Melodi khas dengan chart yang bersahabat.", "cover-gold"),
                    ("Muse Dash", "World's End", "Camellia", 190, "Hard", "Track cepat untuk pemain berpengalaman.", "cover-green"),
                    ("Arcaea", "Blue Zone", "Street", 160, "Normal", "Ritme konsisten yang cocok untuk latihan.", "cover-cyan"),
                ]
                for song in seeded_songs:
                    game = db.execute("SELECT id FROM games WHERE name = ?", (song[0],)).fetchone()
                    db.execute(
                        """INSERT INTO songs(game_id, title, artist, bpm, difficulty, description, cover_class)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (game["id"], *song[1:]),
                    )
            admin_email = os.getenv("RHYTHM_ADMIN_EMAIL", "admin@rhythmshowcase.local").lower()
            admin_password = os.getenv("RHYTHM_ADMIN_PASSWORD", "ChangeMe123!")
            db.execute(
                "INSERT OR IGNORE INTO users(email, display_name, password_hash, role) VALUES (?, ?, ?, 'admin')",
                (admin_email, "Administrator", hash_password(admin_password)),
            )
            db.executemany(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                [
                    ("confirm_publish", "true"),
                    ("notify_new_reviews", "true"),
                    ("auto_save_draft", "false"),
                ],
            )

    def create_user(self, email: str, display_name: str, password: str) -> dict:
        email = validate_email(email)
        display_name = validate_text(display_name, "Nama", 2, 60)
        if not isinstance(password, str) or len(password) < 8 or len(password) > 128:
            raise APIError(400, "Kata sandi harus berisi 8–128 karakter.")
        with self.connect() as db:
            try:
                cursor = db.execute(
                    "INSERT INTO users(email, display_name, password_hash, role) VALUES (?, ?, ?, 'user')",
                    (email, display_name, hash_password(password)),
                )
            except sqlite3.IntegrityError as exc:
                raise APIError(409, "Email sudah terdaftar.") from exc
            return self.public_user(db.execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone())

    @staticmethod
    def public_user(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        return {"id": row["id"], "email": row["email"], "name": row["display_name"], "role": row["role"]}

    def authenticate(self, email: str, password: str, expected_role: str | None = None) -> tuple[dict, str]:
        email = validate_email(email)
        if not isinstance(password, str):
            raise APIError(401, "Email atau kata sandi salah.")
        with self.connect() as db:
            row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if row is None or not verify_password(password, row["password_hash"]):
                raise APIError(401, "Email atau kata sandi salah.")
            if expected_role and row["role"] != expected_role:
                raise APIError(403, "Akun tidak memiliki akses untuk halaman ini.")
            token = secrets.token_urlsafe(32)
            db.execute(
                "INSERT INTO sessions(token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (hashlib.sha256(token.encode()).hexdigest(), row["id"], int(time.time()) + SESSION_SECONDS),
            )
            return self.public_user(row), token

    def current_user(self, token: str | None) -> dict | None:
        if not token:
            return None
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as db:
            row = db.execute(
                """SELECT users.* FROM sessions JOIN users ON users.id=sessions.user_id
                   WHERE sessions.token_hash=? AND sessions.expires_at>?""",
                (digest, int(time.time())),
            ).fetchone()
            return self.public_user(row)

    def logout(self, token: str | None) -> None:
        if token:
            digest = hashlib.sha256(token.encode()).hexdigest()
            with self.connect() as db:
                db.execute("DELETE FROM sessions WHERE token_hash=?", (digest,))

    def games(self, include_inactive: bool = False) -> list[dict]:
        with self.connect() as db:
            sql = "SELECT id, name, song_count, active FROM games"
            if not include_inactive:
                sql += " WHERE active=1"
            return [dict(row) for row in db.execute(sql + " ORDER BY name")]

    def catalog(self, params: dict[str, list[str]]) -> list[dict]:
        query = params.get("q", [""])[0].strip()
        game_id = params.get("game", [""])[0]
        difficulty = params.get("difficulty", [""])[0].strip()
        try:
            bpm_min = int(params.get("bpmMin", ["0"])[0] or 0)
            bpm_max = int(params.get("bpmMax", ["999"])[0] or 999)
        except ValueError as exc:
            raise APIError(400, "Filter BPM harus berupa angka.") from exc
        if not 0 <= bpm_min <= 999 or not 1 <= bpm_max <= 999 or bpm_min > bpm_max:
            raise APIError(400, "Rentang BPM tidak valid.")
        sql = """SELECT songs.*, games.name AS game, games.active,
                        (SELECT COUNT(*) FROM user_reviews WHERE song_id=songs.id) AS review_count,
                        (SELECT ROUND(AVG(rating), 1) FROM user_reviews WHERE song_id=songs.id) AS rating
                 FROM songs JOIN games ON games.id=songs.game_id WHERE games.active=1"""
        values: list[object] = []
        if query:
            sql += " AND (songs.title LIKE ? OR songs.artist LIKE ? OR games.name LIKE ?)"
            match = f"%{query}%"
            values.extend((match, match, match))
        if game_id:
            try:
                values.append(int(game_id))
            except ValueError as exc:
                raise APIError(400, "Filter game tidak valid.") from exc
            sql += " AND games.id=?"
        if difficulty:
            sql += " AND songs.difficulty = ?"
            values.append(difficulty)
        sql += " AND songs.bpm BETWEEN ? AND ? ORDER BY songs.title"
        values.extend((bpm_min, bpm_max))
        with self.connect() as db:
            return [dict(row) for row in db.execute(sql, values)]

    def song_detail(self, song_id: int) -> dict:
        with self.connect() as db:
            song = db.execute(
                """SELECT songs.*, games.name AS game,
                          (SELECT COUNT(*) FROM user_reviews WHERE song_id=songs.id) AS review_count,
                          (SELECT ROUND(AVG(rating), 1) FROM user_reviews WHERE song_id=songs.id) AS rating
                   FROM songs JOIN games ON games.id=songs.game_id WHERE songs.id=? AND games.active=1""",
                (song_id,),
            ).fetchone()
            if song is None:
                raise APIError(404, "Lagu tidak ditemukan.")
            review = db.execute(
                """SELECT reviews.id, reviews.title, reviews.body, reviews.pros, reviews.cons,
                          reviews.video_url, reviews.updated_at, users.display_name AS author
                   FROM reviews JOIN users ON users.id=reviews.author_id
                   WHERE reviews.song_id=? AND reviews.status='published'
                   ORDER BY reviews.updated_at DESC LIMIT 1""",
                (song_id,),
            ).fetchone()
            public_reviews = [
                dict(row)
                for row in db.execute(
                    """SELECT user_reviews.id, user_reviews.rating, user_reviews.content,
                              user_reviews.created_at, users.display_name AS author
                       FROM user_reviews JOIN users ON users.id=user_reviews.author_id
                       WHERE user_reviews.song_id=? ORDER BY user_reviews.created_at DESC""",
                    (song_id,),
                )
            ]
            result = dict(song)
            if review:
                editorial_review = dict(review)
                editorial_review["pros"] = json.loads(editorial_review["pros"])
                editorial_review["cons"] = json.loads(editorial_review["cons"])
                result["review"] = editorial_review
            else:
                result["review"] = None
            result["community_reviews"] = public_reviews
            return result

    def add_user_review(self, actor: dict, data: dict) -> dict:
        if actor["role"] != "user":
            raise APIError(403, "Hanya akun pengguna yang dapat menulis ulasan.")
        try:
            song_id = int(data.get("song_id"))
            rating = int(data.get("rating"))
        except (ValueError, TypeError) as exc:
            raise APIError(400, "Lagu dan rating wajib diisi.") from exc
        if not 1 <= rating <= 5:
            raise APIError(400, "Rating harus bernilai 1 sampai 5.")
        content = validate_text(data.get("content"), "Ulasan", 10, 1200)
        with self.connect() as db:
            if db.execute("SELECT id FROM songs WHERE id=?", (song_id,)).fetchone() is None:
                raise APIError(404, "Lagu tidak ditemukan.")
            try:
                cursor = db.execute(
                    "INSERT INTO user_reviews(song_id, author_id, rating, content) VALUES (?, ?, ?, ?)",
                    (song_id, actor["id"], rating, content),
                )
            except sqlite3.IntegrityError as exc:
                raise APIError(409, "Kamu sudah mengirim ulasan untuk lagu ini.") from exc
            row = db.execute(
                """SELECT user_reviews.id, rating, content, user_reviews.created_at,
                          users.display_name AS author
                   FROM user_reviews JOIN users ON users.id=user_reviews.author_id WHERE user_reviews.id=?""",
                (cursor.lastrowid,),
            ).fetchone()
            return dict(row)

    def admin_reviews(self, status: str | None = None) -> list[dict]:
        if status and status not in {"draft", "published"}:
            raise APIError(400, "Status review tidak valid.")
        sql = """SELECT reviews.*, songs.title AS song_title, games.name AS game,
                        users.display_name AS author
                 FROM reviews JOIN songs ON songs.id=reviews.song_id
                 JOIN games ON games.id=songs.game_id JOIN users ON users.id=reviews.author_id"""
        values: tuple[object, ...] = ()
        if status:
            sql += " WHERE reviews.status=?"
            values = (status,)
        sql += " ORDER BY reviews.updated_at DESC, reviews.id DESC"
        with self.connect() as db:
            result = []
            for row in db.execute(sql, values):
                item = dict(row)
                item["pros"] = json.loads(item["pros"])
                item["cons"] = json.loads(item["cons"])
                result.append(item)
            return result

    def save_admin_review(self, actor: dict, data: dict, review_id: int | None = None) -> dict:
        if actor["role"] != "admin":
            raise APIError(403, "Akses admin dibutuhkan.")
        try:
            song_id = int(data.get("song_id"))
        except (ValueError, TypeError) as exc:
            raise APIError(400, "Pilih lagu yang valid.") from exc
        title = validate_text(data.get("title"), "Judul", 3, 140)
        body = validate_text(data.get("body"), "Isi review", 20, 8000)
        status = data.get("status", "draft")
        if status not in {"draft", "published"}:
            raise APIError(400, "Status harus draft atau published.")
        pros = self._review_points(data.get("pros", []), "Kelebihan")
        cons = self._review_points(data.get("cons", []), "Kekurangan")
        video_url = data.get("video_url", "")
        if not isinstance(video_url, str) or (video_url and not re.fullmatch(r"https://(www\.)?(youtube\.com/watch\?v=[\w-]{11}|youtu\.be/[\w-]{11})", video_url.strip())):
            raise APIError(400, "URL video YouTube tidak valid.")
        with self.connect() as db:
            if db.execute("SELECT id FROM songs WHERE id=?", (song_id,)).fetchone() is None:
                raise APIError(404, "Lagu tidak ditemukan.")
            if review_id is None:
                cursor = db.execute(
                    """INSERT INTO reviews(song_id, author_id, title, body, status, pros, cons, video_url)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (song_id, actor["id"], title, body, status, json.dumps(pros), json.dumps(cons), video_url.strip()),
                )
                review_id = cursor.lastrowid
            else:
                cursor = db.execute(
                    """UPDATE reviews SET song_id=?, title=?, body=?, status=?, pros=?, cons=?,
                               video_url=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                    (song_id, title, body, status, json.dumps(pros), json.dumps(cons), video_url.strip(), review_id),
                )
                if cursor.rowcount == 0:
                    raise APIError(404, "Review tidak ditemukan.")
            result = db.execute(
                """SELECT reviews.*, songs.title AS song_title, games.name AS game
                   FROM reviews JOIN songs ON songs.id=reviews.song_id
                   JOIN games ON games.id=songs.game_id WHERE reviews.id=?""",
                (review_id,),
            ).fetchone()
            item = dict(result)
            item["pros"] = json.loads(item["pros"])
            item["cons"] = json.loads(item["cons"])
            return item

    @staticmethod
    def _review_points(value: object, label: str) -> list[str]:
        if not isinstance(value, list) or len(value) > 10:
            raise APIError(400, f"{label} harus berupa daftar maksimal 10 poin.")
        return [validate_text(point, label, 2, 160) for point in value]

    def delete_admin_review(self, review_id: int) -> None:
        with self.connect() as db:
            cursor = db.execute("DELETE FROM reviews WHERE id=?", (review_id,))
            if cursor.rowcount == 0:
                raise APIError(404, "Review tidak ditemukan.")

    def dashboard(self) -> dict:
        with self.connect() as db:
            counts = db.execute(
                """SELECT COUNT(*) AS total,
                          SUM(CASE WHEN status='published' THEN 1 ELSE 0 END) AS published,
                          SUM(CASE WHEN status='draft' THEN 1 ELSE 0 END) AS draft
                   FROM reviews"""
            ).fetchone()
            games = db.execute("SELECT COUNT(*) FROM games WHERE active=1").fetchone()[0]
            return {"total_reviews": counts["total"], "published": counts["published"] or 0,
                    "draft": counts["draft"] or 0, "games": games}

    def save_game(self, actor: dict, data: dict, game_id: int | None = None) -> dict:
        if actor["role"] != "admin":
            raise APIError(403, "Akses admin dibutuhkan.")
        name = validate_text(data.get("name"), "Nama game", 2, 80)
        active = data.get("active", True)
        if not isinstance(active, bool):
            raise APIError(400, "Status game tidak valid.")
        with self.connect() as db:
            try:
                if game_id is None:
                    cursor = db.execute("INSERT INTO games(name, active) VALUES (?, ?)", (name, int(active)))
                    game_id = cursor.lastrowid
                else:
                    cursor = db.execute("UPDATE games SET name=?, active=? WHERE id=?", (name, int(active), game_id))
                    if cursor.rowcount == 0:
                        raise APIError(404, "Game tidak ditemukan.")
            except sqlite3.IntegrityError as exc:
                raise APIError(409, "Nama game sudah terdaftar atau game masih memiliki lagu.") from exc
            return dict(db.execute("SELECT id, name, song_count, active FROM games WHERE id=?", (game_id,)).fetchone())

    def save_settings(self, data: dict) -> dict:
        allowed = {"confirm_publish", "notify_new_reviews", "auto_save_draft"}
        if set(data) - allowed or any(not isinstance(value, bool) for value in data.values()):
            raise APIError(400, "Pengaturan harus berisi opsi boolean yang dikenal.")
        with self.connect() as db:
            db.executemany(
                "INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                [(key, json.dumps(value)) for key, value in data.items()],
            )
            return {row["key"]: json.loads(row["value"]) for row in db.execute("SELECT key, value FROM settings")}

    def get_settings(self) -> dict:
        with self.connect() as db:
            return {row["key"]: json.loads(row["value"]) for row in db.execute("SELECT key, value FROM settings")}


def make_handler(database: Database):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, fmt, *args):
            print(f"{self.address_string()} - {fmt % args}", file=sys.stderr)

        def end_headers(self):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            super().end_headers()

        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            path = parsed.path.rstrip("/") or "/"
            try:
                if path == "/":
                    self.path = "/index.html"
                    return super().do_GET()
                if path == "/api/me":
                    return self.respond({"user": database.current_user(self.session_token())})
                if path == "/api/games":
                    return self.respond({"games": database.games()})
                if path == "/api/admin/games":
                    self.require_role("admin")
                    return self.respond({"games": database.games(include_inactive=True)})
                if path == "/api/songs":
                    return self.respond({"songs": database.catalog(params)})
                if path == "/api/dashboard":
                    self.require_role("admin")
                    return self.respond(database.dashboard())
                if path == "/api/admin/reviews":
                    self.require_role("admin")
                    return self.respond({"reviews": database.admin_reviews(params.get("status", [None])[0])})
                if path == "/api/admin/settings":
                    self.require_role("admin")
                    return self.respond(database.get_settings())
                match = re.fullmatch(r"/api/songs/(\d+)", path)
                if match:
                    return self.respond(database.song_detail(int(match.group(1))))
                match = re.fullmatch(r"/api/admin/reviews/(\d+)", path)
                if match:
                    self.require_role("admin")
                    review_id = int(match.group(1))
                    review = next((item for item in database.admin_reviews() if item["id"] == review_id), None)
                    if review is None:
                        raise APIError(404, "Review tidak ditemukan.")
                    return self.respond(review)
                if path.startswith("/api/"):
                    raise APIError(404, "Endpoint tidak ditemukan.")
            except APIError as error:
                return self.respond({"error": error.message}, error.status)
            return super().do_GET()

        def do_POST(self):
            path = urlparse(self.path).path.rstrip("/")
            try:
                data = self.read_json()
                if path == "/api/auth/register":
                    user = database.create_user(data.get("email", ""), data.get("name", ""), data.get("password", ""))
                    user, token = database.authenticate(user["email"], data["password"], "user")
                    return self.respond({"user": user}, headers=[self.cookie_header(token)])
                if path in {"/api/auth/login", "/api/admin/login"}:
                    expected_role = "admin" if path == "/api/admin/login" else data.get("role")
                    user, token = database.authenticate(data.get("email", ""), data.get("password", ""), expected_role)
                    return self.respond({"user": user}, headers=[self.cookie_header(token)])
                if path == "/api/auth/logout":
                    database.logout(self.session_token())
                    return self.respond({"ok": True}, headers=[self.cookie_header("", expired=True)])
                if path == "/api/reviews":
                    actor = self.require_role("user")
                    return self.respond({"review": database.add_user_review(actor, data)}, HTTPStatus.CREATED)
                if path == "/api/admin/reviews":
                    actor = self.require_role("admin")
                    return self.respond({"review": database.save_admin_review(actor, data)}, HTTPStatus.CREATED)
                if path == "/api/admin/games":
                    actor = self.require_role("admin")
                    return self.respond({"game": database.save_game(actor, data)}, HTTPStatus.CREATED)
                if path == "/api/admin/settings":
                    self.require_role("admin")
                    return self.respond({"settings": database.save_settings(data)})
                raise APIError(404, "Endpoint tidak ditemukan.")
            except APIError as error:
                return self.respond({"error": error.message}, error.status)

        def do_PUT(self):
            path = urlparse(self.path).path.rstrip("/")
            try:
                data = self.read_json()
                match = re.fullmatch(r"/api/admin/reviews/(\d+)", path)
                if match:
                    actor = self.require_role("admin")
                    return self.respond({"review": database.save_admin_review(actor, data, int(match.group(1)))})
                match = re.fullmatch(r"/api/admin/games/(\d+)", path)
                if match:
                    actor = self.require_role("admin")
                    return self.respond({"game": database.save_game(actor, data, int(match.group(1)))})
                raise APIError(404, "Endpoint tidak ditemukan.")
            except APIError as error:
                return self.respond({"error": error.message}, error.status)

        def do_DELETE(self):
            path = urlparse(self.path).path.rstrip("/")
            try:
                self.require_role("admin")
                match = re.fullmatch(r"/api/admin/reviews/(\d+)", path)
                if match:
                    database.delete_admin_review(int(match.group(1)))
                    return self.respond({"ok": True})
                raise APIError(404, "Endpoint tidak ditemukan.")
            except APIError as error:
                return self.respond({"error": error.message}, error.status)

        def read_json(self) -> dict:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise APIError(400, "Ukuran request tidak valid.") from exc
            if length <= 0 or length > 1_000_000:
                raise APIError(413 if length > 1_000_000 else 400, "Ukuran data tidak valid.")
            try:
                data = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise APIError(400, "Format JSON tidak valid.") from exc
            if not isinstance(data, dict):
                raise APIError(400, "Body request harus berupa object JSON.")
            return data

        def session_token(self) -> str | None:
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get("Cookie", ""))
                morsel = cookie.get(SESSION_COOKIE)
                return morsel.value if morsel else None
            except Exception:
                return None

        def require_role(self, role: str) -> dict:
            user = database.current_user(self.session_token())
            if not user:
                raise APIError(401, "Silakan masuk terlebih dahulu.")
            if user["role"] != role:
                raise APIError(403, "Akun tidak memiliki akses untuk fitur ini.")
            return user

        def cookie_header(self, token: str, expired: bool = False) -> str:
            value = f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax"
            if expired:
                value += "; Max-Age=0"
            else:
                value += f"; Max-Age={SESSION_SECONDS}"
            return value

        def respond(self, data: dict, status: int = 200, headers: list[str] | None = None):
            content = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(content)))
            for header in headers or []:
                self.send_header("Set-Cookie", header)
            self.end_headers()
            self.wfile.write(content)

    return Handler


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="RhythmShowcase MVP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--database", default=str(ROOT / "data" / "rhythmshowcase.sqlite3"))
    args = parser.parse_args()
    database = Database(args.database)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(database))
    print(f"RhythmShowcase running at http://{args.host}:{args.port}/")
    print("Development admin: admin@rhythmshowcase.local / ChangeMe123!")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping RhythmShowcase.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
