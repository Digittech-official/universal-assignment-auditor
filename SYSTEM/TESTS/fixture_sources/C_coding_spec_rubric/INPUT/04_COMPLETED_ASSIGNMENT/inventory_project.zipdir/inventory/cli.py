"""Interactive command-line interface for the Inventory Manager."""

from inventory.core import add_item, average_price, list_items, remove_item
from inventory.storage import load_inventory, save_inventory

MENU = """
1. Add item
2. Remove item
3. List items
4. Average unit price
5. Quit
"""


def prompt_add(items):
    """Ask the user for item details and add the item to the inventory.

    Args:
        items: The inventory dictionary to modify.
    """
    name = input("Item name: ")
    try:
        quantity = int(input("Quantity: "))
        unit_price = float(input("Unit price: "))
        add_item(items, name, quantity, unit_price)
    except ValueError as error:
        print(f"Error: {error}")
        return
    print(f"Added {name.strip()}.")


def prompt_remove(items):
    """Ask the user for an item name and remove it from the inventory.

    Args:
        items: The inventory dictionary to modify.
    """
    name = input("Item name to remove: ").strip()
    remove_item(items, name)
    print(f"Removed {name}.")


def show_items(items):
    """Print every item in the inventory in a simple table.

    Args:
        items: The inventory dictionary.
    """
    rows = list_items(items)
    if not rows:
        print("The inventory is empty.")
        return
    print(f"{'Name':<20}{'Qty':>6}{'Price':>10}")
    for name, quantity, unit_price in rows:
        print(f"{name:<20}{quantity:>6}{unit_price:>10.2f}")


def main():
    """Run the interactive menu loop until the user chooses to quit."""
    items = load_inventory()
    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()
        if choice == "1":
            prompt_add(items)
            save_inventory(items)
        elif choice == "2":
            prompt_remove(items)
            save_inventory(items)
        elif choice == "3":
            show_items(items)
        elif choice == "4":
            print(f"Average unit price: {average_price(items):.2f}")
        elif choice == "5":
            print("Goodbye.")
            break
        else:
            print("Error: please enter a number from 1 to 5.")


if __name__ == "__main__":
    main()
