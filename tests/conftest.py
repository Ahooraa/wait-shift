import pytest


@pytest.fixture(autouse=True)
def _private_run_mark(tmp_path, monkeypatch):
    """Tests that run a LiveSim must not stamp (or read) the real last-run-end file of the hub the tests happen to run on."""
    monkeypatch.setenv("TESTBED_RUN_MARK", str(tmp_path / "last-run-end"))
