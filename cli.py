#!/usr/bin/env python3
"""
Growth-Tier Ads Protocol Agent CLI

Usage:
    python cli.py test-connection
    python cli.py generate-personas --config examples/saas_config.json
    python cli.py generate-ads --config examples/saas_config.json
    python cli.py generate-upsell --config examples/saas_config.json
    python cli.py run-workflow --config examples/saas_config.json
"""

import json
import asyncio
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    name="ads-agent",
    help="Growth-Tier Ads Protocol Agent - Autonomous Google Ads Management",
)


def load_config(config_path: str):
    """Load campaign configuration from JSON file."""
    from src.models.configuration import CampaignConfiguration

    with open(config_path, "r") as f:
        data = json.load(f)
    return CampaignConfiguration(**data)


@app.command()
def test_connection():
    """Test connection to the Google Ads API."""
    from src.config.google_ads_client import get_google_ads_client
    from google.ads.googleads.errors import GoogleAdsException

    typer.echo("Testing Google Ads API connection...")

    client = get_google_ads_client()
    if not client:
        typer.secho("FAILED: Could not initialize client", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        customer_service = client.get_service("CustomerService")
        accessible_customers = customer_service.list_accessible_customers()

        typer.secho("SUCCESS: Connected to Google Ads API", fg=typer.colors.GREEN)
        typer.echo("\nAccessible accounts:")
        for resource_name in accessible_customers.resource_names:
            typer.echo(f"  - {resource_name}")

    except GoogleAdsException as ex:
        typer.secho(f"FAILED: {ex.error.code().name}", fg=typer.colors.RED)
        for error in ex.failure.errors:
            typer.echo(f"  Error: {error.message}")
        raise typer.Exit(1)


@app.command()
def generate_personas(
    config: str = typer.Option(..., "--config", "-c", help="Path to config JSON"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """Generate buyer personas for a campaign."""
    from src.generators.persona_generator import generate_personas as gen_personas

    typer.echo(f"Loading config from {config}...")
    campaign_config = load_config(config)

    typer.echo("Generating personas (this may take a moment)...")
    personas = gen_personas(campaign_config)

    typer.secho(f"\nGenerated {len(personas.personas)} personas:", fg=typer.colors.GREEN)
    for i, p in enumerate(personas.personas, 1):
        typer.echo(f"\n{i}. {p.name}")
        typer.echo(f"   Pain Point: {p.pain_point}")
        typer.echo(f"   Purchase Driver: {p.purchase_driver}")
        typer.echo(f"   Ad Group: {p.ad_group_name}")

    if output:
        with open(output, "w") as f:
            json.dump(personas.model_dump(), f, indent=2)
        typer.echo(f"\nSaved to {output}")


@app.command()
def generate_ads(
    config: str = typer.Option(..., "--config", "-c", help="Path to config JSON"),
    persona_name: str = typer.Option("Default Persona", "--persona", "-p", help="Persona name"),
):
    """Generate polarity ad copy (Pull/Push) for a persona."""
    from src.generators.ad_copy_generator import generate_polarity_ads
    from src.generators.persona_generator import PersonaSchema

    typer.echo(f"Loading config from {config}...")
    campaign_config = load_config(config)

    # Create a sample persona for demo
    persona = PersonaSchema(
        name=persona_name,
        pain_point="Struggling with manual processes",
        purchase_driver="Wants to save time and increase efficiency",
        ad_group_name="persona_default",
    )

    typer.echo(f"Generating ads for persona: {persona.name}...")
    ads = generate_polarity_ads(persona, campaign_config)

    for ad in ads:
        typer.secho(f"\n{ad.angle} Ad:", fg=typer.colors.CYAN)
        typer.echo("  Headlines:")
        for h in ad.copy.headlines[:5]:
            typer.echo(f"    - {h}")
        typer.echo("  Descriptions:")
        for d in ad.copy.descriptions[:2]:
            typer.echo(f"    - {d}")


@app.command()
def generate_upsell(
    config: str = typer.Option(..., "--config", "-c", help="Path to config JSON"),
):
    """Generate upsell script based on monetization model."""
    from src.generators.upsell_generator import generate_upsell_script

    typer.echo(f"Loading config from {config}...")
    campaign_config = load_config(config)

    typer.echo(f"Generating upsell script for {campaign_config.monetization_model.value}...")
    script = generate_upsell_script(campaign_config)

    typer.secho("\nUpsell Script:", fg=typer.colors.GREEN)
    typer.echo(f"\nHook:\n  {script.hook}")
    typer.echo(f"\nTransition:\n  {script.transition}")
    typer.echo(f"\nCTA:\n  {script.cta}")
    typer.echo(f"\nUrgency:\n  {script.urgency_element}")


@app.command()
def run_workflow(
    config: str = typer.Option(..., "--config", "-c", help="Path to config JSON"),
):
    """Run the full campaign setup workflow with Claude Agent."""
    from src.agent.client import client
    from src.workflows.setup_workflow import run_setup

    typer.echo(f"Loading config from {config}...")
    campaign_config = load_config(config)

    typer.echo("\nStarting campaign setup workflow...")
    typer.echo("The agent will ask for approval before creating the campaign.\n")

    result = asyncio.run(run_setup(client, campaign_config))

    if result.status == "SUCCESS":
        typer.secho(f"\n{result.status}: {result.message}", fg=typer.colors.GREEN)
        if result.campaign_id:
            typer.echo(f"Campaign ID: {result.campaign_id}")
    else:
        typer.secho(f"\n{result.status}: {result.message}", fg=typer.colors.YELLOW)


@app.command()
def list_examples():
    """List available example configurations."""
    examples_dir = Path(__file__).parent / "examples"

    typer.secho("Available example configurations:\n", fg=typer.colors.GREEN)
    for config_file in examples_dir.glob("*.json"):
        with open(config_file, "r") as f:
            data = json.load(f)
        typer.echo(f"  {config_file.name}")
        typer.echo(f"    Offer: {data.get('offer_name', 'N/A')}")
        typer.echo(f"    Vertical: {data.get('vertical_type', 'N/A')}")
        typer.echo(f"    Model: {data.get('monetization_model', 'N/A')}")
        typer.echo()


if __name__ == "__main__":
    app()
