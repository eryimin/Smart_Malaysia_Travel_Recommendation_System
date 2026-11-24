"""Unlimited History: recover original profiles and retain Festival Mode metadata."""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HISTORY_DIRECTORY = DATA_DIR / "history_archive"
PROFILE_DIRECTORY = DATA_DIR / "profiles"


def _path(user_id):
    digest = hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()
    return HISTORY_DIRECTORY / (digest + ".json")


def _write(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)
    os.replace(temporary, path)


def _date(record):
    try:
        value = datetime.fromisoformat(str(record.get("timestamp", "")))
        return value.replace(tzinfo=None)
    except (TypeError, ValueError):
        return datetime.min


def _signature(record):
    return json.dumps(
        [record.get("preferences", {}), record.get("destination_ids", [])],
        sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def _profile_history(user_id):
    # Read the original JSON directly. UserProfile methods may return only 20.
    filename = str(user_id)
    if not filename or filename != Path(filename).name or filename in (".", ".."):
        raise ValueError("Invalid user ID")
    profile_path = PROFILE_DIRECTORY / (filename + ".json")
    if not profile_path.exists():
        return []
    with profile_path.open("r", encoding="utf-8") as file:
        profile = json.load(file)
    entries = profile.get("recommendation_history", [])
    if not isinstance(entries, list):
        raise ValueError("Invalid recommendation history in profile")
    return entries


def get_history(user_id, existing_records=None):
    """Merge archived history with ALL records in the original profile."""
    path = _path(user_id)
    if path.exists():
        with path.open("r", encoding="utf-8") as file:
            archive = json.load(file)
        if not isinstance(archive, list):
            raise ValueError("History archive is invalid")
    else:
        archive = []

    # Profile contains the full history, not just the limited getter output.
    profile_records = _profile_history(user_id)
    # If the profile does not exist, fall back to the passed history.
    originals = profile_records if profile_records else (existing_records or [])
    matched_archive_indices = set()
    changed = not path.exists()

    for original in originals:
        if not isinstance(original, dict):
            continue
        signature = _signature(original)
        original_date = _date(original)
        match = None

        # Match copies of the same recommendation one-to-one, keeping
        # distinct recommendations even when their preferences are identical.
        for index, saved in enumerate(archive):
            if index in matched_archive_indices or _signature(saved) != signature:
                continue
            if saved.get("timestamp") == original.get("timestamp"):
                match = index
                break

        if match is None:
            for index, saved in enumerate(archive):
                if index in matched_archive_indices or _signature(saved) != signature:
                    continue
                if (saved.get("mode") in ("normal", "festival")
                        and abs((_date(saved) - original_date).total_seconds()) <= 3):
                    match = index
                    break

        if match is not None:
            matched_archive_indices.add(match)
        else:
            recovered = dict(original)
            recovered.setdefault("mode", "legacy")
            recovered.setdefault("festival_id", None)
            archive.append(recovered)
            matched_archive_indices.add(len(archive) - 1)
            changed = True

    archive.sort(key=_date)
    for index, record in enumerate(archive, start=1):
        if record.get("history_number") != index:
            record["history_number"] = index
            changed = True
    if changed:
        _write(path, archive)
    return archive


def append_history(user_id, preferences, destination_ids, festival_id=None):
    records = get_history(user_id)
    record = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "preferences": dict(preferences),
        "destination_ids": list(destination_ids),
        "mode": "festival" if festival_id else "normal",
        "festival_id": festival_id,
    }
    records.append(record)
    records.sort(key=_date)
    for index, entry in enumerate(records, start=1):
        entry["history_number"] = index
    _write(_path(user_id), records)
    return record
