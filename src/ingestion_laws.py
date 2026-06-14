# src/ingestion.py
import os
import glob
import json
from src.config import Config
from src.database import LawVectorDB
import time


def ingest_legal_data():
    # 1. 기존 프로젝트의 LawVectorDB 엔진 및 Chroma 객체 로드
    engine = LawVectorDB()
    db = engine.db

    # 2. 데이터가 위치한 폴더 경로 지정
    # 프로젝트 루트 기준 또는 필요에 맞게 경로를 조정하세요 (예: "data" 또는 ".")
    DATA_DIR = "data/laws"  
    
    # 폴더 내의 모든 .json 파일 목록 검색
    json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))

    # 데이터를 한꺼번에 모아서 DB에 저장하기 위한 리스트
    all_docs = []
    all_metadatas = []
    all_ids = []

    # ID 생성을 위한 전역 카운터
    global_idx = 0

    print(f"📂 데이터 탐색 시작 (경로: {os.path.abspath(DATA_DIR)})")

    for file_path in json_files:
        file_name = os.path.basename(file_path)
        
        # 시스템 구성요소나 사례 파일은 패스하고 법령 데이터만 추출
        if file_name in ["약관법_위반사례.json", "package.json", "tsconfig.json"]:
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 실제 파일 데이터 구조 반영: 최상위 공통 메타데이터 추출
            law_name_ko = data.get('법령명한글', '')
            law_id = data.get('법령ID', '')
            department = data.get('소관부처', '')
            # 약관법_시행령의 경우 '법령시행일자' 키를 사용하는 예외 처리 적용
            enforcement_date = data.get('시행일자') or data.get('법령시행일자', '')
            
            # 조문 리스트 가져오기
            articles = data.get('조문리스트', [])
            
            if not articles:
                # 만약 조문리스트 형식이 아니고 단순 리스트 구조일 경우를 위한 방어 코드
                if isinstance(data, list):
                    articles = data
                    law_name_ko = os.path.splitext(file_name)[0]
                else:
                    continue

            print(f"📖 [{law_name_ko}] 파일 로딩 성공. 조문 개수: {len(articles)}")

            for item in articles:
                article_title = item.get('조문제목', '')
                content = item.get('조문내용', '')
                article_num = item.get('조문번호', '')
                
                # 만약 한글 키값이 없을 경우 영문 키값 맵핑 방어 코드
                if not article_title:
                    article_title = item.get('article_title', '')
                if not content:
                    content = item.get('content', '') or item.get('article_content', '')
                if not article_num:
                    article_num = item.get('article_num', '')

                text = f"법령명한글: {law_name_ko}\n조문제목: {article_title}\n조문내용: {content}"
                all_docs.append(text)


                metadata = {
                    "law_id": str(law_id) if law_id else "N/A",
                    "article_number": str(article_num) if article_num else "N/A",
                    "department": str(department) if department else "N/A",
                    "enforcement_date": str(enforcement_date) if enforcement_date else "N/A",
                    "type": "law"
                }
                all_metadatas.append(metadata)


                safe_file_name = os.path.splitext(file_name)[0]
                all_ids.append(f"law_{safe_file_name}_{global_idx}")
                global_idx += 1

        except Exception as e:
            print(f"❌ {file_name} 파일 처리 중 오류 발생: {e}")

    # 3. 모든 파일 순회가 끝난 후 벡터 DB에 저장
    if all_docs:
        try:
            print(f"\n🚀 총 {len(all_docs)}개의 조문 데이터를 벡터 DB에 빌드 중...")

            # 현재 저장된 문서 수 확인
            current_count = db._collection.count()

            print(f"📊 현재 DB 저장 개수: {current_count}")

            if current_count >= len(all_docs):
                print("✅ 모든 데이터가 이미 저장되어 있습니다.")
                return

            # 저장 안 된 부분만 추출
            remaining_docs = all_docs[current_count:]
            remaining_metadatas = all_metadatas[current_count:]
            remaining_ids = all_ids[current_count:]

            print(f"📦 남은 데이터 수: {len(remaining_docs)}")

            batch_size = 30

            for i in range(0, len(remaining_docs), batch_size):

                batch_docs = remaining_docs[i:i + batch_size]
                batch_metadatas = remaining_metadatas[i:i + batch_size]
                batch_ids = remaining_ids[i:i + batch_size]

                current_position = current_count + i
                end_position = min(
                    current_count + i + batch_size,
                    len(all_docs)
                )

                print(
                    f"📦 데이터 빌드 중... "
                    f"({current_position} ~ {end_position} / {len(all_docs)})"
                )

                db.add_texts(
                    texts=batch_docs,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )

                time.sleep(1.5)

            print(
                f"✨ 임베딩 및 Chroma 벡터 DB 저장 완료! "
                f"(총 {len(all_docs)}개)"
            )

        except Exception as e:
            print(f"❌ 벡터 DB 저장 중 크리티컬 오류 발생: {e}")


if __name__ == "__main__":
    # Config 필수 값 검증 후 실행
    Config.validate()
    ingest_legal_data()