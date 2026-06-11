import streamlit as st
import pandas as pd
import re
from datetime import datetime
from PIL import Image
import numpy as np
import easyocr
import io

# PDF 처리 라이브러리들
from pdf2image import convert_from_bytes
import PyPDF2  # 텍스트 PDF 고속 추출용 추가

# =========================
# 기존 프로젝트 모듈
# =========================
try:
    from src.engine import LawAnalysisEngine
    from src.config import Config
except ImportError as e:
    st.error(f"필수 모듈 로드 실패: {e}")
    st.stop()

# =========================
# Streamlit 설정
# =========================
st.set_page_config(
    page_title="Legal Toxin Finder",
    layout="wide"
)

# =========================
# Session State 초기화
# =========================
if "history" not in st.session_state:
    st.session_state["history"] = []

if "current_results" not in st.session_state:
    st.session_state["current_results"] = []

if "ocr_text" not in st.session_state:
    st.session_state["ocr_text"] = ""

# =========================
# EasyOCR 로드
# =========================
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['ko', 'en'])

reader = load_ocr()

# =========================
# OCR 텍스트 정제 및 오타 보정 함수
# =========================
def clean_ocr_text(text):
    # 1. 불필요한 공백 및 연속된 줄바꿈 정리
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 2. OCR 인식 오류 방어: '제 1 조', '제l조', '제I조', '제ㅣ조' 등을 '제1조' 형태로 표준화
    # 숫자 사이에 들어간 오타나 공백을 1차적으로 보정합니다.
    text = re.sub(r'제\s*[lIㅣ1]\s*조', '제1조', text) 
    text = re.sub(r'제\s*([0-9]+)\s*조', r'제\1조', text)
    
    return text.strip()

# =========================
# 계약 조항 분리 함수
# =========================
def split_contract_clauses(text):
    """
    계약서를 조항(제X조) 단위로 정교하게 분리
    """
    # 보정된 텍스트를 기반으로 조항 탐지
    pattern = r'(제\s*\d+\s*조[\s\S]*?)(?=제\s*\d+\s*조|$)'
    clauses = re.findall(pattern, text)

    # 조항 인식 실패 시 Fallback (문단 단위 분리)
    if not clauses:
        clauses = [
            p.strip()
            for p in text.split("\n\n")
            if len(p.strip()) > 20
        ]
    return clauses

# =========================
# OCR 함수 (이미지)
# =========================
def extract_text_from_image(image):
    image_np = np.array(image)
    results = reader.readtext(
        image_np,
        detail=0,
        paragraph=True
    )
    text = "\n".join(results)
    return clean_ocr_text(text)

# =========================
# 하이브리드 PDF 텍스트 추출 함수 (최적화)
# =========================
def extract_text_from_pdf(pdf_bytes):
    """
    1차로 디지털 PDF 텍스트 추출을 시도하고, 
    텍스트가 없는 스캔본(이미지) PDF인 경우에만 2차로 무거운 OCR을 가동합니다.
    """
    full_text = ""
    
    # 1단계: PyPDF2를 이용한 고속 텍스트 추출 시도 (디지털 PDF 대응)
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        digital_text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                digital_text += page_text + "\n"
        
        # 의미 있는 수준의 텍스트가 추출되었다면 바로 반환 (OCR 건너뜀)
        if len(digital_text.strip()) > 100:
            return clean_ocr_text(digital_text)
    except Exception as e:
        # 디지털 추출 실패 시 로그만 남기고 OCR 단계로 전환
        pass

    # 2단계: 스캔된 이미지 PDF인 경우 OCR 수행 (기존 로직 유지 및 최적화)
    pages = convert_from_bytes(pdf_bytes, dpi=200) # 속도와 정확도의 균형을 위해 200~300 DPI 설정
    for idx, page in enumerate(pages):
        image_np = np.array(page)
        results = reader.readtext(
            image_np,
            detail=0,
            paragraph=True
        )
        page_text = "\n".join(results)
        full_text += f"\n\n--- {idx+1} 페이지 ---\n"
        full_text += page_text
        
    return clean_ocr_text(full_text)

