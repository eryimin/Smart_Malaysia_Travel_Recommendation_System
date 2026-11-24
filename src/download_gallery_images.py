
import json
import re
import time
import hashlib
from io import BytesIO
from pathlib import Path
from html import unescape

import requests
from PIL import Image, ImageOps

# /* PROJECT PATHS */

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "destinations.json"
IMAGE_FOLDER = ROOT / "static" / "images"
MAPPING_FILE = ROOT / "static" / "js" / "destination_images.js"
CREDITS_FILE = ROOT / "data" / "image_credits.json"

API_URL = "https://commons.wikimedia.org/w/api.php"
MAX_PHOTOS = 10

IMAGE_FOLDER.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({
    "User-Agent": "SmartMalaysiaTravelEducationalProject/1.1"
})


# /* IMAGE SIMILARITY */

def image_hash(image):
    image = ImageOps.exif_transpose(image)
    image = image.convert("L").resize((9, 8))

    pixels = list(image.getdata())
    bits = 0

    for row in range(8):
        for col in range(8):
            left = pixels[row * 9 + col]
            right = pixels[row * 9 + col + 1]
            bits = (bits << 1) | int(left > right)

    return bits


def is_duplicate(new_hash, used_hashes):
    return any(
        (new_hash ^ old_hash).bit_count() <= 3
        for old_hash in used_hashes
    )


# /* READ EXISTING DATA */

def load_json(path, default):
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_mapping():
    if not MAPPING_FILE.exists():
        return {}

    content = MAPPING_FILE.read_text(encoding="utf-8")

    match = re.search(
        r"window\.DESTINATION_IMAGES\s*=\s*(\{.*\})\s*;",
        content,
        re.DOTALL
    )

    if not match:
        return {}

    return json.loads(match.group(1))


def clean_text(value):
    value = re.sub(r"<[^>]*>", "", str(value or ""))
    return unescape(value).strip()


def get_metadata(metadata, field):
    return clean_text(metadata.get(field, {}).get("value", ""))


# /* SEARCH USING REAL DESTINATION ATTRACTIONS */

def create_searches(destination):
    name = destination["name"]
    state = destination["state"]

    searches = [
        (f'"{name}" Malaysia', name)
    ]

    generic = {
        "local food", "local cuisine", "town centre",
        "waterfront", "beaches", "rainforest",
        "coastal scenery", "nature trails",
        "markets", "island scenery", "photography",
        "forest trails", "heritage landmarks",
        "local markets", "mountain views"
    }

    for highlight in destination.get("highlights", []):
        if highlight.lower() in generic:
            continue

        if len(highlight) < 6:
            continue

        searches.append((
            f'"{highlight}" Malaysia',
            highlight
        ))

    # A maximum of four searches per destination.
    return searches[:4]


# /* SEARCH WIKIMEDIA COMMONS */

def search_photos(query):
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 15,
        "prop": "imageinfo",
        "iiprop": "url|sha1|mime|extmetadata",
        "iiurlwidth": 1200
    }

    response = session.get(
        API_URL,
        params=params,
        timeout=30
    )
    response.raise_for_status()

    pages = response.json().get(
        "query", {}
    ).get("pages", {})

    return list(pages.values())


# /* CHECK PHOTOGRAPH AND LICENCE */

def choose_candidate(page, search_subject):
    title = page.get("title", "")

    if not title.lower().endswith(
        (".jpg", ".jpeg", ".png", ".webp")
    ):
        return None

    info_list = page.get("imageinfo", [])

    if not info_list:
        return None

    info = info_list[0]

    if info.get("mime", "") not in (
        "image/jpeg", "image/png", "image/webp"
    ):
        return None

    # Search title must identify the destination
    # or the specific attraction.
    title_normalized = title.lower().replace("_", " ")
    subject_normalized = search_subject.lower()

    if subject_normalized not in title_normalized:
        return None

    metadata = info.get("extmetadata", {})
    license_name = get_metadata(
        metadata, "LicenseShortName"
    )

    license_lower = license_name.lower()

    allowed = (
        license_lower.startswith("cc by")
        or license_lower.startswith("cc-by")
        or license_lower == "cc0"
        or "public domain" in license_lower
        or license_lower.startswith("pd-")
    )

    if not allowed:
        return None

    url = info.get("thumburl") or info.get("url")

    if not url:
        return None

    return {
        "url": url,
        "sha1": info.get("sha1", ""),
        "source": info.get("descriptionurl", ""),
        "title": title,
        "author": get_metadata(metadata, "Artist"),
        "license": license_name,
        "license_url": get_metadata(
            metadata, "LicenseUrl"
        )
    }


# /* DOWNLOAD AND CHECK IMAGE */

