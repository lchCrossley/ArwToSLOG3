"""Convert Sony ARW stills to standard S-Gamut3.Cine / S-Log3 images."""

import argparse
import copy
import importlib.util
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Sequence
import warnings

with warnings.catch_warnings():
    # These optional plotting/SciPy APIs are unused by this converter.
    warnings.filterwarnings("ignore", message='.*related API features are not available.*', category=Warning)
    import colour
import numpy as np
import rawpy
import tifffile

_PROPHOTO = copy.deepcopy(colour.models.RGB_COLOURSPACE_PROPHOTO_RGB)
_SONY = copy.deepcopy(colour.models.RGB_COLOURSPACE_S_GAMUT3_CINE)
# Derive the matrices from the published xy coordinates instead of rounded tables.
_PROPHOTO.use_derived_transformation_matrices(True)
_SONY.use_derived_transformation_matrices(True)


def to_linear_sgamut3cine(rgb: np.ndarray, exposure_ev: float = 0.0) -> np.ndarray:
    """Convert scene-linear ProPhoto RGB D50 to linear S-Gamut3.Cine D65."""
    source = np.asarray(rgb)
    if source.ndim != 3 or source.shape[-1] != 3:
        raise ValueError("linear RGB must have shape (height, width, 3)")
    if not math.isfinite(exposure_ev):
        raise ValueError("exposure EV must be finite")
    gain = 2.0**exposure_ev
    if not math.isfinite(gain):
        raise ValueError("exposure EV is too large")

    result = np.empty(source.shape, dtype=np.float32)
    for row in range(0, source.shape[0], 256):
        stop = row + 256
        result[row:stop] = colour.RGB_to_RGB(
            source[row:stop].astype(np.float64) * gain,
            _PROPHOTO,
            _SONY,
            chromatic_adaptation_transform="Bradford",
            apply_cctf_decoding=False,
            apply_cctf_encoding=False,
        )
    return result


def encode_slog3(linear_rgb: np.ndarray) -> np.ndarray:
    """Encode linear S-Gamut3.Cine with Sony full-range S-Log3."""
    # colour's piecewise np.where evaluates the unused log branch for negatives.
    with np.errstate(invalid="ignore", divide="ignore"):
        return colour.models.log_encoding_SLog3(
            np.asarray(linear_rgb),
            bit_depth=10,
            out_normalised_code_value=True,
            in_reflection=True,
        )


