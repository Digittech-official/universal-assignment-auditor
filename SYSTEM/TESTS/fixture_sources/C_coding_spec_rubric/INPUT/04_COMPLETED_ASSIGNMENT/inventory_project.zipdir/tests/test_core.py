"""Unit tests for inventory.core."""

import unittest

from inventory.core import add_item, list_items


class TestAddItem(unittest.TestCase):
    """Tests for add_item."""

    def test_add_new_item(self):
        """A new item is stored with its quantity and price."""
        items = {}
        add_item(items, "Milk", 10, 1.20)
        self.assertEqual(items["Milk"], {"quantity": 10, "unit_price": 1.20})

    def test_add_existing_item_updates(self):
        """Adding an existing name replaces its details."""
        items = {}
        add_item(items, "Bread", 5, 0.95)
        add_item(items, "Bread", 8, 1.05)
        self.assertEqual(items["Bread"]["quantity"], 8)

    def test_negative_quantity_rejected(self):
        """A negative quantity raises ValueError."""
        with self.assertRaises(ValueError):
            add_item({}, "Eggs", -1, 2.50)

    def test_empty_name_rejected(self):
        """An empty name raises ValueError."""
        with self.assertRaises(ValueError):
            add_item({}, "   ", 3, 2.50)


class TestListItems(unittest.TestCase):
    """Tests for list_items."""

    def test_list_sorted(self):
        """Items are returned sorted by name."""
        items = {}
        add_item(items, "Tea", 4, 2.00)
        add_item(items, "Apples", 12, 0.30)
        self.assertEqual(
            list_items(items),
            [("Apples", 12, 0.30), ("Tea", 4, 2.00)],
        )

    def test_list_empty(self):
        """An empty inventory gives an empty list."""
        self.assertEqual(list_items({}), [])


if __name__ == "__main__":
    unittest.main()
