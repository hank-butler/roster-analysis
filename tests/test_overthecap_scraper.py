import pytest
import pandas as pd
from pathlib import Path
from src.data_collection.overthecap_scraper import OverTheCapScraper

FIXTURE_HTML = Path(__file__).parent / "fixtures" / "sample_otc.html"


def test_parse_html_table_returns_dataframe():
    scraper = OverTheCapScraper()
    html = FIXTURE_HTML.read_text()
    df = scraper._parse_roster_html(html, team="SF")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3


def test_parse_html_extracts_required_columns():
    scraper = OverTheCapScraper()
    html = FIXTURE_HTML.read_text()
    df = scraper._parse_roster_html(html, team="SF")
    required = {"player_name", "position", "age", "cap_hit", "total_value", "team"}
    assert required.issubset(set(df.columns))


def test_parse_html_converts_currency_to_float():
    scraper = OverTheCapScraper()
    html = FIXTURE_HTML.read_text()
    df = scraper._parse_roster_html(html, team="SF")
    assert df["cap_hit"].dtype == float
    assert df.loc[df["player_name"] == "Brock Purdy", "cap_hit"].iloc[0] == 37_750_000.0


def test_parse_html_adds_team_column():
    scraper = OverTheCapScraper()
    html = FIXTURE_HTML.read_text()
    df = scraper._parse_roster_html(html, team="SF")
    assert (df["team"] == "SF").all()


def test_team_slugs_contains_all_required_teams():
    scraper = OverTheCapScraper()
    required_teams = {"SF", "SEA", "LAR", "ARI", "KC", "TB", "PHI"}
    assert required_teams.issubset(set(scraper.TEAM_SLUGS.keys()))
