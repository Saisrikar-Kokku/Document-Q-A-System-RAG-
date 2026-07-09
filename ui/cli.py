"""
cli.py — The Interactive Terminal UI
====================================

WHAT THIS FILE DOES:
    Provides a beautiful, chat-like interface in your terminal. It talks to 
    your FastAPI server so you can ingest documents and ask questions.

RUN WITH: python -m ui.cli
"""

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()
API_URL = "http://localhost:8000"

def check_server():
    """Ensures the FastAPI server is running."""
    try:
        httpx.get(f"{API_URL}/docs", timeout=2.0)
        return True
    except httpx.RequestError:
        return False

def ingest_documents():
    """Calls the /ingest endpoint."""
    if not check_server():
        console.print("[bold red]Error:[/bold red] The API server is not running. Start it with `python -m api.main`")
        return
        
    console.print("[cyan]Triggering incremental ingestion...[/cyan]")
    try:
        # We use timeout=None because ingestion might take minutes
        response = httpx.post(f"{API_URL}/ingest", timeout=None)
        data = response.json()
        console.print(f"[bold green]Success![/bold green] {data['status']}")
    except Exception as e:
        console.print(f"[bold red]Failed to trigger ingestion: {e}[/bold red]")

def ask_question():
    """Interactive loop to ask questions."""
    if not check_server():
        console.print("[bold red]Error:[/bold red] The API server is not running. Start it with `python -m api.main`")
        return
        
    console.print("\n[bold cyan]Type 'exit' or 'quit' to return to menu.[/bold cyan]")
    
    while True:
        query = Prompt.ask("\n[bold yellow]Your Question[/bold yellow]")
        if query.lower() in ['exit', 'quit']:
            break
            
        # Show a spinner while the LLM is "thinking"
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description="Thinking...", total=None)
            
            try:
                # Call our FastAPI /query endpoint (give it 120 seconds in case local LLM is slow)
                response = httpx.post(f"{API_URL}/query", json={"query": query}, timeout=120.0)
                response.raise_for_status()
                data = response.json()
                
                answer = data["answer"]
                sources = data["sources"]
                
                # Print the AI's answer nicely formatted as Markdown
                console.print(Panel(Markdown(answer), title="AI Answer", border_style="green"))
                
                # Print the sources used
                if sources:
                    source_names = list(set([s.get("file_name", "Unknown") for s in sources]))
                    console.print(f"[italic cyan]Sources used: {', '.join(source_names)}[/italic cyan]")
                    
            except Exception as e:
                console.print(f"[bold red]Error getting answer: {e}[/bold red]")

def main():
    console.print(Panel.fit("[bold magenta]Personal RAG System[/bold magenta]\nYour private, grounded AI assistant.", border_style="magenta"))
    
    while True:
        console.print("\n[bold white]What would you like to do?[/bold white]")
        console.print("1. Ingest/Update Documents (Scan data/ folder)")
        console.print("2. Ask a Question")
        console.print("3. Exit")
        
        choice = Prompt.ask("Select an option", choices=["1", "2", "3"])
        
        if choice == "1":
            ingest_documents()
        elif choice == "2":
            ask_question()
        else:
            console.print("[bold magenta]Goodbye![/bold magenta]")
            break

if __name__ == "__main__":
    main()
