import os
from contextlib import contextmanager
from typing import Final, Generator

import pytest
from _pytest.tmpdir import TempPathFactory
from coveo_testing.parametrize import parametrize

from coveo_stew.ci.runner import ContinuousIntegrationRunner
from coveo_stew.ci.runner_status import RunnerStatus
from coveo_stew.stew import PythonProject

PROJECT_NAME: Final = "mock_linter_errors"

BASE_PYPROJECT_TOML: Final = f"""\
[tool.poetry]
name = "{PROJECT_NAME}"
version = "0.1.1"
description = "an internal test for linters"
authors = ["tests <tools@coveo.com>"]

[tool.poetry.dependencies]
python = ">=3.8,<4"

[tool.poetry.dev-dependencies]
mypy = "*"
black = "*"
isort = "~5"

[tool.stew.ci]
black = true
mypy = true

[tool.stew.ci.custom-runners.isort]
args = ["--check", "--profile black", "."]
autofix = ["--profile black", "."]


[build-system]
requires = ["poetry_core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
"""


POETRY_LOCK: Final = r"""
[[package]]
name = "black"
version = "22.3.0"
description = "The uncompromising code formatter."
category = "dev"
optional = false
python-versions = ">=3.6.2"

[package.dependencies]
click = ">=8.0.0"
mypy-extensions = ">=0.4.3"
pathspec = ">=0.9.0"
platformdirs = ">=2"
tomli = {version = ">=1.1.0", markers = "python_version < \"3.11\""}
typing-extensions = {version = ">=3.10.0.0", markers = "python_version < \"3.10\""}

[package.extras]
colorama = ["colorama (>=0.4.3)"]
d = ["aiohttp (>=3.7.4)"]
jupyter = ["ipython (>=7.8.0)", "tokenize-rt (>=3.2.0)"]
uvloop = ["uvloop (>=0.15.2)"]

[[package]]
name = "click"
version = "8.1.3"
description = "Composable command line interface toolkit"
category = "dev"
optional = false
python-versions = ">=3.7"

[package.dependencies]
colorama = {version = "*", markers = "platform_system == \"Windows\""}

[[package]]
name = "colorama"
version = "0.4.4"
description = "Cross-platform colored terminal text."
category = "dev"
optional = false
python-versions = ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*"

[[package]]
name = "isort"
version = "5.10.1"
description = "A Python utility / library to sort Python imports."
category = "dev"
optional = false
python-versions = ">=3.6.1,<4.0"

[package.extras]
pipfile_deprecated_finder = ["pipreqs", "requirementslib"]
requirements_deprecated_finder = ["pipreqs", "pip-api"]
colors = ["colorama (>=0.4.3,<0.5.0)"]
plugins = ["setuptools"]

[[package]]
name = "mypy"
version = "0.950"
description = "Optional static typing for Python"
category = "dev"
optional = false
python-versions = ">=3.6"

[package.dependencies]
mypy-extensions = ">=0.4.3"
tomli = {version = ">=1.1.0", markers = "python_version < \"3.11\""}
typing-extensions = ">=3.10"

[package.extras]
dmypy = ["psutil (>=4.0)"]
python2 = ["typed-ast (>=1.4.0,<2)"]
reports = ["lxml"]

[[package]]
name = "mypy-extensions"
version = "0.4.3"
description = "Experimental type system extensions for programs checked with the mypy typechecker."
category = "dev"
optional = false
python-versions = "*"

[[package]]
name = "pathspec"
version = "0.9.0"
description = "Utility library for gitignore style pattern matching of file paths."
category = "dev"
optional = false
python-versions = "!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*,>=2.7"

[[package]]
name = "platformdirs"
version = "2.5.2"
description = "A small Python module for determining appropriate platform-specific dirs, e.g. a \"user data dir\"."
category = "dev"
optional = false
python-versions = ">=3.7"

[package.extras]
docs = ["furo (>=2021.7.5b38)", "proselint (>=0.10.2)", "sphinx-autodoc-typehints (>=1.12)", "sphinx (>=4)"]
test = ["appdirs (==1.4.4)", "pytest-cov (>=2.7)", "pytest-mock (>=3.6)", "pytest (>=6)"]

[[package]]
name = "tomli"
version = "2.0.1"
description = "A lil' TOML parser"
category = "dev"
optional = false
python-versions = ">=3.7"

[[package]]
name = "typing-extensions"
version = "4.2.0"
description = "Backported and Experimental Type Hints for Python 3.7+"
category = "dev"
optional = false
python-versions = ">=3.7"

[metadata]
lock-version = "1.1"
python-versions = ">=3.8,<4"
content-hash = "cb4c3bcef0a2713ef9e428e2ef049c49ab82c29e93143c57bec390d2e1670f84"

[metadata.files]
black = [
    {file = "black-22.3.0-cp310-cp310-macosx_10_9_universal2.whl", hash = "sha256:2497f9c2386572e28921fa8bec7be3e51de6801f7459dffd6e62492531c47e09"},
    {file = "black-22.3.0-cp310-cp310-macosx_10_9_x86_64.whl", hash = "sha256:5795a0375eb87bfe902e80e0c8cfaedf8af4d49694d69161e5bd3206c18618bb"},
    {file = "black-22.3.0-cp310-cp310-macosx_11_0_arm64.whl", hash = "sha256:e3556168e2e5c49629f7b0f377070240bd5511e45e25a4497bb0073d9dda776a"},
    {file = "black-22.3.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl", hash = "sha256:67c8301ec94e3bcc8906740fe071391bce40a862b7be0b86fb5382beefecd968"},
    {file = "black-22.3.0-cp310-cp310-win_amd64.whl", hash = "sha256:fd57160949179ec517d32ac2ac898b5f20d68ed1a9c977346efbac9c2f1e779d"},
    {file = "black-22.3.0-cp36-cp36m-macosx_10_9_x86_64.whl", hash = "sha256:cc1e1de68c8e5444e8f94c3670bb48a2beef0e91dddfd4fcc29595ebd90bb9ce"},
    {file = "black-22.3.0-cp36-cp36m-manylinux_2_17_x86_64.manylinux2014_x86_64.whl", hash = "sha256:6d2fc92002d44746d3e7db7cf9313cf4452f43e9ea77a2c939defce3b10b5c82"},
    {file = "black-22.3.0-cp36-cp36m-win_amd64.whl", hash = "sha256:a6342964b43a99dbc72f72812bf88cad8f0217ae9acb47c0d4f141a6416d2d7b"},
    {file = "black-22.3.0-cp37-cp37m-macosx_10_9_x86_64.whl", hash = "sha256:328efc0cc70ccb23429d6be184a15ce613f676bdfc85e5fe8ea2a9354b4e9015"},
    {file = "black-22.3.0-cp37-cp37m-manylinux_2_17_x86_64.manylinux2014_x86_64.whl", hash = "sha256:06f9d8846f2340dfac80ceb20200ea5d1b3f181dd0556b47af4e8e0b24fa0a6b"},
    {file = "black-22.3.0-cp37-cp37m-win_amd64.whl", hash = "sha256:ad4efa5fad66b903b4a5f96d91461d90b9507a812b3c5de657d544215bb7877a"},
    {file = "black-22.3.0-cp38-cp38-macosx_10_9_universal2.whl", hash = "sha256:e8477ec6bbfe0312c128e74644ac8a02ca06bcdb8982d4ee06f209be28cdf163"},
    {file = "black-22.3.0-cp38-cp38-macosx_10_9_x86_64.whl", hash = "sha256:637a4014c63fbf42a692d22b55d8ad6968a946b4a6ebc385c5505d9625b6a464"},
    {file = "black-22.3.0-cp38-cp38-macosx_11_0_arm64.whl", hash = "sha256:863714200ada56cbc366dc9ae5291ceb936573155f8bf8e9de92aef51f3ad0f0"},
    {file = "black-22.3.0-cp38-cp38-manylinux_2_17_x86_64.manylinux2014_x86_64.whl", hash = "sha256:10dbe6e6d2988049b4655b2b739f98785a884d4d6b85bc35133a8fb9a2233176"},
    {file = "black-22.3.0-cp38-cp38-win_amd64.whl", hash = "sha256:cee3e11161dde1b2a33a904b850b0899e0424cc331b7295f2a9698e79f9a69a0"},
    {file = "black-22.3.0-cp39-cp39-macosx_10_9_universal2.whl", hash = "sha256:5891ef8abc06576985de8fa88e95ab70641de6c1fca97e2a15820a9b69e51b20"},
    {file = "black-22.3.0-cp39-cp39-macosx_10_9_x86_64.whl", hash = "sha256:30d78ba6bf080eeaf0b7b875d924b15cd46fec5fd044ddfbad38c8ea9171043a"},
    {file = "black-22.3.0-cp39-cp39-macosx_11_0_arm64.whl", hash = "sha256:ee8f1f7228cce7dffc2b464f07ce769f478968bfb3dd1254a4c2eeed84928aad"},
    {file = "black-22.3.0-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl", hash = "sha256:6ee227b696ca60dd1c507be80a6bc849a5a6ab57ac7352aad1ffec9e8b805f21"},
    {file = "black-22.3.0-cp39-cp39-win_amd64.whl", hash = "sha256:9b542ced1ec0ceeff5b37d69838106a6348e60db7b8fdd245294dc1d26136265"},
    {file = "black-22.3.0-py3-none-any.whl", hash = "sha256:bc58025940a896d7e5356952228b68f793cf5fcb342be703c3a2669a1488cb72"},
    {file = "black-22.3.0.tar.gz", hash = "sha256:35020b8886c022ced9282b51b5a875b6d1ab0c387b31a065b84db7c33085ca79"},
]
click = [
    {file = "click-8.1.3-py3-none-any.whl", hash = "sha256:bb4d8133cb15a609f44e8213d9b391b0809795062913b383c62be0ee95b1db48"},
    {file = "click-8.1.3.tar.gz", hash = "sha256:7682dc8afb30297001674575ea00d1814d808d6a36af415a82bd481d37ba7b8e"},
]
colorama = [
    {file = "colorama-0.4.4-py2.py3-none-any.whl", hash = "sha256:9f47eda37229f68eee03b24b9748937c7dc3868f906e8ba69fbcbdd3bc5dc3e2"},
    {file = "colorama-0.4.4.tar.gz", hash = "sha256:5941b2b48a20143d2267e95b1c2a7603ce057ee39fd88e7329b0c292aa16869b"},
]
isort = [
    {file = "isort-5.10.1-py3-none-any.whl", hash = "sha256:6f62d78e2f89b4500b080fe3a81690850cd254227f27f75c3a0c491a1f351ba7"},
    {file = "isort-5.10.1.tar.gz", hash = "sha256:e8443a5e7a020e9d7f97f1d7d9cd17c88bcb3bc7e218bf9cf5095fe550be2951"},
]
mypy = [
    {file = "mypy-0.950-cp310-cp310-macosx_10_9_universal2.whl", hash = "sha256:cf9c261958a769a3bd38c3e133801ebcd284ffb734ea12d01457cb09eacf7d7b"},
    {file = "mypy-0.950-cp310-cp310-macosx_10_9_x86_64.whl", hash = "sha256:b5b5bd0ffb11b4aba2bb6d31b8643902c48f990cc92fda4e21afac658044f0c0"},
    {file = "mypy-0.950-cp310-cp310-macosx_11_0_arm64.whl", hash = "sha256:5e7647df0f8fc947388e6251d728189cfadb3b1e558407f93254e35abc026e22"},
    {file = "mypy-0.950-cp310-cp310-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl", hash = "sha256:eaff8156016487c1af5ffa5304c3e3fd183edcb412f3e9c72db349faf3f6e0eb"},
    {file = "mypy-0.950-cp310-cp310-win_amd64.whl", hash = "sha256:563514c7dc504698fb66bb1cf897657a173a496406f1866afae73ab5b3cdb334"},
    {file = "mypy-0.950-cp36-cp36m-macosx_10_9_x86_64.whl", hash = "sha256:dd4d670eee9610bf61c25c940e9ade2d0ed05eb44227275cce88701fee014b1f"},
    {file = "mypy-0.950-cp36-cp36m-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl", hash = "sha256:ca75ecf2783395ca3016a5e455cb322ba26b6d33b4b413fcdedfc632e67941dc"},
    {file = "mypy-0.950-cp36-cp36m-win_amd64.whl", hash = "sha256:6003de687c13196e8a1243a5e4bcce617d79b88f83ee6625437e335d89dfebe2"},
    {file = "mypy-0.950-cp37-cp37m-macosx_10_9_x86_64.whl", hash = "sha256:4c653e4846f287051599ed8f4b3c044b80e540e88feec76b11044ddc5612ffed"},
    {file = "mypy-0.950-cp37-cp37m-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl", hash = "sha256:e19736af56947addedce4674c0971e5dceef1b5ec7d667fe86bcd2b07f8f9075"},
    {file = "mypy-0.950-cp37-cp37m-win_amd64.whl", hash = "sha256:ef7beb2a3582eb7a9f37beaf38a28acfd801988cde688760aea9e6cc4832b10b"},
    {file = "mypy-0.950-cp38-cp38-macosx_10_9_universal2.whl", hash = "sha256:0112752a6ff07230f9ec2f71b0d3d4e088a910fdce454fdb6553e83ed0eced7d"},
    {file = "mypy-0.950-cp38-cp38-macosx_10_9_x86_64.whl", hash = "sha256:ee0a36edd332ed2c5208565ae6e3a7afc0eabb53f5327e281f2ef03a6bc7687a"},
    {file = "mypy-0.950-cp38-cp38-macosx_11_0_arm64.whl", hash = "sha256:77423570c04aca807508a492037abbd72b12a1fb25a385847d191cd50b2c9605"},
    {file = "mypy-0.950-cp38-cp38-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl", hash = "sha256:5ce6a09042b6da16d773d2110e44f169683d8cc8687e79ec6d1181a72cb028d2"},
    {file = "mypy-0.950-cp38-cp38-win_amd64.whl", hash = "sha256:5b231afd6a6e951381b9ef09a1223b1feabe13625388db48a8690f8daa9b71ff"},
    {file = "mypy-0.950-cp39-cp39-macosx_10_9_universal2.whl", hash = "sha256:0384d9f3af49837baa92f559d3fa673e6d2652a16550a9ee07fc08c736f5e6f8"},
    {file = "mypy-0.950-cp39-cp39-macosx_10_9_x86_64.whl", hash = "sha256:1fdeb0a0f64f2a874a4c1f5271f06e40e1e9779bf55f9567f149466fc7a55038"},
    {file = "mypy-0.950-cp39-cp39-macosx_11_0_arm64.whl", hash = "sha256:61504b9a5ae166ba5ecfed9e93357fd51aa693d3d434b582a925338a2ff57fd2"},
    {file = "mypy-0.950-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl", hash = "sha256:a952b8bc0ae278fc6316e6384f67bb9a396eb30aced6ad034d3a76120ebcc519"},
    {file = "mypy-0.950-cp39-cp39-win_amd64.whl", hash = "sha256:eaea21d150fb26d7b4856766e7addcf929119dd19fc832b22e71d942835201ef"},
    {file = "mypy-0.950-py3-none-any.whl", hash = "sha256:a4d9898f46446bfb6405383b57b96737dcfd0a7f25b748e78ef3e8c576bba3cb"},
    {file = "mypy-0.950.tar.gz", hash = "sha256:1b333cfbca1762ff15808a0ef4f71b5d3eed8528b23ea1c3fb50543c867d68de"},
]
mypy-extensions = [
    {file = "mypy_extensions-0.4.3-py2.py3-none-any.whl", hash = "sha256:090fedd75945a69ae91ce1303b5824f428daf5a028d2f6ab8a299250a846f15d"},
    {file = "mypy_extensions-0.4.3.tar.gz", hash = "sha256:2d82818f5bb3e369420cb3c4060a7970edba416647068eb4c5343488a6c604a8"},
]
pathspec = [
    {file = "pathspec-0.9.0-py2.py3-none-any.whl", hash = "sha256:7d15c4ddb0b5c802d161efc417ec1a2558ea2653c2e8ad9c19098201dc1c993a"},
    {file = "pathspec-0.9.0.tar.gz", hash = "sha256:e564499435a2673d586f6b2130bb5b95f04a3ba06f81b8f895b651a3c76aabb1"},
]
platformdirs = [
    {file = "platformdirs-2.5.2-py3-none-any.whl", hash = "sha256:027d8e83a2d7de06bbac4e5ef7e023c02b863d7ea5d079477e722bb41ab25788"},
    {file = "platformdirs-2.5.2.tar.gz", hash = "sha256:58c8abb07dcb441e6ee4b11d8df0ac856038f944ab98b7be6b27b2a3c7feef19"},
]
tomli = [
    {file = "tomli-2.0.1-py3-none-any.whl", hash = "sha256:939de3e7a6161af0c887ef91b7d41a53e7c5a1ca976325f429cb46ea9bc30ecc"},
    {file = "tomli-2.0.1.tar.gz", hash = "sha256:de526c12914f0c550d15924c62d72abc48d6fe7364aa87328337a31007fe8a4f"},
]
typing-extensions = [
    {file = "typing_extensions-4.2.0-py3-none-any.whl", hash = "sha256:6657594ee297170d19f67d55c05852a874e7eb634f4f753dbd667855e07c1708"},
    {file = "typing_extensions-4.2.0.tar.gz", hash = "sha256:f1c24655a0da0d1b67f07e17a5e6b2a105894e6824b92096378bb3668ef02376"},
]
"""

