# Inventory Manager CLI

A small command-line inventory manager for a corner shop, written for COMP1101 Coursework 2. It lets you add stock items, remove them, list the current stock and see the average unit price. The inventory is saved to `inventory.json` in the current folder so it is kept between runs.

## Requirements

- Python 3.10 or later
- No third-party packages are needed

## Project structure

- `inventory/core.py` – add, remove, list and average-price functions
- `inventory/storage.py` – loading and saving the inventory as JSON
- `inventory/cli.py` – the interactive menu
- `tests/` – unit tests

## How to run the program

From the project folder, run:

```
python3 -m inventory.cli
```

You will see a numbered menu. Type the number of an option and press Enter, then follow the prompts. For example, choose `1` to add an item and enter its name, quantity and unit price. Choose `5` to quit. Your inventory is saved automatically after every change.
