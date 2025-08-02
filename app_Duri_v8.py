import streamlit as st
import sys
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 업데이트된 모듈들 import
from response_formatter_v4 import StudentFriendlyFormatter
from agent_evaluator_v2 import SimplifiedRAGEvaluator

# =============================================================================
# 상수 정의
# =============================================================================
class Config:
    """애플리케이션 설정 상수"""
    TITLE_MAX_LENGTH = 30
    MAX_RECENT_QUESTIONS = 5
    QUESTION_ANCHOR_OFFSET = 80
    MAX_DISPLAY_PROBLEMS = 2
    SIDEBAR_QUESTION_PREVIEW_LENGTH = 22
    
    COLORS = {
        'background': '#f7f6f3',
        'text_primary': '#37352f',
        'text_secondary': '#787774',
        'border': '#e9e9e7',
        'accent': '#2383e2',
        'surface': '#fafafa',
        'info_bg': '#f1f3f4'
    }

# =============================================================================
# CSS 스타일 모듈
# =============================================================================
class StyleManager:
    """CSS 스타일 관리 클래스"""
    
    @staticmethod
    def load_custom_styles():
        """커스텀 CSS 스타일을 로드합니다."""
        colors = Config.COLORS
        st.markdown(f"""
        <style>
            /* 기본 스타일 */
            .stChatMessage {{ font-size: 16px; }}
            
            /* AI 메시지 컨테이너 */
            .ai-message-container {{
                background: white;
                border: 1px solid {colors['border']};
                border-radius: 8px;
                overflow: hidden;
                margin: 16px 0;
            }}
            
            .ai-header {{
                background: {colors['background']};
                padding: 16px 20px;
                border-bottom: 1px solid {colors['border']};
                font-weight: 600;
                color: {colors['text_primary']};
                font-size: 16px;
            }}
            
            .ai-body {{
                padding: 24px;
                color: {colors['text_primary']};
                line-height: 1.7;
                font-size: 16px;
            }}
            
            /* 섹션 공통 스타일 */
            .content-section {{
                padding: 0 24px 24px 24px;
            }}
            
            .content-section h6 {{
                color: {colors['text_primary']};
                margin-bottom: 16px;
                font-size: 16px;
                font-weight: 600;
            }}
            
            /* 참고 자료 링크 */
            .reference-link {{
                color: {colors['accent']};
                text-decoration: none;
                display: block;
                padding: 8px 0;
                font-size: 15px;
            }}
            
            .reference-link:hover {{
                text-decoration: underline;
            }}
            
            /* 연습 문제 스타일 */
            .problem-item {{
                margin-bottom: 20px;
                padding: 0;
            }}
            
            .problem-header {{
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 12px;
            }}
            
            .problem-type-badge {{
                display: inline-block;
                background: {colors['accent']};
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
            }}
            
            .problem-number {{
                font-weight: 600;
                color: {colors['text_primary']};
            }}
            
            .problem-text {{
                color: {colors['text_primary']};
                margin-bottom: 12px;
                line-height: 1.6;
            }}
            
            .problem-choices {{
                margin-top: 12px;
            }}
            
            .problem-choice {{
                padding: 4px 0 4px 16px;
                color: {colors['text_secondary']};
                line-height: 1.5;
            }}
            
            /* 사이드바 스타일 */
            section[data-testid="stSidebar"] {{
                background: {colors['surface']};
                border-left: 1px solid {colors['border']};
            }}
            
            section[data-testid="stSidebar"] .stButton > button {{
                background-color: {colors['background']};
                border: 1px solid {colors['border']};
                color: {colors['text_primary']};
                font-weight: 500;
                transition: all 0.2s ease;
            }}
            
            section[data-testid="stSidebar"] .stButton > button:hover {{
                background-color: {colors['border']};
                border-color: {colors['accent']};
            }}
            
            /* 빈 상태 스타일 */
            .empty-history {{
                text-align: center;
                padding: 20px;
                color: {colors['text_secondary']};
                font-style: italic;
                background: {colors['background']};
                border-radius: 8px;
                border: 1px dashed {colors['border']};
            }}
            
            .empty-history .empty-icon {{
                font-size: 24px;
                margin-bottom: 8px;
                opacity: 0.5;
            }}
            
            /* 앵커 스타일 */
            .question-anchor {{
                padding-top: {Config.QUESTION_ANCHOR_OFFSET}px;
                margin-top: -{Config.QUESTION_ANCHOR_OFFSET}px;
            }}
            
            html {{ scroll-behavior: smooth; }}
            
            /* 입력창 스타일 개선 */
            .stChatInputContainer {{
                border-top: 1px solid {colors['border']};
                padding-top: 1rem;
                background: {colors['surface']};
            }}
            
            /* 이미지 스타일 */
            .problem-image-container {{
                margin: 12px 0;
                text-align: center;
            }}
        </style>
        """, unsafe_allow_html=True)

