/**
 * @file python_bridge.cpp
 * @brief PythonBridge 및 PythonProcessBridge 클래스 구현
 */

#include "python_bridge.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <cstring>

#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#include <sys/wait.h>
#include <signal.h>
#endif

#ifdef PYTHON_ENABLED
#include <Python.h>
#endif

namespace sion {

// ============================================================================
// PythonBridge 구현 (임베디드 Python)
// ============================================================================

PythonBridge::PythonBridge()
    : m_initialized(false)
    , m_module(nullptr)
{
}

PythonBridge::~PythonBridge() {
    finalize();
}

bool PythonBridge::initialize(const std::string& pythonHome) {
#ifdef PYTHON_ENABLED
    if (m_initialized) {
        return true;
    }
    
    if (!pythonHome.empty()) {
        Py_SetPythonHome(Py_DecodeLocale(pythonHome.c_str(), nullptr));
    }
    
    Py_Initialize();
    
    if (!Py_IsInitialized()) {
        m_lastError = "Python 초기화 실패";
        return false;
    }
    
    m_initialized = true;
    return true;
#else
    m_lastError = "Python 지원이 비활성화되어 있습니다.";
    return false;
#endif
}

void PythonBridge::finalize() {
#ifdef PYTHON_ENABLED
    if (m_initialized) {
        if (m_module) {
            Py_DECREF(static_cast<PyObject*>(m_module));
            m_module = nullptr;
        }
        Py_Finalize();
        m_initialized = false;
    }
#endif
}

bool PythonBridge::importModule(const std::string& moduleName) {
#ifdef PYTHON_ENABLED
    if (!m_initialized) {
        m_lastError = "Python이 초기화되지 않았습니다.";
        return false;
    }
    
    PyObject* module = PyImport_ImportModule(moduleName.c_str());
    if (!module) {
        PyErr_Print();
        m_lastError = "모듈 임포트 실패: " + moduleName;
        return false;
    }
    
    if (m_module) {
        Py_DECREF(static_cast<PyObject*>(m_module));
    }
    m_module = module;
    
    return true;
#else
    return false;
#endif
}

std::string PythonBridge::processAudio(const std::vector<uint8_t>& audioData) {
#ifdef PYTHON_ENABLED
    if (!m_module) {
        m_lastError = "모듈이 로드되지 않았습니다.";
        return "";
    }
    
    PyObject* func = PyObject_GetAttrString(
        static_cast<PyObject*>(m_module), "process_audio");
    
    if (!func || !PyCallable_Check(func)) {
        Py_XDECREF(func);
        m_lastError = "process_audio 함수를 찾을 수 없습니다.";
        return "";
    }
    
    // 바이트 배열을 Python bytes로 변환
    PyObject* pyBytes = PyBytes_FromStringAndSize(
        reinterpret_cast<const char*>(audioData.data()),
        audioData.size());
    
    PyObject* args = PyTuple_Pack(1, pyBytes);
    PyObject* result = PyObject_CallObject(func, args);
    
    Py_DECREF(pyBytes);
    Py_DECREF(args);
    Py_DECREF(func);
    
    if (!result) {
        PyErr_Print();
        m_lastError = "함수 호출 실패";
        return "";
    }
    
    std::string resultStr;
    if (PyUnicode_Check(result)) {
        resultStr = PyUnicode_AsUTF8(result);
    }
    
    Py_DECREF(result);
    return resultStr;
#else
    return "";
#endif
}

std::string PythonBridge::callFunction(const std::string& functionName, const std::string& arg) {
#ifdef PYTHON_ENABLED
    if (!m_module) {
        return "";
    }
    
    PyObject* func = PyObject_GetAttrString(
        static_cast<PyObject*>(m_module), functionName.c_str());
    
    if (!func || !PyCallable_Check(func)) {
        Py_XDECREF(func);
        return "";
    }
    
    PyObject* pyArg = PyUnicode_FromString(arg.c_str());
    PyObject* args = PyTuple_Pack(1, pyArg);
    PyObject* result = PyObject_CallObject(func, args);
    
    Py_DECREF(pyArg);
    Py_DECREF(args);
    Py_DECREF(func);
    
    if (!result) {
        PyErr_Print();
        return "";
    }
    
    std::string resultStr;
    if (PyUnicode_Check(result)) {
        resultStr = PyUnicode_AsUTF8(result);
    }
    
    Py_DECREF(result);
    return resultStr;
#else
    return "";
#endif
}

bool PythonBridge::executeScript(const std::string& scriptPath) {
#ifdef PYTHON_ENABLED
    if (!m_initialized) {
        return false;
    }
    
    std::ifstream file(scriptPath);
    if (!file.is_open()) {
        m_lastError = "스크립트 파일을 열 수 없습니다: " + scriptPath;
        return false;
    }
    
    std::stringstream buffer;
    buffer << file.rdbuf();
    std::string code = buffer.str();
    
    int result = PyRun_SimpleString(code.c_str());
    return result == 0;
#else
    return false;
#endif
}

// ============================================================================
// PythonProcessBridge 구현 (프로세스 간 통신)
// ============================================================================

PythonProcessBridge::PythonProcessBridge(
    const std::string& pythonPath,
    const std::string& scriptPath)
    : m_pythonPath(pythonPath)
    , m_scriptPath(scriptPath)
    , m_processHandle(nullptr)
    , m_stdinPipe(nullptr)
    , m_stdoutPipe(nullptr)
    , m_running(false)
{
}

PythonProcessBridge::~PythonProcessBridge() {
    stop();
}

bool PythonProcessBridge::start() {
#ifdef _WIN32
    SECURITY_ATTRIBUTES sa;
    sa.nLength = sizeof(SECURITY_ATTRIBUTES);
    sa.bInheritHandle = TRUE;
    sa.lpSecurityDescriptor = nullptr;
    
    HANDLE hStdinRead, hStdinWrite;
    HANDLE hStdoutRead, hStdoutWrite;
    
    // stdin 파이프 생성
    if (!CreatePipe(&hStdinRead, &hStdinWrite, &sa, 0)) {
        std::cerr << "[PythonProcessBridge] stdin 파이프 생성 실패" << std::endl;
        return false;
    }
    SetHandleInformation(hStdinWrite, HANDLE_FLAG_INHERIT, 0);
    
    // stdout 파이프 생성
    if (!CreatePipe(&hStdoutRead, &hStdoutWrite, &sa, 0)) {
        CloseHandle(hStdinRead);
        CloseHandle(hStdinWrite);
        std::cerr << "[PythonProcessBridge] stdout 파이프 생성 실패" << std::endl;
        return false;
    }
    SetHandleInformation(hStdoutRead, HANDLE_FLAG_INHERIT, 0);
    
    // 프로세스 시작 정보 설정
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.hStdInput = hStdinRead;
    si.hStdOutput = hStdoutWrite;
    si.hStdError = hStdoutWrite;
    si.dwFlags |= STARTF_USESTDHANDLES;
    
    ZeroMemory(&pi, sizeof(pi));
    
    // 명령줄 구성
    std::string cmdLine = m_pythonPath + " " + m_scriptPath + " --pipe-mode";
    
    // 프로세스 생성
    if (!CreateProcessA(
            nullptr,
            const_cast<char*>(cmdLine.c_str()),
            nullptr,
            nullptr,
            TRUE,
            CREATE_NO_WINDOW,
            nullptr,
            nullptr,
            &si,
            &pi)) {
        CloseHandle(hStdinRead);
        CloseHandle(hStdinWrite);
        CloseHandle(hStdoutRead);
        CloseHandle(hStdoutWrite);
        std::cerr << "[PythonProcessBridge] 프로세스 생성 실패: " 
                  << GetLastError() << std::endl;
        return false;
    }
    
    // 자식 프로세스 측 핸들 닫기
    CloseHandle(hStdinRead);
    CloseHandle(hStdoutWrite);
    
    m_processHandle = pi.hProcess;
    m_stdinPipe = hStdinWrite;
    m_stdoutPipe = hStdoutRead;
    m_running = true;
    
    // 스레드 핸들 닫기 (필요 없음)
    CloseHandle(pi.hThread);
    
    return true;
#else
    // Linux/macOS 구현
    std::cout << "[PythonProcessBridge] 더미 모드로 시작" << std::endl;
    m_running = true;
    return true;
#endif
}

void PythonProcessBridge::stop() {
#ifdef _WIN32
    if (m_running) {
        // 프로세스 종료
        if (m_processHandle) {
            TerminateProcess(static_cast<HANDLE>(m_processHandle), 0);
            CloseHandle(static_cast<HANDLE>(m_processHandle));
            m_processHandle = nullptr;
        }
        
        // 파이프 닫기
        if (m_stdinPipe) {
            CloseHandle(static_cast<HANDLE>(m_stdinPipe));
            m_stdinPipe = nullptr;
        }
        if (m_stdoutPipe) {
            CloseHandle(static_cast<HANDLE>(m_stdoutPipe));
            m_stdoutPipe = nullptr;
        }
        
        m_running = false;
    }
#else
    m_running = false;
#endif
}

std::string PythonProcessBridge::sendAudio(const std::vector<uint8_t>& audioData) {
    if (!m_running) {
        return "";
    }
    
#ifdef _WIN32
    // 데이터 크기 전송 (4바이트)
    uint32_t dataSize = static_cast<uint32_t>(audioData.size());
    DWORD bytesWritten;
    
    if (!WriteFile(static_cast<HANDLE>(m_stdinPipe), 
                   &dataSize, sizeof(dataSize), &bytesWritten, nullptr)) {
        return "";
    }
    
    // 오디오 데이터 전송
    if (!WriteFile(static_cast<HANDLE>(m_stdinPipe),
                   audioData.data(), dataSize, &bytesWritten, nullptr)) {
        return "";
    }
    
    FlushFileBuffers(static_cast<HANDLE>(m_stdinPipe));
    
    // 응답 크기 수신
    uint32_t responseSize;
    DWORD bytesRead;
    
    if (!ReadFile(static_cast<HANDLE>(m_stdoutPipe),
                  &responseSize, sizeof(responseSize), &bytesRead, nullptr)) {
        return "";
    }
    
    // 응답 데이터 수신
    std::string response(responseSize, '\0');
    if (!ReadFile(static_cast<HANDLE>(m_stdoutPipe),
                  response.data(), responseSize, &bytesRead, nullptr)) {
        return "";
    }
    
    return response;
#else
    return "더미 응답";
#endif
}

std::string PythonProcessBridge::sendCommand(const std::string& command) {
    if (!m_running) {
        return "";
    }
    
    // 명령을 UTF-8 바이트로 변환하여 전송
    std::vector<uint8_t> cmdBytes(command.begin(), command.end());
    return sendAudio(cmdBytes);  // 동일한 프로토콜 사용
}

bool PythonProcessBridge::isRunning() const {
#ifdef _WIN32
    if (!m_processHandle) {
        return false;
    }
    
    DWORD exitCode;
    if (GetExitCodeProcess(static_cast<HANDLE>(m_processHandle), &exitCode)) {
        return exitCode == STILL_ACTIVE;
    }
    return false;
#else
    return m_running;
#endif
}

} // namespace sion


