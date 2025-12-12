/**
 * @file main.cpp
 * @brief Personal Assistant SION - C++ Hotkey Module Entry Point
 * 
 * 시스템 전역 핫키를 감지하고, 음성을 캡처하여
 * Python 클라이언트로 전달하는 메인 프로그램
 */

#include <iostream>
#include <string>
#include <memory>
#include <csignal>

#include "hotkey_handler.h"
#include "audio_capture.h"
#include "python_bridge.h"

// 전역 실행 플래그
std::atomic<bool> g_running{true};

// 시그널 핸들러
void signalHandler(int signal) {
    std::cout << "\n[SION] 종료 신호 수신 (signal: " << signal << ")" << std::endl;
    g_running = false;
}

/**
 * @brief 음성 명령 처리 함수
 * @param audioCapture 오디오 캡처 객체
 * @param pythonBridge Python 브릿지 객체
 */
void handleVoiceCommand(
    sion::AudioCapture& audioCapture,
    sion::PythonProcessBridge& pythonBridge
) {
    std::cout << "[SION] 🎤 음성 녹음 시작..." << std::endl;
    
    // 5초간 녹음
    auto audioData = audioCapture.captureForDuration(5.0f);
    
    if (audioData.empty()) {
        std::cerr << "[SION] ❌ 오디오 캡처 실패" << std::endl;
        return;
    }
    
    std::cout << "[SION] ✅ 녹음 완료 (" 
              << audioData.size() << " samples)" << std::endl;
    
    // WAV 바이트로 변환
    auto wavBytes = audioCapture.toWavBytes(audioData);
    
    // Python으로 전송
    std::cout << "[SION] 🔄 Python 처리 중..." << std::endl;
    auto result = pythonBridge.sendAudio(wavBytes);
    
    if (!result.empty()) {
        std::cout << "[SION] 📝 결과: " << result << std::endl;
    } else {
        std::cerr << "[SION] ❌ Python 처리 실패" << std::endl;
    }
}

/**
 * @brief 메인 함수
 */
int main(int argc, char* argv[]) {
    std::cout << "========================================" << std::endl;
    std::cout << "   Personal Assistant SION v0.1.0" << std::endl;
    std::cout << "   C++ Hotkey Module" << std::endl;
    std::cout << "========================================" << std::endl;
    
    // 시그널 핸들러 등록
    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);
    
    // Python 경로 설정 (기본값 또는 인자로 전달)
    std::string pythonPath = "python";
    std::string scriptPath = "../python/main.py";
    
    if (argc > 1) {
        pythonPath = argv[1];
    }
    if (argc > 2) {
        scriptPath = argv[2];
    }
    
    // 오디오 캡처 초기화
    sion::AudioConfig audioConfig;
    audioConfig.sampleRate = 16000;
    audioConfig.channels = 1;
    audioConfig.bitsPerSample = 16;
    
    sion::AudioCapture audioCapture(audioConfig);
    if (!audioCapture.initialize()) {
        std::cerr << "[SION] ❌ 오디오 장치 초기화 실패" << std::endl;
        return 1;
    }
    std::cout << "[SION] ✅ 오디오 장치 초기화 완료" << std::endl;
    
    // Python 브릿지 초기화
    sion::PythonProcessBridge pythonBridge(pythonPath, scriptPath);
    if (!pythonBridge.start()) {
        std::cerr << "[SION] ❌ Python 프로세스 시작 실패" << std::endl;
        return 1;
    }
    std::cout << "[SION] ✅ Python 브릿지 연결 완료" << std::endl;
    
    // 핫키 핸들러 초기화
    sion::HotkeyHandler hotkeyHandler;
    
    // 활성화 핫키 등록 (Ctrl+Shift+S)
    int activateHotkeyId = hotkeyHandler.registerHotkey("ctrl+shift+s", [&]() {
        std::cout << "\n[SION] ⌨️ 핫키 감지: Ctrl+Shift+S" << std::endl;
        handleVoiceCommand(audioCapture, pythonBridge);
    });
    
    if (activateHotkeyId < 0) {
        std::cerr << "[SION] ❌ 핫키 등록 실패" << std::endl;
        return 1;
    }
    std::cout << "[SION] ✅ 핫키 등록 완료 (Ctrl+Shift+S)" << std::endl;
    
    // 취소 핫키 등록 (Escape)
    int cancelHotkeyId = hotkeyHandler.registerHotkey("escape", [&]() {
        std::cout << "\n[SION] ⌨️ 취소 키 감지" << std::endl;
        // TODO: 현재 진행 중인 작업 취소
    });
    
    std::cout << "\n[SION] 🚀 대기 중... (Ctrl+Shift+S로 음성 명령)" << std::endl;
    std::cout << "[SION] 종료하려면 Ctrl+C를 누르세요." << std::endl;
    std::cout << "----------------------------------------" << std::endl;
    
    // 핫키 리스너 시작 (블로킹)
    while (g_running) {
        hotkeyHandler.startListening();
    }
    
    // 정리
    std::cout << "\n[SION] 정리 중..." << std::endl;
    hotkeyHandler.unregisterAllHotkeys();
    pythonBridge.stop();
    
    std::cout << "[SION] 👋 종료 완료" << std::endl;
    return 0;
}


