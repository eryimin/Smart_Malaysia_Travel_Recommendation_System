
from pathlib import Path
from PIL import Image, ImageOps
import hashlib

# /* IMAGE FOLDER */

ROOT = Path(__file__).resolve().parent.parent
IMAGE_FOLDER = ROOT / "static" / "images"

# /* CHECK DUPLICATE IMAGES */

seen = {}
duplicate_groups = []

for image_path in sorted(IMAGE_FOLDER.glob("*.jpg")):
    try:
        with Image.open(image_path) as image:
            image = ImageOps.exif_transpose(image)
            image = image.convert("RGB")
            image = image.resize((256, 256))

            image_hash = hashlib.sha256(
                image.tobytes()
            ).hexdigest()

        if image_hash in seen:
            duplicate_groups.append(
                (seen[image_hash], image_path.name)
            )
        else:
            seen[image_hash] = image_path.name

    except Exception as error:
        print(f"Error reading {image_path.name}: {error}")

# /* DISPLAY RESULTS */

if duplicate_groups:
    print("\nDUPLICATE IMAGES FOUND:\n")

    for original, duplicate in duplicate_groups:
        print(f"{original} = {duplicate}")

    print(f"\nTotal duplicate files: {len(duplicate_groups)}")
else:
    print("\nNo exact duplicate images found.")

print("\nNote: Visually similar photos may not be detected.")
