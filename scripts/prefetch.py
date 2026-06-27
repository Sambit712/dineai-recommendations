import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.loader import load_or_fetch
from src.data.preprocessor import preprocess
from rich.console import Console

console = Console(stderr=True)

def main():
    console.print("[bold cyan]Prefetching and caching dataset during build phase...[/bold cyan]")
    try:
        raw = load_or_fetch()
        if "budget_category" not in raw.columns:
            preprocess(raw)
        console.print("[bold green]Dataset prefetched and cached successfully![/bold green]")
    except Exception as e:
        console.print(f"[bold red]Failed to prefetch dataset: {e}[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
