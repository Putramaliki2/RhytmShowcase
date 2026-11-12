from tests.support import DatabaseTestCase


class AdminFeatureTests(DatabaseTestCase):
    def test_dashboard_counts_reviews_games(self):
        self.database.save_admin_review(
            self.admin,
            {"song_id": self.song["id"], "title": "Published review", "body": "This body is long enough to publish.", "status": "published"},
        )
        self.database.save_admin_review(
            self.admin,
            {"song_id": self.song["id"], "title": "Draft review", "body": "This body is long enough for a draft.", "status": "draft"},
        )

        self.assertEqual(self.database.dashboard(), {"total_reviews": 2, "published": 1, "draft": 1, "games": 5})

    def test_games_can_be_created_edited_and_deactivated(self):
        created = self.database.save_game(self.admin, {"name": "New Rhythm Game", "active": True})
        updated = self.database.save_game(self.admin, {"name": "Updated Rhythm Game", "active": False}, created["id"])

        self.assertEqual(updated["name"], "Updated Rhythm Game")
        self.assertFalse(updated["active"])
        self.assertFalse(any(game["name"] == updated["name"] for game in self.database.games()))

    def test_duplicate_game_names_are_rejected(self):
        self.assert_api_error(409, self.database.save_game, self.admin, {"name": "Project Sekai", "active": True})

    def test_settings_are_saved_and_persisted(self):
        expected = {"confirm_publish": False, "notify_new_reviews": True, "auto_save_draft": True}

        self.assertEqual(self.database.save_settings(expected), expected)
        self.assertEqual(self.database.get_settings(), expected)

    def test_settings_reject_unknown_keys_and_non_boolean_values(self):
        self.assert_api_error(400, self.database.save_settings, {"admin_password": "secret"})
        self.assert_api_error(400, self.database.save_settings, {"auto_save_draft": "yes"})


if __name__ == "__main__":
    import unittest
    unittest.main()
