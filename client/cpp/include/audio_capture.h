#pragma once

#ifndef AUDIO_CAPTURE_H
#define AUDIO_CAPTURE_H

#include <vector>
#include <cstdint>
#include <string>
#include <functional>
#include <atomic>

namespace sion {

/**
 * @brief 오디오 설정 구조체
 */
struct AudioConfig {
    int sampleRate = 16000;      // 샘플링 레이트 (Hz)
    int channels = 1;            // 채널 수 (모노)
    int bitsPerSample = 16;      // 비트 깊이
    float maxDuration = 10.0f;   // 최대 녹음 시간 (초)
};

/**
 * @brief 오디오 데이터 콜백 타입
 */
using AudioCallback = std::function<void(const std::vector<int16_t>&)>;

/**
 * @brief 오디오 캡처 클래스
 * 
 * Windows WASAPI를 사용하여 마이크 입력을 캡처합니다.
 */
class AudioCapture {
public:
    /**
     * @brief 생성자
     * @param config 오디오 설정
     */
    explicit AudioCapture(const AudioConfig& config = AudioConfig{});

    /**
     * @brief 소멸자
     */
    ~AudioCapture();

    // 복사 금지
    AudioCapture(const AudioCapture&) = delete;
    AudioCapture& operator=(const AudioCapture&) = delete;

    /**
     * @brief 오디오 장치 초기화
     * @return 성공 여부
     */
    bool initialize();

    /**
     * @brief 녹음 시작
     * @return 성공 여부
     */
    bool startCapture();

    /**
     * @brief 녹음 중지
     * @return 캡처된 오디오 데이터
     */
    std::vector<int16_t> stopCapture();

    /**
     * @brief 고정 시간 녹음
     * @param durationSeconds 녹음 시간 (초)
     * @return 캡처된 오디오 데이터
     */
    std::vector<int16_t> captureForDuration(float durationSeconds);

    /**
     * @brief 녹음 중인지 확인
     */
    bool isCapturing() const;

    /**
     * @brief 오디오 데이터를 WAV 파일로 저장
     * @param data 오디오 데이터
     * @param filepath 저장 경로
     * @return 성공 여부
     */
    bool saveToWav(const std::vector<int16_t>& data, const std::string& filepath);

    /**
     * @brief 오디오 데이터를 WAV 바이트로 변환
     * @param data 오디오 데이터
     * @return WAV 형식 바이트 배열
     */
    std::vector<uint8_t> toWavBytes(const std::vector<int16_t>& data);

    /**
     * @brief 설정 반환
     */
    const AudioConfig& getConfig() const { return m_config; }

private:
    /**
     * @brief WAV 헤더 작성
     */
    void writeWavHeader(std::vector<uint8_t>& buffer, uint32_t dataSize);

    AudioConfig m_config;
    std::atomic<bool> m_capturing;
    std::vector<int16_t> m_buffer;
    
    // 플랫폼 별 핸들 (구현에서 정의)
    void* m_platformHandle;
};

} // namespace sion

#endif // AUDIO_CAPTURE_H

