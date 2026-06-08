import json
import os

def load_case_data(file_path):
    """지정된 경로에서 JSON 판례 데이터를 로드합니다."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_few_shot_prompt(case_data, target_industry, top_k=2):
    """산업군에 따른 유사 판례를 검색하여 프롬프트 템플릿을 생성합니다."""
    relevant_cases = [c for c in case_data if target_industry in c['industry']][:top_k]
    
    prompt = "다음은 유사한 산업군의 판례 분석 사례입니다. 이를 참고하여 사용자의 질문을 분석하세요.\n\n"
    
    for case in relevant_cases:
        prompt += f"""
                    ### 법리 판단 예시
                    산업군: {case['industry']}
                    쟁점: {case['issue']}
                    검토 대상 조항: "{case['target_term']}"
                    [판단 근거]: {case['judgment']}
                    [참조 법령]: {case['referenced_law']}
                    --------------------------------------------------
                    """
    return prompt