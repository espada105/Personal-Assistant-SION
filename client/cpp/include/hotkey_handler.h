#pragma once

#ifndef HOTKEY_HANDLER_H
#define HOTKEY_HANDLER_H

#include <functional>
#include <string>
#include <unordered_map>
#include <atomic>
#include <thread>

#ifdef _WIN32
#include <windows.h>
#endif

namespace sion {

/**
 * @brief 핫키 이벤트 콜백 타입
 */
using HotkeyCallback = std::function<void()>;

/**
 * @brief 핫키 식별자
 */
struct HotkeyId {
    int id;
    int modifiers;
    int keyCode;
};

/**
 * @brief 글로벌 핫키를 관리하는 클래스
 * 
 * Windows API를 사용하여 시스템 전역 핫키를 등록하고
 * 해당 핫키가 눌렸을 때 콜백을 실행합니다.
 */
class HotkeyHandler {
public:
    /**
     * @brief 생성자
     */
    HotkeyHandler();

    /**
     * @brief 소멸자 - 등록된 모든 핫키 해제
     */
    ~HotkeyHandler();

    // 복사 금지
    HotkeyHandler(const HotkeyHandler&) = delete;
    HotkeyHandler& operator=(const HotkeyHandler&) = delete;

    /**
     * @brief 핫키 등록
     * @param hotkeyString 핫키 문자열 (예: "ctrl+shift+s")
     * @param callback 핫키가 눌렸을 때 실행할 콜백
     * @return 성공 시 핫키 ID, 실패 시 -1
     */
    int registerHotkey(const std::string& hotkeyString, HotkeyCallback callback);

    /**
     * @brief 핫키 해제
     * @param hotkeyId 등록 시 반환받은 핫키 ID
     * @return 성공 여부
     */
    bool unregisterHotkey(int hotkeyId);

    /**
     * @brief 모든 핫키 해제
     */
    void unregisterAllHotkeys();

    /**
     * @brief 핫키 리스너 시작 (블로킹)
     */
    void startListening();

    /**
     * @brief 핫키 리스너 시작 (논블로킹, 별도 스레드)
     */
    void startListeningAsync();

    /**
     * @brief 핫키 리스너 중지
     */
    void stopListening();

    /**
     * @brief 리스너 실행 중인지 확인
     */
    bool isListening() const;

private:
    /**
     * @brief 핫키 문자열 파싱
     * @param hotkeyString 핫키 문자열
     * @param modifiers 출력: 수정자 키 플래그
     * @param keyCode 출력: 가상 키 코드
     * @return 파싱 성공 여부
     */
    bool parseHotkeyString(const std::string& hotkeyString, int& modifiers, int& keyCode);

    /**
     * @brief 메시지 루프 (Windows)
     */
    void messageLoop();

    std::unordered_map<int, HotkeyCallback> m_callbacks;
    std::unordered_map<int, HotkeyId> m_hotkeys;
    std::atomic<bool> m_running;
    std::thread m_listenerThread;
    int m_nextId;

#ifdef _WIN32
    HWND m_hwnd;
#endif
};

} // namespace sion

#endif // HOTKEY_HANDLER_H


