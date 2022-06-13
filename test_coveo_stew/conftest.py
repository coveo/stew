from _pytest.config import Config
from coveo_testing.markers import register_markers


def pytest_configure(config: Config) -> None:
    register_markers(config)
