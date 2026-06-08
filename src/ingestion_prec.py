# src/ingestion_prec.py
import os
import glob
import json
import time
from src.config import Config
from src.database import LawVectorDB

def ingest_prec_data():
    # 1. 기존 프로젝트의 LawVectorDB 엔진 및 Chroma 객체 로드
    engine = LawVectorDB()
    db = engine.db

    # 2. 판례 데이터가 위치한 폴더 경로 지정
    DATA_DIR = "data/판례"  
    
    # 폴더 내의 모든 .json 파일 목록 검색
    json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))

    # 데이터를 한꺼번에 모아서 DB에 저장하기 위한 리스트
    all_docs = []
    all_metadatas = []
    all_ids = []

    print(f"📂 판례 데이터 탐색 시작 (경로: {os.path.abspath(DATA_DIR)})")

    for file_path in json_files:
        file_name = os.path.basename(file_path)
        
        # ⚠️ 판례 파일만 타겟으로 지정합니다.
        if "판례" not in file_name:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                prec_list = json.load(f)
                
            print(f"📖 파일 로드 완료: {file_name} (데이터 수: {len(prec_list)}건)")

            for item in prec_list:
                # 3. HTML 태그 정제 및 검색용 본문(Context) 텍스트 조립
                def clean_html(text):
                    if not text: 
                        return ""
                    return text.replace("<br/>", "\n").replace("<br>", "\n").strip()

                판시사항 = clean_html(item.get('content', {}).get('판시사항', ''))
                판결요지 = clean_html(item.get('content', {}).get('판결요지', ''))
                
                # 💡 들여쓰기 공백이 본문에 섞이지 않도록 정렬 수정
                page_content = (
                    f"사건명: {item.get('metadata', {}).get('사건명', '')}\n"
                    f"사건번호: {item.get('metadata', {}).get('사건번호', '')}\n"
                    f"참조조문: {clean_html(item.get('metadata', {}).get('참조조문', ''))}\n\n"
                    f"[판시사항]\n{판시사항}\n\n"
                    f"[판결요지]\n{판결요지}"
                ).strip()

                # 4. 벡터 DB 필터링용 메타데이터 구성
                metadata = {
                    "source": "국가법령정보공동활용기구",
                    "doc_type": "precedent",  
                    "판례정보일련번호": str(item.get('판례정보일련번호', '')),
                    "사건명": item.get('metadata', {}).get('사건명', ''),
                    "사건번호": item.get('metadata', {}).get('사건번호', ''),
                    "법원명": item.get('metadata', {}).get('법원명', ''),
                    "사건종류명": item.get('metadata', {}).get('사건종류명', ''),
                    "참조조문": clean_html(item.get('metadata', {}).get('참조조문', ''))
                }

                # Chroma DB 내부 고유 ID 설정
                prec_id = item.get('판례정보일련번호')
                if not prec_id:
                    prec_id = f"prec_{file_name}_{len(all_ids)}"
                else:
                    prec_id = f"prec_{prec_id}"

                all_docs.append(page_content)
                all_metadatas.append(metadata)
                all_ids.append(prec_id)

        except Exception as e:
            print(f"❌ 파일 읽기 실패 ({file_name}): {e}")
            continue

    if not all_docs:
        print("📭 적재할 판례 데이터가 없습니다.")
        return

    print(f"\n📊 전처리 완료: 총 {len(all_docs)}건의 판례 조각을 확보했습니다.")

    # 5. 기존 적재 데이터 개수 확인 및 중단 시점 이어쓰기 방어 로직 (버그 수정 완료)
    print(f"🔎 기존 DB와 대조하여 미적재 데이터 필터링 중 (안전 분할 조회)...")
    
    existing_ids = set()
    check_batch_size = 500  # 한 번에 조회할 ID 개수를 500개로 제한하여 쿼리 과부하 방지

    for i in range(0, len(all_ids), check_batch_size):
        batch_to_check = all_ids[i:i + check_batch_size]
        try:
            existing_data = db.get(ids=batch_to_check)
            if existing_data and 'ids' in existing_data:
                existing_ids.update(existing_data['ids'])
        except Exception as e:
            # 최초 적재 시 컬렉션이 비어있어 에러가 날 수 있으므로 예외 처리 후 통과
            break

    remaining_docs = []
    remaining_metadatas = []
    remaining_ids = []

    # DB에 없는 데이터만 남기기
    for doc, meta, p_id in zip(all_docs, all_metadatas, all_ids):
        if p_id not in existing_ids:
            remaining_docs.append(doc)
            remaining_metadatas.append(meta)
            remaining_ids.append(p_id)

    total_count = len(all_docs)
    skip_count = total_count - len(remaining_docs)
    
    print(f"📊 총 판례: {total_count}건 | 기적재 스킵: {skip_count}건 | 신규 적재 대상: {len(remaining_docs)}건")

    if not remaining_docs:
        print("✅ 모든 판례 데이터가 이미 벡터 DB에 저장되어 있어 작업을 종료합니다.")
        return

    print(f"📦 DB 적재 시작 (남은 데이터 수: {len(remaining_docs)})")

    # 6. 30개 단위 배치(Batch) 처리 및 Rate Limit 방어
    batch_size = 30

    for i in range(0, len(remaining_docs), batch_size):
        batch_docs = remaining_docs[i:i + batch_size]
        batch_metadatas = remaining_metadatas[i:i + batch_size]
        batch_ids = remaining_ids[i:i + batch_size]

        end_position = min(i + batch_size, len(remaining_docs))

        print(f"📦 판례 임베딩 빌드 중... ({i} ~ {end_position} / {len(remaining_docs)})")

        # Chroma DB에 텍스트 및 메타데이터 적재
        db.add_texts(
            texts=batch_docs,
            metadatas=batch_metadatas,
            ids=batch_ids
        )

        # OpenAI/기타 임베딩 API 초당 호출 제한(Rate Limit)을 피하기 위한 슬립
        time.sleep(1.5)

    print(f"✨ 판례 데이터 임베딩 및 Chroma 벡터 DB 저장 완료! (이번 회차 총 {len(remaining_docs)}건 신규 저장)")

if __name__ == "__main__":
    ingest_prec_data()