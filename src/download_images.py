
import json
import re
import time
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

IMAGE_FOLDER.mkdir(parents=True, exist_ok=True)
MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)

# /* WIKIMEDIA CONNECTION */

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "SmartMalaysiaTravelStudentProject/1.0 "
        "(educational destination image downloader; "
        "contact: student-project@example.org)"
    )
})

# /* CLEAN METADATA */

def clean_text(value):
    value = re.sub(r"<[^>]+>", "", str(value or ""))
    return unescape(value).strip()


def metadata_value(metadata, key):
    return clean_text(metadata.get(key, {}).get("value", ""))


# /* SEARCH DESTINATION IMAGE */

def find_image(destination):
    name = destination["name"]
    state = destination["state"]

    searches = [
        f'"{name}" "{state}" Malaysia',
        f'"{name}" Malaysia tourism'
    ]

    allowed_licenses = (
        "cc by",
        "cc-by",
        "cc0",
        "public domain",
        "pd-"
    )

    for search_text in searches:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": search_text,
            "gsrnamespace": 6,
            "gsrlimit": 10,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime",
            "iiurlwidth": 1000
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

        for page in pages.values():
            title = page.get("title", "")

            if not title.lower().endswith(
                (".jpg", ".jpeg", ".png", ".webp")
            ):
                continue

            image_info = page.get("imageinfo", [])

            if not image_info:
                continue

            info = image_info[0]

            if not info.get("mime", "").startswith("image/"):
                continue

            metadata = info.get("extmetadata", {})

            license_name = metadata_value(
                metadata, "LicenseShortName"
            )

            license_lower = license_name.lower()

            if not any(
                allowed in license_lower
                for allowed in allowed_licenses
            ):
                continue

            image_url = info.get(
                "thumburl", info.get("url")
            )

            if not image_url:
                continue

            return {
                "url": image_url,
                "source": info.get("descriptionurl", ""),
                "title": title,
                "author": metadata_value(metadata, "Artist"),
                "license": license_name,
                "license_url": metadata_value(
                    metadata, "LicenseUrl"
                )
            }

        time.sleep(1)

    return None


# /* DOWNLOAD IMAGE */

def download_image(image_url, output_path):
    response = session.get(
        image_url,
        timeout=40
    )
    response.raise_for_status()

    if len(response.content) > 15_000_000:
        raise ValueError("Image file is too large.")

    with Image.open(BytesIO(response.content)) as original:
        image = ImageOps.exif_transpose(original)
        image = image.convert("RGB")
        image.thumbnail((1200, 900))

        image.save(
            output_path,
            format="JPEG",
            quality=85,
            optimize=True
        )


# /* MAIN PROGRAM */

def main():
    if not DATA_FILE.exists():
        print("ERROR: destinations.json was not found.")
        return

    with DATA_FILE.open("r", encoding="utf-8") as file:
        destinations = json.load(file)

    mapping = {}
    credits = {}
    success = 0
    failed = 0

    print(f"Found {len(destinations)} destinations.\n")

    for index, destination in enumerate(destinations, start=1):
        destination_id = destination["id"]
        name = destination["name"]

        print(
            f"[{index}/{len(destinations)}] Searching: {name}"
        )

        # Keep the Melaka photo you already downloaded.
        existing_melaka = IMAGE_FOLDER / "malacca.jpg"

        if (
            destination_id == "DEST013"
            and existing_melaka.exists()
        ):
            mapping[destination_id] = "malacca.jpg"
            print("  Using existing malacca.jpg")
            continue

        filename = f"{destination_id}.jpg"
        output_path = IMAGE_FOLDER / filename

        # Do not download an existing picture again.
        if output_path.exists():
            mapping[destination_id] = filename
            print("  Image already exists.")
            continue

        try:
            result = find_image(destination)

            if result is None:
                print("  No suitable licensed image found.")
                failed += 1
                continue

            download_image(result["url"], output_path)

            mapping[destination_id] = filename

            credits[destination_id] = {
                "destination": name,
                "filename": filename,
                "source": result["source"],
                "file_title": result["title"],
                "author": result["author"],
                "license": result["license"],
                "license_url": result["license_url"]
            }

            success += 1
            print(f"  Saved: {filename}")

        except (
            requests.RequestException,
            OSError,
            ValueError
        ) as error:
            print(f"  Failed: {error}")
            failed += 1

        time.sleep(1)

    # /* SAVE IMAGE MAPPING */

    with MAPPING_FILE.open("w", encoding="utf-8") as file:
        file.write(
            "window.DESTINATION_IMAGES = "
            + json.dumps(mapping, indent=4)
            + ";\n"
        )

    # /* PRESERVE PREVIOUS IMAGE CREDITS */

    previous_credits = {}

    if CREDITS_FILE.exists():
        try:
            with CREDITS_FILE.open(
                "r", encoding="utf-8"
            ) as file:
                previous_credits = json.load(file)
        except (OSError, json.JSONDecodeError):
            pass

    previous_credits.update(credits)

    with CREDITS_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            previous_credits,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n/* DOWNLOAD SUMMARY */")
    print(f"New images downloaded: {success}")
    print(f"Images not downloaded: {failed}")
    print(f"Total mapped images: {len(mapping)}")
    print("Image mapping saved.")
    print("Image credits saved.")
    print("\nDone! Review each photo before submission.")


if __name__ == "__main__":
    main()
