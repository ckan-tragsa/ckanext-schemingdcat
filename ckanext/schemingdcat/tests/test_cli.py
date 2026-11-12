from click.testing import CliRunner
from ckanext.schemingdcat.cli import schemingdcat


def test_create_inspire_tags():
    runner = CliRunner()
    result = runner.invoke(schemingdcat, ["create-inspire-tags", "-l", "en"])
    assert result.exit_code == 0
    assert "inspire_themes created!" in result.output


def test_delete_inspire_tags():
    runner = CliRunner()
    result = runner.invoke(schemingdcat, ["delete-inspire-tags"])
    assert result.exit_code == 0
    assert "inspire_themes deleted!" in result.output


def test_create_dcat_tags():
    runner = CliRunner()
    result = runner.invoke(schemingdcat, ["create-dcat-tags", "-l", "en"])
    assert result.exit_code == 0
    assert "theme_es created!" in result.output or "theme_eu created!" in result.output


def test_delete_dcat_tags():
    runner = CliRunner()
    result = runner.invoke(schemingdcat, ["delete-dcat-tags"])
    assert result.exit_code == 0
    assert "theme_es deleted!" in result.output or "theme_eu deleted!" in result.output


def test_create_iso_topic_tags():
    runner = CliRunner()
    result = runner.invoke(schemingdcat, ["create-iso-topic-tags", "-l", "en"])
    assert result.exit_code == 0
    assert "topic created!" in result.output


def test_delete_iso_topic_tags():
    runner = CliRunner()
    result = runner.invoke(schemingdcat, ["delete-iso-topic-tags"])
    assert result.exit_code == 0
    assert "topic deleted!" in result.output


def test_download_rdf_eu_vocabs():
    runner = CliRunner()
    result = runner.invoke(schemingdcat, ["download-rdf-eu-vocabs"])
    assert result.exit_code == 0
    assert "EU Vocabs downloaded!" in result.output