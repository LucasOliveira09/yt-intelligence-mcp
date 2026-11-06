import os
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.analytics.outliers import analyze_outliers
from src.auth import finish_auth_flow, load_all_accounts, remove_account, start_auth_flow
from src.services.competitor import fetch_channel_videos, search_youtube_videos
from src.services.content_arbitrage import find_viral_gringo_arbitrage
from src.services.flexible_search import search_youtube_flexible
from src.services.owned import get_channel_overview

app = typer.Typer(help="YT Intelligence CLI — vidIQ alternativo direto na VPS.")
console = Console()


@app.command("analyze")
def analyze(
    channel: str = typer.Argument(..., help="Handle (@canal) ou URL do canal concorrente"),
    limit: int = typer.Option(30, "--limit", "-l", help="Quantidade de vídeos recentes a analisar"),
    threshold: float = typer.Option(2.0, "--threshold", "-t", help="Multiplicador mínimo para ser considerado outlier"),
):
    """
    Analisa os vídeos recentes de um canal concorrente e identifica outliers de audiência (Zero Cota).
    """
    with console.status(f"[bold green]Minerando vídeos de {channel}...[/bold green]"):
        channel_data = fetch_channel_videos(channel, limit=limit)

    if channel_data.get("error"):
        console.print(f"[bold red]Erro ao buscar canal:[/bold red] {channel_data['error']}")
        raise typer.Exit(code=1)

    videos = channel_data.get("videos", [])
    if not videos:
        console.print("[yellow]Nenhum vídeo retornado para este canal.[/yellow]")
        raise typer.Exit()

    analysis = analyze_outliers(videos, threshold=threshold)

    # Header info
    title = channel_data.get("channel_title") or channel
    followers = channel_data.get("followers_count")
    followers_str = f"{followers:,}" if followers else "N/A"

    console.print(Panel(
        f"[bold cyan]Canal:[/bold cyan] {title}\n"
        f"[bold cyan]Inscritos:[/bold cyan] {followers_str}\n"
        f"[bold cyan]Amostra:[/bold cyan] {analysis['sample_size']} vídeos analisados\n"
        f"[bold cyan]Mediana de Views:[/bold cyan] {analysis['median_views']:,}\n"
        f"[bold cyan]Média de Views:[/bold cyan] {analysis['mean_views']:,}\n"
        f"[bold cyan]Outliers Encontrados:[/bold cyan] [bold yellow]{analysis['outliers_count']}[/bold yellow]",
        title="🎯 Inteligência de Concorrência",
        expand=False,
    ))

    # Outliers Table
    table = Table(title="🔥 Vídeos Outliers (Furaram a Bolha do Canal)", show_lines=True)
    table.add_column("Score", style="bold magenta", justify="right")
    table.add_column("Classificação", style="bold")
    table.add_column("Views", justify="right")
    table.add_column("Título", style="white")
    table.add_column("URL", style="dim blue")

    for v in analysis["outliers"]:
        tier_style = "[bold red]MEGA VIRAL 🔥[/bold red]" if v["tier"] == "MEGA_VIRAL" else "[bold green]OUTLIER 🚀[/bold green]"
        table.add_row(
            f"{v['multiplier']}x",
            tier_style,
            f"{v['view_count']:,}",
            v["title"][:75] + ("..." if len(v["title"]) > 75 else ""),
            v["url"],
        )

    if analysis["outliers"]:
        console.print(table)
    else:
        console.print("[yellow]Nenhum vídeo superou o limiar de outlier nesta amostra recente.[/yellow]")


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Termo de busca no YouTube"),
    sort: str = typer.Option("relevance", "--sort", "-s", help="relevance | upload_date | view_count | rating"),
    period: Optional[str] = typer.Option(None, "--period", "-p", help="hour | today | this_week | this_month | this_year"),
    duration: Optional[str] = typer.Option(None, "--duration", "-d", help="short | medium | long"),
    min_views: Optional[int] = typer.Option(None, "--min-views", help="Mínimo de views"),
    exclude_shorts: bool = typer.Option(False, "--no-shorts", help="Ignorar Shorts"),
    limit: int = typer.Option(15, "--limit", "-l", help="Quantidade de vídeos"),
):
    """
    Busca ultra-flexível no YouTube com filtros de data, visualizações, duração e relevância (Zero Cota).
    """
    with console.status(f"[bold green]Buscando vídeos para '{query}'...[/bold green]"):
        res = search_youtube_flexible(
            query=query,
            sort_by=sort,
            upload_period=period,
            duration=duration,
            min_views=min_views,
            exclude_shorts=exclude_shorts,
            limit=limit,
        )

    results = res.get("resultados", [])
    table = Table(title=f"Resultados de Busca: '{query}' ({len(results)} itens)", show_lines=True)
    table.add_column("Views", justify="right", style="bold magenta")
    table.add_column("Duração", justify="center", style="dim")
    table.add_column("Título", style="white")
    table.add_column("Canal / Uploader", style="cyan")
    table.add_column("URL", style="dim blue")

    for item in results:
        table.add_row(
            item.get("views_formatted") or "N/A",
            item.get("duration_formatted") or "N/A",
            item.get("title", "")[:70],
            item.get("uploader") or "N/A",
            item.get("url") or "",
        )

    console.print(table)


