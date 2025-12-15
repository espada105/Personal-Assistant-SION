"""
XTTS HTTP Server (별도 Python 3.10 venv에서 실행)

실행:
    cd C:\\GitHubRepo\\Personal-Assistant-SION
    xtts_env\\Scripts\\python.exe voice\\xtts_server.py

엔드포인트:
    POST http://127.0.0.1:9882/tts
    JSON: { "text": "...", "ref_path": "C:/.../3.wav", "language": "ko" }
    응답: audio/wav 바이트
"""

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

# PyTorch 2.6+ 에서 torch.load 기본 weights_only=True로 바뀌어
# TTS의 기존 체크포인트 로딩이 실패하므로, 환경변수로 옛 동작으로 되돌립니다.
os.environ.setdefault("TORCH_LOAD_DEFAULT_WEIGHTS_ONLY", "0")

import torch
from TTS.api import TTS


class TTSRequest(BaseModel):
    text: str
    ref_path: str
    language: str = "ko"


app = FastAPI(title="XTTS Server", version="0.1.0")

_tts: TTS | None = None


@app.on_event("startup")
def load_model():
    global _tts
    device = "cuda" if torch.cuda.is_available() else "cpu"
    # 다국어 XTTS v2 기본 모델
    _tts = TTS(
        model_name="tts_models/multilingual/multi-dataset/xtts_v2",
        gpu=device == "cuda",
        progress_bar=False,
    )


@app.post("/tts", response_class=Response)
def tts_endpoint(payload: TTSRequest):
    if _tts is None:
        raise HTTPException(status_code=500, detail="TTS model not loaded")

    ref = Path(payload.ref_path)
    if not ref.exists():
        raise HTTPException(status_code=400, detail=f"ref_path not found: {ref}")

    # 합성 후 임시 wav 파일 반환
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        out_path = tmp.name

    try:
        _tts.tts_to_file(
            text=payload.text,
            speaker_wav=str(ref),
            language=payload.language,
            file_path=out_path,
            split_sentences=False,
        )
        audio_bytes = Path(out_path).read_bytes()
        return Response(content=audio_bytes, media_type="audio/wav")
    finally:
        try:
            if os.path.exists(out_path):
                os.remove(out_path)
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9882)


