/**
 * @file audio_capture.cpp
 * @brief AudioCapture 클래스 구현
 */

#include "audio_capture.h"
#include <iostream>
#include <fstream>
#include <cstring>
#include <thread>
#include <chrono>

#ifdef _WIN32
#include <windows.h>
#include <mmsystem.h>
#pragma comment(lib, "winmm.lib")
#endif

namespace sion {

// WAV 파일 헤더 구조체
#pragma pack(push, 1)
struct WavHeader {
    char riff[4] = {'R', 'I', 'F', 'F'};
    uint32_t fileSize;
    char wave[4] = {'W', 'A', 'V', 'E'};
    char fmt[4] = {'f', 'm', 't', ' '};
    uint32_t fmtSize = 16;
    uint16_t audioFormat = 1;  // PCM
    uint16_t numChannels;
    uint32_t sampleRate;
    uint32_t byteRate;
    uint16_t blockAlign;
    uint16_t bitsPerSample;
    char data[4] = {'d', 'a', 't', 'a'};
    uint32_t dataSize;
};
#pragma pack(pop)

AudioCapture::AudioCapture(const AudioConfig& config)
    : m_config(config)
    , m_capturing(false)
    , m_platformHandle(nullptr)
{
}

AudioCapture::~AudioCapture() {
    if (m_capturing) {
        stopCapture();
    }
}

bool AudioCapture::initialize() {
#ifdef _WIN32
    // Windows 오디오 장치 확인
    UINT numDevices = waveInGetNumDevs();
    if (numDevices == 0) {
        std::cerr << "[AudioCapture] 오디오 입력 장치를 찾을 수 없습니다." << std::endl;
        return false;
    }
    
    // 기본 장치 정보 출력
    WAVEINCAPS caps;
    if (waveInGetDevCaps(0, &caps, sizeof(caps)) == MMSYSERR_NOERROR) {
        std::wcout << L"[AudioCapture] 기본 오디오 장치: " << caps.szPname << std::endl;
    }
    
    return true;
#else
    // Linux/macOS 구현은 추후 추가
    std::cout << "[AudioCapture] 플랫폼 미지원 (더미 모드)" << std::endl;
    return true;
#endif
}

bool AudioCapture::startCapture() {
    if (m_capturing) {
        return false;
    }
    
    m_buffer.clear();
    m_capturing = true;
    
    return true;
}

std::vector<int16_t> AudioCapture::stopCapture() {
    m_capturing = false;
    return std::move(m_buffer);
}

std::vector<int16_t> AudioCapture::captureForDuration(float durationSeconds) {
#ifdef _WIN32
    // Wave 포맷 설정
    WAVEFORMATEX wfx;
    wfx.wFormatTag = WAVE_FORMAT_PCM;
    wfx.nChannels = static_cast<WORD>(m_config.channels);
    wfx.nSamplesPerSec = static_cast<DWORD>(m_config.sampleRate);
    wfx.wBitsPerSample = static_cast<WORD>(m_config.bitsPerSample);
    wfx.nBlockAlign = wfx.nChannels * wfx.wBitsPerSample / 8;
    wfx.nAvgBytesPerSec = wfx.nSamplesPerSec * wfx.nBlockAlign;
    wfx.cbSize = 0;
    
    // 버퍼 크기 계산
    int numSamples = static_cast<int>(durationSeconds * m_config.sampleRate);
    int bufferSize = numSamples * wfx.nBlockAlign;
    
    std::vector<int16_t> audioData(numSamples);
    
    // Wave 입력 장치 열기
    HWAVEIN hWaveIn;
    MMRESULT result = waveInOpen(&hWaveIn, WAVE_MAPPER, &wfx, 0, 0, CALLBACK_NULL);
    if (result != MMSYSERR_NOERROR) {
        std::cerr << "[AudioCapture] waveInOpen 실패: " << result << std::endl;
        return {};
    }
    
    // 버퍼 준비
    WAVEHDR waveHdr;
    std::memset(&waveHdr, 0, sizeof(waveHdr));
    waveHdr.lpData = reinterpret_cast<LPSTR>(audioData.data());
    waveHdr.dwBufferLength = bufferSize;
    
    result = waveInPrepareHeader(hWaveIn, &waveHdr, sizeof(waveHdr));
    if (result != MMSYSERR_NOERROR) {
        waveInClose(hWaveIn);
        return {};
    }
    
    result = waveInAddBuffer(hWaveIn, &waveHdr, sizeof(waveHdr));
    if (result != MMSYSERR_NOERROR) {
        waveInUnprepareHeader(hWaveIn, &waveHdr, sizeof(waveHdr));
        waveInClose(hWaveIn);
        return {};
    }
    
    // 녹음 시작
    result = waveInStart(hWaveIn);
    if (result != MMSYSERR_NOERROR) {
        waveInUnprepareHeader(hWaveIn, &waveHdr, sizeof(waveHdr));
        waveInClose(hWaveIn);
        return {};
    }
    
    // 녹음 완료 대기
    while (!(waveHdr.dwFlags & WHDR_DONE)) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    
    // 정리
    waveInStop(hWaveIn);
    waveInUnprepareHeader(hWaveIn, &waveHdr, sizeof(waveHdr));
    waveInClose(hWaveIn);
    
    return audioData;
#else
    // 더미 구현
    int numSamples = static_cast<int>(durationSeconds * m_config.sampleRate);
    std::vector<int16_t> dummyData(numSamples, 0);
    std::this_thread::sleep_for(
        std::chrono::milliseconds(static_cast<int>(durationSeconds * 1000)));
    return dummyData;
#endif
}

bool AudioCapture::isCapturing() const {
    return m_capturing;
}

bool AudioCapture::saveToWav(const std::vector<int16_t>& data, const std::string& filepath) {
    auto wavBytes = toWavBytes(data);
    
    std::ofstream file(filepath, std::ios::binary);
    if (!file.is_open()) {
        std::cerr << "[AudioCapture] 파일 열기 실패: " << filepath << std::endl;
        return false;
    }
    
    file.write(reinterpret_cast<const char*>(wavBytes.data()), wavBytes.size());
    file.close();
    
    return true;
}

std::vector<uint8_t> AudioCapture::toWavBytes(const std::vector<int16_t>& data) {
    uint32_t dataSize = static_cast<uint32_t>(data.size() * sizeof(int16_t));
    
    WavHeader header;
    header.fileSize = dataSize + sizeof(WavHeader) - 8;
    header.numChannels = static_cast<uint16_t>(m_config.channels);
    header.sampleRate = static_cast<uint32_t>(m_config.sampleRate);
    header.bitsPerSample = static_cast<uint16_t>(m_config.bitsPerSample);
    header.blockAlign = header.numChannels * header.bitsPerSample / 8;
    header.byteRate = header.sampleRate * header.blockAlign;
    header.dataSize = dataSize;
    
    std::vector<uint8_t> result(sizeof(WavHeader) + dataSize);
    
    // 헤더 복사
    std::memcpy(result.data(), &header, sizeof(WavHeader));
    
    // 데이터 복사
    std::memcpy(result.data() + sizeof(WavHeader), data.data(), dataSize);
    
    return result;
}

void AudioCapture::writeWavHeader(std::vector<uint8_t>& buffer, uint32_t dataSize) {
    // toWavBytes에서 처리
}

} // namespace sion

