import copy

import colour
import numpy as np
import pytest

from arw_to_slog3 import encode_slog3, to_linear_sgamut3cine


def test_slog3_reference_values():
    linear = np.array([0.0, 0.18, 0.90])
    assert np.rint(1023 * encode_slog3(linear)).astype(int).tolist() == [95, 420, 598]


def test_sgamut3cine_primaries():
    space = colour.models.RGB_COLOURSPACE_S_GAMUT3_CINE
    np.testing.assert_allclose(space.primaries, [[0.766, 0.275], [0.225, 0.800], [0.089, -0.087]])
    np.testing.assert_allclose(space.whitepoint, [0.3127, 0.3290])


def test_neutral_and_ev():
    neutral = np.full((1, 1, 3), 0.18, dtype=np.float32)
    zero_ev = to_linear_sgamut3cine(neutral)
    np.testing.assert_allclose(zero_ev, neutral, atol=2e-5)
    np.testing.assert_allclose(to_linear_sgamut3cine(neutral, 1), 2 * zero_ev, atol=2e-5)


def test_slog3_negative_branch():
    linear = np.array([-0.005, 0.0, 0.01])
    expected = (linear * (171.2102946929 - 95) / 0.01125 + 95) / 1023
    np.testing.assert_allclose(encode_slog3(linear), expected, atol=1e-12)


def test_libraw_prophoto_convention():
    # LibRaw's prophoto_rgb matrix maps its linear sRGB intermediate to ProPhoto.
    # Compare its published constants to a derived Bradford D65 -> D50 matrix.
    libraw = np.array([
        [0.529317, 0.330092, 0.140588],
        [0.098368, 0.873465, 0.028169],
        [0.016879, 0.117663, 0.865457],
    ])
    srgb = copy.deepcopy(colour.models.RGB_COLOURSPACE_sRGB)
    prophoto = copy.deepcopy(colour.models.RGB_COLOURSPACE_PROPHOTO_RGB)
    srgb.use_derived_transformation_matrices(True)
    prophoto.use_derived_transformation_matrices(True)
    standard = colour.matrix_RGB_to_RGB(
        srgb, prophoto, chromatic_adaptation_transform="Bradford"
    )
    np.testing.assert_allclose(libraw, standard, atol=5e-5, rtol=5e-5)


@pytest.mark.parametrize("bad_ev", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_transform_ev(bad_ev):
    with pytest.raises(ValueError, match="finite"):
        to_linear_sgamut3cine(np.zeros((1, 1, 3)), bad_ev)


def test_transform_rejects_wrong_shape():
    with pytest.raises(ValueError, match="shape"):
        to_linear_sgamut3cine(np.zeros((2, 2)))
