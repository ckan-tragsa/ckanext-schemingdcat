import os


def get_file_contents(file_name):
    """
    Reads the contents of a file located in the examples directory.

    Args:
        file_name (str): The name of the file to read.

    Returns:
        str: The contents of the file as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If an I/O error occurs while reading the file.
    """
    path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "examples", file_name
    )
    with open(path, "r") as f:
        return f.read()