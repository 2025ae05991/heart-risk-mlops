import json

import pytest

from heartml.data import load_clean
from heartml.settings import ROOT


@pytest.fixture
def frame():
    return load_clean()


@pytest.fixture
def patient():
    return json.loads((ROOT / "examples/patient.json").read_text())
