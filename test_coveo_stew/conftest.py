from coveo_testing.markers import register_markers
from _pytest.config import Config


def pytest_configure(config: Config) -> None:
    register_markers(config)
