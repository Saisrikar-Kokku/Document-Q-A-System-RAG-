"""
html_parser.py — Extracts text from HTML files
==============================================

WHAT THIS FILE DOES:
    Reads an HTML file (like a saved webpage), strips away all the markup
    (<div>, <p>, <script>), and leaves only the human-readable text.

WHY IT'S DESIGNED THIS WAY:
    LLMs don't need to read CSS classes or Javascript tags; that's just noise
    that wastes context limits. BeautifulSoup extracts just the text efficiently.
"""

from pathlib import Path
from bs4 import BeautifulSoup

def parse_html(file_path: Path) -> str:
    """
    Extracts clean text from an HTML file.
    
    Args:
        file_path (Path): The path to the HTML file.
        
    Returns:
        str: The clean, extracted text.
    """
    # We explicitly read as UTF-8. If it fails, standard fallback (handled
    # later by our text parser logic if needed, but UTF-8 covers 99% of web).
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        html_content = file.read()
        
    # Parse the HTML using the lxml engine (faster than built-in html.parser)
    soup = BeautifulSoup(html_content, "lxml")
    
    # Get all text. The separator ensures that different elements are spaced out.
    # e.g., <div>Hello</div><div>World</div> becomes "Hello\nWorld" instead of "HelloWorld"
    text = soup.get_text(separator="\n", strip=True)
    
    return text
