#!/usr/bin/env python3
"""
H.265 (HEVC) → H.264 (AVC) 비디오 변환기
ffmpeg-python 라이브러리 사용

설치:
    pip install ffmpeg-python
    
ffmpeg 바이너리 필요:
    - Windows: https://ffmpeg.org/download.html
    - macOS:   brew install ffmpeg
    - Linux:   sudo apt install ffmpeg
"""

import argparse
import sys
import os
from pathlib import Path


def check_ffmpeg():
    """ffmpeg 설치 여부 확인"""
    import subprocess
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_video(
    input_path: str,
    output_path: str = None,
    crf: int = 23,
    preset: str = "medium",
    audio_codec: str = "aac",
    audio_bitrate: str = "192k",
    overwrite: bool = False,
):
    """
    H.265 영상을 H.264로 변환

    Args:
        input_path:    입력 파일 경로
        output_path:   출력 파일 경로 (None이면 자동 생성)
        crf:           화질 (0~51, 낮을수록 고화질 / 권장: 18~28)
        preset:        인코딩 속도 (ultrafast ~ veryslow)
        audio_codec:   오디오 코덱 (aac / copy)
        audio_bitrate: 오디오 비트레이트
        overwrite:     출력 파일 덮어쓰기 여부
    """
    try:
        import ffmpeg
    except ImportError:
        print("❌ ffmpeg-python이 설치되지 않았습니다.")
        print("   pip install ffmpeg-python")
        sys.exit(1)

    input_path = Path(input_path)
    if not input_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)

    # 출력 경로 자동 생성
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_h264.mp4"
    output_path = Path(output_path)

    if output_path.exists() and not overwrite:
        print(f"⚠️  출력 파일이 이미 존재합니다: {output_path}")
        answer = input("   덮어쓸까요? [y/N] ").strip().lower()
        if answer != "y":
            print("취소되었습니다.")
            return

    print(f"\n📂 입력:  {input_path}")
    print(f"📁 출력:  {output_path}")
    print(f"🎬 코덱:  libx264  |  CRF: {crf}  |  Preset: {preset}")
    print(f"🔊 오디오: {audio_codec}  |  비트레이트: {audio_bitrate}")
    print("\n⏳ 변환 중...\n")

    try:
        stream = ffmpeg.input(str(input_path))

        video = stream.video.filter("copy") if False else stream.video  # placeholder
        audio = stream.audio

        output_kwargs = {
            "vcodec": "libx264",
            "crf": crf,
            "preset": preset,
            "pix_fmt": "yuv420p",   # 호환성 최대화
        }

        if audio_codec == "copy":
            output_kwargs["acodec"] = "copy"
        else:
            output_kwargs["acodec"] = audio_codec
            output_kwargs["audio_bitrate"] = audio_bitrate

        (
            ffmpeg
            .input(str(input_path))
            .output(str(output_path), **output_kwargs)
            .overwrite_output()
            .run(quiet=False)
        )

        # 결과 파일 크기 비교
        in_size  = input_path.stat().st_size  / (1024 ** 2)
        out_size = output_path.stat().st_size / (1024 ** 2)
        ratio    = (1 - out_size / in_size) * 100 if in_size else 0

        print(f"\n✅ 변환 완료!")
        print(f"   입력 크기:  {in_size:.1f} MB")
        print(f"   출력 크기:  {out_size:.1f} MB")
        print(f"   크기 변화:  {ratio:+.1f}%")

    except ffmpeg.Error as e:
        print("❌ 변환 중 오류 발생:")
        print(e.stderr.decode() if e.stderr else str(e))
        sys.exit(1)


def batch_convert(
    input_dir: str,
    output_dir: str = None,
    extensions: list = None,
    **kwargs
):
    """
    폴더 내 모든 H.265 파일 일괄 변환

    Args:
        input_dir:  입력 폴더
        output_dir: 출력 폴더 (None이면 입력 폴더와 동일)
        extensions: 처리할 확장자 목록 (기본: mp4, mkv, mov, hevc)
    """
    if extensions is None:
        extensions = [".mp4", ".mkv", ".mov", ".hevc", ".m4v", ".ts"]

    input_dir  = Path(input_dir)
    output_dir = Path(output_dir) if output_dir else input_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    files = [f for f in input_dir.iterdir() if f.suffix.lower() in extensions]
    if not files:
        print(f"⚠️  처리할 파일이 없습니다: {input_dir}")
        return

    print(f"\n📦 일괄 변환 시작: {len(files)}개 파일\n{'─'*40}")
    for i, f in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] {f.name}")
        out = output_dir / f"{f.stem}_h264.mp4"
        convert_video(str(f), str(out), **kwargs)

    print(f"\n🎉 모든 변환 완료! ({len(files)}개)")


# ──────────────────────────────────────────
# CLI
# ──────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="H.265 → H.264 비디오 변환기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 단일 파일 변환 (기본 설정)
  python convert_h265_to_h264.py video.mp4

  # 출력 경로 지정 + 고화질
  python convert_h265_to_h264.py video.mp4 -o output.mp4 --crf 18

  # 빠른 변환 (화질 낮춤)
  python convert_h265_to_h264.py video.mp4 --crf 28 --preset ultrafast

  # 오디오 스트림 그대로 복사
  python convert_h265_to_h264.py video.mp4 --audio copy

  # 폴더 전체 일괄 변환
  python convert_h265_to_h264.py --batch ./videos --output-dir ./converted
        """
    )

    parser.add_argument("input",           nargs="?",      help="입력 파일 경로")
    parser.add_argument("-o", "--output",                  help="출력 파일 경로")
    parser.add_argument("--crf",           type=int, default=23,
                        help="화질 (0~51, 기본: 23 / 낮을수록 고화질)")
    parser.add_argument("--preset",        default="medium",
                        choices=["ultrafast","superfast","veryfast","faster",
                                 "fast","medium","slow","slower","veryslow"],
                        help="인코딩 속도/효율 (기본: medium)")
    parser.add_argument("--audio",         default="aac", dest="audio_codec",
                        help="오디오 코덱: aac (기본) 또는 copy")
    parser.add_argument("--audio-bitrate", default="192k",
                        help="오디오 비트레이트 (기본: 192k)")
    parser.add_argument("-y", "--yes",     action="store_true",
                        help="덮어쓰기 자동 확인")

    # 일괄 변환 옵션
    batch_group = parser.add_argument_group("일괄 변환")
    batch_group.add_argument("--batch",      metavar="DIR", help="입력 폴더 (일괄 변환)")
    batch_group.add_argument("--output-dir", metavar="DIR", help="출력 폴더 (일괄 변환)")

    args = parser.parse_args()

    # ffmpeg 확인
    if not check_ffmpeg():
        print("❌ ffmpeg를 찾을 수 없습니다.")
        print("   설치 방법:")
        print("     macOS  : brew install ffmpeg")
        print("     Ubuntu : sudo apt install ffmpeg")
        print("     Windows: https://ffmpeg.org/download.html")
        sys.exit(1)

    # 일괄 변환 모드
    if args.batch:
        batch_convert(
            input_dir=args.batch,
            output_dir=args.output_dir,
            crf=args.crf,
            preset=args.preset,
            audio_codec=args.audio_codec,
            audio_bitrate=args.audio_bitrate,
            overwrite=args.yes,
        )
    elif args.input:
        convert_video(
            input_path=args.input,
            output_path=args.output,
            crf=args.crf,
            preset=args.preset,
            audio_codec=args.audio_codec,
            audio_bitrate=args.audio_bitrate,
            overwrite=args.yes,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()