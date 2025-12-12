"""
Audio Recorder Module
음성 녹음을 담당하는 모듈
"""

import io
import logging
import wave
from typing import Optional

import numpy as np

try:
    import sounddevice as sd
    import soundfile as sf
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

logger = logging.getLogger(__name__)


class AudioRecorder:
    """음성 녹음 클래스"""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "float32"
    ):
        """
        Args:
            sample_rate: 샘플링 레이트 (Hz)
            channels: 오디오 채널 수
            dtype: 데이터 타입
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self._recording = False
        self._audio_buffer = []
        
        if not AUDIO_AVAILABLE:
            logger.warning(
                "sounddevice/soundfile가 설치되지 않았습니다. "
                "pip install sounddevice soundfile 실행 필요"
            )
    
    def record(
        self,
        duration: float = 5.0,
        silence_threshold: float = 0.01,
        silence_duration: float = 1.5
    ) -> bytes:
        """
        음성을 녹음하고 WAV 바이트로 반환
        
        Args:
            duration: 최대 녹음 시간 (초)
            silence_threshold: 무음 감지 임계값
            silence_duration: 무음이 지속되면 녹음 종료할 시간 (초)
            
        Returns:
            WAV 형식의 오디오 바이트
        """
        if not AUDIO_AVAILABLE:
            raise RuntimeError("Audio recording is not available. Install sounddevice and soundfile.")
        
        logger.info(f"녹음 시작 (최대 {duration}초)...")
        
        # 고정 시간 녹음
        audio_data = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype
        )
        sd.wait()
        
        logger.info("녹음 완료")
        
        # NumPy 배열을 WAV 바이트로 변환
        return self._to_wav_bytes(audio_data)
    
    def record_with_vad(
        self,
        max_duration: float = 10.0,
        silence_threshold: float = 0.01,
        silence_duration: float = 1.5
    ) -> bytes:
        """
        VAD(Voice Activity Detection)를 사용한 음성 녹음
        음성이 감지되면 녹음을 시작하고, 무음이 지속되면 종료
        
        Args:
            max_duration: 최대 녹음 시간 (초)
            silence_threshold: 무음 감지 임계값
            silence_duration: 무음 지속 시 종료할 시간 (초)
            
        Returns:
            WAV 형식의 오디오 바이트
        """
        if not AUDIO_AVAILABLE:
            raise RuntimeError("Audio recording is not available.")
        
        logger.info("음성 대기 중... (말씀해주세요)")
        
        frames = []
        silence_frames = 0
        max_silence_frames = int(silence_duration * self.sample_rate / 1024)
        max_frames = int(max_duration * self.sample_rate / 1024)
        
        def audio_callback(indata, frames_count, time_info, status):
            if status:
                logger.warning(f"Audio callback status: {status}")
            frames.append(indata.copy())
        
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            blocksize=1024,
            callback=audio_callback
        ):
            voice_detected = False
            
            while len(frames) < max_frames:
                sd.sleep(100)  # 100ms 대기
                
                if not frames:
                    continue
                
                # 현재 프레임의 에너지 계산
                current_frame = frames[-1]
                energy = np.abs(current_frame).mean()
                
                if energy > silence_threshold:
                    voice_detected = True
                    silence_frames = 0
                elif voice_detected:
                    silence_frames += 1
                    if silence_frames >= max_silence_frames:
                        logger.info("무음 감지 - 녹음 종료")
                        break
        
        if not frames:
            raise RuntimeError("녹음된 오디오가 없습니다.")
        
        audio_data = np.concatenate(frames, axis=0)
        logger.info(f"녹음 완료: {len(audio_data) / self.sample_rate:.2f}초")
        
        return self._to_wav_bytes(audio_data)
    
    def _to_wav_bytes(self, audio_data: np.ndarray) -> bytes:
        """NumPy 배열을 WAV 바이트로 변환"""
        buffer = io.BytesIO()
        sf.write(buffer, audio_data, self.sample_rate, format='WAV')
        buffer.seek(0)
        return buffer.read()
    
    @staticmethod
    def list_devices() -> list:
        """사용 가능한 오디오 장치 목록 반환"""
        if not AUDIO_AVAILABLE:
            return []
        return sd.query_devices()
    
    @staticmethod
    def get_default_device() -> Optional[dict]:
        """기본 입력 장치 정보 반환"""
        if not AUDIO_AVAILABLE:
            return None
        try:
            device_id = sd.default.device[0]
            return sd.query_devices(device_id)
        except Exception as e:
            logger.error(f"기본 장치 조회 실패: {e}")
            return None


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)
    
    print("사용 가능한 오디오 장치:")
    for i, device in enumerate(AudioRecorder.list_devices()):
        print(f"  [{i}] {device['name']}")
    
    recorder = AudioRecorder()
    print("\n5초간 녹음합니다...")
    audio_bytes = recorder.record(duration=5.0)
    print(f"녹음된 오디오 크기: {len(audio_bytes)} bytes")


