#!/usr/bin/env python3
"""
ACE-Step + Seed-VC Voice Conversion Pipeline

Usage:
    python rvc_pipeline/convert.py <input_mp3> [--reference <ref_wav>] [--output <output_mp3>]

Pipeline:
    1. Demucs: separate vocals + instrumental
    2. Seed-VC: convert vocals to target voice (MPS accelerated)
    3. FFmpeg: recombine into final mix
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
DEFAULT_REFERENCE = SCRIPT_DIR / "reference" / "biggie_reference.wav"


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


def recombine(vocals_path: str, instrumental_path: str, output_path: str):
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


def main():
    parser = argparse.ArgumentParser(description="Voice conversion pipeline")
    parser.add_argument("input", help="Input MP3/WAV from ACE-Step")
    parser.add_argument(
        "--reference", "-r",
        default=str(DEFAULT_REFERENCE),
        help="Reference voice WAV (default: Biggie)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output MP3 path (default: <input>_converted.mp3)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    if not os.path.exists(args.reference):
        print(f"Error: Reference file not found: {args.reference}")
        sys.exit(1)

    if args.output is None:
        stem = Path(args.input).stem
        args.output = str(Path(args.input).parent / f"{stem}_biggie.mp3")

    # Create temp working directory
    work_dir = str(SCRIPT_DIR / "temp")
    os.makedirs(work_dir, exist_ok=True)

    # Step 1: Separate stems
    vocals_path, instrumental_path = separate_stems(args.input, work_dir)

    # Step 2: Convert vocals
    converted_dir = os.path.join(work_dir, "converted")
    converted_vocals = convert_voice(vocals_path, args.reference, converted_dir)

    # Step 3: Recombine
    recombine(converted_vocals, instrumental_path, args.output)

    print(f"\nDone! Output: {args.output}")


if __name__ == "__main__":
    main()
