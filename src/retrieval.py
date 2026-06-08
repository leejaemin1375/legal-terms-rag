# 벡터 검색과 산업군 기반 사례 필터링
from src.database import LawVectorDB
from src.prompts import load_case_data

class LegalRetriever:
    def __init__(self):
        self.db = LawVectorDB()
        self.case_data = load_case_data("data/raws/약관법_위반사례.json")

    def retrieve(self, query, industry):
        # 1. 벡터 DB에서 관련 법령 검색
        legal_statutes = self.db.search_laws(query)
        
        # 2. 산업군 기반 위반 사례 검색
        relevant_cases = [c for c in self.case_data if industry in c['industry']][:2]
        
        return legal_statutes, relevant_cases