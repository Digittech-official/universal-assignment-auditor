"""Loading and saving the inventory to a JSON file."""

import json
import os

DEFAULT_PATH = "inventory.json"


def load_inventory(path=DEFAULT_PATH):
    """Load the inventory from a JSON file.

    Args:
        path: Location of the JSON file.

    Returns:
        The inventory dictionary, or an empty dictionary if the file does
        not exist or cannot be read.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        print(f"Warning: could not read {path}; starting with an empty "
              "inventory.")
        return {}


def save_inventory(items, path=DEFAULT_PATH):
    """Save the inventory to a JSON file.

    Args:
        items: The inventory dictionary to save.
        path: Location of the JSON file.
    """
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(items, handle, indent=2)
