import streamlit as st
import subprocess
import tempfile
import threading
from pathlib import Path

st.set_page_config(
    page_title="H.265 → H.264 변환기",
    page_icon="🎬",
    layout="centered",
)

# ── session state 초기화 ──────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None   # {"data", "name", "in_size", "out_size"}
if "error" not in st.session_state:
    st.session_state.error = None


def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def get_duration(path: Path) -> float | None:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             str(path)],
            capture_output=True, text=True, timeout=30,
        )
        return float(r.stdout.strip())
    except Exception:
        return None


# ── 헤더 ─────────────────────────────────────────────────────
st.title("🎬 H.265 → H.264 변환기")
st.caption("HEVC(H.265) 영상을 호환성이 높은 H.264(MP4)로 변환합니다.")
st.divider()

# ffmpeg 설치 확인
if not check_ffmpeg():
    st.error(
        "❌ 서버에 **ffmpeg**가 설치되어 있지 않습니다.\n\n"
        "- Windows: https://ffmpeg.org/download.html → PATH에 추가\n"
        "- 설치 후 서버를 재시작하세요."
    )
    st.stop()

# ── 파일 업로드 ───────────────────────────────────────────────
def _on_upload():
    st.session_state.result = None
    st.session_state.error = None

uploaded = st.file_uploader(
    "영상 파일을 드래그하거나 클릭하여 선택하세요",
    type=["mp4", "mkv", "mov", "hevc", "m4v", "ts"],
    on_change=_on_upload,
)

# ── 변환 설정 ─────────────────────────────────────────────────
st.subheader("변환 설정")
col1, col2 = st.columns(2)
with col1:
    crf = st.slider(
        "화질 (CRF)",
        min_value=0, max_value=51, value=23,
        help="낮을수록 고화질·큰 파일 / 권장: 18(고화질) ~ 28(압축 중심)",
    )
with col2:
    preset = st.selectbox(
        "인코딩 속도",
        ["ultrafast", "superfast", "veryfast", "faster",
         "fast", "medium", "slow", "slower", "veryslow"],
        index=5,
        help="빠를수록 파일이 커지고, 느릴수록 더 효율적으로 압축됩니다.",
    )

audio_copy = st.checkbox(
    "오디오 원본 유지 (재인코딩 없음)",
    help="체크하면 오디오를 변환하지 않고 그대로 복사합니다. 빠르지만 일부 기기에서 재생 안 될 수 있음.",
)

st.divider()

# ── 변환 실행 ─────────────────────────────────────────────────
if uploaded:
    mb = uploaded.size / (1024 ** 2)
    st.info(f"📄 **{uploaded.name}** — {mb:.1f} MB")

    if st.button("🚀 변환 시작", type="primary", use_container_width=True):
        st.session_state.result = None
        st.session_state.error = None

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            input_path  = tmpdir / uploaded.name
            output_name = f"{input_path.stem}_h264.mp4"
            output_path = tmpdir / output_name

            # 업로드 파일 저장
            with open(input_path, "wb") as f:
                f.write(uploaded.getbuffer())

            duration = get_duration(input_path)

            # ffmpeg 명령 구성
            cmd = [
                "ffmpeg", "-y",
                "-i", str(input_path),
                "-vcodec", "libx264",
                "-crf",    str(crf),
                "-preset", preset,
                "-pix_fmt", "yuv420p",
                "-acodec", "copy" if audio_copy else "aac",
            ]
            if not audio_copy:
                cmd += ["-b:a", "192k"]
            cmd += ["-progress", "pipe:1", "-nostats", str(output_path)]

            # 진행률 UI
            pb          = st.progress(0.0, text="변환 준비 중...")
            speed_label = st.empty()
            stderr_buf  = []

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,  # 언버퍼드 — Windows에서 line-buffer 이슈 방지
            )

            # stderr를 별도 스레드로 소비 (파이프 교착 방지)
            def _drain(p):
                for line in p.stderr:
                    stderr_buf.append(line.decode("utf-8", errors="replace"))

            drain_t = threading.Thread(target=_drain, args=(proc,), daemon=True)
            drain_t.start()

            # stdout에서 진행률 파싱 (readline 방식 — Windows EOF 감지 안정적)
            while True:
                raw = proc.stdout.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").strip()
                key, _, val = line.partition("=")
                if key == "out_time_ms" and duration:
                    try:
                        pct = min(int(val) / (duration * 1_000_000), 0.99)
                        pb.progress(pct, text=f"변환 중... {pct*100:.0f}%")
                    except ValueError:
                        pass
                elif key == "speed" and val.strip() not in ("", "N/A"):
                    speed_label.caption(f"처리 속도: {val.strip()}")
                elif key == "progress" and val.strip() == "end":
                    pb.progress(1.0, text="✅ 변환 완료!")
                    break  # ffmpeg 완료 신호 — 루프 즉시 탈출

            proc.wait()
            drain_t.join(timeout=5)
            speed_label.empty()

            if proc.returncode == 0 and output_path.exists():
                pb.progress(1.0, text="✅ 변환 완료!")
                in_sz  = input_path.stat().st_size  / (1024 ** 2)
                out_sz = output_path.stat().st_size / (1024 ** 2)
                with open(output_path, "rb") as f:
                    data = f.read()
                st.session_state.result = {
                    "data":     data,
                    "name":     output_name,
                    "in_size":  in_sz,
                    "out_size": out_sz,
                }
            else:
                pb.empty()
                tail = "".join(stderr_buf[-30:])
                st.session_state.error = tail

# ── 결과 표시 ─────────────────────────────────────────────────
if st.session_state.result:
    r     = st.session_state.result
    ratio = (1 - r["out_size"] / r["in_size"]) * 100 if r["in_size"] else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("원본 크기",   f"{r['in_size']:.1f} MB")
    c2.metric("변환 후 크기", f"{r['out_size']:.1f} MB")
    c3.metric("크기 변화",   f"{ratio:+.0f}%")

    st.download_button(
        "⬇️ 변환된 파일 다운로드",
        data=r["data"],
        file_name=r["name"],
        mime="video/mp4",
        use_container_width=True,
        type="primary",
    )

if st.session_state.error:
    with st.expander("❌ 변환 실패 — 오류 상세 보기"):
        st.code(st.session_state.error, language="text")
