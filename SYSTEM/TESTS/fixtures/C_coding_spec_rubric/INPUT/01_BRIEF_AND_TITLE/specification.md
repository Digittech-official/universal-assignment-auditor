# COMP1101 Introduction to Programming — Coursework 2 Specification

**Northbridge University — School of Computing**
**Assignment title:** Inventory Manager CLI
**Weighting:** 40% of module mark
**Submission:** a single ZIP archive of your project folder via the VLE

## Overview

You will build a small command-line inventory manager for a fictional corner shop. The program lets a user record stock items, remove them, view the current stock and obtain summary information. The aim of the assignment is to demonstrate that you can structure a small Python program into functions and modules, handle errors gracefully, persist data, test your code and document it for another developer.

## Requirements

Your submission must meet all of the following requirements:

1. The program must be written in Python 3 and use the Python standard library only (no third-party packages, apart from pytest for running tests if you choose to use it).
2. Provide a function to add an item to the inventory, recording its name, quantity and unit price.
3. Provide a function to remove an item from the inventory by name.
4. Provide a function to list all items currently in the inventory.
5. Provide a function to compute the average unit price of the items in the inventory.
6. Invalid input (for example a non-numeric quantity, a negative price, an unknown item name or an operation on an empty inventory) must produce a clear error message and must not crash the program.
7. The inventory must be persisted to a JSON file so that it is preserved between runs of the program.
8. Include unit tests (using unittest or pytest) covering at least three of your functions.
9. Include a README.md explaining how to run the program and how to run the tests.
10. Code must follow PEP 8 style conventions and every function must have a docstring.

## Deliverables

A ZIP archive containing your project folder: the Python package, the tests folder and the README.md.

## Marking

Your work will be marked using the COMP1101 Coursework 2 rubric (see the Rubric document). Late submissions are subject to the standard University penalties.
