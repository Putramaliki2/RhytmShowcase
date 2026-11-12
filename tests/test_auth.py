import time
import unittest

from server.app import SESSION_SECONDS, hash_password, verify_password
from tests.support import DatabaseTestCase


class AuthenticationTests(DatabaseTestCase):
    def test_password_is_salted_hash_and_verifies(self):
        first = hash_password("password-123")
        second = hash_password("password-123")

        self.assertNotEqual(first, "password-123")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("password-123", first))
        self.assertFalse(verify_password("wrong-password", first))

    def test_registration_normalizes_email_and_rejects_duplicate(self):
        self.assertEqual(self.user["email"], "player@example.com")
        self.assert_api_error(
            409,
            self.database.create_user,
            "PLAYER@example.com",
            "Second Player",
            "DifferentPass123",
        )

    def test_registration_rejects_invalid_email_and_weak_password(self):
        self.assert_api_error(400, self.database.create_user, "not-an-email", "Player", "Password123")
        self.assert_api_error(400, self.database.create_user, "new@example.com", "Player", "short")

    def test_role_mismatch_is_forbidden(self):
        self.assert_api_error(403, self.database.authenticate, self.user["email"], "PlayerPass123", "admin")

    def test_session_is_revoked_on_logout_and_expires(self):
        user, token = self.database.authenticate(self.user["email"], "PlayerPass123", "user")
        self.assertEqual(self.database.current_user(token), user)

        self.database.logout(token)
        self.assertIsNone(self.database.current_user(token))

        _, expired_token = self.database.authenticate(self.user["email"], "PlayerPass123")
        import hashlib
        with self.database.connect() as db:
            db.execute(
                "UPDATE sessions SET expires_at=? WHERE token_hash=?",
                (int(time.time()) - 1, hashlib.sha256(expired_token.encode()).hexdigest()),
            )
        self.assertGreater(SESSION_SECONDS, 0)
        self.assertIsNone(self.database.current_user(expired_token))


if __name__ == "__main__":
    unittest.main()