def get_image(candidate, used_hashes):
    response = session.get(
        candidate["url"],
        timeout=40
    )
    response.raise_for_status()

    if len(response.content) > 15_000_000:
        return None

    with Image.open(BytesIO(response.content)) as original:
        image = ImageOps.exif_transpose(original)
        image = image.convert("RGB")

        if image.width < 400 or image.height < 250:
            return None

        image.thumbnail((1200, 900))
        new_hash = image_hash(image)

        if is_duplicate(new_hash, used_hashes):
            return None

        return image.copy(), new_hash


# /* MAIN PROGRAM */

def main():
    destinations = load_json(DATA_FILE, [])
    old_mapping = load_mapping()
    credits = load_json(CREDITS_FILE, {})

    mapping = {}
    used_hashes = []
    used_sources = set()

    # Reserve all existing pictures, including manually added ones.
    for image_path in sorted(IMAGE_FOLDER.glob("*.jpg")):
        try:
            with Image.open(image_path) as image:
                used_hashes.append(image_hash(image))
        except (OSError, ValueError):
            print("Unreadable image:", image_path.name)

    for credit in credits.values():
        if isinstance(credit, dict):
            source = credit.get("source")
            if source:
                used_sources.add(source)

    # Preserve existing mapping.
    for destination in destinations:
        destination_id = destination["id"]
        existing = old_mapping.get(destination_id, [])

        if isinstance(existing, str):
            existing = [existing]

        # Preserve photos already saved for this destination.
        existing = [
            filename for filename in existing
            if (IMAGE_FOLDER / filename).exists()
        ]

        # Also find additional numbered photos.
        for number in range(2, MAX_PHOTOS + 1):
            filename = f"{destination_id}_{number}.jpg"

            if (
                (IMAGE_FOLDER / filename).exists()
                and filename not in existing
            ):
                existing.append(filename)

        # Preserve older primary pictures.
        primary = IMAGE_FOLDER / f"{destination_id}.jpg"

        if primary.exists() and primary.name not in existing:
            existing.insert(0, primary.name)

        mapping[destination_id] = existing[:MAX_PHOTOS]

    total_new = 0

    print(f"Found {len(destinations)} destinations.")

    for index, destination in enumerate(destinations, 1):
        destination_id = destination["id"]
        name = destination["name"]
        images = mapping[destination_id]

        print(
            f"\n[{index}/{len(destinations)}] "
            f"{name}: {len(images)}/{MAX_PHOTOS} photos"
        )

        if len(images) >= MAX_PHOTOS:
            continue

        for query, subject in create_searches(destination):
            if len(images) >= MAX_PHOTOS:
                break

            try:
                pages = search_photos(query)
            except requests.RequestException as error:
                print("  Search error:", error)
                continue

            for page in pages:
                if len(images) >= MAX_PHOTOS:
                    break

                candidate = choose_candidate(page, subject)

                if not candidate:
                    continue

                source = candidate["source"]

                if source in used_sources:
                    continue

                try:
                    result = get_image(candidate, used_hashes)

                    if result is None:
                        continue

                    image, new_hash = result

                    number = 2

                    while (
                        IMAGE_FOLDER /
                        f"{destination_id}_{number}.jpg"
                    ).exists():
                        number += 1

                    filename = f"{destination_id}_{number}.jpg"
                    output_path = IMAGE_FOLDER / filename

                    image.save(
                        output_path,
                        format="JPEG",
                        quality=85,
                        optimize=True
                    )

                    used_hashes.append(new_hash)
                    used_sources.add(source)
                    images.append(filename)

                    # Each new image gets its own credit.
                    credits[filename] = {
                        "destination_id": destination_id,
                        "destination": name,
                        "filename": filename,
                        "subject": subject,
                        "source": source,
                        "author": candidate["author"],
                        "license": candidate["license"],
                        "license_url": candidate["license_url"],
                        "reviewed": False
                    }

                    total_new += 1
                    print(f"  Saved: {filename}")

                except (requests.RequestException, OSError, ValueError) as error:
                    print("  Image skipped:", error)

            time.sleep(1)

        print(f"  Total: {len(images)}/{MAX_PHOTOS}")

    # /* SAVE NEW GALLERY MAPPING */

    MAPPING_FILE.write_text(
        "window.DESTINATION_IMAGES = "
        + json.dumps(mapping, indent=4, ensure_ascii=False)
        + ";\n",
        encoding="utf-8"
    )

    with CREDITS_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            credits,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n/* GALLERY DOWNLOAD SUMMARY */")
    print("New photos:", total_new)
    print(
        "Total gallery photos:",
        sum(len(images) for images in mapping.values())
    )
    print(
        "Destinations:",
        len(destinations)
    )
    print("Done. Review photo locations and licences.")


if __name__ == "__main__":
    main()
