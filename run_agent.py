import argparse
import os
import sys
import logging
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from research_agent.config import AgentConfig
from research_agent.brief_generator import ResearchAgent
from research_agent.live_tools import LiveNSEDataTool

console = Console()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    parser = argparse.ArgumentParser(description="Super Investing - AI Stock Research Agent")
    parser.add_argument("--ticker", type=str, default="SRVCABLE", help="NSE ticker symbol (e.g., SRVCABLE, POLYCAB)")
    parser.add_argument("--docs", type=str, default="research_pack", help="Directory containing company research documents")
    parser.add_argument("--output", type=str, default="SRVCABLE_RESEARCH_BRIEF.md", help="Path to write generated markdown brief")
    parser.add_argument("--api-key", type=str, default=None, help="Google Gemini API Key (or set GEMINI_API_KEY in .env)")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="LLM Model to use (default: gemini-2.5-flash)")
    parser.add_argument("--date", type=str, default="2026-09-23", help="Simulated reference date (YYYY-MM-DD)")
    parser.add_argument("--live", action="store_true", help="Fetch live market data for a real ticker before running agent")

    args = parser.parse_args()

    console.print(Panel.fit(
        f"[bold cyan]Super Investing · AI Research Agent[/bold cyan]\n"
        f"[green]Ticker:[/green] {args.ticker.upper()}  |  [green]Reference Date:[/green] {args.date}\n"
        f"[green]Docs Folder:[/green] {args.docs}  |  [green]Model:[/green] {args.model}",
        border_style="cyan"
    ))

    # Bonus: Live NSE ticker data mode
    if args.live:
        console.print(f"[yellow]Fetching live market data for real NSE ticker {args.ticker.upper()}...[/yellow]")
        live_tool = LiveNSEDataTool()
        live_file = live_tool.export_live_dossier(args.ticker, output_dir=args.docs)
        if live_file:
            console.print(f"[green]Saved live market snapshot to {live_file}[/green]")
        else:
            console.print(f"[red]Could not retrieve live data for {args.ticker}. Proceeding with existing docs.[/red]")

    config = AgentConfig(
        ticker=args.ticker,
        docs_dir=args.docs,
        reference_date=args.date,
        model_name=args.model,
        api_key=args.api_key
    )

    agent = ResearchAgent(config)
    result = agent.run()

    # Terminal summary table
    table = Table(title="Agent Execution Telemetry", border_style="blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Ticker Analyzed", result["ticker"])
    table.add_row("Documents Processed", str(result["doc_count"]))
    table.add_row("Prompt Injections Neutralized", str(result["injections_blocked"]))
    table.add_row("Entity Mismatches Detected", str(result["entity_mismatches_identified"]))
    table.add_row("Financial Conflicts Resolved", str(result["conflicts_resolved"]))
    table.add_row("Schema & Section Validation", "PASSED" if result["validation_passed"] else "FAILED")

    console.print(table)

    # Save output
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(result["brief_markdown"])

    console.print(f"\n[bold green]Research brief successfully generated and saved to: {args.output}[/bold green]\n")

if __name__ == "__main__":
    main()
