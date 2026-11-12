import tempfile
import unittest
from pathlib import Path

from server.app import APIError, Database


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.sqlite3")
        self.admin, _ = self.database.authenticate(
            "admin@rhythmshowcase.local", "ChangeMe123!", "admin"
        )
        self.user = self.database.create_user("player@example.com", "Player One", "PlayerPass123")
        self.song = self.database.catalog({})[0]

    def tearDown(self):
        self.temp_dir.cleanup()

    def assert_api_error(self, status, function, *args, **kwargs):
        with self.assertRaises(APIError) as context:
            function(*args, **kwargs)
        self.assertEqual(context.exception.status, status)
        return context.exception
