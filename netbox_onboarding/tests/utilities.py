"""Utilities for testing."""
from os import path


def load_test_output(file_name: str = None) -> str:
    """Function to load text from the fixtures provided

    Args:
        file_name (string): Name of file
    """
    # Check that something was passed in, otherwise raise exception
    if file_name is None:
        raise Exception(f"load_test_output(file_name) expects a filename to be passed in. No file name was received.")

    # Verify that the type of variable passed in was as expected
    if not isinstance(file_name, str):
        raise Exception(f"load_test_output(file_name) expects a string. {type(file_name)} was passed in.")

    # Verify that the file exists
    if not path.exists(file_name):
        raise Exception(f"Unable to find file: {file_name}")

    with open(file_name, "r") as load_file:
        data = load_file.read()

    return data
