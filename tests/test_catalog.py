from tests.support import DatabaseTestCase


class CatalogTests(DatabaseTestCase):
    def test_seed_catalog_has_active_songs_with_game_metadata(self):
        songs = self.database.catalog({})

        self.assertGreaterEqual(len(songs), 6)
        self.assertTrue(all(song["game"] and song["bpm"] > 0 for song in songs))

    def test_search_matches_title_artist_and_game(self):
        title_matches = self.database.catalog({"q": ["hatsune"]})
        artist_matches = self.database.catalog({"q": ["sasakure"]})
        game_matches = self.database.catalog({"q": ["arcaea"]})

        self.assertEqual([song["title"] for song in title_matches], ["Hatsune Miku Dance"])
        self.assertEqual(len(artist_matches), 1)
        self.assertTrue(all(song["game"] == "Arcaea" for song in game_matches))

    def test_game_difficulty_and_bpm_filters_compose(self):
        game = next(game for game in self.database.games() if game["name"] == "Arcaea")
        songs = self.database.catalog({
            "game": [str(game["id"])],
            "difficulty": ["Hard"],
            "bpmMin": ["190"],
            "bpmMax": ["210"],
        })

        self.assertEqual([song["title"] for song in songs], ["Testify"])

    def test_invalid_bpm_range_is_rejected(self):
        self.assert_api_error(400, self.database.catalog, {"bpmMin": ["210"], "bpmMax": ["100"]})

    def test_inactive_games_are_not_publicly_listed(self):
        game = self.database.games()[0]
        self.database.save_game(self.admin, {"name": game["name"], "active": False}, game["id"])

        self.assertFalse(any(song["game"] == game["name"] for song in self.database.catalog({})))
