# src/config.py
import os
from dotenv import load_dotenv

# .env 파일이 존재하는 경로에서 환경 변수를 로드합니다.
load_dotenv()

class Config:
    """프로젝트 전역 설정값 관리"""
    
    # 1. 필수 설정 (API Key 등)
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # 2. 경로 설정
    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "data/processed/chroma_db")
    

    @classmethod
    def validate(cls):
        """필수 설정값들이 정상적으로 로드되었는지 확인"""
        if not cls.GOOGLE_API_KEY:
            raise ValueError("환경변수 오류: GOOGLE_API_KEY가 .env 파일에 설정되지 않았습니다.")
        print("설정 검증 완료: 모든 필수 환경변수가 로드되었습니다.")