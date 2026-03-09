import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Iterable, List, Tuple, Optional


TimedCaption = Tuple[Tuple[float, float], str]
TimedMedia = Tuple[Tuple[float, float], str]


@dataclass
class RenderOptions:
    width: int
    height: int
    fps: int = 24
    preset: str = "veryfast"
    crf: int = 20


def _run(cmd: List[str]) -> None:
    # Keep stderr for debugging in terminal output
    subprocess.run(cmd, check=True)


def _download(url: str, out_path: str) -> None:
    # Using curl for reliability + redirects.
    _run(["curl", "-L", "-o", out_path, url])


def _seconds_to_srt_time(t: float) -> str:
    if t < 0:
        t = 0.0
    ms = int(round(t * 1000))
    h = ms // 3_600_000
    ms %= 3_600_000
    m = ms // 60_000
    ms %= 60_000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _write_srt(captions: Iterable[TimedCaption], out_path: str) -> None:
    lines: List[str] = []
    idx = 1
    for (t1, t2), text in captions:
        text = (text or "").strip()
        if not text:
            continue
        lines.append(str(idx))
        lines.append(f"{_seconds_to_srt_time(float(t1))} --> {_seconds_to_srt_time(float(t2))}")
        lines.append(text)
        lines.append("")
        idx += 1
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip() + "\n")


def _make_image_clip(img_path: str, duration: float, out_path: str, opts: RenderOptions) -> None:
    # Cover-style scale + center crop to exact size.
    vf = (
        f"scale={opts.width}:{opts.height}:force_original_aspect_ratio=increase,"
        f"crop={opts.width}:{opts.height}"
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            img_path,
            "-t",
            str(max(0.1, float(duration))),
            "-r",
            str(opts.fps),
            "-vf",
            vf,
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            opts.preset,
            "-crf",
            str(opts.crf),
            out_path,
        ]
    )


def _make_video_clip(video_path: str, duration: float, out_path: str, opts: RenderOptions) -> None:
    vf = (
        f"scale={opts.width}:{opts.height}:force_original_aspect_ratio=increase,"
        f"crop={opts.width}:{opts.height}"
    )
    # Loop input as needed, trim to segment duration, drop audio (we add narration later)
    _run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            video_path,
            "-t",
            str(max(0.1, float(duration))),
            "-an",
            "-r",
            str(opts.fps),
            "-vf",
            vf,
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            opts.preset,
            "-crf",
            str(opts.crf),
            out_path,
        ]
    )


def _concat_mp4s(mp4_paths: List[str], out_path: str) -> None:
    # Concat demuxer requires a file list.
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as f:
        list_path = f.name
        for p in mp4_paths:
            f.write(f"file {shlex.quote(p)}\n")

    try:
        _run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_path,
                "-c",
                "copy",
                out_path,
            ]
        )
    finally:
        try:
            os.remove(list_path)
        except Exception:
            pass


def _escape_ffmpeg_filter_path(path: str) -> str:
    """
    Escape a filesystem path for use inside an FFmpeg filter argument.

    Notes:
    - On Windows, temp paths often contain backslashes and a drive colon (C:\...).
      FFmpeg filter syntax treats ':' as a separator, so it must be escaped.
    - Backslashes are escape characters and must be doubled.
    - Spaces are fine when the value is wrapped in single quotes.
    """
    # Normalize Windows paths to use forward slashes where possible.
    # This avoids many backslash-escaping pitfalls and FFmpeg accepts it.
    p = path.replace("\\", "/")
    # Escape characters meaningful to FFmpeg filter parser.
    p = p.replace(":", r"\:")
    p = p.replace("'", r"\'")
    return p


def render_video_ffmpeg(
    audio_file_path: str,
    timed_captions: List[TimedCaption],
    background_video_data: List[TimedMedia],
    *,
    output_file_name: str = "rendered_video.mp4",
    orientation_landscape: bool = False,
    captions_enabled: bool = True,
    opts: Optional[RenderOptions] = None,
) -> str:
    """
    Render final video with FFmpeg only (no NumPy/MoviePy).
    - Downloads each segment's media URL
    - Creates per-segment mp4 clips
    - Concats clips
    - Muxes narration audio
    - Optionally burns SRT subtitles
    """
    base_w, base_h = (1920, 1080) if orientation_landscape else (1080, 1920)
    if opts is None:
        opts = RenderOptions(width=base_w, height=base_h)

    with tempfile.TemporaryDirectory(prefix="ffmpeg_render_") as td:
        segment_mp4s: List[str] = []
        for i, ((t1, t2), url) in enumerate(background_video_data or []):
            if not url:
                continue
            dur = float(t2) - float(t1)
            if dur <= 0:
                continue

            # Download media
            ext = ".mp4"
            lower = url.lower()
            if any(lower.endswith(x) for x in [".png", ".jpg", ".jpeg", ".webp"]):
                ext = os.path.splitext(lower)[1]
            in_path = os.path.join(td, f"seg_{i:03d}{ext}")
            _download(url, in_path)

            out_path = os.path.join(td, f"seg_{i:03d}.mp4")
            if ext == ".mp4":
                _make_video_clip(in_path, dur, out_path, opts)
            else:
                _make_image_clip(in_path, dur, out_path, opts)
            segment_mp4s.append(out_path)

        if not segment_mp4s:
            raise RuntimeError("No media segments were downloaded/rendered.")

        concat_path = os.path.join(td, "concat.mp4")
        _concat_mp4s(segment_mp4s, concat_path)

        # Add audio + optional subtitles (burn-in)
        final_cmd = ["ffmpeg", "-y", "-i", concat_path, "-i", audio_file_path]
        vf_filters: List[str] = []

        srt_path = os.path.join(td, "captions.srt")
        if captions_enabled and timed_captions:
            _write_srt(timed_captions, srt_path)
            # subtitles filter needs libass; path must be escaped for FFmpeg filter parser.
            vf_filters.append(f"subtitles='{_escape_ffmpeg_filter_path(srt_path)}'")

        if vf_filters:
            final_cmd += ["-vf", ",".join(vf_filters)]

        final_cmd += [
            "-c:v",
            "libx264",
            "-preset",
            opts.preset,
            "-crf",
            str(opts.crf),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            output_file_name,
        ]
        _run(final_cmd)

    return output_file_name