# =============================================================================
# HTML 생성 모듈
# =============================================================================
class HTMLGenerator:
    """HTML 생성 관련 유틸리티 클래스"""
    
    @staticmethod
    def create_ai_container(title: str, content: str) -> str:
        """AI 메시지 컨테이너 HTML을 생성합니다."""
        return f"""
        <div class="ai-message-container">
            <div class="ai-header">{title}</div>
            <div class="ai-body">{content}</div>
        """
    
    @staticmethod
    def clean_html_tags(text: str) -> str:
        """HTML 태그를 제거하고 텍스트만 반환합니다."""
        return re.sub('<.*?>', '', text) if '<' in text and '>' in text else text
    
    @staticmethod
    def create_problem_type_badge(paper_type: str) -> str:
        """문제 유형 뱃지 HTML을 생성합니다."""
        return f'<span class="problem-type-badge">{paper_type}</span>' if paper_type else ""

# =============================================================================
# 렌더링 모듈
# =============================================================================
class MessageRenderer:
    """메시지 렌더링 클래스"""
    
    def __init__(self, html_generator: HTMLGenerator):
        self.html = html_generator
    
    def render_images(self, images: List[dict]):
        """이미지 섹션을 렌더링합니다."""
        if not images:
            return
        
        st.markdown('<div class="content-section image-section">', unsafe_allow_html=True)
        st.markdown('<h6>🖼️ 관련 이미지</h6>', unsafe_allow_html=True)
        
        for img in images:
            img_data = self._parse_image_data(img)
            if img_data['url']:
                self._display_image(img_data)
            else:
                st.warning(f"이미지 URL이 없습니다: {img_data['description']}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def render_reference_links(self, links: List[dict]):
        """참고 자료 링크를 렌더링합니다."""
        if not links:
            return
        
        st.markdown('<div class="content-section reference-links">', unsafe_allow_html=True)
        st.markdown('<h6>📚 더 알아보기</h6>', unsafe_allow_html=True)
        
        for link in links:
            st.markdown(
                f'<a href="{link["url"]}" class="reference-link" target="_blank">'
                f'{link["title"]}</a>',
                unsafe_allow_html=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def render_problems(self, problems: List[dict]):
        """연습 문제를 렌더링합니다."""
        if not problems:
            return
        
        display_problems = problems[:Config.MAX_DISPLAY_PROBLEMS]
        
        st.markdown('<div class="content-section problems-section">', unsafe_allow_html=True)
        st.markdown('<h6>🎯 연습 문제</h6>', unsafe_allow_html=True)
        
        for i, problem in enumerate(display_problems, 1):
            self._render_single_problem(problem, i)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def render_ai_message(self, message: dict, is_new: bool = False):
        """AI 메시지를 렌더링합니다."""
        # 메인 컨테이너
        title = message.get('title', '두리의 답변')
        content = message['answer']
        st.markdown(self.html.create_ai_container(title, content), unsafe_allow_html=True)
        
        # 각 섹션 렌더링
        self.render_images(message.get("images", []))
        
        links_key = "links" if "links" in message else "related_links"
        self.render_reference_links(message.get(links_key, []))
        
        problems = message.get("problems", [])
        if isinstance(problems, dict):
            problems = problems.get('items', [])
        self.render_problems(problems)
        
        # 컨테이너 닫기
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 평가 결과 (새 메시지일 때만 콘솔 출력)
        if is_new and message.get("evaluation"):
            self._log_evaluation(message["evaluation"])
    
    # Private methods
    def _parse_image_data(self, img) -> dict:
        """이미지 데이터를 파싱합니다."""
        if isinstance(img, dict):
            return {
                'url': img.get('url', ''),
                'description': img.get('description', '이미지'),
                'source': img.get('source', 'unknown')
            }
        return {
            'url': str(img),
            'description': '관련 이미지',
            'source': 'unknown'
        }
    
    def _display_image(self, img_data: dict):
        """이미지를 표시합니다."""
        caption = f"{img_data['description']} (출처: {img_data['source']})"
        try:
            st.image(img_data['url'], caption=caption, width=400)
        except Exception as e:
            st.error(f"이미지를 불러올 수 없습니다: {img_data['description']}")
            print(f"Image loading error: {e}, URL: {img_data['url']}")
    
    def _render_single_problem(self, problem: dict, index: int):
        """단일 문제를 렌더링합니다."""
        # 문제 컨테이너
        st.markdown('<div class="problem-item">', unsafe_allow_html=True)
        
        # 헤더 (문제 번호와 유형)
        type_badge = self.html.create_problem_type_badge(problem.get('paper_type', ''))
        st.markdown(
            f'<div class="problem-header">'
            f'{type_badge}'
            f'<span class="problem-number">문제 {index}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        
        # 문제 텍스트
        question_text = self.html.clean_html_tags(problem.get('question', ''))
        st.markdown(f'<div class="problem-text">{question_text}</div>', unsafe_allow_html=True)
        
        # 문제 이미지
        if problem.get('l_img_url'):
            with st.container():
                st.markdown('<div class="problem-image-container">', unsafe_allow_html=True)
                st.image(problem['l_img_url'], caption="문제 이미지", width=400)
                st.markdown('</div>', unsafe_allow_html=True)
        
        # 선택지
        if problem.get('choices'):
            choices_html = '<div class="problem-choices">'
            for j, choice in enumerate(problem['choices'], 1):
                choices_html += f'<div class="problem-choice">{j}. {choice}</div>'
            choices_html += '</div>'
            st.markdown(choices_html, unsafe_allow_html=True)
        
        # 선택지 이미지
        if problem.get('c_img_url'):
            with st.container():
                st.markdown('<div class="problem-image-container">', unsafe_allow_html=True)
                st.image(problem['c_img_url'], caption="선택지 이미지", width=400)
                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def _log_evaluation(self, evaluation: dict):
        """평가 결과를 콘솔에 출력합니다."""
        print(f"[평가 결과] 정확도: {int(evaluation['retrieval']*100)}%, "
              f"품질: {int(evaluation['generation']*100)}%, "
              f"속도: {evaluation['time']:.1f}s, "
              f"등급: {evaluation['grade']}")

# =============================================================================
# 사이드바 모듈
# =============================================================================
class SidebarManager:
    """사이드바 관리 클래스"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def render(self, messages: List[dict]):
        """사이드바를 렌더링합니다."""
        with st.sidebar:
            st.header("⚙️ 설정")
            st.subheader("📌 최근 대화")
            
            recent_data = self._extract_recent_conversations(messages)
            
            if recent_data:
                self._render_conversation_history(recent_data)
            else:
                self._render_empty_state()
            
            self._render_divider()
            self._render_clear_button()
    
    def _extract_recent_conversations(self, messages: List[dict]) -> List[Tuple]:
        """최근 대화 데이터를 추출합니다."""
        recent_questions = []
        question_indices = []
        recent_answers = []
        
        for idx, msg in enumerate(messages):
            if msg["role"] == "user":
                recent_questions.append(msg["content"])
                question_indices.append(idx // 2)
                
                if idx + 1 < len(messages):
                    recent_answers.append(messages[idx + 1])
                else:
                    recent_answers.append({})
        
        if not recent_questions:
            return []
        
        return list(zip(
            recent_questions[-Config.MAX_RECENT_QUESTIONS:],
            question_indices[-Config.MAX_RECENT_QUESTIONS:],
            recent_answers[-Config.MAX_RECENT_QUESTIONS:]
        ))
    
    def _render_conversation_history(self, recent_data: List[Tuple]):
        """대화 히스토리를 렌더링합니다."""
        for q, q_idx, answer_data in recent_data:
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    self._render_question_link(q, q_idx)
                
                with col2:
                    self._render_download_button(q, q_idx, answer_data)
    
    def _render_question_link(self, question: str, idx: int):
        """질문 링크를 렌더링합니다."""
        display_text = (f"{question[:Config.SIDEBAR_QUESTION_PREVIEW_LENGTH]}..." 
                       if len(question) > Config.SIDEBAR_QUESTION_PREVIEW_LENGTH 
                       else question)
        
        link_html = f"""
        <a href="#question-{idx}" style="
            color: #37352f;
            text-decoration: none;
            display: block;
            padding: 8px 12px;
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            border: 1px solid #e9e9e7;
            border-radius: 6px 0 0 6px;
            font-size: 13px;
            font-weight: 500;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            transition: all 0.3s ease;
        ">
            {display_text}
        </a>
        """
        st.markdown(link_html, unsafe_allow_html=True)
    
    def _render_download_button(self, question: str, idx: int, answer_data: dict):
        """다운로드 버튼을 렌더링합니다."""
        qa_content = self._generate_qa_content(question, answer_data)
        # 더 고유한 key 생성 (타임스탬프와 인덱스 조합)
        import time
        unique_key = f"download_{idx}_{int(time.time() * 1000)}_{hash(question) % 10000}"
        st.download_button(
            label="📥",
            data=qa_content,
            file_name=f"두리_QA_{idx+1}.txt",
            mime="text/plain",
            key=unique_key,
            use_container_width=True
        )
    
    def _render_empty_state(self):
        """빈 상태를 렌더링합니다."""
        st.markdown("""
        <div class="empty-history">
            <div class="empty-icon">💬</div>
            <div>아직 대화가 없습니다</div>
            <div style="font-size: 12px; margin-top: 4px;">질문을 해보세요!</div>
        </div>
        """, unsafe_allow_html=True)
    
    def _render_divider(self):
        """구분선을 렌더링합니다."""
        st.markdown("""
        <div style="margin: 20px 0; border-bottom: 1px solid #e9e9e7; opacity: 0.5;"></div>
        """, unsafe_allow_html=True)
    
    def _render_clear_button(self):
        """대화 초기화 버튼을 렌더링합니다."""
        if st.button("🗑️ 대화 초기화", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    def _generate_qa_content(self, question: str, answer_data: dict) -> str:
        """Q&A 내용을 텍스트로 생성합니다."""
        content = f"""AI 학습 도우미 두리 - Q&A

🌟 질문: {question}

📝 답변:
{answer_data.get('answer', '')}

"""
        
        # 이미지 정보
        images = answer_data.get('images', [])
        if images:
            content += "🖼️ 관련 이미지:\n"
            for i, img in enumerate(images, 1):
                if isinstance(img, dict):
                    content += f"{i}. {img.get('description', '이미지')} "
                    content += f"(출처: {img.get('source', 'unknown')})\n"
                    if img.get('url'):
                        content += f"   URL: {img['url']}\n"
                else:
                    content += f"{i}. URL: {img}\n"
            content += "\n"
        
        # 참고 자료
        links = answer_data.get('links', []) or answer_data.get('related_links', [])
        if links:
            content += "📚 더 알아보기:\n"
            for link in links:
                content += f"• {link.get('title', '')}: {link.get('url', '')}\n"
            content += "\n"
        
        # 연습 문제
        problems = answer_data.get('problems', [])
        if problems:
            content += "🎯 연습 문제:\n"
            for i, problem in enumerate(problems[:2], 1):
                paper_type = problem.get('paper_type', '')
                type_text = f"[{paper_type}]" if paper_type else ""
                content += f"\n문제 {i} {type_text}: {problem.get('question', '')}\n"
                
                if problem.get('choices'):
                    for j, choice in enumerate(problem['choices'], 1):
                        content += f"{j}. {choice}\n"
        
        content += f"\n생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return content

# =============================================================================
# 메시지 처리 모듈
# =============================================================================
class MessageHandler:
    """메시지 처리 클래스"""
    
    @staticmethod
    def create_message_data(response: dict, eval_result: dict, 
                          answer_title: str, answer_text: str) -> dict:
        """메시지 데이터를 생성합니다."""
        return {
            "role": "assistant",
            "title": answer_title,
            "answer": answer_text,
            "images": response.get('images', []),
            "links": response.get('related_links', []),
            "problems": response.get('problems', {}).get('items', []),
            "evaluation": {
                "retrieval": eval_result['scores']['retrieval'],
                "generation": eval_result['scores']['generation'],
                "time": eval_result['execution_time'],
                "grade": eval_result['grade']
            }
        }
    
    @staticmethod
    def generate_answer_title(prompt: str) -> str:
        """답변 제목을 생성합니다."""
        if len(prompt) > Config.TITLE_MAX_LENGTH:
            return f'"{prompt[:Config.TITLE_MAX_LENGTH]}..."에 대한 답변'
        return f'"{prompt}"에 대한 답변'

# =============================================================================
# 애플리케이션 클래스
# =============================================================================
class DuriChatApp:
    """두리 챗봇 애플리케이션 메인 클래스"""
    
    def __init__(self):
        self.config = Config()
        self.style_manager = StyleManager()
        self.html_generator = HTMLGenerator()
        self.message_renderer = MessageRenderer(self.html_generator)
        self.sidebar_manager = SidebarManager(self.config)
        self.message_handler = MessageHandler()
    
    def initialize_session_state(self):
        """세션 상태를 초기화합니다."""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        if "formatter" not in st.session_state:
            st.session_state.formatter = StudentFriendlyFormatter()
        
        if "evaluator" not in st.session_state:
            st.session_state.evaluator = SimplifiedRAGEvaluator()
    
    def setup_page(self):
        """페이지 설정을 구성합니다."""
        st.set_page_config(
            page_title="AI 학습 도우미 두리",
            page_icon="🌟",
            layout="wide"
        )
        self.style_manager.load_custom_styles()
    
    def render_header(self):
        """헤더를 렌더링합니다."""
        st.title("🌟 AI 학습 도우미 두리")
        st.caption("초등학생을 위한 똑똑한 공부 친구")
    
    def render_chat_history(self):
        """채팅 히스토리를 렌더링합니다."""
        for idx, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.markdown(
                        f'<div id="question-{idx//2}" class="question-anchor"></div>', 
                        unsafe_allow_html=True
                    )
                    st.write(message["content"])
                else:
                    self.message_renderer.render_ai_message(message)
    
    def handle_user_input(self):
        """사용자 입력을 처리합니다."""
        if prompt := st.chat_input("질문을 입력하세요. (예: 고조선은 어떻게 만들어졌어?)"):
            # 사용자 메시지 추가
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # 사용자 메시지 표시
            with st.chat_message("user"):
                question_id = (len(st.session_state.messages) - 1) // 2
                st.markdown(
                    f'<div id="question-{question_id}" class="question-anchor"></div>', 
                    unsafe_allow_html=True
                )
                st.write(prompt)
            
            # AI 응답 생성
            self.generate_ai_response(prompt)
    
    def generate_ai_response(self, prompt: str):
        """AI 응답을 생성합니다."""
        with st.chat_message("assistant"):
            # 로딩 메시지 표시
            loading_message = st.empty()
            loading_message.write("두리가 답변을 준비하고 있어요... 🤔")
            
            # 응답 생성 및 평가
            response = st.session_state.formatter.search_and_format(prompt)
            eval_result = st.session_state.evaluator.evaluate_question(prompt)
            
            # 로딩 메시지 제거
            loading_message.empty()
            
            # 메시지 데이터 생성
            answer_title = self.message_handler.generate_answer_title(prompt)
            answer_text = response['main_concept']['explanation']
            
            new_message = self.message_handler.create_message_data(
                response, eval_result, answer_title, answer_text
            )
            
            # 메시지 렌더링 및 저장
            self.message_renderer.render_ai_message(new_message, is_new=True)
            st.session_state.messages.append(new_message)
    
    def run(self):
        """애플리케이션을 실행합니다."""
        self.setup_page()
        self.initialize_session_state()
        self.render_header()
        self.render_chat_history()
        self.handle_user_input()
        self.sidebar_manager.render(st.session_state.messages)

# =============================================================================
# 메인 실행
# =============================================================================
def main():
    """메인 애플리케이션 함수"""
    app = DuriChatApp()
    app.run()

if __name__ == "__main__":
    main()