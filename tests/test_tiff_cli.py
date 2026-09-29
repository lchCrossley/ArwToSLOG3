from pathlib import Path

import numpy as np
import pytest
import tifffile

import arw_to_slog3


def test_tiff_round_trip(tmp_path):
    path = tmp_path / "out.tif"
    linear = np.array([[[0.0, 0.18, 0.90]]], dtype=np.float32)
    arw_to_slog3.write_slog3_tiff(path, linear)
    with tifffile.TiffFile(path) as tiff:
        image = tiff.asarray()
        page = tiff.pages[0]
        assert image.dtype == np.uint16
        assert image.shape == linear.shape
        assert page.photometric == tifffile.PHOTOMETRIC.RGB
        assert "S-Gamut3.Cine" in page.description
        assert "S-Log3" in page.description
        assert "full-range" in page.description
        assert "ICCProfile" not in page.tags
    expected = np.rint(np.array([95, 420, 598]) / 1023 * 65535).astype(np.uint16)
    np.testing.assert_allclose(image[0, 0], expected, atol=32)


def test_tiff_boundary_clip(tmp_path):
    path = tmp_path / "out.tif"
    arw_to_slog3.write_slog3_tiff(path, np.array([[[-1.0, 0.0, 1e9]]]))
    image = tifffile.imread(path)
    assert image[0, 0, 0] == 0
    assert image[0, 0, 2] == 65535
    assert image[0, 0, 1] > 0


def _source(tmp_path):
    path = tmp_path / "input.ARW"
    path.write_bytes(b"placeholder")
    return path


def test_default_ev_is_zero(tmp_path, monkeypatch):
    source = _source(tmp_path)
    output = tmp_path / "out.tif"
    seen = []
    monkeypatch.setattr(arw_to_slog3, "develop_arw", lambda _: np.zeros((1, 1, 3)))

    def transform(rgb, exposure_ev):
        seen.append(exposure_ev)
        return rgb

    monkeypatch.setattr(arw_to_slog3, "to_linear_sgamut3cine", transform)
    assert arw_to_slog3.main([str(source), str(output)]) == 0
    assert seen == [0.0]
    assert output.exists()


def test_bad_arw_is_atomic(tmp_path, monkeypatch, capsys):
    source = _source(tmp_path)
    output = tmp_path / "out.tif"

    def bad_decode(_):
        raise RuntimeError("unsupported RAW")

    monkeypatch.setattr(arw_to_slog3, "develop_arw", bad_decode)
    assert arw_to_slog3.main([str(source), str(output)]) != 0
    assert "unsupported RAW" in capsys.readouterr().err
    assert sorted(tmp_path.iterdir()) == [source]


def test_destination_created_during_decode_is_not_overwritten(tmp_path, monkeypatch):
    source = _source(tmp_path)
    output = tmp_path / "out.tif"

    def decode(_):
        output.write_bytes(b"another application's data")
        return np.zeros((1, 1, 3), dtype=np.float32)

    monkeypatch.setattr(arw_to_slog3, "develop_arw", decode)
    assert arw_to_slog3.main([str(source), str(output)]) != 0
    assert output.read_bytes() == b"another application's data"
    assert sorted(tmp_path.iterdir()) == [source, output]


@pytest.mark.parametrize("case", ["same", "exists", "extension"])
def test_rejected_paths_before_decode(tmp_path, monkeypatch, case):
    source = _source(tmp_path)
    output = {"same": source, "exists": tmp_path / "out.tif", "extension": tmp_path / "out.png"}[case]
    if case == "exists":
        output.write_bytes(b"keep me")
    monkeypatch.setattr(arw_to_slog3, "develop_arw", lambda _: pytest.fail("RAW was read"))
    assert arw_to_slog3.main([str(source), str(output)]) != 0
    if case == "exists":
        assert output.read_bytes() == b"keep me"


@pytest.mark.parametrize("ev", ["nan", "inf", "-inf"])
def test_nonfinite_ev(tmp_path, monkeypatch, ev):
    source = _source(tmp_path)
    output = tmp_path / "out.tif"
    monkeypatch.setattr(arw_to_slog3, "develop_arw", lambda _: pytest.fail("RAW was read"))
    assert arw_to_slog3.main([str(source), str(output), "--exposure", ev]) != 0
    assert not output.exists()
