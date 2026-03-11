#!/usr/bin/env python3
"""
ACE-Step + Seed-VC Voice Conversion Pipeline

Usage:
    python rvc_pipeline/convert.py <input_mp3> [--artist biggie] [--reference <ref_wav>]
    python rvc_pipeline/convert.py <input_mp3> --artist tupac,snoop,jayz
    python rvc_pipeline/convert.py <input_mp3> --artist all
    python rvc_pipeline/convert.py --list-artists

Pipeline:
    1. Demucs: separate vocals + instrumental
    2. Seed-VC: convert vocals to target voice (MPS accelerated)
    3. FFmpeg: recombine into final mix
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add parent dir to path so catalog imports work when run as a script
if __name__ == "__main__" or __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog import (
    get_reference_path,
    list_artists,
    resolve_artist_slugs,
)


SCRIPT_DIR = Path(__file__).parent
DEFAULT_REFERENCE = SCRIPT_DIR / "reference" / "biggie_juicy_reference.wav"


def separate_stems(input_path: str, output_dir: str) -> tuple[str, str]:
    """Use Demucs to separate vocals from instrumental."""
    print("\n[1/3] Separating vocals and instrumental with Demucs...")
    cmd = [
        sys.executable, "-m", "demucs",
        "--two-stems=vocals",
        "-o", output_dir,
        input_path,
    ]
    subprocess.run(cmd, check=True)

    stem_name = Path(input_path).stem
    vocals = os.path.join(output_dir, "htdemucs", stem_name, "vocals.wav")
    no_vocals = os.path.join(output_dir, "htdemucs", stem_name, "no_vocals.wav")

    if not os.path.exists(vocals):
        raise FileNotFoundError(f"Demucs did not produce vocals at {vocals}")

    print(f"  Vocals: {vocals}")
    print(f"  Instrumental: {no_vocals}")
    return vocals, no_vocals


def convert_voice(vocals_path: str, reference_path: str, output_dir: str) -> str:
    """Use Seed-VC to convert vocals to target voice."""
    print("\n[2/3] Converting vocals with Seed-VC (MPS accelerated)...")

    os.makedirs(output_dir, exist_ok=True)

    # Use seed-vc-infer-v1 console script — uses MPS automatically on Apple Silicon
    # fp16=False because MPS has limited fp16 support
    seed_vc_bin = os.path.join(os.path.dirname(sys.executable), "seed-vc-infer-v1")
    cmd = [
        seed_vc_bin,
        "--source", vocals_path,
        "--target", reference_path,
        "--output", output_dir,
        "--diffusion-steps", "25",
        "--inference-cfg-rate", "0.7",
        "--fp16", "False",
    ]
    subprocess.run(cmd, check=True)

    # Seed-VC output naming: vc_{source}_{target}_{length}_{steps}_{cfg}.wav
    wav_files = sorted(
        Path(output_dir).glob("vc_*.wav"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not wav_files:
        raise FileNotFoundError(f"Seed-VC did not produce output in {output_dir}")

    converted = str(wav_files[0])
    print(f"  Converted vocals: {converted}")
    return converted


def recombine(vocals_path: str, instrumental_path: str, output_path: str) -> None:
    """Recombine converted vocals with instrumental using ffmpeg."""
    print("\n[3/3] Recombining vocals + instrumental...")

    cmd = [
        "ffmpeg", "-y",
        "-i", vocals_path,
        "-i", instrumental_path,
        "-filter_complex",
        "[0:a]volume=1.2[v];[1:a]volume=0.9[i];[v][i]amix=inputs=2:duration=longest",
        "-ac", "2",
        "-ar", "44100",
        "-b:a", "320k",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"  Final output: {output_path}")



def run_pipeline(
    input_path: str,
    reference_path: str,
    output_path: str,
    vocals_path: str | None = None,
    instrumental_path: str | None = None,
) -> None:
    """Run the full conversion pipeline, optionally reusing pre-separated stems."""
    work_dir = str(SCRIPT_DIR / "temp")
    os.makedirs(work_dir, exist_ok=True)

    if vocals_path is None or instrumental_path is None:
        vocals_path, instrumental_path = separate_stems(input_path, work_dir)

    converted_dir = os.path.join(work_dir, "converted")
    converted_vocals = convert_voice(vocals_path, reference_path, converted_dir)
    recombine(converted_vocals, instrumental_path, output_path)
    print(f"\nDone! Output: {output_path}")


def main() -> None:
    """CLI entry point for voice conversion."""
    parser = argparse.ArgumentParser(description="Voice conversion pipeline")
    parser.add_argument("input", nargs="?", help="Input MP3/WAV from ACE-Step")
    parser.add_argument(
        "--reference", "-r",
        default=None,
        help="Reference voice WAV path (default: Biggie)",
    )
    parser.add_argument(
        "--artist", "-a",
        default=None,
        help="Artist slug from catalog (e.g. 'snoop', 'tupac,jayz', or 'all')",
    )
    parser.add_argument(
        "--list-artists",
        action="store_true",
        help="List all available artist voices",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output MP3 path (default: <input>_<artist>.mp3)",
    )
    args = parser.parse_args()

    # --list-artists mode
    if args.list_artists:
        print(list_artists())
        return

    # Require input file for conversion
    if args.input is None:
        parser.error("input file is required (or use --list-artists)")

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    input_stem = Path(args.input).stem
    input_dir = Path(args.input).parent

    # Single artist or batch mode
    if args.artist:
        slugs = resolve_artist_slugs(args.artist)

        # Pre-separate stems once for batch reuse
        work_dir = str(SCRIPT_DIR / "temp")
        os.makedirs(work_dir, exist_ok=True)
        vocals_path, instrumental_path = separate_stems(args.input, work_dir)

        for slug in slugs:
            print(f"\n{'='*60}")
            print(f"Converting to: {slug}")
            print(f"{'='*60}")
            ref_path = str(get_reference_path(slug))
            output = args.output if len(slugs) == 1 and args.output else None
            if output is None:
                output = str(input_dir / f"{input_stem}_{slug}.mp3")
            run_pipeline(
                args.input, ref_path, output,
                vocals_path=vocals_path,
                instrumental_path=instrumental_path,
            )
        return

    # Direct --reference mode (backward compat)
    reference = args.reference or str(DEFAULT_REFERENCE)
    if not os.path.exists(reference):
        print(f"Error: Reference file not found: {reference}")
        sys.exit(1)

    output = args.output or str(input_dir / f"{input_stem}_converted.mp3")
    run_pipeline(args.input, reference, output)


if __name__ == "__main__":
    main()