POETRY_CONFIG: Final = """\
[virtualenvs]
create = true
in-project = true
"""


BROKEN_CODE: Final = """\
# imports are in the wrong order (isort)
from pprint import pprint
from pathlib import Path


def fn(a: str) -> Path:
    return Path(a)

# mypy will complain about 1 not being a str
# black will complain about the extra space
pprint(fn(1 ))
"""


WORKING_CODE: Final = """\
from pathlib import Path
from pprint import pprint


def fn(a: str) -> Path:
    return Path(a)


pprint(fn("test"))
"""


@pytest.fixture(scope="module")
def linter_project(tmp_path_factory: TempPathFactory) -> PythonProject:
    tmpdir = tmp_path_factory.mktemp("linter-project")
    (tmpdir / "pyproject.toml").write_text(BASE_PYPROJECT_TOML)
    (tmpdir / "poetry.toml").write_text(POETRY_CONFIG)
    (tmpdir / "poetry.lock").write_text(POETRY_LOCK)
    project_folder = tmpdir / PROJECT_NAME
    project_folder.mkdir()

    (project_folder / "py.typed").touch()
    (project_folder / "__init__.py").touch()
    project = PythonProject(tmpdir)
    project.install(sync=True)
    return project


@contextmanager
def write_code(project: PythonProject, code: str) -> Generator[None, None, None]:
    code_file = project.project_path / project.package.safe_name / "code.py"
    code_file.write_text(code, encoding="utf-8")
    try:
        yield
    finally:
        code_file.unlink()


