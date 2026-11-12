from tests.support import DatabaseTestCase


class AdminReviewTests(DatabaseTestCase):
    def test_admin_can_save_draft_and_publish_review(self):
        payload = {
            "song_id": self.song["id"],
            "title": "Hatsune Miku chart review",
            "body": "The chart mixes energetic patterns with a memorable chorus.",
            "status": "draft",
            "pros": ["Strong rhythm"],
            "cons": ["Bridge is difficult"],
        }
        saved = self.database.save_admin_review(self.admin, payload)

        self.assertEqual(saved["status"], "draft")
        self.assertEqual(self.database.song_detail(self.song["id"])["review"], None)

        payload["status"] = "published"
        published = self.database.save_admin_review(self.admin, payload, saved["id"])
        self.assertEqual(published["status"], "published")
        self.assertEqual(
            self.database.song_detail(self.song["id"])["review"]["title"],
            "Hatsune Miku chart review",
        )

    def test_regular_user_cannot_manage_editorial_reviews(self):
        self.assert_api_error(
            403,
            self.database.save_admin_review,
            self.user,
            {"song_id": self.song["id"], "title": "A valid title", "body": "A review body long enough."},
        )

    def test_review_fields_status_and_video_url_are_validated(self):
        invalid = {
            "song_id": self.song["id"],
            "title": "x",
            "body": "too short",
            "status": "unknown",
            "video_url": "javascript:alert(1)",
        }
        self.assert_api_error(400, self.database.save_admin_review, self.admin, invalid)

    def test_review_can_be_deleted(self):
        review = self.database.save_admin_review(
            self.admin,
            {"song_id": self.song["id"], "title": "A valid review title", "body": "A sufficiently long editorial review body."},
        )
        self.database.delete_admin_review(review["id"])

        self.assertEqual(self.database.admin_reviews(), [])
        self.assert_api_error(404, self.database.delete_admin_review, review["id"])

    def test_editorial_review_lists_can_be_filtered_by_status(self):
        for title, status in [("First review title", "draft"), ("Second review title", "published")]:
            self.database.save_admin_review(
                self.admin,
                {"song_id": self.song["id"], "title": title, "body": "A sufficiently long editorial review body.", "status": status},
            )

        self.assertEqual(len(self.database.admin_reviews("draft")), 1)
        self.assertEqual(len(self.database.admin_reviews("published")), 1)
        self.assert_api_error(400, self.database.admin_reviews, "archived")


if __name__ == "__main__":
    import unittest
    unittest.main()
