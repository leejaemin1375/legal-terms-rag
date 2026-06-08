# projects

legal-rag-project/
├── data/
│   ├── raw/               # 원본 JSON 데이터 저장소 (약관법_통합.json, 위반사례.json)
│   └── processed/         # (선택) 임베딩 후 저장된 데이터나, 전처리가 완료된 캐시 파일
├── src/                   # 실제 로직을 담을 코드 폴더
│   ├── __init__.py        # 파이썬 모듈로 인식하게 함
│   ├── database.py        # Vector DB (ChromaDB) 연결 및 관리 로직
│   ├── ingestion.py       # JSON 로드, Chunk 분할, 벡터 DB 저장 로직
│   ├── retrieval.py       # 검색 로직 (조항 검색, 유사 판례 검색 등)
│   ├── prompts.py         # Few-shot 템플릿, 프롬프트 생성 로직
│   └── engine.py          # RAG 파이프라인(검색 -> 프롬프트 -> 생성) 통합 로직
├── notebooks/             # 프로토타이핑 및 실험용 (기존 .ipynb 파일 이동)
│   └── experiment.ipynb
├── requirements.txt       # 필요한 라이브러리 목록 (langchain, chromadb, openai 등)
├── main.py                # 프로젝트 실행 진입점 (CLI 실행용)
└── .gitignore             # 가상환경(venv), .env, DB 파일 등 git 관리 제외 설정

