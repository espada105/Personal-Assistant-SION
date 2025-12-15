# SION Voice Cloning Module

일본 성우의 목소리를 사용하여 한국어를 발화하는 교차언어(Cross-Lingual) 음성 클로닝 모듈입니다.

## 개요

이 모듈은 GPT-SoVITS 기반의 교차언어 음성 클로닝을 구현하여, 일본 성우의 음색과 특성을 유지하면서 한국어 텍스트를 자연스럽게 발화할 수 있게 합니다.

## 기능

- **교차언어 음성 클로닝**: 일본어 음성 데이터로 학습한 모델이 한국어 발화
- **Few-shot 학습**: 짧은 음성 샘플(1분 이상)로 음성 클로닝 가능
- **실시간 TTS**: SION 프로젝트의 Google TTS 대체
- **감정 표현**: 다양한 감정 톤 지원

## 디렉토리 구조

```
voice/
├── README.md
├── requirements.txt
├── config.yaml                 # 설정 파일
├── app/
│   ├── __init__.py
│   ├── tts_service.py         # TTS 서비스 메인 클래스
│   ├── voice_cloner.py        # 음성 클로닝 래퍼
│   └── audio_utils.py         # 오디오 유틸리티
├── models/
│   ├── gpt/                   # GPT 모델 저장
│   └── sovits/                # SoVITS 모델 저장
├── reference_audio/           # 참조 음성 파일
│   └── speaker_1/             # 화자별 폴더
├── output/                    # 생성된 음성 파일
└── scripts/
    ├── prepare_data.py        # 데이터 전처리
    ├── train.py               # 모델 학습
    └── inference.py           # 추론 스크립트
```

## 설치

### 1. 의존성 설치

```bash
cd voice
pip install -r requirements.txt
```

### 2. GPT-SoVITS 설치

```bash
# GPT-SoVITS 클론
git clone https://github.com/RVC-Boss/GPT-SoVITS.git
cd GPT-SoVITS
pip install -r requirements.txt
```

### 3. 사전 학습된 모델 다운로드

GPT-SoVITS 사전 학습 모델을 다운로드하여 `models/` 폴더에 배치합니다.

## 사용법

### 기본 사용

```python
from voice.app.tts_service import VoiceCloningTTS

# TTS 서비스 초기화
tts = VoiceCloningTTS(
    reference_audio="reference_audio/speaker_1/sample.wav",
    model_path="models/gpt/pretrained.ckpt"
)

# 텍스트를 음성으로 변환
audio = tts.synthesize("안녕하세요, 시온입니다.")
tts.save(audio, "output/hello.wav")

# 바로 재생
tts.play(audio)
```

### SION 프로젝트 통합

```python
# main.py에서 사용
from voice.app.tts_service import VoiceCloningTTS

# 기존 edge-tts 대신 사용
class SionApp:
    def __init__(self):
        self.tts = VoiceCloningTTS()
    
    def speak_text(self, text: str):
        audio = self.tts.synthesize(text)
        self.tts.play(audio)
```

## 학습 가이드

### 1. 음성 데이터 준비

- 고품질 WAV 파일 (44.1kHz, 16bit)
- 최소 1분 이상의 깨끗한 음성
- 배경 잡음 최소화

### 2. 데이터 전처리

```bash
python scripts/prepare_data.py --input_dir raw_audio/ --output_dir processed/
```

### 3. 모델 학습

```bash
python scripts/train.py --config config.yaml
```

## 라이선스

MIT License

## 참고 자료

- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)
- [VITS](https://github.com/jaywalnut310/vits)
- [Coqui TTS](https://github.com/coqui-ai/TTS)

