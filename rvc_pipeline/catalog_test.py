"""Tests for the artist voice catalog."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from catalog import (
    CATALOG_PATH,
    add_artist,
    get_artist,
    get_reference_path,
    list_artists,
    load_catalog,
    resolve_artist_slugs,
)


class TestLoadCatalog(unittest.TestCase):
    """Tests for load_catalog."""

    def test_loads_real_catalog(self) -> None:
        catalog = load_catalog()
        self.assertIn("artists", catalog)
        self.assertGreater(len(catalog["artists"]), 0)

    def test_missing_catalog_raises(self) -> None:
        with patch("catalog.CATALOG_PATH", Path("/nonexistent/catalog.json")):
            with self.assertRaises(FileNotFoundError):
                load_catalog()


class TestGetArtist(unittest.TestCase):
    """Tests for get_artist."""

    def test_known_artist(self) -> None:
        artist = get_artist("biggie")
        self.assertEqual(artist["name"], "Notorious B.I.G.")
        self.assertEqual(artist["genre"], "hip-hop")

    def test_unknown_artist_raises(self) -> None:
        with self.assertRaises(KeyError) as ctx:
            get_artist("nonexistent")
        self.assertIn("nonexistent", str(ctx.exception))


class TestGetReferencePath(unittest.TestCase):
    """Tests for get_reference_path."""

    def test_biggie_reference_exists(self) -> None:
        path = get_reference_path("biggie")
        self.assertTrue(path.exists())
        self.assertTrue(path.name.endswith(".wav"))

    def test_missing_reference_raises(self) -> None:
        """Artist exists in catalog but WAV file is missing."""
        from unittest.mock import patch as mock_patch

        fake_artist = {
            "slug": "fake",
            "name": "Fake",
            "genre": "test",
            "reference": "nonexistent_file.wav",
        }
        with mock_patch("catalog.get_artist", return_value=fake_artist):
            with self.assertRaises(FileNotFoundError):
                get_reference_path("fake")


class TestListArtists(unittest.TestCase):
    """Tests for list_artists."""

    def test_returns_table(self) -> None:
        result = list_artists()
        self.assertIn("Slug", result)
        self.assertIn("biggie", result)
        self.assertIn("20 artists available", result)


class TestResolveArtistSlugs(unittest.TestCase):
    """Tests for resolve_artist_slugs."""

    def test_single_slug(self) -> None:
        self.assertEqual(resolve_artist_slugs("biggie"), ["biggie"])

    def test_comma_separated(self) -> None:
        self.assertEqual(
            resolve_artist_slugs("tupac,snoop,jayz"),
            ["tupac", "snoop", "jayz"],
        )

    def test_all_returns_full_catalog(self) -> None:
        slugs = resolve_artist_slugs("all")
        self.assertEqual(len(slugs), 20)
        self.assertIn("biggie", slugs)


class TestAddArtist(unittest.TestCase):
    """Tests for add_artist."""

    def test_add_new_artist(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"artists": []}, f)
            tmp_path = Path(f.name)

        try:
            with patch("catalog.CATALOG_PATH", tmp_path):
                add_artist(
                    slug="test",
                    name="Test Artist",
                    genre="test",
                    reference="test.wav",
                )
                catalog = json.loads(tmp_path.read_text())
                self.assertEqual(len(catalog["artists"]), 1)
                self.assertEqual(catalog["artists"][0]["slug"], "test")
        finally:
            tmp_path.unlink()

    def test_update_existing_artist(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(
                {"artists": [{"slug": "test", "name": "Old", "genre": "x",
                               "reference": "x.wav", "source_song": "",
                               "quality": 0, "notes": ""}]},
                f,
            )
            tmp_path = Path(f.name)

        try:
            with patch("catalog.CATALOG_PATH", tmp_path):
                add_artist(
                    slug="test",
                    name="Updated",
                    genre="y",
                    reference="y.wav",
                )
                catalog = json.loads(tmp_path.read_text())
                self.assertEqual(len(catalog["artists"]), 1)
                self.assertEqual(catalog["artists"][0]["name"], "Updated")
        finally:
            tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
