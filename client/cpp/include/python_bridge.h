#pragma once

#ifndef PYTHON_BRIDGE_H
#define PYTHON_BRIDGE_H

#include <string>
#include <vector>
#include <cstdint>

namespace sion {

/**
 * @brief Python 인터프리터와의 통신을 담당하는 클래스
 * 
 * C++에서 캡처한 오디오 데이터를 Python 클라이언트로 전달하고,
 * Python 함수를 호출하여 결과를 받아옵니다.
 */
class PythonBridge {
public:
    /**
     * @brief 생성자
     */
    PythonBridge();

    /**
     * @brief 소멸자
     */
    ~PythonBridge();

    /**
     * @brief Python 인터프리터 초기화
     * @param pythonHome Python 설치 경로 (선택)
     * @return 성공 여부
     */
    bool initialize(const std::string& pythonHome = "");

    /**
     * @brief Python 인터프리터 종료
     */
    void finalize();

    /**
     * @brief Python 모듈 임포트
     * @param moduleName 모듈 이름
     * @return 성공 여부
     */
    bool importModule(const std::string& moduleName);

    /**
     * @brief 오디오 데이터를 Python으로 전송하고 처리
     * @param audioData WAV 형식 오디오 바이트
     * @return 처리 결과 문자열
     */
    std::string processAudio(const std::vector<uint8_t>& audioData);

    /**
     * @brief Python 함수 호출 (문자열 인자, 문자열 반환)
     * @param functionName 함수 이름
     * @param arg 인자
     * @return 반환 값
     */
    std::string callFunction(const std::string& functionName, const std::string& arg);

    /**
     * @brief Python 스크립트 파일 실행
     * @param scriptPath 스크립트 경로
     * @return 성공 여부
     */
    bool executeScript(const std::string& scriptPath);

    /**
     * @brief 초기화 상태 확인
     */
    bool isInitialized() const { return m_initialized; }

    /**
     * @brief 마지막 오류 메시지 반환
     */
    const std::string& getLastError() const { return m_lastError; }

private:
    bool m_initialized;
    std::string m_lastError;
    void* m_module;  // PyObject* (Python.h 의존성 숨김)
};

/**
 * @brief 프로세스 간 통신을 통한 Python 연동
 * 
 * Python 인터프리터를 임베딩하지 않고,
 * 별도 프로세스로 Python 스크립트를 실행하고 통신합니다.
 */
class PythonProcessBridge {
public:
    /**
     * @brief 생성자
     * @param pythonPath Python 실행 파일 경로
     * @param scriptPath 실행할 스크립트 경로
     */
    PythonProcessBridge(const std::string& pythonPath, const std::string& scriptPath);

    /**
     * @brief 소멸자
     */
    ~PythonProcessBridge();

    /**
     * @brief Python 프로세스 시작
     * @return 성공 여부
     */
    bool start();

    /**
     * @brief Python 프로세스 종료
     */
    void stop();

    /**
     * @brief 오디오 데이터 전송 및 결과 수신
     * @param audioData WAV 형식 오디오 바이트
     * @return 처리 결과
     */
    std::string sendAudio(const std::vector<uint8_t>& audioData);

    /**
     * @brief 텍스트 명령 전송
     * @param command 명령 문자열
     * @return 응답 문자열
     */
    std::string sendCommand(const std::string& command);

    /**
     * @brief 프로세스 실행 중인지 확인
     */
    bool isRunning() const;

private:
    std::string m_pythonPath;
    std::string m_scriptPath;
    void* m_processHandle;
    void* m_stdinPipe;
    void* m_stdoutPipe;
    bool m_running;
};

} // namespace sion

#endif // PYTHON_BRIDGE_H

