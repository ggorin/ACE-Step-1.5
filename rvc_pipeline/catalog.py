"""Artist voice catalog manager for the RVC pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from loguru import logger


CATALOG_PATH = Path(__file__).parent / "reference" / "catalog.json"


def load_catalog() -> dict:
    """Load the artist catalog from catalog.json."""
    if not CATALOG_PATH.exists():
        logger.error(f"Catalog not found: {CATALOG_PATH}")
        raise FileNotFoundError(f"Catalog not found: {CATALOG_PATH}")
    with open(CATALOG_PATH) as f:
        return json.load(f)


def get_artist(slug: str) -> dict:
    """Look up an artist by slug. Raises KeyError if not found."""
    catalog = load_catalog()
    for artist in catalog["artists"]:
        if artist["slug"] == slug:
            return artist
    available = [a["slug"] for a in catalog["artists"]]
    raise KeyError(
        f"Artist '{slug}' not found. Available: {', '.join(available)}"
    )


def get_reference_path(slug: str) -> Path:
    """Return the full path to an artist's reference WAV."""
    artist = get_artist(slug)
    ref_dir = Path(__file__).parent / "reference"
    ref_path = ref_dir / artist["reference"]
    if not ref_path.exists():
        raise FileNotFoundError(
            f"Reference file missing for '{slug}': {ref_path}\n"
            f"Download it and place it in {ref_dir}/"
        )
    return ref_path


def list_artists() -> str:
    """Return a formatted table of all artists in the catalog."""
    catalog = load_catalog()
    artists = catalog["artists"]
    if not artists:
        return "No artists in catalog."

    lines = [
        f"{'Slug':<16} {'Name':<24} {'Genre':<12} {'Song':<28} {'Q':>1}",
        "-" * 83,
    ]
    for a in sorted(artists, key=lambda x: x["genre"]):
        q = "*" * a.get("quality", 0)
        lines.append(
            f"{a['slug']:<16} {a['name']:<24} {a['genre']:<12} "
            f"{a.get('source_song', ''):<28} {q}"
        )
    lines.append(f"\n{len(artists)} artists available.")
    return "\n".join(lines)


def resolve_artist_slugs(artist_arg: str) -> list[str]:
    """Parse an --artist argument into a list of slugs."""
    if artist_arg == "all":
        catalog = load_catalog()
        return [a["slug"] for a in catalog["artists"]]
    return [s.strip() for s in artist_arg.split(",")]


def add_artist(
    slug: str,
    name: str,
    genre: str,
    reference: str,
    source_song: str = "",
    quality: int = 0,
    notes: str = "",
) -> None:
    """Add or update an artist entry in the catalog."""
    catalog = load_catalog()
    entry = {
        "slug": slug,
        "name": name,
        "genre": genre,
        "reference": reference,
        "source_song": source_song,
        "quality": quality,
        "notes": notes,
    }
    # Update existing or append
    for i, a in enumerate(catalog["artists"]):
        if a["slug"] == slug:
            catalog["artists"][i] = entry
            logger.info(f"Updated artist: {slug}")
            break
    else:
        catalog["artists"].append(entry)
        logger.info(f"Added artist: {slug}")

    with open(CATALOG_PATH, "w") as f:
        json.dump(catalog, f, indent=2)
        f.write("\n")
