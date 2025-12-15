"""
Data Preparation Script
음성 데이터 전처리 스크립트

사용법:
    python prepare_data.py --input_dir raw_audio/ --output_dir processed/
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Tuple
import json

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.audio_utils import AudioProcessor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataPreparator:
    """음성 데이터 전처리 클래스"""
    
    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        target_sr: int = 44100,
        min_duration: float = 3.0,
        max_duration: float = 30.0
    ):
        """
        Args:
            input_dir: 원본 오디오 디렉토리
            output_dir: 처리된 오디오 저장 디렉토리
            target_sr: 목표 샘플링 레이트
            min_duration: 최소 오디오 길이 (초)
            max_duration: 최대 오디오 길이 (초)
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.target_sr = target_sr
        self.min_duration = min_duration
        self.max_duration = max_duration
        
        self.processor = AudioProcessor(sample_rate=target_sr)
        
        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 메타데이터 저장용
        self.metadata: List[dict] = []
    
    def process_all(self) -> List[dict]:
        """모든 오디오 파일 처리"""
        audio_files = self._find_audio_files()
        logger.info(f"발견된 오디오 파일: {len(audio_files)}개")
        
        processed_count = 0
        skipped_count = 0
        
        for audio_path in audio_files:
            try:
                result = self.process_file(audio_path)
                if result:
                    self.metadata.append(result)
                    processed_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                logger.error(f"처리 실패 {audio_path}: {e}")
                skipped_count += 1
        
        # 메타데이터 저장
        self._save_metadata()
        
        logger.info(f"처리 완료: {processed_count}개 성공, {skipped_count}개 스킵")
        return self.metadata
    
    def process_file(self, audio_path: Path) -> dict:
        """
        단일 오디오 파일 처리
        
        Args:
            audio_path: 오디오 파일 경로
            
        Returns:
            처리 결과 메타데이터
        """
        logger.info(f"처리 중: {audio_path.name}")
        
        # 오디오 로드
        audio, sr = self.processor.load_audio(audio_path, target_sr=self.target_sr)
        
        # 모노 변환
        audio = self.processor.to_mono(audio)
        
        # 무음 제거
        audio = self.processor.remove_silence(audio, self.target_sr, top_db=30)
        
        # 길이 확인
        duration = self.processor.get_duration(audio, self.target_sr)
        
        if duration < self.min_duration:
            logger.warning(f"너무 짧음 ({duration:.2f}초): {audio_path.name}")
            return None
        
        if duration > self.max_duration:
            logger.warning(f"너무 김 ({duration:.2f}초): {audio_path.name}")
            # 최대 길이로 자르기
            max_samples = int(self.max_duration * self.target_sr)
            audio = audio[:max_samples]
            duration = self.max_duration
        
        # 정규화
        audio = self.processor.normalize_audio(audio, target_db=-20.0)
        
        # 페이드 인/아웃
        audio = self.processor.add_fade(audio, self.target_sr, fade_in_ms=10, fade_out_ms=10)
        
        # 저장
        output_name = audio_path.stem + ".wav"
        output_path = self.output_dir / output_name
        self.processor.save_audio(audio, output_path, self.target_sr)
        
        return {
            "original_path": str(audio_path),
            "processed_path": str(output_path),
            "duration": duration,
            "sample_rate": self.target_sr,
            "samples": len(audio)
        }
    
    def _find_audio_files(self) -> List[Path]:
        """오디오 파일 검색"""
        extensions = {'.wav', '.mp3', '.flac', '.ogg', '.m4a'}
        files = []
        
        for ext in extensions:
            files.extend(self.input_dir.glob(f"**/*{ext}"))
        
        return sorted(files)
    
    def _save_metadata(self):
        """메타데이터 저장"""
        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump({
                "total_files": len(self.metadata),
                "sample_rate": self.target_sr,
                "files": self.metadata
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"메타데이터 저장: {metadata_path}")


class TranscriptionManager:
    """대본(transcription) 관리 클래스"""
    
    def __init__(self, processed_dir: str):
        """
        Args:
            processed_dir: 처리된 오디오 디렉토리
        """
        self.processed_dir = Path(processed_dir)
        self.transcription_file = self.processed_dir / "transcriptions.txt"
    
    def create_template(self):
        """
        대본 템플릿 생성
        
        각 오디오 파일에 대해 대본을 입력할 수 있는 템플릿 생성
        """
        audio_files = list(self.processed_dir.glob("*.wav"))
        
        with open(self.transcription_file, 'w', encoding='utf-8') as f:
            f.write("# 음성 파일 대본\n")
            f.write("# 형식: 파일명|언어|대본\n")
            f.write("# 예시: sample_01.wav|ja|こんにちは、私はシオンです。\n")
            f.write("#\n")
            
            for audio_path in sorted(audio_files):
                f.write(f"{audio_path.name}|ja|\n")
        
        logger.info(f"대본 템플릿 생성: {self.transcription_file}")
        logger.info(f"총 {len(audio_files)}개 파일에 대한 대본을 입력해주세요.")
    
    def load_transcriptions(self) -> List[Tuple[str, str, str]]:
        """
        대본 파일 로드
        
        Returns:
            [(파일명, 언어, 대본), ...] 리스트
        """
        if not self.transcription_file.exists():
            logger.warning(f"대본 파일이 없습니다: {self.transcription_file}")
            return []
        
        transcriptions = []
        
        with open(self.transcription_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split('|')
                if len(parts) >= 3:
                    filename, language, text = parts[0], parts[1], parts[2]
                    if text:  # 대본이 있는 경우만
                        transcriptions.append((filename, language, text))
        
        logger.info(f"로드된 대본: {len(transcriptions)}개")
        return transcriptions
    
    def validate(self) -> bool:
        """대본 검증"""
        transcriptions = self.load_transcriptions()
        audio_files = {p.name for p in self.processed_dir.glob("*.wav")}
        
        missing = []
        for audio_name in audio_files:
            has_transcription = any(t[0] == audio_name for t in transcriptions)
            if not has_transcription:
                missing.append(audio_name)
        
        if missing:
            logger.warning(f"대본이 없는 파일: {len(missing)}개")
            for name in missing[:5]:
                logger.warning(f"  - {name}")
            if len(missing) > 5:
                logger.warning(f"  ... 외 {len(missing) - 5}개")
            return False
        
        logger.info("모든 파일에 대본이 있습니다.")
        return True


def main():
    parser = argparse.ArgumentParser(description="음성 데이터 전처리")
    parser.add_argument("--input_dir", "-i", required=True, help="원본 오디오 디렉토리")
    parser.add_argument("--output_dir", "-o", required=True, help="출력 디렉토리")
    parser.add_argument("--sample_rate", "-sr", type=int, default=44100, help="목표 샘플링 레이트")
    parser.add_argument("--min_duration", type=float, default=3.0, help="최소 오디오 길이 (초)")
    parser.add_argument("--max_duration", type=float, default=30.0, help="최대 오디오 길이 (초)")
    parser.add_argument("--create_template", action="store_true", help="대본 템플릿 생성")
    
    args = parser.parse_args()
    
    # 데이터 전처리
    preparator = DataPreparator(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        target_sr=args.sample_rate,
        min_duration=args.min_duration,
        max_duration=args.max_duration
    )
    
    preparator.process_all()
    
    # 대본 템플릿 생성
    if args.create_template:
        manager = TranscriptionManager(args.output_dir)
        manager.create_template()


if __name__ == "__main__":
    main()