# =========================
# Sidebar (최근 분석 기록)
# =========================
with st.sidebar:
    st.header("🕒 최근 분석 기록")

    if not st.session_state["history"]:
        st.info("최근 기록이 없습니다.")
    else:
        for idx, item in enumerate(
            reversed(st.session_state["history"])
        ):
            button_label = (
                f"[{item['time']}] "
                f"{item['text'][:15]}..."
            )

            if st.button(
                button_label,
                key=f"hist_{idx}",
                use_container_width=True
            ):
                st.session_state["current_results"] = item["results"]
                st.session_state["ocr_text"] = item["text"]
                st.rerun()

# =========================
# Main Header
# =========================

st.markdown(
    """
    <h1 style='text-align: center; margin-top: -50px; margin-bottom: 30px;'>
        LawCheck
    </h1>
    <h4 style='text-align: center; margin-top: -50px;'>
        법률 약관 rag를 이용한 약관 독소조항 판별 시스템
    </h4>
    """, 
    unsafe_allow_html=True
)

st.warning(
    "⚠️ 본 서비스의 결과는 참고용이며 법적 효력을 가지지 않습니다. "
    "실제 계약 검토는 반드시 법률 전문가와 상담하세요."
)


# =========================
# Layout
# =========================
col1, col2 = st.columns([1, 1])

target_text = ""
run_analysis = False

# =========================
# LEFT (입력 및 업로드)
# =========================
with col1:
    st.subheader("데이터 입력")

    tab1, tab2 = st.tabs([
        "파일 업로드",
        "텍스트 직접 입력"
    ])

    # 1. 파일 업로드 탭
    with tab1:
        uploaded_file = st.file_uploader(
            "PDF 또는 이미지(PNG, JPG, JPEG) 파일",
            type=["pdf", "png", "jpg", "jpeg"],
            key="file_uploader_widget"
        )

        if uploaded_file:
            st.info(f"📁 선택된 파일: {uploaded_file.name}")
            
            file_analyze_btn = st.button(
                "🚀 파일 업로드 후 독소조항 분석",
                type="primary",
                use_container_width=True,
                key="file_analyze_btn"
            )

            if file_analyze_btn:
                with st.spinner("파일에서 글자를 판별 중....."):
                    try:
                        file_ext = uploaded_file.name.split(".")[-1].lower()
                        extracted_text = ""

                        if file_ext in ["png", "jpg", "jpeg"]:
                            image = Image.open(uploaded_file)
                            extracted_text = extract_text_from_image(image)
                        elif file_ext == "pdf":
                            pdf_bytes = uploaded_file.read()
                            extracted_text = extract_text_from_pdf(pdf_bytes)

                        if extracted_text.strip():
                            st.session_state["ocr_text"] = extracted_text
                            target_text = extracted_text
                            run_analysis = True
                        else:
                            st.warning("파일에서 텍스트를 인식하지 못했습니다. 파일 상태를 확인해주세요.")
                    except Exception as e:
                        st.error(f"텍스트 추출 중 오류가 발생했습니다: {e}")

    # 2. 직접 입력 탭
    with tab2:
        input_text = st.text_area(
            "계약 조항 직접 입력",
            value=st.session_state["ocr_text"],
            height=350,
            placeholder="""제1조 계약 해지\n'을'이 계약을 중도 해지할 경우 잔여 기간 이용료 전액을 위약금으로 지급한다.""",
            key="text_input_area"
        )
        
        text_analyze_btn = st.button(
            "🔍 입력한 텍스트 분석 시작",
            type="secondary",
            use_container_width=True,
            key="text_analyze_btn"
        )
        
        if text_analyze_btn and input_text.strip():
            st.session_state["ocr_text"] = input_text
            target_text = input_text
            run_analysis = True

