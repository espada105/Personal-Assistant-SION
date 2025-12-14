"""
SION Personal Assistant - Desktop Application
메인 GUI 애플리케이션
"""

import customtkinter as ctk
import threading
import subprocess
import sys
import os
import time
import io
import requests
from datetime import datetime, timedelta

# 음성 녹음 관련 임포트
try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

# TTS 관련 임포트 (무료 edge-tts 사용)
try:
    import edge_tts
    import asyncio
    import pygame
    pygame.mixer.init()
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# 글로벌 핫키 관련 임포트
try:
    import keyboard
    HOTKEY_AVAILABLE = True
except ImportError:
    HOTKEY_AVAILABLE = False

import tempfile
import json
import webbrowser

# 프로젝트 루트 경로 (먼저 정의)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SETTINGS_FILE = os.path.join(PROJECT_ROOT, "configs", "user_settings.json")


class SettingsManager:
    """사용자 설정 관리 클래스"""
    
    DEFAULT_SETTINGS = {
        # 창 크기/위치
        "window": {
            "width": 1180,
            "height": 650,
            "x": None,  # None이면 중앙
            "y": None,
            "side_panel_open": True
        },
        # 음성 설정
        "voice": {
            "tts_enabled": True,          # TTS 활성화
            "email_voice_read": True,     # 메일 도착 시 음성으로 읽기
            "email_voice_response": True, # 메일 알림 후 음성 응답 대기
            "schedule_voice_read": True,  # 일정 알림 시 음성으로 읽기
            "volume": 0.8                 # 음량 (0.0 ~ 1.0)
        },
        # 알림 설정
        "notification": {
            "email_enabled": True,
            "schedule_enabled": True,
            "schedule_minutes_before": 10  # 일정 몇 분 전 알림
        }
    }
    
    def __init__(self):
        self.settings = self._load_settings()
    
    def _load_settings(self) -> dict:
        """설정 파일 로드"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # 기본값과 병합 (새로운 설정이 추가되어도 호환)
                    return self._merge_settings(self.DEFAULT_SETTINGS.copy(), loaded)
            return self.DEFAULT_SETTINGS.copy()
        except Exception as e:
            print(f"[Settings] 설정 로드 실패: {e}")
            return self.DEFAULT_SETTINGS.copy()
    
    def _merge_settings(self, default: dict, loaded: dict) -> dict:
        """기본 설정과 로드된 설정 병합"""
        result = default.copy()
        for key, value in loaded.items():
            if key in result:
                if isinstance(value, dict) and isinstance(result[key], dict):
                    result[key] = self._merge_settings(result[key], value)
                else:
                    result[key] = value
        return result
    
    def save(self):
        """설정 저장"""
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            print("[Settings] 설정 저장 완료")
        except Exception as e:
            print(f"[Settings] 설정 저장 실패: {e}")
    
    def get(self, *keys, default=None):
        """설정값 가져오기 (중첩 키 지원)"""
        value = self.settings
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, *keys_and_value):
        """설정값 설정 (마지막 인자가 값)"""
        if len(keys_and_value) < 2:
            return
        
        keys = keys_and_value[:-1]
        value = keys_and_value[-1]
        
        current = self.settings
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value

# 커스텀 폰트 로드 (경기천년체)
FONT_LOADED = False
FONT_NAME = "경기천년제목"  # 폰트 이름
FONT_NAME_EN = "GyeonggiCheonnyeon Title"

def load_custom_fonts():
    """Windows에서 커스텀 폰트 로드"""
    global FONT_LOADED
    if sys.platform != "win32":
        return
    
    try:
        import ctypes
        from ctypes import wintypes
        
        # Windows API 함수
        gdi32 = ctypes.WinDLL('gdi32')
        AddFontResourceEx = gdi32.AddFontResourceExW
        AddFontResourceEx.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPVOID]
        AddFontResourceEx.restype = ctypes.c_int
        
        FR_PRIVATE = 0x10  # 현재 프로세스에서만 사용
        
        # 폰트 파일 경로
        font_dir = os.path.join(PROJECT_ROOT, "configs", "경기천년체_220929", "TTF")
        
        fonts_to_load = [
            "경기천년제목_Medium.ttf",
            "경기천년제목_Bold.ttf",
            "경기천년제목_Light.ttf",
        ]
        
        for font_file in fonts_to_load:
            font_path = os.path.join(font_dir, font_file)
            if os.path.exists(font_path):
                result = AddFontResourceEx(font_path, FR_PRIVATE, None)
                if result > 0:
                    print(f"[Font] 로드 성공: {font_file}")
                    FONT_LOADED = True
        
    except Exception as e:
        print(f"[Font] 폰트 로드 실패: {e}")

# 폰트 로드 실행
load_custom_fonts()

# Google Services 임포트
try:
    # 패키지로 실행될 때
    from .google_services import get_auth_manager, get_calendar_service, get_gmail_service
    GOOGLE_AVAILABLE = True
except ImportError:
    try:
        # 직접 실행될 때
        from google_services import get_auth_manager, get_calendar_service, get_gmail_service
        GOOGLE_AVAILABLE = True
    except ImportError:
        GOOGLE_AVAILABLE = False

# OpenAI 임포트
try:
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, "configs", ".env"))
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# LLM Agent 임포트
try:
    from llm_agent import get_agent, LLMAgent
    LLM_AGENT_AVAILABLE = True
except ImportError:
    try:
        from .llm_agent import get_agent, LLMAgent
        LLM_AGENT_AVAILABLE = True
    except ImportError:
        LLM_AGENT_AVAILABLE = False


class ServiceManager:
    """백엔드 서비스 관리 클래스"""
    
    def __init__(self):
        self.processes = {}
        self.venv_python = os.path.join(PROJECT_ROOT, "venv", "Scripts", "python.exe")
    
    def start_service(self, name: str, port: int, path: str) -> bool:
        """서비스 시작"""
        try:
            service_path = os.path.join(PROJECT_ROOT, path)
            
            # 이미 실행 중인지 확인
            if self.is_running(port):
                print(f"[ServiceManager] {name} already running on port {port}")
                return True
            
            print(f"[ServiceManager] Starting {name} on port {port}...")
            
            process = subprocess.Popen(
                [self.venv_python, "-m", "uvicorn", "app.main:app", 
                 "--host", "127.0.0.1", "--port", str(port)],
                cwd=service_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            self.processes[name] = process
            
            # 서비스 시작 대기
            for _ in range(30):  # 최대 30초 대기
                time.sleep(1)
                if self.is_running(port):
                    print(f"[ServiceManager] {name} started successfully")
                    return True
            
            print(f"[ServiceManager] {name} failed to start")
            return False
            
        except Exception as e:
            print(f"[ServiceManager] Error starting {name}: {e}")
            return False
    
    def is_running(self, port: int) -> bool:
        """서비스 실행 중인지 확인"""
        try:
            response = requests.get(f"http://127.0.0.1:{port}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def stop_all(self):
        """모든 서비스 종료"""
        for name, process in self.processes.items():
            try:
                process.terminate()
                print(f"[ServiceManager] {name} stopped")
            except:
                pass


# 색상 테마 (보라색 기반)
COLORS = {
    "bg_dark": "#0D0D0D",           # 가장 어두운 배경
    "bg_main": "#1A1A2E",           # 메인 배경
    "bg_card": "#16213E",           # 카드/컨테이너 배경
    "bg_input": "#1F1F3D",          # 입력창 배경
    "primary": "#9D4EDD",           # 메인 보라색
    "primary_dark": "#7B2CBF",      # 어두운 보라색
    "primary_light": "#C77DFF",     # 밝은 보라색
    "accent": "#E040FB",            # 악센트 핑크
    "user_bubble": "#9D4EDD",       # 사용자 메시지 (보라색)
    "ai_bubble": "#2D2D44",         # AI 메시지 (어두운 보라 회색)
    "text_primary": "#FFFFFF",      # 기본 텍스트
    "text_secondary": "#B0B0B0",    # 보조 텍스트
    "success": "#4CAF50",           # 성공 (녹색)
    "error": "#FF5252",             # 에러 (빨간색)
}


class ChatMessage(ctk.CTkFrame):
    """채팅 메시지 위젯 (모던 디자인 + 스트리밍 지원)"""
    
    def __init__(self, parent, message: str, is_user: bool = True, streaming: bool = False, on_update=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(fg_color="transparent")
        self.full_message = message
        self.current_text = ""
        self.streaming = streaming
        self.on_update = on_update  # 업데이트 시 호출할 콜백 (스크롤용)
        self.is_user = is_user
        
        # 메시지 정렬 및 색상 - 60% 너비 사용
        if is_user:
            self.anchor = "e"
            bg_color = COLORS["user_bubble"]
            self.text_color = COLORS["text_primary"]
            self.padx = (150, 15)  # 좌측 여백 늘려서 60% 너비
            corner = 20
        else:
            self.anchor = "w"
            bg_color = COLORS["ai_bubble"]
            self.text_color = COLORS["text_primary"]
            self.padx = (15, 150)  # 우측 여백 늘려서 60% 너비
            corner = 20
        
        # 메시지 컨테이너 (그라데이션 효과)
        self.msg_frame = ctk.CTkFrame(
            self, 
            fg_color=bg_color, 
            corner_radius=corner,
            border_width=1 if not is_user else 0,
            border_color="#3D3D5C" if not is_user else None
        )
        self.msg_frame.pack(anchor=self.anchor, padx=self.padx, pady=10)
        
        # 메시지 텍스트
        initial_text = "" if streaming else message
        self.msg_label = ctk.CTkLabel(
            self.msg_frame, 
            text=initial_text,
            text_color=self.text_color,
            wraplength=450,  # 60% 너비에 맞춤
            justify="left",
            font=("경기천년제목 Medium", 14)
        )
        self.msg_label.pack(padx=18, pady=14)
        
        # 스트리밍 모드면 타이핑 시작
        if streaming and not is_user:
            self.char_index = 0
            self.after(10, self._type_next_char)
    
    def _type_next_char(self):
        """한 글자씩 타이핑 효과"""
        if self.char_index < len(self.full_message):
            # 여러 글자씩 추가 (속도 향상)
            chunk_size = 3  # 한 번에 3글자씩
            end_index = min(self.char_index + chunk_size, len(self.full_message))
            self.current_text = self.full_message[:end_index]
            self.msg_label.configure(text=self.current_text)
            self.char_index = end_index
            
            # 스크롤 콜백 호출
            if self.on_update:
                self.on_update()
            
            # 다음 글자
            self.after(15, self._type_next_char)  # 15ms 간격
    
    def set_text(self, text: str):
        """텍스트 직접 설정 (스트리밍 완료 후 등)"""
        self.full_message = text
        self.current_text = text
        self.msg_label.configure(text=text)


class SplashScreen(ctk.CTkToplevel):
    """영화 인트로 스타일 스플래시 스크린"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # 창 설정 (테두리 없이, 중앙에)
        self.overrideredirect(True)  # 타이틀바 제거
        self.configure(fg_color=COLORS["bg_dark"])
        
        # 크기 및 위치
        splash_width, splash_height = 500, 400
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - splash_width) // 2
        y = (screen_height - splash_height) // 2
        self.geometry(f"{splash_width}x{splash_height}+{x}+{y}")
        
        # 항상 위에
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.0)
        
        # 레이아웃
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        
        # SION 캐릭터 이미지
        try:
            from PIL import Image, ImageTk
            image_path = os.path.join(PROJECT_ROOT, "configs", "SION.png")
            if os.path.exists(image_path):
                pil_image = Image.open(image_path)
                # 이미지 크기 조정
                pil_image = pil_image.resize((200, 200), Image.Resampling.LANCZOS)
                self.splash_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(200, 200))
                
                image_label = ctk.CTkLabel(
                    self,
                    text="",
                    image=self.splash_image
                )
                image_label.grid(row=0, column=0, pady=(50, 20))
        except Exception as e:
            print(f"[Splash] 이미지 로드 실패: {e}")
        
        # 로고 텍스트
        logo_label = ctk.CTkLabel(
            self,
            text="✦ SION",
            font=("경기천년제목 Bold", 48),
            text_color=COLORS["primary_light"]
        )
        logo_label.grid(row=1, column=0, pady=(0, 10))
        
        # 서브 텍스트
        sub_label = ctk.CTkLabel(
            self,
            text="Personal Assistant",
            font=("경기천년제목 Light", 18),
            text_color=COLORS["text_secondary"]
        )
        sub_label.grid(row=2, column=0, pady=(0, 50))
        
        # 페이드인 시작
        self.after(100, lambda: self._fade_in(0.0))
    
    def _fade_in(self, alpha):
        """페이드인"""
        if alpha < 1.0:
            alpha += 0.08
            self.attributes('-alpha', min(alpha, 1.0))
            self.after(30, lambda: self._fade_in(alpha))
    
    def fade_out_and_close(self, callback):
        """페이드아웃 후 닫기"""
        self._fade_out(1.0, callback)
    
    def _fade_out(self, alpha, callback):
        """페이드아웃"""
        if alpha > 0:
            alpha -= 0.08
            self.attributes('-alpha', max(alpha, 0.0))
            self.after(30, lambda: self._fade_out(alpha, callback))
        else:
            self.destroy()
            callback()


