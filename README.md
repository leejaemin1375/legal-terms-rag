# LawCheck (Legal Toxin Finder) ⚖️

법률 약관 RAG(Retrieval-Augmented Generation)를 이용한 계약서 및 약관 내 독소조항 판별 시스템입니다. Streamlit 기반의 웹 인터페이스를 통해 PDF나 이미지 형태의 계약서를 업로드하고, 내부 조항을 분리하여 공정거래법, 약관법 및 관련 판례를 바탕으로 위험 조항을 자동으로 진단합니다.

---

## 1. 프로젝트 구조 (Directory Tree)

```text
legal-rag-project/
├── data/
│   ├── laws/               # 원본 법령 JSON 데이터 (약관법, 공정거래법, 하도급법 및 시행령)
│   ├── 판례/               # 관련 판례 JSON 데이터 (약관, 계약, 임대차 판례)
│   └── processed/         
│       └── chroma_db/      # 기포맷 데이터 임베딩 후 저장된 Vector DB (ChromaDB) 캐시
├── src/                    # 핵심 RAG 파이프라인 및 백엔드 로직
│   ├── __init__.py        
│   ├── config.py           # API Key 및 환경 변수, DB 경로 관리 설정
│   ├── database.py         # Vector DB (ChromaDB) 연결 및 콜렉션 관리 로직
│   ├── ingestion_laws.py   # 법령 JSON 데이터 로드 및 벡터 DB 빌드 스크립트
│   ├── ingestion_prec.py   # 판례 JSON 데이터 로드 및 벡터 DB 빌드 스크립트
│   ├── retrieval.py        # 하이브리드 검색 로직 (조항 검색, 유사 판례 매칭)
│   ├── prompts.py          # Few-shot 템플릿 및 법률 진단 프롬프트 엔지니어링
│   └── engine.py           # RAG 파이프라인 통합 제어 엔진 (검색 -> 프롬프트 합성 -> 생성)
├── requirements.txt        # 프로젝트 실행을 위한 필수 라이브러리 목록
├── app_final.py            # Streamlit 기반 웹 GUI 애플리케이션 (진입점)
└── .gitignore              # 가상환경, .env, DB 로컬 파일 등 Git 제외 설정



# .env 파일 예시
GOOGLE_API_KEY="YOUR_GOOGLE_GEMINI_API_KEY_HERE"


# 필수 패키지 설치
pip install -r requirements.txt

# 웹 애플리케이션 실행
streamlit run app_final.py
