from tests.support import DatabaseTestCase


class UserReviewTests(DatabaseTestCase):
    def test_user_can_submit_review_and_rating_aggregates(self):
        first = self.database.add_user_review(
            self.user,
            {"song_id": self.song["id"], "rating": 5, "content": "Chart seru dan musiknya enak."},
        )
        second_user = self.database.create_user("player2@example.com", "Player Two", "PlayerPass456")
        self.database.add_user_review(
            second_user,
            {"song_id": self.song["id"], "rating": 3, "content": "Cukup menantang untuk dicoba."},
        )
        detail = self.database.song_detail(self.song["id"])

        self.assertEqual(first["rating"], 5)
        self.assertEqual(detail["review_count"], 2)
        self.assertEqual(detail["rating"], 4.0)
        self.assertEqual(len(detail["community_reviews"]), 2)

    def test_admin_cannot_write_community_review(self):
        self.assert_api_error(
            403,
            self.database.add_user_review,
            self.admin,
            {"song_id": self.song["id"], "rating": 5, "content": "Valid review text."},
        )

    def test_rating_and_content_rules_are_enforced(self):
        self.assert_api_error(
            400,
            self.database.add_user_review,
            self.user,
            {"song_id": self.song["id"], "rating": 6, "content": "This review is long enough."},
        )
        self.assert_api_error(
            400,
            self.database.add_user_review,
            self.user,
            {"song_id": self.song["id"], "rating": 4, "content": "short"},
        )

    def test_same_user_cannot_review_same_song_twice(self):
        payload = {"song_id": self.song["id"], "rating": 4, "content": "A useful review of this song."}
        self.database.add_user_review(self.user, payload)

        self.assert_api_error(409, self.database.add_user_review, self.user, payload)

    def test_nonexistent_song_returns_not_found(self):
        self.assert_api_error(
            404,
            self.database.add_user_review,
            self.user,
            {"song_id": 99999, "rating": 4, "content": "A useful review of this song."},
        )


if __name__ == "__main__":
    import unittest
    unittest.main()
