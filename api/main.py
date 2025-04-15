import os
import logging
import psutil
from glob import glob
from typing import List
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama.llms import OllamaLLM
from langchain_community.vectorstores import FAISS
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Configuración de CORS
origins = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Permite estos orígenes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RAGPipeline:
    def __init__(
        self,
        max_memory_gb: float = 4.0,
        docs_folder: str = "docs",
        ollama_base_url: str = "http://host.docker.internal:11434"
    ):
        self.setup_logging()
        self.logger.info("Initialize RAGPipeline...")
        self.check_system_memory(max_memory_gb)
        
        # Endpoint de Ollama en Docker (se asume que el modelo ya está instalado en el contenedor)
        self.ollama_base_url = ollama_base_url
        
        # Nombre del modelo que queremos usar
        self.model_name = "deepseek-r1:7b"
        
        # Cargar el modelo de lenguaje (LLM) usando el endpoint de Docker
        self.llm = OllamaLLM(model=self.model_name, base_url=self.ollama_base_url)
        
        # Inicializar embeddings con un modelo ligero
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2",
            model_kwargs={'device': 'cpu'}  # Uso de CPU para eficiencia
        )
        
        # Definir la plantilla de prompt
        # self.prompt = ChatPromptTemplate.from_template(
        #     "Answer the question based only on the following context. Be concise.\n"
        #     "If you cannot find the answer in the context, say \"I cannot answer this based on the provided context.\"\n\n"
        #     "Context: {context}\n"
        #     "Question: {question}\n"
        #     "Answer: "
        # )
        self.prompt = ChatPromptTemplate.from_template(
            "Responde la pregunta basándote únicamente en el siguiente contexto. Sé conciso. Siempre responde en el idioma que te hablen.\n"
            "Si no puedes encontrar la respuesta en el contexto, di \"No puedo responder esto con la información proporcionada.\"\n\n"
            "Contexto: {context}\n"
            "Pregunta: {question}\n"
            "Respuesta: "
        )

        
        # Inicializar documentos, vectorstore y chain a partir de la carpeta de Markdown
        documents = self.load_documents(docs_folder)
        self.logger.info(f"Total document chunks loaded: {len(documents)}")
        self.vectorstore = self.create_vectorstore(documents)
        self.chain = self.setup_rag_chain(self.vectorstore)
        self.logger.info("RAGPipeline initialize success.")
    
    def setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def check_system_memory(self, max_memory_gb: float):
        available_memory = psutil.virtual_memory().available / (1024 ** 3)
        self.logger.info(f"Available system memory: {available_memory:.1f} GB")
        if available_memory < max_memory_gb:
            self.logger.warning("Memory is below recommended threshold.")
    
    def load_documents(self, folder_path: str) -> List[Document]:
        pattern = os.path.join(folder_path, "**/*.md")
        documents = []
        self.logger.info(f"Searching for markdown files with pattern: {pattern}")
        for filepath in glob(pattern, recursive=True):
            self.logger.info(f"Found file: {filepath}")
            docs = self.load_and_split_documents(filepath)
            documents.extend(docs)
        return documents
    
    def load_and_split_documents(self, file_path: str) -> List[Document]:
        loader = TextLoader(file_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            add_start_index=True,
        )
        splits = text_splitter.split_documents(documents)
        self.logger.info(f"Created {len(splits)} document chunks from {file_path}")
        return splits
    
    def create_vectorstore(self, documents: List[Document]) -> FAISS:
        batch_size = 32
        self.logger.info("Creating vectorstore...")
        vectorstore = FAISS.from_documents(documents[:batch_size], self.embeddings)
        for i in range(batch_size, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            vectorstore.add_documents(batch)
            self.logger.info(f"Processed batch {i // batch_size + 1}")
        return vectorstore
    
    def setup_rag_chain(self, vectorstore: FAISS):
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 2, "fetch_k": 3})
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
        return rag_chain
    
    def query(self, question: str) -> str:
        memory_usage = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        self.logger.info(f"Memory usage: {memory_usage:.1f} MB")
        return self.chain.invoke(question)

# Modelo Pydantic para el endpoint
class Query(BaseModel):
    question: str

# Instancia global para FastAPI
rag_pipeline = None

@app.on_event("startup")
async def startup_event():
    global rag_pipeline
    # Inicializar RAGPipeline con la carpeta que contiene los archivos .md y el endpoint de Docker de Ollama
    rag_pipeline = RAGPipeline(docs_folder="docs", ollama_base_url="http://host.docker.internal:11434")

@app.post("/consulta")
def consulta(query: Query):
    print("Consultado...")
    if rag_pipeline is None:
        print("No hay rag_pipeline...")
        raise HTTPException(status_code=500, detail="RAGPipeline is not initialized")
    print("query...")
    answer = rag_pipeline.query(query.question)
    print(f"result: {answer}")
    return {"answer": answer}

# Para ejecutar con uvicorn, descomenta las siguientes líneas:
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8001)
