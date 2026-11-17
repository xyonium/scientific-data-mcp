from __future__ import annotations

from scientific_data_mcp.config import Settings


def test_from_env_reads_ncbi_key(monkeypatch):
    monkeypatch.setenv("NCBI_API_KEY", "k")
    assert Settings.from_env().ncbi_api_key == "k"


def test_from_env_blank_key_is_none(monkeypatch):
    monkeypatch.setenv("NCBI_API_KEY", "   ")
    assert Settings.from_env().ncbi_api_key is None


def test_default_host_delay_for_eutils():
    assert Settings().host_delays["eutils.ncbi.nlm.nih.gov"] == 0.34