@parametrize(
    ("code", "expected_outcome"),
    (
        (BROKEN_CODE, RunnerStatus.CheckFailed),
        (WORKING_CODE, RunnerStatus.Success),
    ),
    ids=("broken", "correct"),
)
@parametrize(
    ("check", "failure_text"),
    [
        (
            "mypy",
            'error: Argument 1 to "fn" has incompatible type "int"; expected "str"',
        ),
        ("isort", "Imports are incorrectly sorted and/or formatted."),
        ("black", f"would reformat mock_linter_errors{os.sep}code.py"),
    ],
    ids=("mypy", "isort", "black"),
)
def test_linters(
    code: str,
    expected_outcome: RunnerStatus,
    check: str,
    failure_text: str,
    linter_project: PythonProject,
) -> None:
    with write_code(linter_project, code):
        outcome = linter_project.launch_continuous_integration(checks=[check], quick=True)
        assert outcome in (RunnerStatus.Success, RunnerStatus.CheckFailed)
        ci_runner = _check_result(outcome, expected_outcome, linter_project, check, failure_text)
        if expected_outcome is RunnerStatus.CheckFailed and ci_runner.supports_auto_fix:
            outcome = linter_project.launch_continuous_integration(
                auto_fix=True, checks=[check], quick=True
            )
            _ = _check_result(outcome, RunnerStatus.Success, linter_project, check, failure_text)


def _check_result(
    outcome: RunnerStatus,
    expected_outcome: RunnerStatus,
    project: PythonProject,
    check_name: str,
    failure_text: str,
) -> ContinuousIntegrationRunner:
    assert outcome is expected_outcome
    check_instance = project.ci.get_runner(check_name)
    assert isinstance(check_instance, ContinuousIntegrationRunner)
    if expected_outcome is RunnerStatus.Success:
        assert failure_text not in check_instance.last_output()
    else:
        assert failure_text in check_instance.last_output()
    return check_instance