@app.command("add-account")
def add_account(
    alias: str = typer.Argument(..., help="Identificador da conta (ex: canal_dev, galuzera)"),
    client_id: Optional[str] = typer.Option(None, "--client-id", "-i", help="Google Client ID"),
    client_secret: Optional[str] = typer.Option(None, "--client-secret", "-s", help="Google Client Secret"),
):
    """
    Inicia o fluxo de autorização OAuth2 Google na VPS (Sem necessidade de arquivo).
    """
    cid = client_id or os.getenv("GOOGLE_CLIENT_ID")
    csecret = client_secret or os.getenv("GOOGLE_CLIENT_SECRET")

    # If neither file nor env vars exist, ask interactively
    from src.config import DATA_DIR
    if not (DATA_DIR / "client_secret.json").exists() and not (cid and csecret):
        console.print("[cyan]Configuração OAuth sem arquivo:[/cyan]")
        cid = typer.prompt("Cole o seu Google Client ID")
        csecret = typer.prompt("Cole o seu Google Client Secret", hide_input=True)

    flow_res = start_auth_flow(alias, client_id=cid, client_secret=csecret)
    if flow_res.get("error"):
        console.print(f"[bold red]Erro:[/bold red] {flow_res.get('message')}")
        raise typer.Exit(code=1)

    console.print(Panel(
        f"[bold yellow]URL de Autorização:[/bold yellow]\n{flow_res['auth_url']}\n\n"
        f"[bold cyan]Instruções:[/bold cyan]\n{flow_res['instructions']}",
        title=f"Conectar Conta Google: {alias}",
        expand=False,
    ))

    code = typer.prompt("Cole aqui o código de autorização ou a URL de redirecionamento")
    with console.status("[bold green]Trocando token...[/bold green]"):
        res = finish_auth_flow(alias, code, client_id=cid, client_secret=csecret)

    if res.get("status") == "success":
        console.print(f"[bold green]✓ Sucesso![/bold green] Canal '[bold cyan]{res['channel_title']}[/bold cyan]' conectado como '[bold]{alias}[/bold]'.")
    else:
        console.print(f"[bold red]Falha na autorização:[/bold red] {res.get('message')}")


@app.command("list-accounts")
def list_accounts():
    """
    Lista todas as contas próprias conectadas.
    """
    accounts = load_all_accounts()
    if not accounts:
        console.print("[yellow]Nenhuma conta conectada ainda. Use 'python -m src.cli add-account <alias>'[/yellow]")
        return

    table = Table(title="Contas Conectadas", show_lines=True)
    table.add_column("Alias", style="bold cyan")
    table.add_column("Título do Canal", style="white")
    table.add_column("Channel ID", style="dim")

    for alias, data in accounts.items():
        table.add_row(
            alias,
            data.get("channel_title") or "N/A",
            data.get("channel_id") or "N/A",
        )

    console.print(table)


@app.command("arbitrage")
def arbitrage_cmd(
    topic: str = typer.Argument("GTA 6", help="Tópico a minerar no exterior"),
    min_multiplier: float = typer.Option(2.5, "--multiplier", "-m", help="Multiplicador mínimo sobre a mediana do canal"),
    min_views: int = typer.Option(50000, "--views", "-v", help="Visualizações mínimas"),
):
    """
    Minera conteúdos virais gringos e gera sugestões adaptadas para o Brasil (Arbitragem de Conteúdo).
    """
    with console.status(f"[bold green]Minerando canais gringos para '{topic}'...[/bold green]"):
        res = find_viral_gringo_arbitrage(
            topic=topic,
            min_multiplier=min_multiplier,
            min_views=min_views,
        )

    table = Table(title=f"🔥 Oportunidades de Arbitragem Gringa: '{topic}'", show_lines=True)
    table.add_column("Score Outlier", style="bold magenta", justify="right")
    table.add_column("Views", justify="right")
    table.add_column("Canal Gringo", style="cyan")
    table.add_column("Título Original", style="white")
    table.add_column("Adaptação Sugerida (PT-BR)", style="bold green")

    for o in res.get("ranking_de_arbitragem", []):
        sug_title = o["adaptacao_brasil"]["titulos_adaptados_ptbr"][0]
        table.add_row(
            o["multiplicador_de_performance"],
            f"{o['views_obtidas']:,}",
            f"{o['canal_gringo']} ({o['canal_handle']})",
            o["titulo_gringo"][:60],
            sug_title,
        )

    console.print(table)


@app.command("remove-account")
def rm_account(
    alias: str = typer.Argument(..., help="Alias da conta a remover"),
):
    """
    Remove uma conta conectada.
    """
    if remove_account(alias):
        console.print(f"[bold green]✓ Conta '{alias}' removida com sucesso.[/bold green]")
    else:
        console.print(f"[bold red]Conta '{alias}' não encontrada.[/bold red]")


@app.command("serve")
def serve():
    """
    Inicia o servidor MCP FastMCP via stdio.
    """
    from src.server import mcp
    mcp.run()


if __name__ == "__main__":
    app()
