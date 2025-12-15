"""
Inference Script
음성 합성 추론 스크립트

사용법:
    python inference.py --text "안녕하세요" --reference reference.wav --output output.wav
    python inference.py --text "안녕하세요" --reference reference.wav --play
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tts_service import VoiceCloningTTS

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="음성 클로닝 추론")
    parser.add_argument("--text", "-t", required=True, help="합성할 텍스트")
    parser.add_argument("--reference", "-r", required=True, help="참조 음성 파일 경로")
    parser.add_argument("--reference_text", "-rt", default=None, help="참조 음성 대본 (옵션)")
    parser.add_argument("--output", "-o", default=None, help="출력 파일 경로")
    parser.add_argument("--play", "-p", action="store_true", help="합성 후 재생")
    parser.add_argument("--speed", "-s", type=float, default=1.0, help="재생 속도 (0.5-2.0)")
    parser.add_argument("--pitch", type=float, default=0.0, help="피치 시프트 (-12 ~ 12)")
    parser.add_argument("--device", "-d", default="cuda", choices=["cuda", "cpu", "mps"], help="디바이스")
    
    args = parser.parse_args()
    
    # 참조 음성 확인
    reference_path = Path(args.reference)
    if not reference_path.exists():
        logger.error(f"참조 음성 파일이 없습니다: {reference_path}")
        sys.exit(1)
    
    # TTS 서비스 초기화
    logger.info("TTS 서비스 초기화 중...")
    tts = VoiceCloningTTS(device=args.device)
    tts.initialize()
    
    # 참조 음성 로드
    logger.info(f"참조 음성 로드: {reference_path}")
    if not tts.load_voice(reference_path, args.reference_text):
        logger.error("참조 음성 로드 실패")
        sys.exit(1)
    
    # 설정 적용
    tts.speed = args.speed
    tts.pitch_shift = args.pitch
    
    # 텍스트 합성
    logger.info(f"텍스트 합성: {args.text}")
    
    try:
        if args.output:
            # 파일로 저장
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            tts.save(args.text, output_path, speed=args.speed, pitch_shift=args.pitch)
            logger.info(f"저장 완료: {output_path}")
            
            if args.play:
                logger.info("재생 중...")
                from app.audio_utils import AudioPlayer
                player = AudioPlayer()
                player.play_file(output_path)
        
        elif args.play:
            # 바로 재생
            logger.info("재생 중...")
            tts.speak(args.text, block=True, speed=args.speed, pitch_shift=args.pitch)
        
        else:
            # 출력 없이 합성만
            audio = tts.synthesize(args.text, speed=args.speed, pitch_shift=args.pitch)
            duration = len(audio) / 44100
            logger.info(f"합성 완료: {duration:.2f}초")
    
    except Exception as e:
        logger.error(f"합성 실패: {e}")
        sys.exit(1)
    
    finally:
        tts.cleanup()
    
    logger.info("완료")


if __name__ == "__main__":
    main()

