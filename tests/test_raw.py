from pathlib import Path

import numpy as np
import pytest
import rawpy

import arw_to_slog3


class FakeRaw:
    def __init__(self, whitebalance):
        self.camera_whitebalance = whitebalance
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def postprocess(self, **kwargs):
        self.calls.append(kwargs)
        return np.array([[[0, 32768, 65535]]], dtype=np.uint16)


def test_raw_settings(monkeypatch):
    raw = FakeRaw([2.0, 1.0, 1.5, 0.0])
    monkeypatch.setattr(rawpy, "imread", lambda _: raw)
    result = arw_to_slog3.develop_arw(Path("sample.ARW"))
    assert len(raw.calls) == 1
    assert raw.calls[0] == {
        "gamma": (1, 1),
        "no_auto_bright": True,
        "use_camera_wb": True,
        "use_auto_wb": False,
        "bright": 1.0,
        "output_bps": 16,
        "output_color": rawpy.ColorSpace.ProPhoto,
        "demosaic_algorithm": rawpy.DemosaicAlgorithm.AHD,
        "highlight_mode": rawpy.HighlightMode.Clip,
        "adjust_maximum_thr": 0.0,
        "no_auto_scale": False,
        "fbdd_noise_reduction": rawpy.FBDDNoiseReductionMode.Off,
        "median_filter_passes": 0,
        "noise_thr": None,
        "exp_shift": None,
    }
    assert result.dtype == np.float32
    np.testing.assert_allclose(result[0, 0], [0, 32768 / 65535, 1], atol=1e-7)


@pytest.mark.parametrize("wb", [
    None,
    [],
    [0, 1, 1, 0],
    [1, 0, 1, 0],
    [1, 1, 0, 0],
    [-1, 1, 1, 0],
    [1, float("nan"), 1, 0],
    [1, 1, float("inf"), 0],
])
def test_invalid_camera_wb(monkeypatch, wb):
    raw = FakeRaw(wb)
    monkeypatch.setattr(rawpy, "imread", lambda _: raw)
    with pytest.raises(ValueError, match="camera white balance"):
        arw_to_slog3.develop_arw(Path("sample.ARW"))
    assert raw.calls == []


@pytest.mark.parametrize("g2", [0.0, 1.0])
def test_valid_camera_wb(monkeypatch, g2):
    raw = FakeRaw([2.0, 1.0, 1.5, g2])
    monkeypatch.setattr(rawpy, "imread", lambda _: raw)
    arw_to_slog3.develop_arw(Path("sample.ARW"))
    assert len(raw.calls) == 1
