"""
docx_parser.py — Extracts text from Word documents
==================================================

WHAT THIS FILE DOES:
    Opens a .docx file and extracts all text from paragraphs.

WHY IT'S DESIGNED THIS WAY:
    A .docx file is actually a zipped folder of XML files. `python-docx` unzips
    it in memory and parses the XML tags to find the paragraphs.
"""

from pathlib import Path
import docx

def parse_docx(file_path: Path) -> str:
    """
    Extracts text from a .docx file.
    
    Args:
        file_path (Path): The path to the Word file.
        
    Returns:
        str: The extracted text.
    """
    # Load the document using python-docx
    doc = docx.Document(file_path)
    text_content = []
    
    # Iterate through every paragraph in the document
    for paragraph in doc.paragraphs:
        # We only care about paragraphs that actually have text.
        # Stripping removes leading/trailing whitespace.
        text = paragraph.text.strip()
        if text:
            text_content.append(text)
            
    # Join paragraphs with a single newline
    return "\n".join(text_content)
