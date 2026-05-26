"""Convert a folder of SVG frames to an MP4 video.

Requirements (add to environment or install manually):
    pip install cairosvg opencv-python
"""

import re
from pathlib import Path

import cairosvg
import cv2
import numpy as np

from tqdm import tqdm


def svg_folder_to_mp4(
    frames_dir: str | Path,
    output_path: str | Path | None = None,
    fps: float = 30.0,
    dpi: float = 96.0,
    width: int | None = None,
    height: int | None = None,
    scale: float = 1.0,
) -> Path:
    """Rasterize SVG frames in *frames_dir* and write an MP4.

    Parameters
    ----------
    frames_dir:
        Directory containing ``*.svg`` files sorted numerically by any
        integer in the filename (``frame_0.svg``, ``frame_1.svg`` …).
    output_path:
        Destination ``.mp4`` path.  Defaults to ``<frames_dir>.mp4``
        placed next to the frame directory.
    fps:
        Output frame rate.
    dpi:
        Rasterisation resolution in dots per inch (default 96).
        Scales the output proportionally; ignored when *width*/*height*
        are given explicitly.
    width, height:
        Override rasterisation resolution in pixels.  When omitted the
        SVG's intrinsic dimensions are scaled by *dpi* / 96 * *scale*.
    scale:
        Additional uniform scale factor on top of the DPI scaling
        (ignored when *width* and *height* are both given).

    Returns
    -------
    Path
        Absolute path of the written MP4 file.
    """
    frames_dir = Path(frames_dir)
    if not frames_dir.is_dir():
        raise FileNotFoundError(f"Frame directory not found: {frames_dir}")

    def _sort_key(p: Path) -> int:
        m = re.search(r"\d+", p.stem)
        return int(m.group()) if m else 0

    svg_files = sorted(frames_dir.glob("*.svg"), key=_sort_key)
    if not svg_files:
        raise ValueError(f"No SVG files found in {frames_dir}")

    if output_path is None:
        output_path = frames_dir.parent / (frames_dir.name + ".mp4")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    effective_scale = scale * dpi / 96.0
    writer: cv2.VideoWriter | None = None

    for svg_path in tqdm(svg_files):
        png_bytes = cairosvg.svg2png(
            url=str(svg_path),
            output_width=width,
            output_height=height,
            scale=effective_scale,
            background_color="white",
        )
        arr = np.frombuffer(png_bytes, dtype=np.uint8)
        frame_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame_bgr is None:
            raise RuntimeError(f"Failed to decode rasterised frame: {svg_path.name}")

        if writer is None:
            h, w = frame_bgr.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

        writer.write(frame_bgr)

    if writer is not None:
        writer.release()
    else:
        raise RuntimeError("No frames were written.")

    return output_path.resolve()


def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert a folder of SVG frames to an MP4 video."
    )
    parser.add_argument("frames_dir", help="Directory containing SVG frames")
    parser.add_argument("-o", "--output", default=None, help="Output .mp4 path")
    parser.add_argument("--fps", type=float, default=30.0, help="Frames per second")
    parser.add_argument("--dpi", type=float, default=96.0, help="Rasterisation DPI (default 96)")
    parser.add_argument("--width", type=int, default=None, help="Output width in pixels")
    parser.add_argument("--height", type=int, default=None, help="Output height in pixels")
    parser.add_argument("--scale", type=float, default=1.0, help="Scale factor (default 1.0)")
    args = parser.parse_args()

    out = svg_folder_to_mp4(
        args.frames_dir,
        output_path=args.output,
        fps=args.fps,
        dpi=args.dpi,
        width=args.width,
        height=args.height,
        scale=args.scale,
    )
    print(f"Written: {out}")


if __name__ == "__main__":
    _cli()
