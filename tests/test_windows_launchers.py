"""Smoke-test the Windows drag-and-drop entry point without a real ARW."""

import os
from pathlib import Path
import shutil
import subprocess
import venv

import pytest


@pytest.mark.skipif(os.name != "nt", reason="Windows batch launcher")
def test_drag_drop_launcher_keeps_input_path_and_places_tiff_beside_arw(tmp_path):
    launcher = Path(__file__).resolve().parents[1] / "convert_windows.cmd"
    shutil.copy2(launcher, tmp_path / launcher.name)
    venv.EnvBuilder(with_pip=False).create(tmp_path / ".venv")
    (tmp_path / "arw_to_slog3.py").write_text(
        "import pathlib, sys\n"
        "pathlib.Path(sys.argv[2]).write_text(sys.argv[1], encoding='utf-8')\n",
        encoding="utf-8",
    )
    source = tmp_path / "我的照片 photos" / "样片 image.ARW"
    source.parent.mkdir()
    source.write_bytes(b"placeholder")

    result = subprocess.run(
        ["cmd", "/c", str(tmp_path / launcher.name), str(source)],
        input="\n", text=True, capture_output=True, timeout=30,
    )

    destination = source.with_name("样片 image_SLog3.tif")
    assert result.returncode == 0, result.stdout + result.stderr
    assert destination.read_text(encoding="utf-8") == str(source)


@pytest.mark.skipif(os.name != "nt", reason="Windows batch launcher")
def test_drag_drop_launcher_rejects_missing_environment(tmp_path):
    launcher = Path(__file__).resolve().parents[1] / "convert_windows.cmd"
    shutil.copy2(launcher, tmp_path / launcher.name)
    source = tmp_path / "photo.ARW"
    source.write_bytes(b"placeholder")

    result = subprocess.run(
        ["cmd", "/c", str(tmp_path / launcher.name), str(source)],
        input="\n", text=True, capture_output=True, timeout=30,
    )

    assert result.returncode != 0
    assert "setup_windows.cmd" in result.stdout
    assert not source.with_name("photo_SLog3.tif").exists()
