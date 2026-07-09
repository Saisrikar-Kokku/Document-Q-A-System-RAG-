"""
text_parser.py — Safely reads plain text and markdown
=====================================================

WHAT THIS FILE DOES:
    Reads plain text files (.txt, .md). Its main job is figuring out what
    encoding the file was saved in so it doesn't garble characters.

WHY IT'S DESIGNED THIS WAY:
    If you open a file saved in 'Windows-1252' as 'UTF-8', special characters
    (like quotes, dashes, or accented letters) turn into gibberish ().
    We use the `chardet` library to guess the encoding first, guaranteeing
    clean text.
"""

from pathlib import Path
import chardet

def parse_text(file_path: Path) -> str:
    """
    Extracts text from a plain text or markdown file, detecting encoding safely.
    
    Args:
        file_path (Path): The path to the text file.
        
    Returns:
        str: The decoded string.
    """
    # 1. Read the raw bytes first
    with open(file_path, "rb") as file:
        raw_data = file.read()
        
    # 2. Guess the encoding based on the bytes
    # chardet returns a dict like {'encoding': 'utf-8', 'confidence': 0.99}
    result = chardet.detect(raw_data)
    encoding = result["encoding"] or "utf-8"  # fallback to utf-8 if it can't guess
    
    # 3. Decode the bytes into a string using the guessed encoding.
    # errors="replace" ensures that if one character is still weird, the app
    # doesn't crash; it just puts a  there and continues.
    return raw_data.decode(encoding, errors="replace")
