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

# 프로젝트 루트 경로 (먼저 정의)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
        
        # 윈도우 설정 (6:4 비율 = 900x600)
        self.title("SION Personal Assistant")
        self.geometry("900x600")
        self.minsize(600, 400)
        
        # 화면 중앙에 배치
        self.center_window(900, 600)
        
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
        
        # 음성 모드 (TTS 활성화 여부)
        self.voice_mode = False
        self.is_speaking = False
        
        # 글로벌 핫키 설정
        self.hotkey_registered = False
        self.hotkey_combo = "ctrl+shift+."  # 기본 단축키
        
        # UI 구성
        self.setup_ui()
        
        # 스플래시 스크린 표시
        self.show_splash()
        
        # 서비스 시작 (백그라운드)
        self.start_services_async()
        
        # 글로벌 핫키 등록
        self.register_hotkey()
        
        # 종료 시 서비스 정리
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
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
        # 메인 컨테이너
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # === 헤더 ===
        header_frame = ctk.CTkFrame(
            self, 
            fg_color=COLORS["bg_main"], 
            height=70,
            corner_radius=0
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
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
            text="음성",
            height=36,
            font=("경기천년제목 Medium", 14),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["primary_dark"],
            corner_radius=18,
            border_width=1,
            border_color=COLORS["primary"],
            command=self.toggle_voice_mode
        )
        self.voice_btn.grid(row=0, column=1, padx=8, pady=15, sticky="e")
        
        # Google 로그인 버튼
        self.google_btn = ctk.CTkButton(
            header_frame,
            text="Google",
            height=36,
            font=("경기천년제목 Medium", 14),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["primary_dark"],
            corner_radius=18,
            border_width=1,
            border_color="#666666",
            command=self.google_login
        )
        self.google_btn.grid(row=0, column=2, padx=8, pady=15, sticky="e")
        
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
            font=("경기천년제목 Medium", 14),
            text_color="#FFA500"  # 주황색 (로딩 중)
        )
        self.status_label.grid(row=0, column=3, padx=15, pady=18, sticky="e")
        
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
                text="음성 ON",
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_light"],
                border_color=COLORS["primary_light"]
            )
            self.add_message("🔊 음성 모드가 활성화되었습니다.\n응답을 음성으로 읽어드립니다.", is_user=False)
        else:
            self.voice_btn.configure(
                text="음성",
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
            text="✓ 연결됨",
            fg_color=COLORS["primary"],
            border_color=COLORS["primary_light"]
        )
        
        # 캘린더/메일 바로가기 버튼 표시
        self.show_google_shortcuts()
        
        # 오늘의 브리핑 자동 실행
        self.after(500, self.show_daily_briefing)
    
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
                        text="✓ 연결됨",
                        fg_color=COLORS["primary"],
                        border_color=COLORS["primary_light"]
                    ))
                    # 캘린더/메일 바로가기 버튼 표시
                    self.after(0, self.show_google_shortcuts)
                    # 로그인 성공 후 오늘의 브리핑 자동 실행
                    self.after(500, self.show_daily_briefing)
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
        self.calendar_btn.grid(row=0, column=3, padx=4, pady=15, sticky="e")
        self.mail_btn.grid(row=0, column=4, padx=4, pady=15, sticky="e")
        # 상태 표시를 오른쪽으로 이동
        self.status_label.grid(row=0, column=5, padx=15, pady=15, sticky="e")
    
    def open_google_calendar(self):
        """Google 캘린더 웹페이지 열기"""
        import webbrowser
        webbrowser.open("https://calendar.google.com")
    
    def open_gmail(self):
        """Gmail 웹페이지 열기"""
        import webbrowser
        webbrowser.open("https://mail.google.com")
    
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
        # 핫키 해제
        self.unregister_hotkey()
        self.service_manager.stop_all()
        self.destroy()


def main():
    """메인 함수"""
    app = SionApp()
    app.mainloop()


if __name__ == "__main__":
    main()

