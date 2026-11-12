"""tests/test_bootstrap.py — selección de Python y conservación de datos."""
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

import preparar


@pytest.mark.parametrize("version,compatible", [([3, 10], False), ([3, 11], True),
    ([3, 12], True), ([3, 13], True), ([3, 14], False), ([3, 15], False)])
def test_interpreter_is_checked_before_creating_environment(version, compatible):
    result = subprocess.CompletedProcess([], 0, json.dumps([version, "chosen.exe"]), "")
    with patch.object(preparar.subprocess, "run", return_value=result):
        assert bool(preparar.probe(["candidate"])) is compatible


def test_no_supported_python_does_not_touch_old_environment(tmp_path):
    (tmp_path/".venv").mkdir()
    (tmp_path/".venv"/"keep").touch()
    with patch.object(preparar, "candidates", return_value=iter([["bad"]])), \
         patch.object(preparar, "probe", return_value=None):
        assert preparar.prepare(tmp_path) is None
    assert (tmp_path/".venv"/"keep").exists()


def test_environment_repair_preserves_old_environment_and_data(tmp_path):
    (tmp_path/".venv").mkdir()
    (tmp_path/".venv"/"old").write_text("keep")
    (tmp_path/"data").mkdir()
    (tmp_path/"data"/"records").write_text("untouched")
    (tmp_path/"requirements.txt").write_text("sample==1")
    def pretend_venv_created(*args, **kwargs):
        (tmp_path/".venv").mkdir(exist_ok=True)
    with patch.object(preparar, "candidates", return_value=iter([["good"]])), \
         patch.object(preparar, "probe", return_value="chosen.exe"), \
         patch.object(preparar.subprocess, "run", side_effect=pretend_venv_created) as run:
        python = preparar.prepare(tmp_path)
        assert run.call_count == 2
    assert (tmp_path/"data"/"records").read_text() == "untouched"
    assert next(tmp_path.glob(".venv-anterior-*")).joinpath("old").read_text() == "keep"
    python.parent.mkdir(parents=True, exist_ok=True)
    python.touch()
    with patch.object(preparar, "probe", return_value=str(python)), \
         patch.object(preparar.subprocess, "run") as run:
        assert preparar.prepare(tmp_path) == python
        run.assert_not_called()