def develop_arw(input_path: Path) -> np.ndarray:
    """Develop an ARW to normalized scene-linear ProPhoto RGB D50."""
    with rawpy.imread(str(input_path)) as raw:
        wb = raw.camera_whitebalance
        if wb is None:
            raise ValueError("camera white balance is missing or invalid")
        try:
            coefficients = np.asarray(wb, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ValueError("camera white balance is missing or invalid") from exc
        if (
            coefficients.ndim != 1
            or coefficients.size < 3
            or not np.all(np.isfinite(coefficients))
            or np.any(coefficients[:3] <= 0)
            or np.any(coefficients[3:] < 0)
        ):
            raise ValueError("camera white balance is missing or invalid")

        developed = raw.postprocess(
            gamma=(1, 1),
            no_auto_bright=True,
            use_camera_wb=True,
            use_auto_wb=False,
            bright=1.0,
            output_bps=16,
            output_color=rawpy.ColorSpace.ProPhoto,
            demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
            highlight_mode=rawpy.HighlightMode.Clip,
            adjust_maximum_thr=0.0,
            no_auto_scale=False,
            fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
            median_filter_passes=0,
            noise_thr=None,
            exp_shift=None,
        )
    return developed.astype(np.float32) / np.float32(65535)


def write_slog3_tiff(output_path: Path, linear_rgb: np.ndarray) -> None:
    """Write full-range Sony S-Log3 samples in an unprofiled 16-bit RGB TIFF."""
    linear = np.asarray(linear_rgb)
    if linear.ndim != 3 or linear.shape[-1] != 3:
        raise ValueError("linear RGB must have shape (height, width, 3)")
    samples = np.empty(linear.shape, dtype=np.uint16)
    for row in range(0, linear.shape[0], 256):
        stop = row + 256
        encoded = encode_slog3(linear[row:stop])
        if not np.all(np.isfinite(encoded)):
            raise ValueError("S-Log3 conversion produced nonfinite samples")
        samples[row:stop] = np.rint(np.clip(encoded, 0, 1) * 65535).astype(np.uint16)
    tifffile.imwrite(
        output_path,
        samples,
        photometric="rgb",
        metadata=None,
        description=(
            "Sony S-Gamut3.Cine / S-Log3, full-range. "
            "RAW: camera WB, linear gamma, no auto brightness or exposure. "
            "Assign Sony S-Gamut3.Cine and Sony S-Log3 in a color-managed application."
        ),
    )


def write_linear_exr(output_path: Path, linear_rgb: np.ndarray) -> None:
    """Write float32 linear S-Gamut3.Cine with its published chromaticities."""
    try:
        import OpenEXR
    except ImportError as exc:
        raise RuntimeError('EXR support requires: pip install -e ".[exr]"') from exc

    linear = np.asarray(linear_rgb)
    if linear.ndim != 3 or linear.shape[-1] != 3:
        raise ValueError("linear RGB must have shape (height, width, 3)")
    if not np.all(np.isfinite(linear)):
        raise ValueError("linear EXR contains nonfinite samples")
    chromaticities = (0.766, 0.275, 0.225, 0.800, 0.089, -0.087, 0.3127, 0.3290)
    header = {
        "compression": OpenEXR.ZIP_COMPRESSION,
        "chromaticities": chromaticities,
        "comments": "linear S-Gamut3.Cine (D65), not S-Log3; developed from Sony ARW with camera WB",
    }
    OpenEXR.File(header, {"RGB": linear.astype(np.float32, copy=False)}).write(str(output_path))


def _exr_available() -> bool:
    return importlib.util.find_spec("OpenEXR") is not None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Sony .ARW still image")
    parser.add_argument("output", type=Path, help="Output .tif/.tiff (S-Log3) or .exr (linear)")
    parser.add_argument("--exposure", type=float, default=0.0, metavar="EV", help="Manual scene-linear exposure compensation (default: 0 EV)")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        if not math.isfinite(args.exposure):
            raise ValueError("exposure EV must be finite")
        if args.input.suffix.lower() != ".arw" or not args.input.is_file():
            raise ValueError("input must be an existing Sony .ARW file")
        suffix = args.output.suffix.lower()
        if suffix not in {".tif", ".tiff", ".exr"}:
            raise ValueError("output must be .tif, .tiff, or .exr")
        if args.input.resolve() == args.output.resolve():
            raise ValueError("output must differ from input")
        if args.output.exists():
            raise ValueError("output already exists; refusing to overwrite")
        if suffix == ".exr" and not _exr_available():
            raise RuntimeError('EXR support requires: pip install -e ".[exr]"')

        linear_prophoto = develop_arw(args.input)
        linear_sony = to_linear_sgamut3cine(linear_prophoto, args.exposure)
        file_descriptor, temporary = tempfile.mkstemp(
            prefix=f".{args.output.stem}-", suffix=args.output.suffix, dir=args.output.parent
        )
        os.close(file_descriptor)
        try:
            if suffix == ".exr":
                write_linear_exr(Path(temporary), linear_sony)
            else:
                write_slog3_tiff(Path(temporary), linear_sony)
            try:
                # Same-directory hard link atomically publishes only if absent.
                os.link(temporary, args.output)
            except FileExistsError as exc:
                raise ValueError("output already exists; refusing to overwrite") from exc
        finally:
            Path(temporary).unlink(missing_ok=True)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
