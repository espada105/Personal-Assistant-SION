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
import requests
from datetime import datetime

# 프로젝트 루트 경로
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
        self.title("🤖 SION Personal Assistant")
        self.geometry("500x700")
        self.minsize(400, 500)
        
        # 테마 설정
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # 서비스 매니저
        self.service_manager = ServiceManager()
        self.services_ready = False
        
        # UI 구성
        self.setup_ui()
        
        # 서비스 시작 (백그라운드)
        self.start_services_async()
        
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
            text="🤖 SION", 
            font=("맑은 고딕", 20, "bold"),
            text_color="#4A9FFF"
        )
        title_label.grid(row=0, column=0, padx=20, pady=15)
        
        # 상태 표시
        self.status_label = ctk.CTkLabel(
            header_frame,
            text="⏳ 서비스 시작 중...",
            font=("맑은 고딕", 11),
            text_color="#888888"
        )
        self.status_label.grid(row=0, column=1, padx=20, pady=15, sticky="e")
        
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
        self.add_message("안녕하세요! SION입니다. 무엇을 도와드릴까요?", is_user=False)
        
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
        self.send_button.grid(row=0, column=1, padx=(0, 15), pady=12)
    
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
        """메시지 처리 (NLU API 호출)"""
        try:
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
        responses = {
            "schedule_check": "📅 일정을 확인하고 있습니다...\n\n(일정 API 연동 필요)",
            "schedule_add": f"📅 일정을 추가하겠습니다.\n\n감지된 정보:\n{self.format_entities(entities)}\n\n(캘린더 API 연동 필요)",
            "schedule_delete": "📅 일정을 삭제하겠습니다.\n\n(캘린더 API 연동 필요)",
            "email_check": "📧 이메일을 확인하고 있습니다...\n\n(이메일 API 연동 필요)",
            "email_send": "📧 이메일을 전송하겠습니다.\n\n(이메일 API 연동 필요)",
            "web_search": f"🔍 '{original_message}'에 대해 검색하고 있습니다...\n\n(검색 API 연동 필요)",
            "weather_check": "🌤️ 날씨를 확인하고 있습니다...\n\n(날씨 API 연동 필요)",
            "llm_chat": f"💬 질문을 이해했습니다.\n\n'{original_message}'\n\n(LLM API 연동 필요 - OpenAI API 키 설정 시 실제 응답 가능)",
        }
        
        return responses.get(intent, f"🤔 '{intent}' 의도로 분류되었습니다.\n\n아직 해당 기능이 구현되지 않았습니다.")
    
    def format_entities(self, entities: list) -> str:
        """엔티티 포맷팅"""
        if not entities:
            return "- 감지된 정보 없음"
        
        lines = []
        for e in entities:
            lines.append(f"- {e['type']}: {e['value']}")
        return "\n".join(lines)
    
    def on_closing(self):
        """앱 종료 시"""
        self.service_manager.stop_all()
        self.destroy()


def main():
    """메인 함수"""
    app = SionApp()
    app.mainloop()


if __name__ == "__main__":
    main()