# =========================
# RIGHT (분석 및 결과 출력)
# =========================
with col2:
    st.subheader("📊 분석 결과")

    # -------------------------
    # 통합 분석 실행 파트
    # -------------------------
    if run_analysis and target_text.strip():
        with st.spinner("⚖️ LawCheck가 독소조항을 분석하고 있습니다..."):
            engine = LawAnalysisEngine()

            clauses = split_contract_clauses(target_text)
            analysis_results = []

            for clause in clauses:
                try:
                    result = engine.query(clause)
                    analysis_results.append({
                        "clause": clause,
                        "result": result
                    })
                except Exception as e:
                    analysis_results.append({
                        "clause": clause,
                        "result": {
                            "status": "오류",
                            "reason": str(e),
                            "law": "N/A",
                            "precedent": "N/A",
                            "suggestion": "분석 중 오류가 발생했습니다."
                        }
                    })

            # 변경 포인트: '위험'만 남기지 않고 '모든 결과 리스트'를 세션과 히스토리에 통째로 저장
            st.session_state["current_results"] = analysis_results

            # 히스토리 저장
            st.session_state["history"].append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "text": target_text,
                "results": analysis_results
            })

            if len(st.session_state["history"]) > 10:
                st.session_state["history"].pop(0)

            st.rerun()

    # -------------------------
    # 결과 화면 시각화 출력 파트 (개선 - 위험 조항만 출력)
    # -------------------------
    if st.session_state["current_results"]:
        all_results = st.session_state["current_results"]

        # 1. 상태별 카운팅 상단 대시보드 (기존 유지하되 위험 위주로 모니터링)
        cnt_danger = sum(1 for r in all_results if r["result"].get("status") == "위험")
        cnt_warning = sum(1 for r in all_results if r["result"].get("status") == "주의")
        cnt_safe = sum(1 for r in all_results if r["result"].get("status") == "안전")
        cnt_error = sum(1 for r in all_results if r["result"].get("status") == "오류")

        # 메트릭 컴포넌트: 총 조항 중 위험 조항을 강조하는 형태로 구성
        m1, m2 = st.columns(2)
        m1.metric("🚨 감지된 위험 조항", f"{cnt_danger}개")
        m2.metric("📋 전체 분석 조항", f"{len(all_results)}개")
        
        if cnt_error > 0:
            st.caption(f"ℹ️ 분석 실패(오류) 조항: {cnt_error}개")

        # 위험 조항이 하나도 없을 때의 예외 처리
        if cnt_danger == 0:
            st.success("🎉 분석 결과, 위험 조항이 발견되지 않았습니다!")
        else:
            # 2. 전수조사 리스트 순회 출력 (필터링 적용)
            for idx, item in enumerate(all_results):
                result = item["result"]
                status = result.get("status", "안전")

                # ⭐ [핵심 변경] '위험' 상태가 아니라면 하단 출력 코드를 건너뛰고 다음 조항으로 넘어감
                if status != "위험":
                    continue

                st.markdown("---")
                
                # 상태(위험도)에 따른 카드 스타일 설정 정의 (위험만 남겨두어도 무방하나 유지)
                title_prefix = "🚨 위험 조항"
                bg_color = "#fff3f3"
                border_color = "red"
                text_color = "red"

                st.markdown(f"## {title_prefix} {idx+1}")
                st.markdown("### 📄 분석된 조항 내용")
                st.code(item["clause"], language=None)

                # 유동적인 색상 변경 HTML 적용 카드 박스
                st.markdown(
                    f"""
                    <div style="
                        padding:15px;
                        border-radius:10px;
                        background:{bg_color};
                        border-left:8px solid {border_color};
                        margin-bottom:15px;
                    ">
                    <h4 style="margin:0; color:{text_color};">
                        진단 상태: {status}
                    </h4>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # 위험 조항이므로 무조건 열려있도록 expanded=True 설정
                with st.expander("🧐 상세 분석 이유", expanded=True):
                    st.write(result.get("reason", "분석 내용이 없습니다."))

                with st.expander("📚 근거 법령 및 판례"):
                    st.markdown(f"**법령:** {result.get('law', 'N/A')}")
                    st.markdown(f"**판례:** {result.get('precedent', 'N/A')}")

                with st.expander("💡 독소조항 방어용 수정 제안"):
                    st.info(result.get("suggestion", "수정 제안 사항이 없습니다."))
    else:
        st.info("왼쪽에서 파일을 업로드하여 분석하거나, 텍스트를 입력 후 분석 버튼을 눌러주세요.")


# =========================
# Footer
# =========================
st.caption(f"© 2026 Legal Toxin Finder | {datetime.now().strftime('%Y-%m-%d')}")