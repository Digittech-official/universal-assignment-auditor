"""Core inventory operations for the Inventory Manager CLI.

The inventory is represented as a dictionary mapping an item name to a
dictionary with the keys ``quantity`` (int) and ``unit_price`` (float).
"""


def add_item(items, name, quantity, unit_price):
    """Add an item to the inventory or update it if it already exists.

    Args:
        items: The inventory dictionary to modify.
        name: The name of the item.
        quantity: The number of units in stock (must be zero or more).
        unit_price: The price of a single unit (must be zero or more).

    Raises:
        ValueError: If the name is empty or quantity/price are negative.
    """
    name = name.strip()
    if not name:
        raise ValueError("Item name must not be empty.")
    if quantity < 0:
        raise ValueError("Quantity must not be negative.")
    if unit_price < 0:
        raise ValueError("Unit price must not be negative.")
    items[name] = {"quantity": int(quantity), "unit_price": float(unit_price)}


def remove_item(items, name):
    """Remove an item from the inventory by name.

    Args:
        items: The inventory dictionary to modify.
        name: The name of the item to remove.
    """
    del items[name]


def list_items(items):
    """Return the inventory as a list of (name, quantity, unit_price) tuples.

    The list is sorted alphabetically by item name.

    Args:
        items: The inventory dictionary.

    Returns:
        A sorted list of tuples.
    """
    return [
        (name, data["quantity"], data["unit_price"])
        for name, data in sorted(items.items())
    ]


def average_price(items):
    """Return the average unit price of all items in the inventory.

    Args:
        items: The inventory dictionary.

    Returns:
        The mean unit price as a float.
    """
    total = sum(data["unit_price"] for data in items.values())
    return total / len(items)
