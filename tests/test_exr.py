import numpy as np
import pytest

import arw_to_slog3


def test_exr_round_trip(tmp_path):
    OpenEXR = pytest.importorskip("OpenEXR")
    path = tmp_path / "linear.exr"
    linear = np.array([[[-0.125, 0.18, 1.25], [0.0, 0.5, 2.0]]], dtype=np.float32)
    arw_to_slog3.write_linear_exr(path, linear)
    image = OpenEXR.File(str(path))
    pixels = image.channels()["RGB"].pixels
    assert pixels.dtype == np.float32
    np.testing.assert_array_equal(pixels, linear)
    header = image.header()
    assert "linear S-Gamut3.Cine" in header["comments"]
    assert header["compression"] == OpenEXR.ZIP_COMPRESSION
    chromaticities = header["chromaticities"]
    np.testing.assert_allclose(
        chromaticities, [0.766, 0.275, 0.225, 0.800, 0.089, -0.087, 0.3127, 0.3290], atol=1e-7
    )


def test_exr_cli_bypasses_slog3(tmp_path, monkeypatch):
    pytest.importorskip("OpenEXR")
    source = tmp_path / "input.ARW"
    source.write_bytes(b"placeholder")
    output = tmp_path / "linear.exr"
    monkeypatch.setattr(arw_to_slog3, "develop_arw", lambda _: np.full((1, 1, 3), 0.18, dtype=np.float32))
    monkeypatch.setattr(arw_to_slog3, "encode_slog3", lambda _: (_ for _ in ()).throw(AssertionError("S-Log3 used")))
    assert arw_to_slog3.main([str(source), str(output)]) == 0
    assert output.exists()


def test_missing_exr_extra_fails_before_decode(tmp_path, monkeypatch, capsys):
    source = tmp_path / "input.ARW"
    source.write_bytes(b"placeholder")
    output = tmp_path / "linear.exr"
    monkeypatch.setattr(arw_to_slog3, "develop_arw", lambda _: pytest.fail("RAW was read"))
    monkeypatch.setattr(arw_to_slog3, "_exr_available", lambda: False, raising=False)
    assert arw_to_slog3.main([str(source), str(output)]) != 0
    assert "[exr]" in capsys.readouterr().err
    assert not output.exists()
