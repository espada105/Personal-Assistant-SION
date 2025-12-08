/**
 * @file hotkey_handler.cpp
 * @brief HotkeyHandler 클래스 구현
 */

#include "hotkey_handler.h"
#include <algorithm>
#include <cctype>
#include <iostream>
#include <sstream>

namespace sion {

HotkeyHandler::HotkeyHandler()
    : m_running(false)
    , m_nextId(1)
#ifdef _WIN32
    , m_hwnd(nullptr)
#endif
{
}

HotkeyHandler::~HotkeyHandler() {
    stopListening();
    unregisterAllHotkeys();
}

int HotkeyHandler::registerHotkey(const std::string& hotkeyString, HotkeyCallback callback) {
    int modifiers = 0;
    int keyCode = 0;
    
    if (!parseHotkeyString(hotkeyString, modifiers, keyCode)) {
        std::cerr << "[HotkeyHandler] 핫키 파싱 실패: " << hotkeyString << std::endl;
        return -1;
    }
    
#ifdef _WIN32
    // Windows에서 핫키 등록
    if (!RegisterHotKey(nullptr, m_nextId, modifiers, keyCode)) {
        std::cerr << "[HotkeyHandler] RegisterHotKey 실패: " << GetLastError() << std::endl;
        return -1;
    }
#endif
    
    int id = m_nextId++;
    m_callbacks[id] = callback;
    m_hotkeys[id] = {id, modifiers, keyCode};
    
    std::cout << "[HotkeyHandler] 핫키 등록됨: " << hotkeyString 
              << " (ID: " << id << ")" << std::endl;
    
    return id;
}

bool HotkeyHandler::unregisterHotkey(int hotkeyId) {
    auto it = m_hotkeys.find(hotkeyId);
    if (it == m_hotkeys.end()) {
        return false;
    }
    
#ifdef _WIN32
    UnregisterHotKey(nullptr, hotkeyId);
#endif
    
    m_callbacks.erase(hotkeyId);
    m_hotkeys.erase(it);
    
    return true;
}

void HotkeyHandler::unregisterAllHotkeys() {
    for (auto& [id, hotkey] : m_hotkeys) {
#ifdef _WIN32
        UnregisterHotKey(nullptr, id);
#endif
    }
    m_callbacks.clear();
    m_hotkeys.clear();
}

void HotkeyHandler::startListening() {
    m_running = true;
    messageLoop();
}

void HotkeyHandler::startListeningAsync() {
    m_running = true;
    m_listenerThread = std::thread(&HotkeyHandler::messageLoop, this);
}

void HotkeyHandler::stopListening() {
    m_running = false;
    
#ifdef _WIN32
    // 메시지 루프 종료를 위한 메시지 전송
    PostThreadMessage(GetCurrentThreadId(), WM_QUIT, 0, 0);
#endif
    
    if (m_listenerThread.joinable()) {
        m_listenerThread.join();
    }
}

bool HotkeyHandler::isListening() const {
    return m_running;
}

bool HotkeyHandler::parseHotkeyString(const std::string& hotkeyString, int& modifiers, int& keyCode) {
    modifiers = 0;
    keyCode = 0;
    
    // 소문자로 변환
    std::string str = hotkeyString;
    std::transform(str.begin(), str.end(), str.begin(), ::tolower);
    
    // '+' 기준으로 분리
    std::stringstream ss(str);
    std::string token;
    std::vector<std::string> parts;
    
    while (std::getline(ss, token, '+')) {
        // 앞뒤 공백 제거
        token.erase(0, token.find_first_not_of(" \t"));
        token.erase(token.find_last_not_of(" \t") + 1);
        
        if (!token.empty()) {
            parts.push_back(token);
        }
    }
    
    if (parts.empty()) {
        return false;
    }
    
#ifdef _WIN32
    // 수정자 키 파싱
    for (size_t i = 0; i < parts.size() - 1; ++i) {
        const auto& part = parts[i];
        
        if (part == "ctrl" || part == "control") {
            modifiers |= MOD_CONTROL;
        } else if (part == "alt") {
            modifiers |= MOD_ALT;
        } else if (part == "shift") {
            modifiers |= MOD_SHIFT;
        } else if (part == "win" || part == "windows") {
            modifiers |= MOD_WIN;
        }
    }
    
    // 메인 키 파싱
    const auto& mainKey = parts.back();
    
    // 알파벳 키
    if (mainKey.length() == 1 && std::isalpha(mainKey[0])) {
        keyCode = std::toupper(mainKey[0]);
    }
    // 숫자 키
    else if (mainKey.length() == 1 && std::isdigit(mainKey[0])) {
        keyCode = mainKey[0];
    }
    // 특수 키
    else if (mainKey == "space") {
        keyCode = VK_SPACE;
    } else if (mainKey == "enter" || mainKey == "return") {
        keyCode = VK_RETURN;
    } else if (mainKey == "escape" || mainKey == "esc") {
        keyCode = VK_ESCAPE;
    } else if (mainKey == "tab") {
        keyCode = VK_TAB;
    } else if (mainKey == "backspace") {
        keyCode = VK_BACK;
    } else if (mainKey == "delete" || mainKey == "del") {
        keyCode = VK_DELETE;
    } else if (mainKey == "insert" || mainKey == "ins") {
        keyCode = VK_INSERT;
    } else if (mainKey == "home") {
        keyCode = VK_HOME;
    } else if (mainKey == "end") {
        keyCode = VK_END;
    } else if (mainKey == "pageup" || mainKey == "pgup") {
        keyCode = VK_PRIOR;
    } else if (mainKey == "pagedown" || mainKey == "pgdn") {
        keyCode = VK_NEXT;
    } else if (mainKey == "up") {
        keyCode = VK_UP;
    } else if (mainKey == "down") {
        keyCode = VK_DOWN;
    } else if (mainKey == "left") {
        keyCode = VK_LEFT;
    } else if (mainKey == "right") {
        keyCode = VK_RIGHT;
    }
    // Function 키 (F1-F12)
    else if (mainKey.length() >= 2 && mainKey[0] == 'f') {
        int fNum = std::stoi(mainKey.substr(1));
        if (fNum >= 1 && fNum <= 12) {
            keyCode = VK_F1 + (fNum - 1);
        }
    }
#endif
    
    return keyCode != 0;
}

void HotkeyHandler::messageLoop() {
#ifdef _WIN32
    MSG msg;
    
    while (m_running && GetMessage(&msg, nullptr, 0, 0)) {
        if (msg.message == WM_HOTKEY) {
            int hotkeyId = static_cast<int>(msg.wParam);
            
            auto it = m_callbacks.find(hotkeyId);
            if (it != m_callbacks.end() && it->second) {
                it->second();
            }
        }
        
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
#else
    // Linux/macOS 구현은 추후 추가
    while (m_running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
#endif
}

} // namespace sion

