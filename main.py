from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import httpx
import io
from pypdf import PdfReader

app = FastAPI(
    title="DataVision AI - RAG & SQL API",
    description="API para leitura de arquivos (PDF/TXT) e consulta direta ao SQL Server",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://localhost:11434/api/generate"

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
# ENDPOINT 1: RAG (PDF / TXT)
# ==========================================
@app.post("/api/rag/ask-document")
async def ask_document(
    file: UploadFile = File(...),
    question: str = Form(...)
):
    try:
        contents = await file.read()
        document_text = ""

        if file.filename.lower().endswith(".pdf"):
            pdf_file = io.BytesIO(contents)
            reader = PdfReader(pdf_file)
            for page in reader.pages:
                extracted_page_text = page.extract_text()
                if extracted_page_text:
                    document_text += extracted_page_text + "\n"
        elif file.filename.lower().endswith(".txt"):
            document_text = contents.decode("utf-8")
        else:
            raise HTTPException(status_code=400, detail="Formato não suportado. Envie .txt ou .pdf.")

        if not document_text.strip():
            raise HTTPException(status_code=400, detail="Arquivo sem texto legível.")

        prompt = f"""Você é um assistente de dados direto e objetivo.
REGRAS:
1. Responda apenas com base no documento fornecido.
2. Seja direto e resumido (máximo 3 frases).
3. NUNCA gere código ou scripts.

Documento:
{document_text[:3000]}

Pergunta: {question}
Resposta:"""

        payload = {
            "model": "phi3",
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 150, "temperature": 0.1}
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            res_json = response.json()

        return {
            "status": "success",
            "source": f"Arquivo {file.filename}",
            "question": question,
            "answer": res_json.get("response", "").strip()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# ENDPOINT 2: SQL SERVER (RESPOSTA EXATA E INSTANTÂNEA)
# ==========================================
@app.post("/api/sql/ask-products")
async def ask_sql_products(question: str = Form(...)):
    if not engine:
        raise HTTPException(status_code=500, detail="Erro de conexão com o banco SQL.")
        
    try:
        q = question.lower()
        
        with engine.connect() as connection:
            # 1. PERGUNTA: PRODUTO MAIS CARO
            if "mais caro" in q or "maior preco" in q or "maior preço" in q:
                query = text("SELECT TOP 1 nome_produto, preco FROM dbo.produtos ORDER BY preco DESC")
                res = connection.execute(query).fetchone()
                if res:
                    ans = f"O produto mais caro é o **{res.nome_produto}**, custando **R$ {res.preco:.2f}**."
                else:
                    ans = "Nenhum produto encontrado no banco."

            # 2. PERGUNTA: PRODUTO MAIS BARATO
            elif "mais barato" in q or "menor preco" in q or "menor preço" in q:
                query = text("SELECT TOP 1 nome_produto, preco FROM dbo.produtos ORDER BY preco ASC")
                res = connection.execute(query).fetchone()
                if res:
                    ans = f"O produto mais barato é o **{res.nome_produto}**, custando **R$ {res.preco:.2f}**."
                else:
                    ans = "Nenhum produto encontrado no banco."

            # 3. PERGUNTA: FATURAMENTO / TOTAL / SOMA
            elif "faturamento" in q or "total" in q or "soma" in q:
                query = text("SELECT SUM(preco) as total, COUNT(*) as qtd FROM dbo.produtos")
                res = connection.execute(query).fetchone()
                if res and res.total is not None:
                    ans = f"O faturamento total estimado vendendo todos os {res.qtd} produtos é de **R$ {res.total:.2f}**."
                else:
                    ans = "Não foi possível calcular o faturamento."

            # 4. OUTRAS PERGUNTAS (CONSULTA O OLLAMA)
            else:
                query = text("SELECT TOP 10 nome_produto, categoria, preco FROM dbo.produtos")
                rows = connection.execute(query).fetchall()
                dados = "\n".join([f"- {r.nome_produto} (R$ {r.preco})" for r in rows])
                
                prompt = f"Com base nestes produtos:\n{dados}\n\nResponda diretamente em 1 frase: {question}"
                payload = {
                    "model": "phi3",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 80, "temperature": 0.0}
                }
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(OLLAMA_URL, json=payload)
                    ans = response.json().get("response", "").strip()

        return {
            "status": "success",
            "source": "SQL Server (dbo.produtos)",
            "question": question,
            "answer": ans
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar SQL: {str(e)}")