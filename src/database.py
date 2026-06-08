import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate
from src.config import Config

class LawVectorDB:
    # 초기화 영역 ---------------------
    def __init__(self, model_name="gemini-3.1-flash-lite", temperature=0.1):
        # 임베딩 모델 선언
        self.embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
        

        # DB 경로를 Config에서 가져오도록 수정
        self.db = Chroma(
            persist_directory=Config.VECTOR_DB_PATH, 
            embedding_function=self.embeddings
        )

        
        # LLM 설정
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        
        # 4. 법률 분석을 위한 전용 프롬프트 구성
        template = """
        당신은 대한민국 약관법 전문 법률 전문가입니다.
        반드시 제공된 [법령 및 판례 정보](Context)에만 기반하여 입력된 계약 조항의 위험성을 분석하세요.
        
        [주의 사항]:
        1. 제공된 [법령 및 판례 정보]에 명시적으로 언급되지 않은 다른 법률(예: 민법, 형법 등)이나 외부 대법원 판례를 임의로 가공하거나 지어내어 답변하는 것은 절대 금지합니다.
        2. 만약 제공된 정보에 분석에 필요한 직접적인 근거가 없다면, '근거 법령' 및 '상세 분석'란에 "제공된 데이터베이스 내에 관련 근거가 존재하지 않습니다."라고 명시하고 임의로 유추하지 마세요.
        
        [법령 및 판례 정보] (Context):
        {context}
        
        [분석할 계약 조항]:
        {question}
        
        반드시 다음 형식을 정밀하게 지켜서 답변하세요:
        1. 상태: (위험/주의/안전 중 택 1)
        2. 위험도 점수: (0~100)
        3. 상세 분석: (제공된 근거에 기반한 이유 설명. 근거가 없다면 데이터베이스 내 정보 부족으로 기재)
        4. 근거 법령: (제공된 Context에 포함된 조항 이름만 기재, 없을 경우 '없음')
        5. 수정 제안: (구체적인 수정 문구, 근거가 없어 수정이 불가능할 경우 '수정 제안 없음')
        """
        self.prompt = PromptTemplate(template=template, input_variables=["context", "question"])



    # RAG 실행 엔진---------------------
    def query(self, text):
        """질문을 받아 DB 검색 후 AI 답변 생성"""

        # 1. 문서 결합 체인 생성 (응답 생성 로직)
        # create_stuff_documents_chain : 찾아낸 문서를 프롬프트의 context 자리에 쑤셔넣고 llm에 전달하여
        # 답변을 받아내는 생성 전용 체인
        combine_docs_chain = create_stuff_documents_chain(
            llm=self.llm, 
            prompt=self.prompt
        )
        
        # 2. 검색기 설정 (유사도 높은 5개 문서)
        retriever = self.db.as_retriever(search_kwargs={"k": 5})
        
        # 3. 전체 RAG 체인 구축 (검색 + 생성 결합)
        rag_chain = create_retrieval_chain(retriever, combine_docs_chain)
        
        # 4. 체인 실행 및 결과 반환
        # 이곳의 text가 question 자리로 들어감
        response = rag_chain.invoke({"input": text})
        
        return response["answer"]
    

    # 단순 검색 엔진---------------------
    def search_laws(self, query, k=5):
        """법령 단순 검색"""
        # Chroma DB에서 유사도가 높은 문서를 k개 찾아 반환합니다.
        docs = self.db.similarity_search(query, k=k)
        return docs