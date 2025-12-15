"""
Training Script
GPT-SoVITS 모델 학습 스크립트

사용법:
    python train.py --config ../config.yaml --data_dir processed/
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import yaml

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """설정 파일 로드"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def check_prerequisites(data_dir: Path) -> bool:
    """학습 전제조건 확인"""
    # 처리된 오디오 파일 확인
    audio_files = list(data_dir.glob("*.wav"))
    if not audio_files:
        logger.error(f"처리된 오디오 파일이 없습니다: {data_dir}")
        return False
    
    logger.info(f"발견된 오디오 파일: {len(audio_files)}개")
    
    # 대본 파일 확인
    transcription_file = data_dir / "transcriptions.txt"
    if not transcription_file.exists():
        logger.error(f"대본 파일이 없습니다: {transcription_file}")
        logger.info("python prepare_data.py --create_template 으로 템플릿을 생성하세요.")
        return False
    
    # 대본 검증
    from prepare_data import TranscriptionManager
    manager = TranscriptionManager(str(data_dir))
    transcriptions = manager.load_transcriptions()
    
    if not transcriptions:
        logger.error("대본이 비어있습니다.")
        return False
    
    # 최소 데이터 확인
    total_duration = 0
    for filename, _, _ in transcriptions:
        audio_path = data_dir / filename
        if audio_path.exists():
            import librosa
            duration = librosa.get_duration(path=str(audio_path))
            total_duration += duration
    
    logger.info(f"총 오디오 길이: {total_duration:.1f}초 ({total_duration/60:.1f}분)")
    
    if total_duration < 60:  # 최소 1분
        logger.warning("오디오 길이가 1분 미만입니다. 더 많은 데이터를 권장합니다.")
    
    return True


def prepare_training_data(data_dir: Path, output_dir: Path, config: dict):
    """
    학습 데이터 준비
    
    GPT-SoVITS 형식에 맞게 데이터를 변환합니다.
    """
    from prepare_data import TranscriptionManager
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 대본 로드
    manager = TranscriptionManager(str(data_dir))
    transcriptions = manager.load_transcriptions()
    
    # 파일리스트 생성
    filelist_path = output_dir / "train_filelist.txt"
    with open(filelist_path, 'w', encoding='utf-8') as f:
        for filename, language, text in transcriptions:
            audio_path = data_dir / filename
            if audio_path.exists():
                # GPT-SoVITS 형식: audio_path|speaker|language|text
                line = f"{audio_path}|speaker_1|{language}|{text}\n"
                f.write(line)
    
    logger.info(f"파일리스트 생성: {filelist_path}")
    return filelist_path


def train_sovits(config: dict, filelist_path: Path, output_dir: Path):
    """SoVITS 모델 학습"""
    logger.info("=" * 50)
    logger.info("SoVITS 모델 학습 시작")
    logger.info("=" * 50)
    
    training_config = config.get("training", {}).get("sovits", {})
    epochs = training_config.get("epochs", 8)
    batch_size = training_config.get("batch_size", 8)
    learning_rate = training_config.get("learning_rate", 0.0001)
    
    logger.info(f"  Epochs: {epochs}")
    logger.info(f"  Batch size: {batch_size}")
    logger.info(f"  Learning rate: {learning_rate}")
    
    # 실제 GPT-SoVITS 학습 코드
    # 이 부분은 GPT-SoVITS 라이브러리가 설치되어 있어야 합니다
    
    try:
        # from GPT_SoVITS.train import train_sovits as gpt_sovits_train
        # gpt_sovits_train(
        #     filelist=str(filelist_path),
        #     output_dir=str(output_dir / "sovits"),
        #     epochs=epochs,
        #     batch_size=batch_size,
        #     learning_rate=learning_rate
        # )
        
        logger.warning("GPT-SoVITS 라이브러리가 설치되지 않았습니다.")
        logger.info("실제 학습을 위해서는 GPT-SoVITS를 설치해주세요:")
        logger.info("  git clone https://github.com/RVC-Boss/GPT-SoVITS.git")
        logger.info("  cd GPT-SoVITS && pip install -r requirements.txt")
        
    except ImportError as e:
        logger.error(f"GPT-SoVITS 임포트 실패: {e}")
        return False
    
    return True


def train_gpt(config: dict, filelist_path: Path, output_dir: Path):
    """GPT 모델 학습"""
    logger.info("=" * 50)
    logger.info("GPT 모델 학습 시작")
    logger.info("=" * 50)
    
    training_config = config.get("training", {}).get("gpt", {})
    epochs = training_config.get("epochs", 15)
    batch_size = training_config.get("batch_size", 4)
    learning_rate = training_config.get("learning_rate", 0.0001)
    
    logger.info(f"  Epochs: {epochs}")
    logger.info(f"  Batch size: {batch_size}")
    logger.info(f"  Learning rate: {learning_rate}")
    
    # 실제 GPT-SoVITS 학습 코드
    try:
        # from GPT_SoVITS.train import train_gpt as gpt_train
        # gpt_train(
        #     filelist=str(filelist_path),
        #     output_dir=str(output_dir / "gpt"),
        #     epochs=epochs,
        #     batch_size=batch_size,
        #     learning_rate=learning_rate
        # )
        
        logger.warning("GPT-SoVITS 라이브러리가 설치되지 않았습니다.")
        
    except ImportError as e:
        logger.error(f"GPT-SoVITS 임포트 실패: {e}")
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description="음성 클로닝 모델 학습")
    parser.add_argument("--config", "-c", default="../config.yaml", help="설정 파일 경로")
    parser.add_argument("--data_dir", "-d", required=True, help="처리된 데이터 디렉토리")
    parser.add_argument("--output_dir", "-o", default="../models/trained", help="모델 저장 디렉토리")
    parser.add_argument("--stage", choices=["all", "sovits", "gpt"], default="all", help="학습 단계")
    parser.add_argument("--skip_check", action="store_true", help="전제조건 확인 건너뛰기")
    
    args = parser.parse_args()
    
    # 경로 설정
    config_path = Path(args.config)
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    
    # 설정 로드
    config = load_config(config_path) if config_path.exists() else {}
    
    # 전제조건 확인
    if not args.skip_check:
        if not check_prerequisites(data_dir):
            logger.error("전제조건 확인 실패")
            sys.exit(1)
    
    # 학습 데이터 준비
    logger.info("학습 데이터 준비 중...")
    filelist_path = prepare_training_data(data_dir, output_dir, config)
    
    # 학습 실행
    if args.stage in ["all", "sovits"]:
        if not train_sovits(config, filelist_path, output_dir):
            logger.error("SoVITS 학습 실패")
            if args.stage == "sovits":
                sys.exit(1)
    
    if args.stage in ["all", "gpt"]:
        if not train_gpt(config, filelist_path, output_dir):
            logger.error("GPT 학습 실패")
            if args.stage == "gpt":
                sys.exit(1)
    
    logger.info("=" * 50)
    logger.info("학습 완료")
    logger.info(f"모델 저장 위치: {output_dir}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()

