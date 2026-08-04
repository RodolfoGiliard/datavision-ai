from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import requests
import io
from pypdf import PdfReader

# Inicialização da aplicação FastAPI
app = FastAPI(
    title="DataVision AI - RAG & SQL API",
    description="API para leitura de arquivos (PDF/TXT) e consulta direta ao SQL Server via Ollama/Phi-3",
    version="2.0.0"
)

# Configuração do Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# URL do endpoint do Ollama local
OLLAMA_URL = "http://localhost:11434/api/generate"

# Configuração de Conexão com o SQL Server (Ajuste o SERVER se seu SQL Express usar outro nome)
SERVER = 'localhost'  
DATABASE = 'newstore'
DATABASE_URL = f"mssql+pyodbc://@{SERVER}/{DATABASE}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"

try:
    engine = create_engine(DATABASE_URL)
except Exception as e:
    engine = None
    print(f"Aviso de inicialização SQL: {e}")


@app.get("/")
def read_root():
    return {"message": "API DataVision AI (PDF, TXT e SQL Server) está rodando com sucesso!"}


# ==========================================
# ENDPOINT 1: PROCESSAMENTO DE ARQUIVOS (PDF / TXT)
# ==========================================
@app.post("/api/rag/ask-document", summary="Faz perguntas baseadas em um arquivo enviado (PDF ou TXT)")
async def ask_document(
    file: UploadFile = File(...),
    question: str = Form(...)
):
    try:
        contents = await file.read()
        document_text = ""

        # Leitura de PDF
        if file.filename.lower().endswith(".pdf"):
            pdf_file = io.BytesIO(contents)
            reader = PdfReader(pdf_file)
            for page in reader.pages:
                extracted_page_text = page.extract_text()
                if extracted_page_text:
                    document_text += extracted_page_text + "\n"

        # Leitura de TXT
        elif file.filename.lower().endswith(".txt"):
            document_text = contents.decode("utf-8")

        else:
            raise HTTPException(
                status_code=400, 
                detail="Formato não suportado. Envie um arquivo .txt ou .pdf."
            )

        if not document_text.strip():
            raise HTTPException(
                status_code=400, 
                detail="Não foi possível extrair texto digital deste arquivo."
            )

        prompt = f"""Você é um assistente de dados. Responda à pergunta do usuário baseando-se estritamente no documento fornecido abaixo.

Documento:
{document_text}

Pergunta:
{question}

Resposta:"""

        payload = {
            "model": "phi3",
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()

        return {
            "status": "success",
            "source": "Arquivo " + file.filename,
            "question": question,
            "answer": response.json().get("response", "")
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro no Ollama: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")


# ==========================================
# ENDPOINT 2: CONSULTA DIRETA AO SQL SERVER
# ==========================================
@app.post("/api/sql/ask-products", summary="Faz perguntas diretas na tabela de produtos do SQL Server")
async def ask_sql_products(question: str = Form(...)):
    if not engine:
        raise HTTPException(status_code=500, detail="Conexão com o banco SQL não foi configurada.")
        
    try:
        # Busca ultra-rápida na tabela de produtos do banco newstore
        query = text("SELECT id_produto, nome_produto, categoria, tamanho, cor, preco, custo FROM dbo.produtos")
        
        with engine.connect() as connection:
            result = connection.execute(query)
            rows = result.fetchall()
            dados_sql = "\n".join([str(dict(row._mapping)) for row in rows])

        if not dados_sql:
            raise HTTPException(status_code=404, detail="Nenhum produto encontrado no banco de dados.")

        prompt = f"""Você é um assistente de dados. Responda à pergunta do usuário utilizando os dados do banco SQL abaixo.

Dados do Banco SQL (Tabela dbo.produtos):
{dados_sql}

Pergunta do Usuário:
{question}

Resposta:"""

        payload = {
            "model": "phi3",
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()

        return {
            "status": "success",
            "source": "SQL Server (dbo.produtos)",
            "question": question,
            "answer": response.json().get("response", "")
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro no Ollama: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar SQL Server: {str(e)}")