class SionApp(ctk.CTk):
    """SION 메인 애플리케이션"""
    
    def __init__(self):
        super().__init__()
        
        # 설정 관리자 초기화 (가장 먼저)
        self.settings = SettingsManager()
        
        # 윈도우 설정
        self.title("SION Personal Assistant")
        self.minsize(600, 400)
        
        # 저장된 창 크기/위치 복원
        saved_width = self.settings.get("window", "width", default=1180)
        saved_height = self.settings.get("window", "height", default=650)
        saved_x = self.settings.get("window", "x")
        saved_y = self.settings.get("window", "y")
        
        if saved_x is not None and saved_y is not None:
            self.geometry(f"{saved_width}x{saved_height}+{saved_x}+{saved_y}")
        else:
            self.center_window(saved_width, saved_height)
        
        # 시작 시 숨김 (스플래시 후 표시)
        self.withdraw()
        
        # 앱 아이콘 설정 (작업 표시줄 포함)
        icon_path = os.path.join(PROJECT_ROOT, "configs", "SION.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
            # Windows 작업 표시줄 아이콘 설정
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SION.PersonalAssistant")
        
        # 테마 설정
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # 배경색 설정
        self.configure(fg_color=COLORS["bg_dark"])
        
        # 서비스 매니저
        self.service_manager = ServiceManager()
        self.services_ready = False
        
        # 음성 모드 (설정에서 로드)
        self.voice_mode = self.settings.get("voice", "tts_enabled", default=True)
        self.is_speaking = False
        
        # 음량 설정 적용
        if TTS_AVAILABLE:
            volume = self.settings.get("voice", "volume", default=0.8)
            pygame.mixer.music.set_volume(volume)
        
        # 글로벌 핫키 설정
        self.hotkey_registered = False
        self.hotkey_combo = "ctrl+shift+."  # 기본 단축키
        
        # 알림 모니터링
        self.monitoring_active = False
        self.monitoring_start_time = None  # 모니터링 시작 시간
        self.notified_email_ids = set()  # 이미 알림한 메일 ID들
        self.email_check_interval = 30000  # 30초 (밀리초)
        self.schedule_check_interval = 60000  # 1분 (밀리초)
        self.notified_events = set()  # 이미 알림한 일정 ID들
        self.waiting_for_response = False  # 알림 응답 대기 중
        self.pending_notification = None  # 대기 중인 알림 정보
        
        # UI 구성
        self.setup_ui()
        
        # 스플래시 스크린 표시
        self.show_splash()
        
        # 서비스 시작 (백그라운드)
        self.start_services_async()
        
        # 글로벌 핫키 등록
        self.register_hotkey()
        
        # 창 크기 변경 이벤트 바인딩
        self.bind("<Configure>", self._on_window_configure)
        self._last_save_time = 0  # 저장 디바운싱용
        
        # 종료 시 서비스 정리
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _on_window_configure(self, event):
        """창 크기/위치 변경 시 설정 저장 (디바운싱)"""
        if event.widget == self and not self.wm_state() == 'iconic':
            current_time = time.time()
            # 0.5초 이내에 중복 저장 방지
            if current_time - self._last_save_time > 0.5:
                self._last_save_time = current_time
                # 실제 저장은 약간의 딜레이 후 (연속 이벤트 대응)
                self.after(500, self._save_window_geometry)
    
    def _save_window_geometry(self):
        """창 크기/위치 저장"""
        try:
            # 최소화 상태가 아닐 때만 저장
            if self.wm_state() != 'iconic':
                geometry = self.geometry()
                # 형식: "WxH+X+Y"
                size_pos = geometry.replace('x', '+').split('+')
                if len(size_pos) >= 4:
                    width, height, x, y = int(size_pos[0]), int(size_pos[1]), int(size_pos[2]), int(size_pos[3])
                    self.settings.set("window", "width", width)
                    self.settings.set("window", "height", height)
                    self.settings.set("window", "x", x)
                    self.settings.set("window", "y", y)
                    self.settings.set("window", "side_panel_open", self.side_panel_open)
                    self.settings.save()
        except Exception as e:
            print(f"[Settings] 창 크기 저장 오류: {e}")
    
    def show_splash(self):
        """스플래시 스크린 표시"""
        self.splash = SplashScreen(self)
        # 4초 후 스플래시 페이드아웃 → 메인 앱 표시
        self.after(4000, self.end_splash)
    
    def end_splash(self):
        """스플래시 종료 후 메인 앱 표시"""
        self.splash.fade_out_and_close(self.show_main_window)
    
    def show_main_window(self):
        """메인 윈도우 표시 (페이드인)"""
        self.deiconify()  # 창 표시
        self.attributes('-alpha', 1.0)  # 바로 표시
        self.lift()
        self.focus_force()
        
        # 사이드 패널 기본으로 열기
        self._open_side_panel_default()
        
        # 자동 로그인 시도
        self.after(500, self.try_auto_login)
    
    def center_window(self, width, height):
        """창을 화면 중앙에 배치"""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """UI 구성 (모던 보라색 테마)"""
        # 메인 컨테이너 (채팅 + 사이드패널)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)  # 사이드 패널
        self.grid_rowconfigure(1, weight=1)
        
        # 사이드 패널 상태
        self.side_panel_open = False
        self.side_panel_width = 480  # 더 넓은 패널
        
        # === 헤더 (전체 너비) ===
        header_frame = ctk.CTkFrame(
            self, 
            fg_color=COLORS["bg_main"], 
            height=70,
            corner_radius=0
        )
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(1, weight=1)
        
        # 로고/타이틀
        title_label = ctk.CTkLabel(
            header_frame, 
            text="✦ SION", 
            font=("경기천년제목 Bold", 24),
            text_color=COLORS["primary_light"]
        )
        title_label.grid(row=0, column=0, padx=25, pady=18)
        
        # 음성 모드 토글 버튼
        self.voice_btn = ctk.CTkButton(
            header_frame,
            text="🔊",
            width=36,
            height=36,
            font=("Segoe UI", 16),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["primary_dark"],
            corner_radius=18,
            border_width=1,
            border_color=COLORS["primary"],
            command=self.toggle_voice_mode
        )
        self.voice_btn.grid(row=0, column=1, padx=4, pady=15, sticky="e")
        
        # Google 로그인 버튼
        self.google_btn = ctk.CTkButton(
            header_frame,
            text="🔗",
            width=36,
            height=36,
            font=("Segoe UI", 16),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["primary_dark"],
            corner_radius=18,
            border_width=1,
            border_color="#666666",
            command=self.google_login
        )
        self.google_btn.grid(row=0, column=2, padx=4, pady=15, sticky="e")
        
        # 캘린더 바로가기 버튼 (로그인 후 표시)
        self.calendar_btn = ctk.CTkButton(
            header_frame,
            text="📅",
            width=36,
            height=36,
            font=("Segoe UI", 16),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["primary_dark"],
            corner_radius=18,
            border_width=1,
            border_color="#666666",
            command=self.open_google_calendar
        )
        # 처음엔 숨김
        
        # 메일 바로가기 버튼 (로그인 후 표시)
        self.mail_btn = ctk.CTkButton(
            header_frame,
            text="📧",
            width=36,
            height=36,
            font=("Segoe UI", 16),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["primary_dark"],
            corner_radius=18,
            border_width=1,
            border_color="#666666",
            command=self.open_gmail
        )
        # 처음엔 숨김
        
        # 상태 표시 (작은 점으로)
        self.status_label = ctk.CTkLabel(
            header_frame,
            text="●",
            font=("경기천년제목 Medium", 12),
            text_color="#FFA500"  # 주황색 (로딩 중)
        )
        self.status_label.grid(row=0, column=3, padx=4, pady=18, sticky="e")
        
        # 설정 버튼
        self.settings_btn = ctk.CTkButton(
            header_frame,
            text="⚙",
            width=36,
            height=36,
            font=("Segoe UI", 16),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["primary_dark"],
            corner_radius=18,
            border_width=1,
            border_color="#666666",
            command=self.open_settings
        )
        self.settings_btn.grid(row=0, column=4, padx=4, pady=15, sticky="e")
        
        # 사이드 패널 토글 버튼
        self.panel_toggle_btn = ctk.CTkButton(
            header_frame,
            text="◀",
            width=36,
            height=36,
            font=("Segoe UI", 14),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["primary_dark"],
            corner_radius=18,
            border_width=1,
            border_color=COLORS["primary"],
            command=self.toggle_side_panel
        )
        self.panel_toggle_btn.grid(row=0, column=6, padx=(4, 15), pady=15, sticky="e")
        
        # === 채팅 영역 ===
        chat_container = ctk.CTkFrame(
            self, 
            fg_color=COLORS["bg_main"],
            corner_radius=20,
            border_width=1,
            border_color="#2D2D44"
        )
        chat_container.grid(row=1, column=0, sticky="nsew", padx=15, pady=10)
        chat_container.grid_columnconfigure(0, weight=1)
        chat_container.grid_rowconfigure(0, weight=1)
        
        # 스크롤 가능한 채팅 영역
        self.chat_frame = ctk.CTkScrollableFrame(
            chat_container,
            fg_color="transparent",
            scrollbar_button_color=COLORS["primary_dark"],
            scrollbar_button_hover_color=COLORS["primary"]
        )
        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chat_frame.grid_columnconfigure(0, weight=1)
        
        # === 입력 영역 ===
        input_frame = ctk.CTkFrame(
            self, 
            fg_color=COLORS["bg_main"], 
            height=60,
            corner_radius=15,
            border_width=1,
            border_color="#2D2D44"
        )
        input_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 12))
        input_frame.grid_columnconfigure(0, weight=1)
        
        # 텍스트 입력
        self.input_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="메시지를 입력하세요...",
            height=40,
            font=("경기천년제목 Medium", 13),
            corner_radius=20,
            fg_color=COLORS["bg_card"],
            border_color=COLORS["primary_dark"],
            border_width=1,
            text_color=COLORS["text_primary"],
            placeholder_text_color=COLORS["text_secondary"]
        )
        self.input_entry.grid(row=0, column=0, padx=(12, 8), pady=10, sticky="ew")
        self.input_entry.bind("<Return>", self.on_send)
        
        # 마이크 버튼 (음성 입력)
        self.is_recording = False
        self.mic_button = ctk.CTkButton(
            input_frame,
            text="🎤",
            width=40,
            height=40,
            font=("Segoe UI", 16),
            corner_radius=20,
            fg_color=COLORS["primary"] if AUDIO_AVAILABLE else "#555555",
            hover_color=COLORS["primary_light"] if AUDIO_AVAILABLE else "#555555",
            command=self.toggle_recording
        )
        self.mic_button.grid(row=0, column=1, padx=(0, 5), pady=10)
        
        if not AUDIO_AVAILABLE:
            self.mic_button.configure(state="disabled")
        
        # 전송 버튼
        self.send_button = ctk.CTkButton(
            input_frame,
            text="➤",
            width=40,
            height=40,
            font=("Segoe UI", 16),
            corner_radius=20,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_light"],
            command=self.on_send
        )
        self.send_button.grid(row=0, column=2, padx=(0, 12), pady=10)
        
        # === 사이드 패널 (오른쪽) ===
        self.side_panel = ctk.CTkFrame(
            self,
            width=self.side_panel_width,
            fg_color=COLORS["bg_card"],
            corner_radius=20,
            border_width=1,
            border_color="#2D2D44"
        )
        # 처음엔 숨김 상태
        
        # 사이드 패널 내용 구성
        self._setup_side_panel()
    
    def _setup_side_panel(self):
        """사이드 패널 내용 구성 - 2열 레이아웃"""
        # 패널을 2열로 구성
        self.side_panel.grid_columnconfigure(0, weight=1)  # 왼쪽 (시온+일정)
        self.side_panel.grid_columnconfigure(1, weight=1)  # 오른쪽 (메일)
        self.side_panel.grid_rowconfigure(0, weight=1)
        
        # === 왼쪽 열: 시온 이미지 + 일정 ===
        left_frame = ctk.CTkFrame(self.side_panel, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_frame.grid_rowconfigure(1, weight=1)
        
        # 시온 이미지
        try:
            from PIL import Image
            icon_path = os.path.join(PROJECT_ROOT, "configs", "SION.png")
            if os.path.exists(icon_path):
                sion_image = Image.open(icon_path)
                sion_image = sion_image.resize((100, 100), Image.Resampling.LANCZOS)
                self.sion_ctk_image = ctk.CTkImage(light_image=sion_image, dark_image=sion_image, size=(100, 100))
                
                sion_label = ctk.CTkLabel(
                    left_frame,
                    image=self.sion_ctk_image,
                    text=""
                )
                sion_label.pack(pady=(15, 10))
        except Exception as e:
            print(f"[SidePanel] 이미지 로드 실패: {e}")
        
        # 일정 타이틀
        schedule_title = ctk.CTkLabel(
            left_frame,
            text="📅 오늘의 일정",
            font=("경기천년제목 Bold", 16),
            text_color=COLORS["primary_light"]
        )
        schedule_title.pack(pady=(10, 8))
        
        # 구분선
        separator = ctk.CTkFrame(left_frame, height=2, fg_color=COLORS["primary_dark"])
        separator.pack(fill="x", padx=10, pady=5)
        
        # 일정 표시 영역
        self.schedule_frame = ctk.CTkScrollableFrame(
            left_frame,
            fg_color="transparent",
            scrollbar_button_color=COLORS["primary_dark"],
            scrollbar_button_hover_color=COLORS["primary"]
        )
        self.schedule_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 로딩 메시지
        self.schedule_loading_label = ctk.CTkLabel(
            self.schedule_frame,
            text="로그인 후 일정 확인",
            font=("경기천년제목 Medium", 11),
            text_color=COLORS["text_secondary"],
            wraplength=180
        )
        self.schedule_loading_label.pack(pady=15)
        
        # === 오른쪽 열: 메일 (전체 높이) ===
        right_frame = ctk.CTkFrame(self.side_panel, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_frame.grid_rowconfigure(1, weight=1)
        
        # 메일 타이틀
        mail_title = ctk.CTkLabel(
            right_frame,
            text="📧 오늘의 메일",
            font=("경기천년제목 Bold", 16),
            text_color=COLORS["primary_light"]
        )
        mail_title.pack(pady=(15, 8))
        
        # 구분선
        separator2 = ctk.CTkFrame(right_frame, height=2, fg_color=COLORS["primary_dark"])
        separator2.pack(fill="x", padx=10, pady=5)
        
        # 메일 표시 영역 (전체 높이)
        self.mail_frame = ctk.CTkScrollableFrame(
            right_frame,
            fg_color="transparent",
            scrollbar_button_color=COLORS["primary_dark"],
            scrollbar_button_hover_color=COLORS["primary"]
        )
        self.mail_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 로딩 메시지
        self.mail_loading_label = ctk.CTkLabel(
            self.mail_frame,
            text="로그인 후 메일 확인",
            font=("경기천년제목 Medium", 11),
            text_color=COLORS["text_secondary"],
            wraplength=180
        )
        self.mail_loading_label.pack(pady=15)
        
        # 새로고침 버튼 (하단 중앙)
        refresh_btn = ctk.CTkButton(
            right_frame,
            text="🔄 새로고침",
            height=32,
            font=("경기천년제목 Medium", 12),
            fg_color=COLORS["primary_dark"],
            hover_color=COLORS["primary"],
            corner_radius=16,
            command=self.refresh_side_panel
        )
        refresh_btn.pack(pady=(5, 10))
    
    def _open_side_panel_default(self):
        """앱 시작 시 사이드 패널 열기 (창 크기 변경 없이)"""
        self.side_panel.grid(row=1, column=1, rowspan=2, sticky="nsew", padx=(0, 15), pady=(10, 12))
        self.panel_toggle_btn.configure(text="▶")
        self.side_panel_open = True
    
    def toggle_side_panel(self):
        """사이드 패널 열기/닫기 - 창 크기 확장 방식"""
        current_width = self.winfo_width()
        current_height = self.winfo_height()
        
        if self.side_panel_open:
            # 패널 닫기 - 창 크기 줄이기
            self.side_panel.grid_forget()
            self.panel_toggle_btn.configure(text="◀")
            self.side_panel_open = False
            
            # 창 너비 줄이기
            new_width = current_width - self.side_panel_width
            self.geometry(f"{new_width}x{current_height}")
        else:
            # 패널 열기 - 창 크기 늘리기
            new_width = current_width + self.side_panel_width
            self.geometry(f"{new_width}x{current_height}")
            
            # 패널 표시
            self.side_panel.grid(row=1, column=1, rowspan=2, sticky="nsew", padx=(0, 15), pady=(10, 12))
            self.panel_toggle_btn.configure(text="▶")
            self.side_panel_open = True
            
            # 데이터 로드
            self.refresh_side_panel()
    
    def refresh_side_panel(self):
        """사이드 패널 데이터 새로고침"""
        if not GOOGLE_AVAILABLE:
            return
        
        def load_data():
            try:
                auth_manager = get_auth_manager()
                if not auth_manager.is_authenticated():
                    return
                
                # 일정 데이터 로드
                try:
                    calendar = get_calendar_service()
                    events = calendar.get_today_events()
                    self.after(0, lambda: self._update_schedule_panel(events))
                except Exception as e:
                    print(f"[SidePanel] 일정 로드 오류: {e}")
                
                # 메일 데이터 로드
                try:
                    gmail = get_gmail_service()
                    emails = gmail.get_unread_emails(10)
                    self.after(0, lambda: self._update_mail_panel(emails))
                except Exception as e:
                    print(f"[SidePanel] 메일 로드 오류: {e}")
                    
            except Exception as e:
                print(f"[SidePanel] 데이터 로드 오류: {e}")
        
        threading.Thread(target=load_data, daemon=True).start()
    
    def _update_schedule_panel(self, events: list):
        """일정 패널 업데이트"""
        # 기존 내용 삭제
        for widget in self.schedule_frame.winfo_children():
            widget.destroy()
        
        if not events:
            no_event_label = ctk.CTkLabel(
                self.schedule_frame,
                text="📅 오늘 일정이 없습니다.",
                font=("경기천년제목 Medium", 13),
                text_color=COLORS["text_secondary"]
            )
            no_event_label.pack(pady=20)
            return
        
        for event in events:
            time_str = event.get('start', '')
            if 'T' in time_str:
                time_str = time_str.split('T')[1][:5]
            else:
                time_str = "종일"
            
            title = event.get('title', '제목 없음')
            event_id = event.get('id', '')
            
            event_frame = ctk.CTkFrame(
                self.schedule_frame,
                fg_color=COLORS["bg_dark"],
                corner_radius=10,
                cursor="hand2"  # 클릭 가능 표시
            )
            event_frame.pack(fill="x", pady=5)
            
            # 클릭 이벤트 바인딩
            event_frame.bind("<Button-1>", lambda e, eid=event_id: self._open_calendar_event(eid))
            
            time_label = ctk.CTkLabel(
                event_frame,
                text=time_str,
                font=("경기천년제목 Bold", 12),
                text_color=COLORS["primary_light"],
                width=50,
                cursor="hand2"
            )
            time_label.pack(side="left", padx=(10, 5), pady=8)
            time_label.bind("<Button-1>", lambda e, eid=event_id: self._open_calendar_event(eid))
            
            title_label = ctk.CTkLabel(
                event_frame,
                text=title,
                font=("경기천년제목 Medium", 12),
                text_color=COLORS["text_primary"],
                anchor="w",
                cursor="hand2"
            )
            title_label.pack(side="left", padx=5, pady=8, fill="x", expand=True)
            title_label.bind("<Button-1>", lambda e, eid=event_id: self._open_calendar_event(eid))
            
            # 호버 효과
            def on_enter(e, frame=event_frame):
                frame.configure(fg_color=COLORS["primary_dark"])
            def on_leave(e, frame=event_frame):
                frame.configure(fg_color=COLORS["bg_dark"])
            
            event_frame.bind("<Enter>", on_enter)
            event_frame.bind("<Leave>", on_leave)
    
    def _open_calendar_event(self, event_id: str):
        """특정 일정 페이지 열기"""
        if event_id:
            url = f"https://calendar.google.com/calendar/r/eventedit/{event_id}"
            webbrowser.open(url)
        else:
            self.open_google_calendar()
    
    def _update_mail_panel(self, emails: list):
        """메일 패널 업데이트"""
        # 기존 내용 삭제
        for widget in self.mail_frame.winfo_children():
            widget.destroy()
        
        if not emails:
            no_mail_label = ctk.CTkLabel(
                self.mail_frame,
                text="📭 새 메일이 없습니다.",
                font=("경기천년제목 Medium", 13),
                text_color=COLORS["text_secondary"]
            )
            no_mail_label.pack(pady=20)
            return
        
        for email in emails[:5]:  # 최대 5개만 표시
            sender = email.get('from', '').split('<')[0].strip().strip('"').strip("'")
            if not sender:
                sender = email.get('from', '알 수 없음')
            subject = email.get('subject', '제목 없음')
            email_id = email.get('id', '')
            
            if len(subject) > 25:
                subject = subject[:25] + "..."
            
            mail_frame = ctk.CTkFrame(
                self.mail_frame,
                fg_color=COLORS["bg_dark"],
                corner_radius=10,
                cursor="hand2"  # 클릭 가능 표시
            )
            mail_frame.pack(fill="x", pady=5)
            
            # 클릭 이벤트 바인딩
            mail_frame.bind("<Button-1>", lambda e, mid=email_id: self._open_email(mid))
            
            sender_label = ctk.CTkLabel(
                mail_frame,
                text=f"✉️ {sender}",
                font=("경기천년제목 Medium", 11),
                text_color=COLORS["primary_light"],
                anchor="w",
                cursor="hand2"
            )
            sender_label.pack(anchor="w", padx=10, pady=(8, 2))
            sender_label.bind("<Button-1>", lambda e, mid=email_id: self._open_email(mid))
            
            subject_label = ctk.CTkLabel(
                mail_frame,
                text=subject,
                font=("경기천년제목 Medium", 12),
                text_color=COLORS["text_primary"],
                anchor="w",
                cursor="hand2"
            )
            subject_label.pack(anchor="w", padx=10, pady=(2, 8))
            subject_label.bind("<Button-1>", lambda e, mid=email_id: self._open_email(mid))
            
            # 호버 효과
            def on_enter(e, frame=mail_frame):
                frame.configure(fg_color=COLORS["primary_dark"])
            def on_leave(e, frame=mail_frame):
                frame.configure(fg_color=COLORS["bg_dark"])
            
            mail_frame.bind("<Enter>", on_enter)
            mail_frame.bind("<Leave>", on_leave)
    
    def _open_email(self, email_id: str):
        """특정 메일 페이지 열기"""
        if email_id:
            url = f"https://mail.google.com/mail/u/0/#inbox/{email_id}"
            webbrowser.open(url)
        else:
            self.open_gmail()
    
    def _fade_in(self, alpha):
        """페이드인 애니메이션"""
        if alpha < 1.0:
            alpha += 0.05  # 0.05씩 증가
            self.attributes('-alpha', alpha)
            self.after(20, lambda: self._fade_in(alpha))  # 20ms 간격
        else:
            self.attributes('-alpha', 1.0)
    
    def add_message(self, message: str, is_user: bool = True, streaming: bool = False):
        """채팅에 메시지 추가 (스트리밍 타이핑 효과 지원)"""
        # AI 응답이고 streaming=True면 타이핑 효과 적용
        use_streaming = streaming and not is_user
        
        msg_widget = ChatMessage(
            self.chat_frame, 
            message, 
            is_user,
            streaming=use_streaming,
            on_update=self._scroll_to_bottom
        )
        msg_widget.pack(fill="x", pady=2)
        
        # 스크롤 맨 아래로
        self._scroll_to_bottom()
        
        return msg_widget
    
    def _scroll_to_bottom(self):
        """채팅 스크롤을 맨 아래로 이동"""
        self.update_idletasks()
        self.chat_frame._parent_canvas.yview_moveto(1.0)
    
    def start_services_async(self):
        """백그라운드에서 서비스 시작"""
        def start():
            # NLU 서비스 시작
            nlu_ok = self.service_manager.start_service("NLU", 8002, "backend/nlu")
            
            if nlu_ok:
                self.services_ready = True
                self.after(0, lambda: self.status_label.configure(
                    text="●",
                    text_color=COLORS["success"]
                ))
            else:
                self.after(0, lambda: self.status_label.configure(
                    text="●",
                    text_color=COLORS["error"]
                ))
        
        thread = threading.Thread(target=start, daemon=True)
        thread.start()
    
    def on_send(self, event=None):
        """메시지 전송"""
        message = self.input_entry.get().strip()
        if not message:
            return
        
        # 입력 초기화
        self.input_entry.delete(0, "end")
        
        # 사용자 메시지 표시
        self.add_message(message, is_user=True)
        
        # 백그라운드에서 응답 처리
        threading.Thread(target=self.process_message, args=(message,), daemon=True).start()
    
    def process_message(self, message: str):
        """메시지 처리 (LLM Agent 사용)"""
        try:
            # LLM Agent 사용 (GPT가 직접 의도 파악 및 함수 호출)
            if LLM_AGENT_AVAILABLE:
                agent = get_agent()
                reply = agent.process(message)
                # 스트리밍 타이핑 효과로 응답 표시
                self.after(0, lambda r=reply: self.add_message(r, is_user=False, streaming=True))
                # 음성 모드일 때 응답을 읽어줌
                if self.voice_mode:
                    self.after(100, lambda r=reply: self.speak_text(r))
                return
            
            # 폴백: 기존 NLU 방식
            if not self.services_ready:
                self.after(0, lambda: self.add_message(
                    "⏳ 서비스가 아직 준비 중입니다. 잠시만 기다려주세요.",
                    is_user=False
                ))
                return
            
            # NLU API 호출
            response = requests.post(
                "http://127.0.0.1:8002/analyze",
                json={"text": message},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                intent = result.get("intent", {})
                entities = result.get("entities", [])
                
                # 응답 생성
                intent_name = intent.get("name", "unknown")
                confidence = intent.get("confidence", 0)
                
                reply = self.generate_response(intent_name, entities, message)
                # 스트리밍 타이핑 효과로 응답 표시
                self.after(0, lambda r=reply: self.add_message(r, is_user=False, streaming=True))
            else:
                self.after(0, lambda: self.add_message(
                    "❌ 서버 응답 오류가 발생했습니다.",
                    is_user=False
                ))
                
        except requests.exceptions.ConnectionError:
            self.after(0, lambda: self.add_message(
                "❌ 서버에 연결할 수 없습니다. 서비스를 확인해주세요.",
                is_user=False
            ))
        except Exception as e:
            self.after(0, lambda: self.add_message(
                f"❌ 오류가 발생했습니다: {str(e)}",
                is_user=False
            ))
    
    def generate_response(self, intent: str, entities: list, original_message: str) -> str:
        """의도에 따른 응답 생성"""
        
        # Google API 사용 가능 여부 확인
        if GOOGLE_AVAILABLE:
            if intent == "schedule_check":
                return self.handle_schedule_check(entities)
            elif intent == "schedule_add":
                return self.handle_schedule_add(entities, original_message)
            elif intent == "email_check":
                return self.handle_email_check()
        
        # LLM 대화 처리
        if intent == "llm_chat" or intent == "web_search":
            return self.handle_llm_chat(original_message)
        
        # 기본 응답
        responses = {
            "schedule_check": "📅 일정을 확인하려면 Google 인증이 필요합니다.\n\n메뉴에서 'Google 로그인'을 클릭해주세요.",
            "schedule_add": f"📅 일정을 추가하겠습니다.\n\n감지된 정보:\n{self.format_entities(entities)}\n\n(Google 인증 필요)",
            "schedule_delete": "📅 일정을 삭제하겠습니다.\n\n(Google 인증 필요)",
            "email_check": "📧 이메일을 확인하려면 Google 인증이 필요합니다.\n\n메뉴에서 'Google 로그인'을 클릭해주세요.",
            "email_send": "📧 이메일을 전송하겠습니다.\n\n(Google 인증 필요)",
            "web_search": f"🔍 '{original_message}'에 대해 검색하고 있습니다...\n\n(검색 API 연동 필요)",
            "weather_check": "🌤️ 날씨를 확인하고 있습니다...\n\n(날씨 API 연동 필요)",
            "llm_chat": f"💬 질문을 이해했습니다.\n\n'{original_message}'\n\n(LLM API 연동 필요 - OpenAI API 키 설정 시 실제 응답 가능)",
        }
        
        return responses.get(intent, f"🤔 '{intent}' 의도로 분류되었습니다.\n\n아직 해당 기능이 구현되지 않았습니다.")
    
    def handle_schedule_check(self, entities: list) -> str:
        """일정 확인 처리"""
        try:
            calendar = get_calendar_service()
            
            # 날짜 엔티티 확인
            date_entity = next((e['value'] for e in entities if e['type'] == 'date'), None)
            
            if date_entity and '내일' in date_entity:
                events = calendar.get_tomorrow_events()
                date_str = "내일"
            else:
                events = calendar.get_today_events()
                date_str = "오늘"
            
            if not events:
                return f"📅 {date_str} 일정이 없습니다."
            
            response = f"📅 {date_str} 일정 ({len(events)}개):\n\n"
            for event in events:
                time_str = event['start']
                if 'T' in time_str:
                    time_str = time_str.split('T')[1][:5]
                response += f"• {time_str} - {event['title']}\n"
                if event['location']:
                    response += f"  📍 {event['location']}\n"
            
            return response
            
        except Exception as e:
            return f"📅 일정 확인 중 오류가 발생했습니다.\n\n오류: {str(e)}\n\n'Google 로그인' 버튼을 클릭해주세요."
    
    def handle_schedule_add(self, entities: list, original_message: str) -> str:
        """일정 추가 처리"""
        try:
            # 엔티티에서 정보 추출
            date_entity = next((e['value'] for e in entities if e['type'] == 'date'), None)
            time_entity = next((e['value'] for e in entities if e['type'] == 'time'), None)
            
            # 간단한 파싱 (실제로는 더 정교한 파싱 필요)
            now = datetime.now()
            
            if date_entity and '내일' in date_entity:
                event_date = now + timedelta(days=1)
            else:
                event_date = now
            
            # 시간 파싱
            hour = 9  # 기본값
            if time_entity:
                if '오후' in time_entity:
                    hour = 12
                import re
                numbers = re.findall(r'\d+', time_entity)
                if numbers:
                    hour = int(numbers[0])
                    if '오후' in time_entity and hour < 12:
                        hour += 12
            
            start_time = event_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            # 제목 추출 (간단한 방식)
            title = "새 일정"
            if '회의' in original_message:
                title = "회의"
            elif '미팅' in original_message:
                title = "미팅"
            elif '약속' in original_message:
                title = "약속"
            
            calendar = get_calendar_service()
            result = calendar.create_event(title, start_time)
            
            if result:
                return f"✅ 일정이 추가되었습니다!\n\n📅 {title}\n🕐 {start_time.strftime('%Y-%m-%d %H:%M')}"
            else:
                return "❌ 일정 추가에 실패했습니다. Google 로그인을 확인해주세요."
            
        except Exception as e:
            return f"📅 일정 추가 중 오류가 발생했습니다.\n\n오류: {str(e)}"
    
    def handle_email_check(self) -> str:
        """이메일 확인 처리"""
        try:
            gmail = get_gmail_service()
            emails = gmail.get_unread_emails(5)
            
            if not emails:
                return "📧 읽지 않은 이메일이 없습니다."
            
            response = f"📧 읽지 않은 이메일 ({len(emails)}개):\n\n"
            for email in emails:
                sender = email['from'].split('<')[0].strip()
                response += f"• {sender}\n  {email['subject'][:40]}...\n\n"
            
            return response
            
        except Exception as e:
            return f"📧 이메일 확인 중 오류가 발생했습니다.\n\n오류: {str(e)}\n\n'Google 로그인' 버튼을 클릭해주세요."
    
    def handle_llm_chat(self, message: str) -> str:
        """LLM 대화 처리"""
        if not OPENAI_AVAILABLE:
            return "💬 OpenAI 라이브러리가 설치되지 않았습니다."
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "여기에-API-키-입력":
            return "💬 OpenAI API 키가 설정되지 않았습니다.\n\nconfigs/.env 파일에 OPENAI_API_KEY를 입력해주세요."
        
        try:
            client = OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4"),
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 SION이라는 친절한 개인 비서 AI입니다. 한국어로 간결하고 도움이 되는 답변을 해주세요."
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return f"💬 {response.choices[0].message.content}"
            
        except Exception as e:
            error_msg = str(e)
            if "api_key" in error_msg.lower():
                return "❌ OpenAI API 키가 유효하지 않습니다.\n\nconfigs/.env 파일을 확인해주세요."
            return f"❌ GPT 응답 오류: {error_msg}"
    
    def format_entities(self, entities: list) -> str:
        """엔티티 포맷팅"""
        if not entities:
            return "- 감지된 정보 없음"
        
        lines = []
        for e in entities:
            lines.append(f"- {e['type']}: {e['value']}")
        return "\n".join(lines)
    
    def toggle_recording(self):
        """음성 녹음 토글"""
        if not AUDIO_AVAILABLE:
            self.add_message("❌ 음성 기능을 사용할 수 없습니다.\n\npip install sounddevice soundfile numpy", is_user=False)
            return
        
        if self.is_recording:
            # 녹음 중지 (녹음은 자동으로 종료됨)
            return
        
        # 녹음 시작
        self.is_recording = True
        self.mic_button.configure(
            text="●",
            fg_color=COLORS["accent"],
            hover_color=COLORS["error"]
        )
        self.add_message("🎤 녹음 중... (최대 10초, 말씀이 끝나면 자동 종료)", is_user=False)
        
        # 백그라운드에서 녹음
        threading.Thread(target=self.record_audio, daemon=True).start()
    
    def record_audio(self):
        """음성 녹음 및 처리"""
        try:
            # 녹음 설정
            sample_rate = 16000
            max_duration = 10  # 최대 10초
            silence_threshold = 0.01
            silence_duration = 1.5  # 1.5초 무음 시 종료
            
            frames = []
            silence_frames = 0
            max_silence_frames = int(silence_duration * sample_rate / 1024)
            max_frames = int(max_duration * sample_rate / 1024)
            voice_detected = False
            
            def audio_callback(indata, frame_count, time_info, status):
                nonlocal silence_frames, voice_detected
                frames.append(indata.copy())
                
                # 에너지 계산
                energy = np.abs(indata).mean()
                
                if energy > silence_threshold:
                    voice_detected = True
                    silence_frames = 0
                elif voice_detected:
                    silence_frames += 1
            
            # 녹음 시작
            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype='float32',
                blocksize=1024,
                callback=audio_callback
            ):
                while len(frames) < max_frames and self.is_recording:
                    sd.sleep(100)  # 100ms 대기
                    
                    # 음성 감지 후 무음이 지속되면 종료
                    if voice_detected and silence_frames >= max_silence_frames:
                        break
            
            # 녹음 종료
            self.is_recording = False
            self.after(0, lambda: self.mic_button.configure(
                text="🎤",
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_light"]
            ))
            
            if not frames:
                self.after(0, lambda: self.add_message("❌ 녹음된 오디오가 없습니다.", is_user=False))
                return
            
            # 오디오 데이터 결합
            audio_data = np.concatenate(frames, axis=0)
            duration = len(audio_data) / sample_rate
            
            self.after(0, lambda: self.add_message(f"🎤 녹음 완료 ({duration:.1f}초) - 음성 인식 중...", is_user=False))
            
            # WAV 바이트로 변환
            buffer = io.BytesIO()
            sf.write(buffer, audio_data, sample_rate, format='WAV')
            buffer.seek(0)
            audio_bytes = buffer.read()
            
            # ASR 서비스 호출
            self.transcribe_audio(audio_bytes)
            
        except Exception as e:
            self.is_recording = False
            self.after(0, lambda: self.mic_button.configure(
                text="🎤",
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_light"]
            ))
            self.after(0, lambda: self.add_message(f"❌ 녹음 오류: {str(e)}", is_user=False))
    
    def transcribe_audio(self, audio_bytes: bytes):
        """음성을 텍스트로 변환"""
        try:
            # ASR 서비스 호출 시도
            try:
                files = {'file': ('audio.wav', audio_bytes, 'audio/wav')}
                response = requests.post(
                    "http://127.0.0.1:8001/transcribe",
                    files=files,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result.get("text", "").strip()
                    
                    if text:
                        self.after(0, lambda t=text: self.add_message(f"🗣️ \"{t}\"", is_user=True))
                        # 텍스트로 에이전트 호출
                        threading.Thread(target=self.process_message, args=(text,), daemon=True).start()
                    else:
                        self.after(0, lambda: self.add_message("❌ 음성을 인식하지 못했습니다.", is_user=False))
                    return
            except requests.exceptions.ConnectionError:
                pass  # ASR 서비스가 실행 중이지 않으면 OpenAI Whisper API 사용
            
            # 폴백: OpenAI Whisper API 사용
            if OPENAI_AVAILABLE:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key and api_key != "여기에-API-키-입력":
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key)
                    
                    # 바이트를 파일 객체로 변환
                    audio_file = io.BytesIO(audio_bytes)
                    audio_file.name = "audio.wav"
                    
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="ko"
                    )
                    
                    text = transcript.text.strip()
                    
                    if text:
                        self.after(0, lambda t=text: self.add_message(f"🗣️ \"{t}\"", is_user=True))
                        threading.Thread(target=self.process_message, args=(text,), daemon=True).start()
                    else:
                        self.after(0, lambda: self.add_message("❌ 음성을 인식하지 못했습니다.", is_user=False))
                    return
            
            self.after(0, lambda: self.add_message(
                "❌ 음성 인식 서비스를 사용할 수 없습니다.\n\n"
                "- ASR 서비스(8001)가 실행 중이거나\n"
                "- OpenAI API 키가 설정되어 있어야 합니다.",
                is_user=False
            ))
            
        except Exception as e:
            self.after(0, lambda: self.add_message(f"❌ 음성 인식 오류: {str(e)}", is_user=False))
    
    def toggle_voice_mode(self):
        """음성 모드 토글"""
        if not TTS_AVAILABLE:
            self.add_message("❌ TTS 기능을 사용할 수 없습니다.\n\npip install edge-tts pygame", is_user=False)
            return
        
        self.voice_mode = not self.voice_mode
        
        if self.voice_mode:
            self.voice_btn.configure(
                text="🔔",
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_light"],
                border_color=COLORS["primary_light"]
            )
            self.add_message("🔊 음성 모드가 활성화되었습니다.\n응답을 음성으로 읽어드립니다.", is_user=False)
        else:
            self.voice_btn.configure(
                text="🔊",
                fg_color=COLORS["bg_card"],
                hover_color=COLORS["primary_dark"],
                border_color=COLORS["primary"]
            )
            self.add_message("🔇 음성 모드가 비활성화되었습니다.", is_user=False)
    
    def speak_text(self, text: str):
        """텍스트를 음성으로 읽기 (edge-tts 사용)"""
        if not TTS_AVAILABLE or not self.voice_mode or self.is_speaking:
            return
        
        def do_speak():
            self.is_speaking = True
            try:
                # 이모지 및 특수문자 제거 (TTS가 읽기 어려운 것들)
                import re
                clean_text = re.sub(r'[📅📆🕐✅❌🔗💬📧🎤🔴🔊🔇•]', '', text)
                clean_text = re.sub(r'\n+', '. ', clean_text)
                clean_text = clean_text.strip()
                
                if not clean_text:
                    return
                
                # edge-tts로 음성 생성 (한국어 여성 음성)
                async def generate_speech():
                    communicate = edge_tts.Communicate(clean_text, "ko-KR-SunHiNeural")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                        tmp_path = tmp_file.name
                    await communicate.save(tmp_path)
                    return tmp_path
                
                # 비동기 실행
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio_path = loop.run_until_complete(generate_speech())
                loop.close()
                
                # pygame으로 재생
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.play()
                
                # 재생 완료 대기
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                
                # 임시 파일 삭제
                try:
                    os.remove(audio_path)
                except:
                    pass
                    
            except Exception as e:
                print(f"[TTS] 음성 출력 오류: {e}")
            finally:
                self.is_speaking = False
        
        threading.Thread(target=do_speak, daemon=True).start()
    
    def try_auto_login(self):
        """앱 시작 시 자동 로그인 시도"""
        if not GOOGLE_AVAILABLE:
            return
        
        def do_auto_login():
            try:
                auth_manager = get_auth_manager()
                
                # 이미 유효한 토큰이 있는지 확인
                if auth_manager.is_authenticated():
                    # 이미 로그인됨
                    self.after(0, self._on_auto_login_success)
                    return
                
                # 토큰이 만료되었지만 갱신 가능한 경우
                if auth_manager.creds and auth_manager.creds.expired and auth_manager.creds.refresh_token:
                    self.after(0, lambda: self.add_message(
                        "🔄 Google 인증 갱신 중...",
                        is_user=False
                    ))
                    if auth_manager.authenticate():
                        self.after(0, self._on_auto_login_success)
                        return
                
                # 자동 로그인 실패 - 수동 로그인 안내
                tip = ""
                if HOTKEY_AVAILABLE:
                    tip = f"\n\n💡 Tip: {self.hotkey_combo.upper()} 키로 어디서든 호출 가능!"
                self.after(0, lambda: self.add_message(
                    "👋 안녕하세요! SION입니다.\n\n"
                    "Google 로그인이 필요합니다.\n"
                    f"상단의 'Google 로그인' 버튼을 클릭해주세요.{tip}",
                    is_user=False
                ))
                
            except Exception as e:
                print(f"[AutoLogin] 오류: {e}")
                tip = ""
                if HOTKEY_AVAILABLE:
                    tip = f"\n\n💡 Tip: {self.hotkey_combo.upper()} 키로 어디서든 호출 가능!"
                self.after(0, lambda: self.add_message(
                    "👋 안녕하세요! SION입니다.\n\n"
                    f"Google 로그인을 위해 상단 버튼을 클릭해주세요.{tip}",
                    is_user=False
                ))
        
        threading.Thread(target=do_auto_login, daemon=True).start()
    
    def _on_auto_login_success(self):
        """자동 로그인 성공 시 처리"""
        tip_msg = ""
        if HOTKEY_AVAILABLE:
            tip_msg = f"\n\n💡 Tip: {self.hotkey_combo.upper()} 키로 어디서든 호출 가능!"
        self.add_message(f"✅ Google 자동 로그인 성공!{tip_msg}", is_user=False)
        
        # 버튼 상태 업데이트
        self.google_btn.configure(
            text="✅",
            fg_color=COLORS["primary"],
            border_color=COLORS["primary_light"]
        )
        
        # 캘린더/메일 바로가기 버튼 표시
        self.show_google_shortcuts()
        
        # 사이드 패널 자동 새로고침
        if self.side_panel_open:
            self.after(300, self.refresh_side_panel)
        
        # 오늘의 브리핑 자동 실행
        self.after(500, self.show_daily_briefing)
        
        # 메일/스케줄 모니터링 시작
        self.after(3000, self.start_monitoring)
    
    def google_login(self):
        """Google 로그인"""
        if not GOOGLE_AVAILABLE:
            self.add_message("❌ Google 서비스를 사용할 수 없습니다.", is_user=False)
            return
        
        def do_login():
            try:
                auth_manager = get_auth_manager()
                
                self.after(0, lambda: self.add_message(
                    "🔗 Google 로그인 중...\n브라우저에서 로그인을 완료해주세요.",
                    is_user=False
                ))
                
                if auth_manager.authenticate():
                    self.after(0, lambda: self.add_message(
                        "✅ Google 로그인 성공!",
                        is_user=False
                    ))
                    self.after(0, lambda: self.google_btn.configure(
                        text="✅",
                        fg_color=COLORS["primary"],
                        border_color=COLORS["primary_light"]
                    ))
                    # 캘린더/메일 바로가기 버튼 표시
                    self.after(0, self.show_google_shortcuts)
                    # 로그인 성공 후 오늘의 브리핑 자동 실행
                    self.after(500, self.show_daily_briefing)
                    # 메일/스케줄 모니터링 시작
                    self.after(3000, self.start_monitoring)
                else:
                    self.after(0, lambda: self.add_message(
                        "❌ Google 로그인에 실패했습니다.",
                        is_user=False
                    ))
            except Exception as e:
                self.after(0, lambda: self.add_message(
                    f"❌ 로그인 오류: {str(e)}",
                    is_user=False
                ))
        
        threading.Thread(target=do_login, daemon=True).start()
    
    def show_google_shortcuts(self):
        """Google 캘린더/메일 바로가기 버튼 표시"""
        self.calendar_btn.grid(row=0, column=4, padx=2, pady=15, sticky="e")
        self.mail_btn.grid(row=0, column=5, padx=2, pady=15, sticky="e")
        # 상태 표시를 오른쪽으로 이동
        self.status_label.grid(row=0, column=3, padx=4, pady=15, sticky="e")
    
    def open_google_calendar(self):
        """Google 캘린더 웹페이지 열기"""
        import webbrowser
        webbrowser.open("https://calendar.google.com")
    
    def open_gmail(self):
        """Gmail 웹페이지 열기"""
        import webbrowser
        webbrowser.open("https://mail.google.com")
    
    # ========== 알림 모니터링 ==========
    
    def start_monitoring(self):
        """메일/스케줄 모니터링 시작"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        # 모니터링 시작 시간 기록 (이 시간 이후 메일만 알림)
        self.monitoring_start_time = datetime.now()
        print(f"[Monitor] 모니터링 시작 - 기준 시간: {self.monitoring_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 주기적 체크 시작
        self.after(self.email_check_interval, self._check_new_emails)
        self.after(self.schedule_check_interval, self._check_upcoming_events)
    
    def _check_new_emails(self):
        """새 메일 확인 (주기적 실행) - 시간 기반 필터링"""
        if not self.monitoring_active:
            return
        
        def check():
            try:
                gmail = get_gmail_service()
                emails = gmail.get_unread_emails(10)
                
                for email in emails:
                    email_id = email.get('id', '')
                    
                    # 이미 알림한 메일은 스킵
                    if email_id in self.notified_email_ids:
                        continue
                    
                    # 메일 날짜 확인 - 모니터링 시작 이후 메일만
                    email_date_str = email.get('date', '')
                    if email_date_str and self.monitoring_start_time:
                        try:
                            # 메일 날짜 파싱 (예: "Sat, 14 Dec 2024 15:30:00 +0900")
                            from email.utils import parsedate_to_datetime
                            email_datetime = parsedate_to_datetime(email_date_str)
                            # timezone aware -> naive 변환
                            if email_datetime.tzinfo:
                                email_datetime = email_datetime.replace(tzinfo=None)
                            
                            # 모니터링 시작 시간 이전 메일은 스킵
                            if email_datetime < self.monitoring_start_time:
                                continue
                            
                            # 새 메일 발견!
                            self.notified_email_ids.add(email_id)
                            self.after(0, lambda e=email: self._notify_new_email(e))
                            break  # 한 번에 하나씩 알림
                            
                        except Exception as parse_error:
                            print(f"[Monitor] 메일 날짜 파싱 오류: {parse_error}")
                            continue
                
            except Exception as e:
                print(f"[Monitor] 메일 체크 오류: {e}")
        
        threading.Thread(target=check, daemon=True).start()
        
        # 다음 체크 예약
        self.after(self.email_check_interval, self._check_new_emails)
    
    def _notify_new_email(self, email: dict):
        """새 메일 알림"""
        # 알림 설정 확인
        if not self.settings.get("notification", "email_enabled", default=True):
            return
        
        if self.waiting_for_response:
            return  # 이미 응답 대기 중이면 스킵
        
        # 사이드 패널 업데이트
        if self.side_panel_open:
            self.refresh_side_panel()
        
        sender = email.get('from', '알 수 없음').split('<')[0].strip().strip('"').strip("'")
        subject = email.get('subject', '제목 없음')
        email_id = email.get('id', '')
        
        # 음성 응답 대기 여부 확인
        voice_response_enabled = self.settings.get("voice", "email_voice_response", default=True)
        
        # 알림 메시지 표시
        notify_msg = f"📬 새 메일이 도착했습니다!\n\n"
        notify_msg += f"보낸 사람: {sender}\n"
        notify_msg += f"제목: {subject}"
        
        if voice_response_enabled:
            notify_msg += "\n\n🎤 '읽어줘', '열어줘', '괜찮아' 중 하나로 응답해주세요."
        
        self.add_message(notify_msg, is_user=False, streaming=True)
        
        # TTS로 알림 (설정 확인)
        email_voice_read = self.settings.get("voice", "email_voice_read", default=True)
        if TTS_AVAILABLE and email_voice_read and self.voice_mode:
            tts_msg = f"메일이 도착했습니다. {sender}님으로부터."
            if voice_response_enabled:
                tts_msg += " 메일을 읽어드릴까요?"
            self.speak_text(tts_msg)
        
        # 음성 응답 대기 (설정된 경우만)
        if voice_response_enabled:
            self.waiting_for_response = True
            self.pending_notification = {
                'type': 'email',
                'data': email,
                'sender': sender,
                'subject': subject,
                'email_id': email_id
            }
            
            # 음성 인식 시작 (TTS 완료 후)
            self.after(3000, self._start_notification_listening)
    
    def _start_notification_listening(self):
        """알림 응답을 위한 음성 인식 시작"""
        if not self.waiting_for_response:
            return
        
        if AUDIO_AVAILABLE:
            # 자동으로 음성 녹음 시작
            self.after(500, self._record_notification_response)
    
    def _record_notification_response(self):
        """알림 응답 녹음"""
        if not self.waiting_for_response:
            return
        
        def record_and_process():
            try:
                import sounddevice as sd
                import soundfile as sf
                import numpy as np
                import tempfile
                
                # 5초간 녹음
                duration = 5
                sample_rate = 16000
                
                print("[Notification] 응답 녹음 시작...")
                self.after(0, lambda: self.add_message("🎤 듣고 있습니다...", is_user=False))
                
                audio_data = sd.rec(
                    int(duration * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype=np.float32
                )
                sd.wait()
                
                # 임시 파일로 저장
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                    temp_path = f.name
                    sf.write(temp_path, audio_data, sample_rate)
                
                # STT 변환
                text = self._transcribe_audio(temp_path)
                os.remove(temp_path)
                
                if text:
                    self.after(0, lambda: self._handle_notification_response(text))
                else:
                    self.after(0, self._end_notification_waiting)
                    
            except Exception as e:
                print(f"[Notification] 녹음 오류: {e}")
                self.after(0, self._end_notification_waiting)
        
        threading.Thread(target=record_and_process, daemon=True).start()
    
    def _transcribe_audio(self, audio_path: str) -> str:
        """오디오를 텍스트로 변환"""
        try:
            from openai import OpenAI
            client = OpenAI()
            
            with open(audio_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ko"
                )
            return transcript.text.strip()
        except Exception as e:
            print(f"[STT] 변환 오류: {e}")
            return ""
    
    def _handle_notification_response(self, response: str):
        """알림 응답 처리"""
        if not self.pending_notification:
            self._end_notification_waiting()
            return
        
        response_lower = response.lower()
        notif_type = self.pending_notification['type']
        
        self.add_message(f"🗣️ \"{response}\"", is_user=True)
        
        if notif_type == 'email':
            if any(word in response_lower for word in ['읽어', '읽어줘', '알려줘', '뭐야']):
                # 메일 내용 읽기
                sender = self.pending_notification['sender']
                subject = self.pending_notification['subject']
                reply = f"📧 {sender}님이 보낸 메일입니다.\n제목: {subject}"
                self.add_message(reply, is_user=False, streaming=True)
                if TTS_AVAILABLE:
                    self.speak_text(f"{sender}님이 보낸 메일입니다. 제목은 {subject}입니다.")
                    
            elif any(word in response_lower for word in ['열어', '열어줘', '보여줘', '확인']):
                # 메일 열기
                import webbrowser
                email_id = self.pending_notification.get('email_id', '')
                if email_id:
                    webbrowser.open(f"https://mail.google.com/mail/u/0/#inbox/{email_id}")
                else:
                    webbrowser.open("https://mail.google.com")
                reply = "📧 메일을 열었습니다."
                self.add_message(reply, is_user=False)
                if TTS_AVAILABLE:
                    self.speak_text("메일을 열었습니다.")
                    
            else:
                # 거절 또는 기타
                reply = "알겠습니다."
                self.add_message(reply, is_user=False)
                if TTS_AVAILABLE:
                    self.speak_text("알겠습니다.")
        
        elif notif_type == 'schedule':
            if any(word in response_lower for word in ['열어', '열어줘', '보여줘', '확인']):
                # 캘린더 열기
                import webbrowser
                webbrowser.open("https://calendar.google.com")
                reply = "📅 캘린더를 열었습니다."
                self.add_message(reply, is_user=False)
                if TTS_AVAILABLE:
                    self.speak_text("캘린더를 열었습니다.")
            else:
                # 확인 또는 거절
                reply = "알겠습니다."
                self.add_message(reply, is_user=False)
                if TTS_AVAILABLE:
                    self.speak_text("알겠습니다.")
        
        self._end_notification_waiting()
    
    def _end_notification_waiting(self):
        """알림 응답 대기 종료"""
        self.waiting_for_response = False
        self.pending_notification = None
    
    def _check_upcoming_events(self):
        """다가오는 일정 확인 (주기적 실행)"""
        if not self.monitoring_active:
            return
        
        def check():
            try:
                calendar = get_calendar_service()
                events = calendar.get_today_events()
                
                now = datetime.now()
                
                for event in events:
                    event_id = event.get('id', '')
                    if event_id in self.notified_events:
                        continue
                    
                    # 시작 시간 파싱
                    start_str = event.get('start', '')
                    if 'T' not in start_str:
                        continue  # 종일 일정은 스킵
                    
                    try:
                        # ISO 형식 파싱
                        start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                        # 로컬 시간으로 변환
                        if start_time.tzinfo:
                            start_time = start_time.replace(tzinfo=None)
                        
                        # 10분 전인지 확인
                        time_diff = (start_time - now).total_seconds() / 60
                        
                        if 0 < time_diff <= 10:
                            # 10분 이내에 시작하는 일정
                            self.notified_events.add(event_id)
                            self.after(0, lambda e=event, mins=int(time_diff): self._notify_upcoming_event(e, mins))
                            break
                            
                    except Exception as e:
                        print(f"[Monitor] 일정 시간 파싱 오류: {e}")
                
            except Exception as e:
                print(f"[Monitor] 일정 체크 오류: {e}")
        
        threading.Thread(target=check, daemon=True).start()
        
        # 다음 체크 예약
        self.after(self.schedule_check_interval, self._check_upcoming_events)
    
    def _notify_upcoming_event(self, event: dict, minutes_left: int):
        """다가오는 일정 알림"""
        # 알림 설정 확인
        if not self.settings.get("notification", "schedule_enabled", default=True):
            return
        
        if self.waiting_for_response:
            return
        
        title = event.get('title', '일정')
        
        # 음성 응답 대기 여부
        voice_response_enabled = self.settings.get("voice", "email_voice_response", default=True)  # 같은 설정 사용
        
        # 알림 메시지 표시
        notify_msg = f"⏰ 일정 알림!\n\n"
        notify_msg += f"'{title}' 시간이 {minutes_left}분 남았습니다."
        
        if voice_response_enabled:
            notify_msg += "\n\n🎤 '알았어', '열어줘' 중 하나로 응답해주세요."
        
        self.add_message(notify_msg, is_user=False, streaming=True)
        
        # TTS로 알림 (설정 확인)
        schedule_voice_read = self.settings.get("voice", "schedule_voice_read", default=True)
        if TTS_AVAILABLE and schedule_voice_read and self.voice_mode:
            tts_msg = f"{title} 일정이 {minutes_left}분 남았습니다."
            self.speak_text(tts_msg)
        
        # 음성 응답 대기 (설정된 경우만)
        if voice_response_enabled:
            self.waiting_for_response = True
            self.pending_notification = {
                'type': 'schedule',
                'data': event,
                'title': title
            }
            
            # 음성 인식 시작
            self.after(3000, self._start_notification_listening)
    
    # ========== 일일 브리핑 ==========
    
    def show_daily_briefing(self):
        """오늘의 일정과 메일을 자동으로 정리해서 보여줌"""
        def fetch_briefing():
            try:
                from datetime import datetime
                now = datetime.now()
                weekdays = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
                today_str = f"{now.year}년 {now.month}월 {now.day}일 ({weekdays[now.weekday()]})"
                
                briefing = f"📋 오늘의 브리핑 - {today_str}\n"
                briefing += "─" * 30 + "\n\n"
                
                # 오늘 일정 조회
                try:
                    calendar = get_calendar_service()
                    events = calendar.get_today_events()
                    
                    if events:
                        briefing += f"📅 오늘 일정 ({len(events)}개)\n\n"
                        for event in events:
                            time_str = event['start']
                            if 'T' in time_str:
                                time_str = time_str.split('T')[1][:5]
                            else:
                                time_str = "종일"
                            briefing += f"  • {time_str} - {event['title']}\n"
                    else:
                        briefing += "📅 오늘 예정된 일정이 없습니다.\n"
                except Exception as e:
                    briefing += f"📅 일정 조회 실패: {str(e)}\n"
                
                briefing += "\n"
                
                # 오늘 온 메일 조회
                try:
                    gmail = get_gmail_service()
                    emails = gmail.get_unread_emails(20)  # 더 많이 조회해서 필터링
                    
                    # 오늘 날짜 메일만 필터링
                    today_str = now.strftime('%d %b %Y')  # "13 Dec 2025" 형식
                    today_emails = []
                    
                    for email in emails:
                        email_date = email.get('date', '')
                        # 날짜 문자열에서 오늘 날짜 확인
                        if today_str in email_date or now.strftime('%Y-%m-%d') in email_date:
                            today_emails.append(email)
                    
                    if today_emails:
                        briefing += f"📧 오늘 온 메일 ({len(today_emails)}개)\n\n"
                        briefing += "─" * 30 + "\n\n"
                        for i, email in enumerate(today_emails):
                            # 보낸 사람 정리
                            sender = email['from'].split('<')[0].strip()
                            if not sender:
                                sender = email['from']
                            sender = sender.strip('"').strip("'")
                            
                            # 제목
                            subject = email['subject']
                            
                            # 내용 미리보기
                            snippet = email.get('snippet', '')[:80]
                            if len(email.get('snippet', '')) > 80:
                                snippet += "..."
                            
                            # 행간 + 구분선
                            briefing += f"📌 {subject} - {sender}\n\n"
                            if snippet:
                                briefing += f"{snippet}\n"
                            briefing += "\n"
                            briefing += "─" * 30 + "\n\n"
                    else:
                        briefing += "📧 오늘 온 새 메일이 없습니다.\n"
                except Exception as e:
                    briefing += f"📧 메일 조회 실패: {str(e)}\n"
                
                briefing += "\n" + "─" * 30
                briefing += "\n💬 무엇을 도와드릴까요?"
                
                # 스트리밍 타이핑 효과로 브리핑 표시
                self.after(0, lambda: self.add_message(briefing, is_user=False, streaming=True))
                
                # 음성 모드면 브리핑 읽어주기
                if self.voice_mode:
                    self.after(100, lambda: self.speak_text(briefing))
                
            except Exception as e:
                self.after(0, lambda: self.add_message(
                    f"❌ 브리핑 생성 오류: {str(e)}",
                    is_user=False
                ))
        
        self.add_message("📋 오늘의 브리핑을 준비하고 있습니다...", is_user=False)
        threading.Thread(target=fetch_briefing, daemon=True).start()
    
    def register_hotkey(self):
        """글로벌 핫키 등록"""
        if not HOTKEY_AVAILABLE:
            print("[Hotkey] keyboard 모듈이 설치되지 않았습니다.")
            return
        
        try:
            keyboard.add_hotkey(self.hotkey_combo, self.on_hotkey_pressed)
            self.hotkey_registered = True
            print(f"[Hotkey] 글로벌 핫키 등록됨: {self.hotkey_combo.upper()}")
        except Exception as e:
            print(f"[Hotkey] 핫키 등록 실패: {e}")
    
    def unregister_hotkey(self):
        """글로벌 핫키 해제"""
        if not HOTKEY_AVAILABLE or not self.hotkey_registered:
            return
        
        try:
            keyboard.remove_hotkey(self.hotkey_combo)
            self.hotkey_registered = False
            print("[Hotkey] 글로벌 핫키 해제됨")
        except Exception as e:
            print(f"[Hotkey] 핫키 해제 실패: {e}")
    
    def on_hotkey_pressed(self):
        """핫키가 눌렸을 때 호출"""
        # GUI 스레드에서 실행되도록 after 사용
        self.after(0, self.activate_and_listen)
    
    def activate_and_listen(self):
        """앱 활성화 및 음성 입력 시작"""
        try:
            # 창 복원 및 최상위로
            self.deiconify()  # 최소화 해제
            self.lift()  # 최상위로
            self.focus_force()  # 포커스 강제
            
            # Windows에서 창을 확실히 활성화
            self.attributes('-topmost', True)
            self.after(100, lambda: self.attributes('-topmost', False))
            
            # 음성 입력 시작 (약간의 딜레이 후)
            if AUDIO_AVAILABLE and not self.is_recording:
                self.after(300, self.toggle_recording)
                
        except Exception as e:
            print(f"[Hotkey] 활성화 오류: {e}")
    
    def on_closing(self):
        """앱 종료 시"""
        # 설정 저장
        self._save_window_geometry()
        
        # 핫키 해제
        self.unregister_hotkey()
        self.service_manager.stop_all()
        self.destroy()
    
    def open_settings(self):
        """설정 화면 열기"""
        SettingsDialog(self, self.settings)


class SettingsDialog(ctk.CTkToplevel):
    """설정 다이얼로그"""
    
    def __init__(self, parent, settings: SettingsManager):
        super().__init__(parent)
        
        self.settings = settings
        self.parent = parent
        
        # 창 설정
        self.title("설정")
        self.geometry("450x530")
        self.resizable(False, False)
        
        # 모달 창 설정
        self.transient(parent)
        self.grab_set()
        
        # 배경색
        self.configure(fg_color=COLORS["bg_dark"])
        
        # 중앙 배치
        self.center_on_parent()
        
        # UI 구성
        self._setup_ui()
        
        # ESC로 닫기
        self.bind("<Escape>", lambda e: self.destroy())
    
    def center_on_parent(self):
        """부모 창 중앙에 배치"""
        self.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        
        w = 450
        h = 530
        x = parent_x + (parent_w - w) // 2
        y = parent_y + (parent_h - h) // 2
        
        self.geometry(f"{w}x{h}+{x}+{y}")
    
    def _setup_ui(self):
        """설정 UI 구성"""
        # 메인 컨테이너
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 타이틀
        title = ctk.CTkLabel(
            main_frame,
            text="⚙ 설정",
            font=("경기천년제목 Bold", 24),
            text_color=COLORS["primary_light"]
        )
        title.pack(pady=(0, 20))
        
        # === 음성 설정 섹션 ===
        voice_section = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_card"], corner_radius=15)
        voice_section.pack(fill="x", pady=10)
        
        voice_title = ctk.CTkLabel(
            voice_section,
            text="🔊 음성 설정",
            font=("경기천년제목 Bold", 16),
            text_color=COLORS["text_primary"]
        )
        voice_title.pack(anchor="w", padx=15, pady=(15, 10))
        
        # TTS 활성화
        self.tts_enabled_var = ctk.BooleanVar(value=self.settings.get("voice", "tts_enabled", default=True))
        tts_switch = ctk.CTkSwitch(
            voice_section,
            text="음성 출력 (TTS) 활성화",
            font=("경기천년제목 Medium", 14),
            variable=self.tts_enabled_var,
            onvalue=True,
            offvalue=False,
            progress_color=COLORS["primary"],
            command=self._on_setting_changed
        )
        tts_switch.pack(anchor="w", padx=20, pady=5)
        
        # 메일 음성 읽기
        self.email_voice_var = ctk.BooleanVar(value=self.settings.get("voice", "email_voice_read", default=True))
        email_voice_switch = ctk.CTkSwitch(
            voice_section,
            text="메일 도착 시 음성으로 알림",
            font=("경기천년제목 Medium", 14),
            variable=self.email_voice_var,
            onvalue=True,
            offvalue=False,
            progress_color=COLORS["primary"],
            command=self._on_setting_changed
        )
        email_voice_switch.pack(anchor="w", padx=20, pady=5)
        
        # 메일 응답 대기
        self.email_response_var = ctk.BooleanVar(value=self.settings.get("voice", "email_voice_response", default=True))
        email_response_switch = ctk.CTkSwitch(
            voice_section,
            text="메일 알림 후 음성 응답 대기",
            font=("경기천년제목 Medium", 14),
            variable=self.email_response_var,
            onvalue=True,
            offvalue=False,
            progress_color=COLORS["primary"],
            command=self._on_setting_changed
        )
        email_response_switch.pack(anchor="w", padx=20, pady=5)
        
        # 일정 음성 알림
        self.schedule_voice_var = ctk.BooleanVar(value=self.settings.get("voice", "schedule_voice_read", default=True))
        schedule_voice_switch = ctk.CTkSwitch(
            voice_section,
            text="일정 알림 시 음성으로 알림",
            font=("경기천년제목 Medium", 14),
            variable=self.schedule_voice_var,
            onvalue=True,
            offvalue=False,
            progress_color=COLORS["primary"],
            command=self._on_setting_changed
        )
        schedule_voice_switch.pack(anchor="w", padx=20, pady=(5, 10))
        
        # 음량 조절
        volume_frame = ctk.CTkFrame(voice_section, fg_color="transparent")
        volume_frame.pack(fill="x", padx=20, pady=(5, 15))
        
        volume_label = ctk.CTkLabel(
            volume_frame,
            text="음량:",
            font=("경기천년제목 Medium", 14),
            text_color=COLORS["text_primary"]
        )
        volume_label.pack(side="left", padx=(0, 10))
        
        current_volume = self.settings.get("voice", "volume", default=0.8)
        self.volume_var = ctk.DoubleVar(value=current_volume)
        
        volume_slider = ctk.CTkSlider(
            volume_frame,
            from_=0.0,
            to=1.0,
            variable=self.volume_var,
            progress_color=COLORS["primary"],
            button_color=COLORS["primary_light"],
            button_hover_color=COLORS["accent"],
            command=self._on_volume_changed
        )
        volume_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.volume_value_label = ctk.CTkLabel(
            volume_frame,
            text=f"{int(current_volume * 100)}%",
            font=("경기천년제목 Medium", 12),
            text_color=COLORS["text_secondary"],
            width=40
        )
        self.volume_value_label.pack(side="left")
        
        # === 알림 설정 섹션 ===
        notify_section = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_card"], corner_radius=15)
        notify_section.pack(fill="x", pady=10)
        
        notify_title = ctk.CTkLabel(
            notify_section,
            text="🔔 알림 설정",
            font=("경기천년제목 Bold", 16),
            text_color=COLORS["text_primary"]
        )
        notify_title.pack(anchor="w", padx=15, pady=(15, 10))
        
        # 메일 알림
        self.email_notify_var = ctk.BooleanVar(value=self.settings.get("notification", "email_enabled", default=True))
        email_notify_switch = ctk.CTkSwitch(
            notify_section,
            text="새 메일 알림",
            font=("경기천년제목 Medium", 14),
            variable=self.email_notify_var,
            onvalue=True,
            offvalue=False,
            progress_color=COLORS["primary"],
            command=self._on_setting_changed
        )
        email_notify_switch.pack(anchor="w", padx=20, pady=5)
        
        # 일정 알림
        self.schedule_notify_var = ctk.BooleanVar(value=self.settings.get("notification", "schedule_enabled", default=True))
        schedule_notify_switch = ctk.CTkSwitch(
            notify_section,
            text="일정 알림",
            font=("경기천년제목 Medium", 14),
            variable=self.schedule_notify_var,
            onvalue=True,
            offvalue=False,
            progress_color=COLORS["primary"],
            command=self._on_setting_changed
        )
        schedule_notify_switch.pack(anchor="w", padx=20, pady=(5, 15))
        
        # 저장 버튼
        save_btn = ctk.CTkButton(
            main_frame,
            text="💾 저장",
            height=45,
            font=("경기천년제목 Bold", 16),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_dark"],
            corner_radius=22,
            command=self._save_and_close
        )
        save_btn.pack(pady=20)
    
    def _on_setting_changed(self):
        """설정 변경 시"""
        pass  # 실시간 업데이트 없이 저장 버튼 클릭 시 저장
    
    def _on_volume_changed(self, value):
        """음량 변경 시"""
        self.volume_value_label.configure(text=f"{int(value * 100)}%")
        # 실시간 음량 적용
        if TTS_AVAILABLE:
            pygame.mixer.music.set_volume(value)
    
    def _save_and_close(self):
        """설정 저장 후 닫기"""
        # 설정 저장
        self.settings.set("voice", "tts_enabled", self.tts_enabled_var.get())
        self.settings.set("voice", "email_voice_read", self.email_voice_var.get())
        self.settings.set("voice", "email_voice_response", self.email_response_var.get())
        self.settings.set("voice", "schedule_voice_read", self.schedule_voice_var.get())
        self.settings.set("voice", "volume", self.volume_var.get())
        self.settings.set("notification", "email_enabled", self.email_notify_var.get())
        self.settings.set("notification", "schedule_enabled", self.schedule_notify_var.get())
        
        self.settings.save()
        
        # 부모 앱에 설정 적용
        self.parent.voice_mode = self.tts_enabled_var.get()
        self.parent._update_voice_button_text()
        
        # 닫기
        self.destroy()


def main():
    """메인 함수"""
    app = SionApp()
    app.mainloop()


if __name__ == "__main__":
    main()

