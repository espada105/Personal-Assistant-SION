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


class ChatMessage(ctk.CTkFrame):
    """채팅 메시지 위젯"""
    
    def __init__(self, parent, message: str, is_user: bool = True, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(fg_color="transparent")
        
        # 메시지 정렬
        if is_user:
            anchor = "e"
            bg_color = "#2B5278"  # 사용자: 파란색
            text_color = "white"
            padx = (50, 10)
        else:
            anchor = "w"
            bg_color = "#3D3D3D"  # AI: 회색
            text_color = "white"
            padx = (10, 50)
        
        # 메시지 컨테이너
        msg_frame = ctk.CTkFrame(self, fg_color=bg_color, corner_radius=15)
        msg_frame.pack(anchor=anchor, padx=padx, pady=5)
        
        # 메시지 텍스트
        msg_label = ctk.CTkLabel(
            msg_frame, 
            text=message,
            text_color=text_color,
            wraplength=400,
            justify="left",
            font=("맑은 고딕", 13)
        )
        msg_label.pack(padx=15, pady=10)


class SionApp(ctk.CTk):
    """SION 메인 애플리케이션"""
    
    def __init__(self):
        super().__init__()
        
        # 윈도우 설정
        self.title("SION Personal Assistant")
        self.geometry("500x700")
        self.minsize(400, 500)
        
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
        
        # 서비스 시작 (백그라운드)
        self.start_services_async()
        
        # 글로벌 핫키 등록
        self.register_hotkey()
        
        # 종료 시 서비스 정리
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """UI 구성"""
        # 메인 컨테이너
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # === 헤더 ===
        header_frame = ctk.CTkFrame(self, fg_color="#1E1E1E", height=60)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(1, weight=1)
        
        # 로고/타이틀
        title_label = ctk.CTkLabel(
            header_frame, 
            text="SION", 
            font=("맑은 고딕", 20, "bold"),
            text_color="#4A9FFF"
        )
        title_label.grid(row=0, column=0, padx=20, pady=15)
        
        # 음성 모드 토글 버튼
        self.voice_btn = ctk.CTkButton(
            header_frame,
            text="🔇 음성 OFF",
            width=100,
            height=30,
            font=("맑은 고딕", 11),
            fg_color="#555555",
            hover_color="#666666",
            corner_radius=15,
            command=self.toggle_voice_mode
        )
        self.voice_btn.grid(row=0, column=1, padx=5, pady=15, sticky="e")
        
        # Google 로그인 버튼
        self.google_btn = ctk.CTkButton(
            header_frame,
            text="🔗 Google 로그인",
            width=120,
            height=30,
            font=("맑은 고딕", 11),
            fg_color="#DB4437",
            hover_color="#C53929",
            corner_radius=15,
            command=self.google_login
        )
        self.google_btn.grid(row=0, column=2, padx=5, pady=15, sticky="e")
        
        # 상태 표시
        self.status_label = ctk.CTkLabel(
            header_frame,
            text="⏳ 서비스 시작 중...",
            font=("맑은 고딕", 11),
            text_color="#888888"
        )
        self.status_label.grid(row=0, column=3, padx=10, pady=15, sticky="e")
        
        # === 채팅 영역 ===
        chat_container = ctk.CTkFrame(self, fg_color="#2B2B2B")
        chat_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        chat_container.grid_columnconfigure(0, weight=1)
        chat_container.grid_rowconfigure(0, weight=1)
        
        # 스크롤 가능한 채팅 영역
        self.chat_frame = ctk.CTkScrollableFrame(
            chat_container,
            fg_color="transparent"
        )
        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.chat_frame.grid_columnconfigure(0, weight=1)
        
        # 환영 메시지
        welcome_msg = "안녕하세요! SION입니다. 무엇을 도와드릴까요?"
        if HOTKEY_AVAILABLE:
            welcome_msg += f"\n\n💡 Tip: {self.hotkey_combo.upper()} 키로 어디서든 호출할 수 있어요!"
        self.add_message(welcome_msg, is_user=False)
        
        # === 입력 영역 ===
        input_frame = ctk.CTkFrame(self, fg_color="#1E1E1E", height=70)
        input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        input_frame.grid_columnconfigure(0, weight=1)
        
        # 텍스트 입력
        self.input_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="메시지를 입력하세요...",
            height=45,
            font=("맑은 고딕", 13),
            corner_radius=20
        )
        self.input_entry.grid(row=0, column=0, padx=(15, 10), pady=12, sticky="ew")
        self.input_entry.bind("<Return>", self.on_send)
        
        # 마이크 버튼 (음성 입력)
        self.is_recording = False
        self.mic_button = ctk.CTkButton(
            input_frame,
            text="🎤",
            width=45,
            height=45,
            font=("맑은 고딕", 16),
            corner_radius=22,
            fg_color="#4CAF50" if AUDIO_AVAILABLE else "#888888",
            hover_color="#45a049" if AUDIO_AVAILABLE else "#888888",
            command=self.toggle_recording
        )
        self.mic_button.grid(row=0, column=1, padx=(0, 5), pady=12)
        
        if not AUDIO_AVAILABLE:
            self.mic_button.configure(state="disabled")
        
        # 전송 버튼
        self.send_button = ctk.CTkButton(
            input_frame,
            text="전송",
            width=70,
            height=45,
            font=("맑은 고딕", 13, "bold"),
            corner_radius=20,
            command=self.on_send
        )
        self.send_button.grid(row=0, column=2, padx=(0, 15), pady=12)
    
    def add_message(self, message: str, is_user: bool = True):
        """채팅에 메시지 추가"""
        msg_widget = ChatMessage(self.chat_frame, message, is_user)
        msg_widget.pack(fill="x", pady=2)
        
        # 스크롤 맨 아래로
        self.chat_frame._parent_canvas.yview_moveto(1.0)
    
    def start_services_async(self):
        """백그라운드에서 서비스 시작"""
        def start():
            # NLU 서비스 시작
            nlu_ok = self.service_manager.start_service("NLU", 8002, "backend/nlu")
            
            if nlu_ok:
                self.services_ready = True
                self.after(0, lambda: self.status_label.configure(
                    text="✅ 서비스 준비 완료",
                    text_color="#4CAF50"
                ))
            else:
                self.after(0, lambda: self.status_label.configure(
                    text="❌ 서비스 시작 실패",
                    text_color="#F44336"
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
                self.after(0, lambda r=reply: self.add_message(r, is_user=False))
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
                self.after(0, lambda r=reply: self.add_message(r, is_user=False))
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
            text="🔴",
            fg_color="#F44336",
            hover_color="#D32F2F"
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
                fg_color="#4CAF50",
                hover_color="#45a049"
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
                fg_color="#4CAF50",
                hover_color="#45a049"
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
                text="🔊 음성 ON",
                fg_color="#4CAF50",
                hover_color="#45a049"
            )
            self.add_message("🔊 음성 모드가 활성화되었습니다.\n응답을 음성으로 읽어드립니다.", is_user=False)
        else:
            self.voice_btn.configure(
                text="🔇 음성 OFF",
                fg_color="#555555",
                hover_color="#666666"
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
                        "✅ Google 로그인 성공!\n\n이제 일정과 이메일을 확인할 수 있습니다.",
                        is_user=False
                    ))
                    self.after(0, lambda: self.google_btn.configure(
                        text="✅ 로그인됨",
                        fg_color="#4CAF50"
                    ))
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

