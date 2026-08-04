import os
from pypdf import PdfReader

class RAGService:
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Lê um arquivo PDF e extrai todo o texto contido nele."""
        reader = PdfReader(file_path)
        extracted_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text)
        return "\n".join(extracted_text).strip()

    @staticmethod
    def format_prompt_with_context(context: str, user_query: str) -> str:
        """Monta o prompt injetando o contexto do documento para o Phi-3."""
        return f"""
Você é um assistente especialista em análise de dados corporativos (DataVision AI).
Responda à pergunta do usuário utilizando ESTRITAMENTE as informações fornecidas no contexto abaixo.

---
CONTEXTO DO DOCUMENTO:
{context}
---

PERGUNTA DO USUÁRIO:
{user_query}

RESPOSTA:
"""
