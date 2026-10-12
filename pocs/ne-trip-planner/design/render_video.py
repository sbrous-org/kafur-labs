"""Render flow-video.html to an MP4.

The HTML exposes window.seek(t) which draws any moment deterministically, so we
screenshot one frame per 1/FPS second with Playwright (Chromium) and encode
with ffmpeg. No real-time screen recording, so no dropped frames.

    pip install playwright
    python render_video.py            # -> ne-trip-planner-flow.mp4
    python render_video.py --fps 12   # faster, lower smoothness
"""
import argparse
import glob
import shutil
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent


def chromium_path() -> str | None:
    hits = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return hits[-1] if hits else None  # None -> Playwright's own browser


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--out", default=str(HERE / "ne-trip-planner-flow.mp4"))
    args = ap.parse_args()

    frames = Path(tempfile.mkdtemp(prefix="netrip-frames-"))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=chromium_path())
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            page.goto((HERE / "flow-video.html").as_uri() + "?render")
            duration = page.evaluate("window.DURATION")
            total = int(duration * args.fps) + args.fps  # hold last frame 1s
            for i in range(total):
                page.evaluate("t => window.seek(t)", min(i / args.fps, duration))
                page.screenshot(path=str(frames / f"f{i:05d}.png"))
            browser.close()

        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-framerate", str(args.fps),
                "-i", str(frames / "f%05d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                "-movflags", "+faststart", args.out,
            ],
            check=True,
        )
        print(f"wrote {args.out} ({total} frames, {total / args.fps:.1f}s)")
    finally:
        shutil.rmtree(frames, ignore_errors=True)


if __name__ == "__main__":
    main()
