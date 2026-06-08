from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from src.config import Config
import json
import re

class LawAnalysisEngine:
    # 초기화 영역 ---------------------
    def __init__(self):
        # 1. 벡터 DB 로드
        self.embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
        self.db = Chroma(
            persist_directory=Config.VECTOR_DB_PATH, 
            embedding_function=self.embeddings
        )
        
        # 2. LLM 설정
        self.llm = ChatGoogleGenerativeAI(
            model="models/gemini-3.1-flash-lite",
            temperature=0.1
        )
        
        # 3. 프롬프트 템플릿 설정
        self.template = """
        당신은 대한민국 공정거래위원회 출신 법률 전문가입니다.
        반드시 제공된 [검색된 법령 및 판례](Context) 정보에만 기반하여 입력된 계약 조항의 독소 가능성을 분석하세요.
        
        [주의 사항]:
        1. 제공된 [검색된 법령 및 판례]에 명시적으로 언급되지 않은 판례나 법률을 임의로 지어내거나 외부 지식을 활용해 답변하는 것은 절대 금지합니다.
        2. 만약 제공된 정보 내에 참조할 만한 판례가 없다면, "precedent" 항목의 값은 반드시 "N/A" 또는 "관련 판례 없음"으로 작성하세요.
        
        [검색된 법령 및 판례]:
        {context}
        
        [분석할 계약 조항]:
        {question}
        
        반드시 다음 JSON 형식으로 답변하세요:
        {{
            "status": "위험/주의/안전",
            "score": 0~100점,
            "reason": "상세 이유(제공된 근거에 기반하여 기술)",
            "law": "관련 법 조항(Context에 없는 경우 N/A)",
            "precedent": "참조 판례(Context에 없는 경우 반드시 N/A)",
            "suggestion": "수정 제안"
        }}
        """

        self.prompt = PromptTemplate(template=self.template, input_variables=["context", "question"])

        # LCEL(LangChain Expression Language) 체인 구성
        retriever = self.db.as_retriever(search_kwargs={"k": 3})
        self.chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )


    def query(self, text):
        raw_response = self.chain.invoke(text)
        
        try:
            # JSON 문자열만 추출 및 파싱
            clean_json = re.sub(r"```json\n|\n```", "", raw_response)
            result = json.loads(clean_json)
            return result
        except Exception as e:
            return {
                "status": "오류",
                "score": 0,
                "reason": f"응답 분석 실패: {str(e)}",
                "law": "N/A",
                "precedent": "N/A",
                "suggestion": "다시 시도해주세요."
            }