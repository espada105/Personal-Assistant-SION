# SION 프로젝트 통합 가이드

## 개요

이 문서는 SION 메인 앱(`client/app/main.py`)에서 음성 클로닝 TTS를 사용하는 방법을 설명합니다.

## 빠른 시작

### 1. 의존성 설치

```bash
cd voice
pip install -r requirements.txt
```

### 2. GPT-SoVITS 설치 (선택사항)

전체 기능을 사용하려면 GPT-SoVITS를 설치합니다:

```bash
git clone https://github.com/RVC-Boss/GPT-SoVITS.git
cd GPT-SoVITS
pip install -r requirements.txt
```

### 3. 참조 음성 준비

일본 성우의 음성 파일을 준비합니다:

```
voice/reference_audio/speaker_1/
├── sample.wav          # 참조 음성 (10초~1분 권장)
└── sample_text.txt     # 참조 음성 대본 (일본어)
```

## SION 메인앱 통합

### 방법 1: 직접 교체 (권장)

`client/app/main.py`의 `speak_text` 함수를 수정합니다:

```python
# 기존 edge-tts 대신 voice cloning 사용
import sys
sys.path.insert(0, os.path.join(PROJECT_ROOT, "voice"))

from voice.app.tts_service import VoiceCloningTTS, SionTTSAdapter

class SionApp(ctk.CTk):
    def __init__(self):
        # ... 기존 코드 ...
        
        # TTS 초기화 (음성 클로닝 사용)
        self.tts = SionTTSAdapter(
            reference_audio=os.path.join(PROJECT_ROOT, "voice/reference_audio/speaker_1/sample.wav"),
            reference_text="こんにちは、私はシオンです。",
            use_fallback=True  # 실패 시 edge-tts 사용
        )
    
    def speak_text(self, text: str):
        """텍스트를 음성으로 읽기 (음성 클로닝 사용)"""
        if not self.voice_mode or self.is_speaking:
            return
        
        def do_speak():
            self.is_speaking = True
            try:
                # 이모지 제거
                import re
                clean_text = re.sub(r'[📅📆🕐✅❌🔗💬📧🎤🔴🔊🔇•]', '', text)
                clean_text = re.sub(r'\n+', '. ', clean_text).strip()
                
                if clean_text:
                    self.tts.speak(clean_text, block=True)
            finally:
                self.is_speaking = False
        
        threading.Thread(target=do_speak, daemon=True).start()
```

### 방법 2: API 서버 사용

별도의 프로세스로 API 서버를 실행하고, HTTP로 통신합니다:

```bash
# 터미널 1: API 서버 실행
cd voice
python -m uvicorn app.api_server:app --host 127.0.0.1 --port 9880
```

```python
# main.py에서 HTTP 클라이언트 사용
import requests
import base64
import tempfile

class SionApp(ctk.CTk):
    def speak_text(self, text: str):
        if not self.voice_mode or self.is_speaking:
            return
        
        def do_speak():
            self.is_speaking = True
            try:
                # API 호출
                response = requests.post(
                    "http://127.0.0.1:9880/synthesize",
                    json={"text": text, "speed": 1.0, "pitch_shift": 0}
                )
                
                if response.ok:
                    data = response.json()
                    audio_bytes = base64.b64decode(data["audio_base64"])
                    
                    # 임시 파일로 저장 후 재생
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                        tmp.write(audio_bytes)
                        tmp_path = tmp.name
                    
                    pygame.mixer.music.load(tmp_path)
                    pygame.mixer.music.play()
                    
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    
                    os.remove(tmp_path)
            finally:
                self.is_speaking = False
        
        threading.Thread(target=do_speak, daemon=True).start()
```

## 커스텀 음성 학습

### 1. 데이터 준비

```bash
# 원본 오디오 폴더에 일본 성우 음성 파일 배치
# voice/training_data/raw/

# 데이터 전처리
cd voice
python scripts/prepare_data.py \
    --input_dir training_data/raw \
    --output_dir training_data/processed \
    --create_template
```

### 2. 대본 입력

`training_data/processed/transcriptions.txt` 파일을 편집하여 각 음성 파일의 대본(일본어)을 입력합니다:

```
sample_01.wav|ja|こんにちは、私はシオンです。
sample_02.wav|ja|今日の天気はとても良いですね。
```

### 3. 모델 학습

```bash
python scripts/train.py \
    --config config.yaml \
    --data_dir training_data/processed \
    --output_dir models/trained
```

### 4. 학습된 모델 사용

`config.yaml`에서 모델 경로 수정:

```yaml
model:
  gpt:
    custom_path: "models/trained/gpt/final.ckpt"
  sovits:
    custom_path: "models/trained/sovits/final.pth"
```

## 설정 옵션

### 음성 품질 설정

```python
tts = VoiceCloningTTS()
tts.speed = 1.0        # 속도 (0.5 ~ 2.0)
tts.pitch_shift = 0    # 피치 (-12 ~ 12 반음)
tts.volume = 1.0       # 볼륨 (0.0 ~ 2.0)
```

### 교차언어 설정 (config.yaml)

```yaml
synthesis:
  cross_lingual:
    source_language: "ja"  # 참조 음성 언어
    target_language: "ko"  # 출력 언어
    accent_preservation: 0.3  # 억양 보존 정도 (0.0 ~ 1.0)
```

## 트러블슈팅

### CUDA 메모리 부족

```yaml
# config.yaml에서 배치 크기 줄이기
inference:
  batch_size: 1
```

### 음성 품질이 낮음

1. 참조 음성 품질 확인 (노이즈 없는 깨끗한 음성)
2. 참조 음성 길이 늘리기 (최소 10초, 권장 1분)
3. 참조 음성 대본 정확히 입력

### GPT-SoVITS 설치 오류

```bash
# PyTorch 먼저 설치
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# 그 후 requirements 설치
pip install -r requirements.txt
```

## API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/status` | GET | 서비스 상태 확인 |
| `/load_voice` | POST | 참조 음성 업로드 |
| `/synthesize` | POST | 텍스트 → 음성 (Base64) |
| `/synthesize_file` | POST | 텍스트 → WAV 파일 |
| `/synthesize_stream` | POST | 스트리밍 합성 |
| `/voices` | GET | 사용 가능한 음성 목록 |
| `/settings` | POST | 설정 변경 |

## 참고 자료

- [GPT-SoVITS GitHub](https://github.com/RVC-Boss/GPT-SoVITS)
- [GPT-SoVITS 사용 가이드](https://github.com/RVC-Boss/GPT-SoVITS/blob/main/docs/kr/README.md)

