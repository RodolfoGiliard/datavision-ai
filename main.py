"""
DataVision AI — FastAPI Backend (Base newstore / Tabela produtos)
==================================================================
Arquitetura modular dividida em 11 blocos:
  • Conexão segura com SQL Server (pyodbc + .env)
  • Validação de dados com Pydantic v2
  • Cache em memória (TTL 60s) para KPIs do Dashboard
  • Pipeline SQL-RAG Local com Ollama (qwen2.5:3b) nos 3 idiomas (PT / ES / EN)
  • Fallback automático caso o Ollama esteja offline
"""

# ===========================================================================
# BLOCO 1 — IMPORTAÇÕES DE BIBLIOTECAS
# ===========================================================================
from __future__ import annotations  # Permite anotações de tipos modernas (ex: str | None)

# Bibliotecas nativas do Python
import json                           # Converte os dados do SQL Server em texto JSON para a IA ler
import logging                        # Registra eventos, avisos e erros no terminal
import re                             # Expressões regulares para identificar códigos SKU
import time                           # Controla o tempo de expiração (TTL) do cache do dashboard
from functools import lru_cache       # Mantém as configurações em memória sem reler o .env toda hora
from typing import Any, Generator     # Tipagem estática para segurança e clareza do código

# Bibliotecas externas (instaladas via pip)
import httpx                          # Cliente HTTP usado para conversar com o Ollama local (porta 11434)
import pyodbc                         # Driver oficial de conexão com o Microsoft SQL Server
import uvicorn                        # Servidor web ASGI que coloca a API no ar
from fastapi import Depends, FastAPI, HTTPException, Query  # Núcleo do FastAPI e validação de rotas
from fastapi.middleware.cors import CORSMiddleware          # Libera acesso do frontend NiceGUI (porta 8080)
from fastapi.responses import JSONResponse                  # Formata respostas de erro em JSON padronizado
from pydantic import BaseModel, Field, field_validator      # Valida e sanitiza dados de entrada/saída
from pydantic_settings import BaseSettings, SettingsConfigDict  # Carrega credenciais do arquivo .env


# ===========================================================================
# BLOCO 2 — CONFIGURAÇÃO DE LOGS
# ===========================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("datavision.backend")


# ===========================================================================
# BLOCO 3 — CONFIGURAÇÕES DO SISTEMA E DO OLLAMA (.env)
# ===========================================================================
class Settings(BaseSettings):
    """Lê variáveis do arquivo .env usando o prefixo DV_ (ex: DV_OLLAMA_MODEL)."""

    model_config = SettingsConfigDict(env_prefix="DV_", env_file=".env", extra="ignore")

    # Banco de Dados SQL Server
    db_connection_string: str = Field(
        default="DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=newstore;Trusted_Connection=yes;",
        description="String de conexão completa do pyodbc.",
    )

    # Segurança de acesso do Frontend (NiceGUI)
    cors_origins: list[str] = Field(
        default=["http://localhost:8080", "http://127.0.0.1:8080"],
        description="Origens permitidas pelo CORS.",
    )

    # Performance e Servidor
    dashboard_cache_ttl: int = Field(default=60, description="Tempo de cache dos KPIs em segundos.")
    environment: str = Field(default="development")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # Configurações do Motor RAG Local (Ollama)
    ollama_url: str = Field(
        default="http://localhost:11434/api/generate",
        description="Endpoint local do servidor Ollama.",
    )
    ollama_model: str = Field(
        default="qwen2.5:3b",
        description="Modelo LLM local usado para gerar análises.",
    )
    ollama_timeout: float = Field(
        default=30.0,
        description="Tempo máximo de espera (segundos) pela resposta da IA.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Instancia e guarda as configurações em cache para reutilização rápida."""
    return Settings()


# ===========================================================================
# BLOCO 4 — CONEXÃO E RESILIÊNCIA COM O SQL SERVER
# ===========================================================================
class DatabaseUnavailableError(RuntimeError):
    """Exceção personalizada disparada quando o SQL Server está fora do ar."""

    def __init__(self, message: str, original: Exception | None = None) -> None:
        super().__init__(message)
        self.original = original


def get_db() -> Generator[pyodbc.Connection, None, None]:
    """Abre uma conexão segura por requisição e garante o fechamento ao final."""
    settings = get_settings()
    conn: pyodbc.Connection | None = None
    try:
        conn = pyodbc.connect(settings.db_connection_string, timeout=5)
        conn.autocommit = False
        yield conn
    except pyodbc.Error as exc:
        logger.error("Erro de conexão pyodbc: %s", exc)
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        raise DatabaseUnavailableError(str(exc), original=exc) from exc
    finally:
        if conn is not None:
            conn.close()


# ===========================================================================
# BLOCO 5 — SCHEMAS DE DADOS E VALIDAÇÃO (PYDANTIC V2)
# ===========================================================================
class ProductResponse(BaseModel):
    """Modelo padronizado de um produto retornado para o dashboard ou chat."""

    sku: str           # Código identificador do produto (id_produto)
    description: str   # Nome completo do produto (nome_produto)
    category: str      # Categoria do item (ex: Shorts, Vestido, Jaqueta)
    stock: float       # Quantidade física disponível em estoque
    unit_price: float  # Preço unitário de venda em Reais
    abc_curve: str     # Classificação de importância financeira ('A', 'B' ou 'C')


class DashboardStats(BaseModel):
    """Estrutura completa dos indicadores enviados para as 4 abas do ui.py."""

    total_products: int                          # Total de SKUs cadastrados
    total_stock_value: float                     # Valor financeiro total imobilizado no estoque
    avg_stock: float                             # Média de unidades por produto
    low_stock_count: int                         # Quantidade de produtos em estoque crítico (<= 10)
    category_count: int                          # Quantidade de categorias distintas
    top_categories: list[dict[str, Any]]         # Ranking das categorias por valor em estoque
    grade_distribution: list[dict[str, Any]]     # Distribuição por grade/tamanho
    abc_distribution: list[dict[str, Any]]       # Resumo agrupado das Classes A, B e C
    low_stock_products: list[dict[str, Any]]     # Lista de produtos com estoque baixo
    abc_products: list[dict[str, Any]] = Field(  # Lista detalhada de Pareto (todos os produtos classificados)
        default_factory=list
    )


class ChatRequest(BaseModel):
    """Valida e limpa a pergunta enviada pelo usuário no chat."""

    message: str = Field(..., min_length=1, max_length=1000)

    @field_validator("message", mode="before")
    @classmethod
    def sanitize_message(cls, value: str) -> str:
        # Remove espaços duplicados e espaços nas pontas antes de processar
        value = value.strip()
        value = re.sub(r"\s+", " ", value)
        return value


class ChatResponse(BaseModel):
    """Resposta devolvida ao ui.py contendo o texto da IA e a tabela de produtos."""

    answer: str                                                # Texto analítico gerado pelo Ollama ou fallback
    products: list[ProductResponse] = Field(default_factory=list)  # Tabela de itens exibida abaixo da resposta
    query_type: str = "general"                                # Tipo de intenção identificada na pergunta


class HealthResponse(BaseModel):
    """Status de saúde da API e do SQL Server."""

    status: str               # Status do servidor FastAPI ('ok')
    db_status: str            # Status da conexão com o SQL Server ('ok' ou 'unavailable')
    version: str = "1.0.0"    # Versão atual da API


# ===========================================================================
# BLOCO 6 — INICIALIZAÇÃO DA API, CORS E TRATAMENTO GLOBAL DE ERROS
# ===========================================================================
app = FastAPI(title="DataVision AI", version="1.0.0")


@app.exception_handler(DatabaseUnavailableError)
async def database_unavailable_handler(request: Any, exc: DatabaseUnavailableError) -> JSONResponse:
    """Devolve HTTP 503 amigável se o SQL Server estiver offline."""
    logger.error("Banco de dados indisponível: %s", exc)
    return JSONResponse(status_code=503, content={"detail": f"Database unavailable: {exc}"})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Any, exc: Exception) -> JSONResponse:
    """Captura qualquer erro inesperado para evitar exposição de stack trace."""
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("Erro interno não tratado: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


def _configure_cors(application: FastAPI) -> None:
    """Autoriza o frontend NiceGUI (porta 8080) a fazer requisições na API."""
    settings = get_settings()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


_configure_cors(app)


# ===========================================================================
# BLOCO 7 — UTILITÁRIOS DE BUSCA E RESPOSTA PADRÃO (PLANO B / FALLBACK)
# ===========================================================================
_SKU_PATTERN = re.compile(r"\b([A-Z]{2,4}-?\d{3,8})\b", re.IGNORECASE)


def extract_sku(text: str) -> str | None:
    """Extrai um código SKU da frase usando expressão regular (ex: CAM-1024)."""
    match = _SKU_PATTERN.search(text)
    return match.group(1).upper() if match else None


def escape_sql_server_like(term: str) -> str:
    """Escapa caracteres curinga (% e _) para evitar buscas maliciosas no LIKE."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_chat_answer(query_type: str, products: list[ProductResponse], raw_message: str) -> str:
    """Gera uma resposta rápida sem IA caso o Ollama esteja desligado."""
    if query_type == "sku_lookup":
        if not products:
            return f"Nenhum produto encontrado para o código '{raw_message}'."
        p = products[0]
        return (
            f"Produto **{p.sku}** — {p.description}\n"
            f"Categoria: {p.category} | Estoque: {p.stock:,.0f} | Preço: R$ {p.unit_price:,.2f}"
        )
    if query_type == "search":
        count = len(products)
        if count == 0:
            return f"Nenhum produto encontrado para '{raw_message}'."
        return f"Encontrei **{count}** produto(s) relacionado(s)."
    if query_type == "low_stock":
        return f"Há **{len(products)}** produto(s) com estoque baixo."
    return "Olá! Sou o assistente DataVision AI. Pergunte sobre SKUs, categorias ou estoque baixo."


# ===========================================================================
# BLOCO 8 — MOTOR RAG LOCAL COM OLLAMA (qwen2.5:3b — PT / ES / EN)
# ===========================================================================
def format_brl(value: float) -> str:
    """Converte float americano (136719.74) em texto brasileiro ('R$ 136.719,74')."""
    texto = f"{value:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def generate_rag_answer(
    user_message: str,
    stats: DashboardStats,
    products: list[ProductResponse],
    top_stock: list[ProductResponse],
    expensive_products: list[ProductResponse] | None = None,
) -> str | None:
    """Envia os KPIs e líderes absolutos (#1 mais caro e #1 maior estoque) para o Ollama."""
    settings = get_settings()
    expensive_list = expensive_products or []

    mais_caro_top1 = (
        {
            "posicao_ranking": 1,
            "sku": expensive_list[0].sku,
            "produto": expensive_list[0].description,
            "categoria": expensive_list[0].category,
            "preco_unitario": format_brl(expensive_list[0].unit_price),
            "estoque_atual": expensive_list[0].stock,
        }
        if expensive_list
        else None
    )

    maior_estoque_top1 = (
        {
            "posicao_ranking": 1,
            "sku": top_stock[0].sku,
            "produto": top_stock[0].description,
            "categoria": top_stock[0].category,
            "estoque_atual": top_stock[0].stock,
            "preco_unitario": format_brl(top_stock[0].unit_price),
        }
        if top_stock
        else None
    )

    context_payload = {
        "destaques_absolutos": {
            "produto_mais_caro_numero_1": mais_caro_top1,
            "produto_maior_quantidade_numero_1": maior_estoque_top1,
        },
        "kpis_gerais": {
            "total_produtos": stats.total_products,
            "valor_total_estoque_reais": format_brl(stats.total_stock_value),
            "estoque_medio_por_item": round(stats.avg_stock, 2),
            "qtd_produtos_estoque_baixo": stats.low_stock_count,
            "total_categorias": stats.category_count,
        },
        "top_categorias_por_valor": stats.top_categories[:5],
        "distribuicao_curva_abc": stats.abc_distribution,
        "ranking_produtos_mais_caros": [
            {
                "posicao_ranking": idx,
                "sku": p.sku,
                "produto": p.description,
                "categoria": p.category,
                "preco_unitario": format_brl(p.unit_price),
                "estoque_atual": p.stock,
            }
            for idx, p in enumerate(expensive_list[:5], start=1)
        ],
        "ranking_produtos_maior_estoque": [
            {
                "posicao_ranking": idx,
                "sku": p.sku,
                "produto": p.description,
                "categoria": p.category,
                "estoque_atual": p.stock,
                "preco_unitario": format_brl(p.unit_price),
            }
            for idx, p in enumerate(top_stock[:5], start=1)
        ],
        "produtos_com_menor_estoque_ruptura": stats.low_stock_products[:8],
        "produtos_especificos_da_busca": [p.model_dump() for p in products[:8]],
    }

    prompt = f"""Você é o DataVision AI, um analista sênior de estoque, varejo e inteligência de compras.
Responda à pergunta do usuário usando EXCLUSIVAMENTE os dados reais fornecidos no JSON abaixo.

REGRAS OBRIGATÓRIAS:
1. Copie os valores monetários exatamente como estão escritos no JSON (ex: 'R$ 136.719,74'), nunca altere pontos ou vírgulas.
2. Para perguntas sobre o produto mais caro ou maior preço, responda obrigatoriamente usando 'destaques_absolutos.produto_mais_caro_numero_1'.
3. Para perguntas sobre maior quantidade ou volume em estoque, responda obrigatoriamente usando 'destaques_absolutos.produto_maior_quantidade_numero_1'.
4. Para perguntas sobre falta, ruptura ou estoque baixo, consulte 'produtos_com_menor_estoque_ruptura'.
5. Idioma: responda exatamente no mesmo idioma da pergunta do usuário (Português, Español ou English).
6. Seja direto e entregue uma breve recomendação prática de compra ou giro de estoque.

DADOS REAIS DO SQL SERVER (BASE NEWSTORE / TABELA PRODUTOS):
{json.dumps(context_payload, ensure_ascii=False)}

PERGUNTA DO USUÁRIO:
{user_message}"""

    try:
        response = httpx.post(
            settings.ollama_url,
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "30m",
                "options": {"temperature": 0.1, "num_predict": 320},
            },
            timeout=settings.ollama_timeout,
        )
        response.raise_for_status()
        answer_text = response.json().get("response", "").strip()
        return answer_text if answer_text else None
    except Exception as exc:
        logger.warning("Ollama indisponível (%s). Usando resposta padrão sem IA.", exc)
        return None


# ===========================================================================
# BLOCO 9 — CONSULTAS SQL, CURVA ABC REAL E CACHE DO DASHBOARD (BASE NEWSTORE)
# ===========================================================================
_dashboard_cache: dict[str, Any] = {"data": None, "expires_at": 0.0}


def _fetch_abc_map(conn: pyodbc.Connection) -> dict[str, str]:
    """Calcula a Curva ABC real via Window Functions e retorna o mapa {sku: 'A'|'B'|'C'}."""
    cursor = conn.cursor()
    cursor.execute(
        """
        WITH BaseEstoque AS (
            SELECT
                CAST(id_produto AS VARCHAR(50)) AS sku,
                CAST(estoque_atual AS FLOAT) * CAST(preco AS FLOAT) AS total_value
            FROM produtos
        ),
        AcumuladoPareto AS (
            SELECT
                sku,
                total_value,
                SUM(total_value) OVER () AS grand_total,
                SUM(total_value) OVER (ORDER BY total_value DESC, sku ASC ROWS UNBOUNDED PRECEDING) AS running_total
            FROM BaseEstoque
        )
        SELECT
            sku,
            CASE
                WHEN (running_total / NULLIF(grand_total, 0)) <= 0.80 THEN 'A'
                WHEN (running_total / NULLIF(grand_total, 0)) <= 0.95 THEN 'B'
                ELSE 'C'
            END AS abc_class
        FROM AcumuladoPareto
        """
    )
    return {row.sku: row.abc_class for row in cursor.fetchall()}


def get_dashboard_stats(conn: pyodbc.Connection) -> DashboardStats:
    """Calcula os KPIs, Grade e Curva ABC da tabela 'produtos' e guarda em cache por 60s."""
    if _dashboard_cache["data"] and time.monotonic() < _dashboard_cache["expires_at"]:
        return _dashboard_cache["data"]

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            COUNT(*)                                             AS total_products,
            SUM(estoque_atual * preco)                           AS total_stock_value,
            AVG(CAST(estoque_atual AS FLOAT))                    AS avg_stock,
            SUM(CASE WHEN estoque_atual <= 10 THEN 1 ELSE 0 END) AS low_stock_count,
            COUNT(DISTINCT categoria)                            AS category_count
        FROM produtos
        """
    )
    row = cursor.fetchone()
    total_products = row.total_products or 0
    total_stock_value = float(row.total_stock_value or 0)
    avg_stock = float(row.avg_stock or 0)
    low_stock_count = row.low_stock_count or 0
    category_count = row.category_count or 0

    cursor.execute(
        """
        SELECT TOP 10
            categoria,
            COUNT(*)                   AS product_count,
            SUM(estoque_atual * preco) AS stock_value
        FROM produtos
        GROUP BY categoria
        ORDER BY stock_value DESC
        """
    )
    top_categories = [
        {"category": r.categoria, "product_count": r.product_count, "stock_value": float(r.stock_value or 0)}
        for r in cursor.fetchall()
    ]

    grade_distribution = []
    try:
        cursor.execute("SELECT tamanho AS grade, COUNT(*) AS count FROM produtos GROUP BY tamanho ORDER BY tamanho")
        grade_distribution = [{"grade": r.grade, "count": r.count} for r in cursor.fetchall()]
    except Exception:
        pass

    cursor.execute(
        """
        WITH BaseEstoque AS (
            SELECT
                CAST(id_produto AS VARCHAR) AS sku,
                nome_produto AS description,
                categoria AS category,
                CAST(estoque_atual AS FLOAT) AS stock,
                CAST(preco AS FLOAT) AS unit_price,
                CAST(estoque_atual * preco AS FLOAT) AS total_value
            FROM produtos
        ),
        AcumuladoPareto AS (
            SELECT
                sku, description, category, stock, unit_price, total_value,
                SUM(total_value) OVER () AS grand_total,
                SUM(total_value) OVER (ORDER BY total_value DESC, sku ASC ROWS UNBOUNDED PRECEDING) AS running_total
            FROM BaseEstoque
        )
        SELECT
            sku, description, category, stock, unit_price,
            ROUND(total_value, 2) AS total_value,
            ROUND((running_total / NULLIF(grand_total, 0)) * 100, 2) AS cumulative_pct,
            CASE
                WHEN (running_total / NULLIF(grand_total, 0)) <= 0.80 THEN 'A'
                WHEN (running_total / NULLIF(grand_total, 0)) <= 0.95 THEN 'B'
                ELSE 'C'
            END AS abc_class
        FROM AcumuladoPareto
        ORDER BY total_value DESC, sku ASC
        """
    )
    abc_products = [
        {
            "sku": r.sku,
            "description": r.description,
            "category": r.category,
            "stock": float(r.stock),
            "unit_price": float(r.unit_price),
            "total_value": float(r.total_value or 0),
            "cumulative_pct": float(r.cumulative_pct or 0),
            "abc_class": r.abc_class,
        }
        for r in cursor.fetchall()
    ]

    abc_map = {item["sku"]: item["abc_class"] for item in abc_products}
    abc_distribution = [
        {
            "curve": curva,
            "count": len([p for p in abc_products if p["abc_class"] == curva]),
            "value": round(sum(p["total_value"] for p in abc_products if p["abc_class"] == curva), 2),
        }
        for curva in ("A", "B", "C")
    ]

    cursor.execute(
        """
        SELECT TOP 20
            CAST(id_produto AS VARCHAR) AS sku,
            nome_produto AS description,
            categoria AS category,
            estoque_atual,
            preco
        FROM produtos
        WHERE estoque_atual <= 10
        ORDER BY estoque_atual ASC, preco DESC
        """
    )
    low_stock_products = [
        {
            "sku": r.sku,
            "description": r.description,
            "category": r.category,
            "stock": float(r.estoque_atual),
            "unit_price": float(r.preco),
            "abc_curve": abc_map.get(r.sku, "C"),
        }
        for r in cursor.fetchall()
    ]

    stats = DashboardStats(
        total_products=total_products,
        total_stock_value=total_stock_value,
        avg_stock=avg_stock,
        low_stock_count=low_stock_count,
        category_count=category_count,
        top_categories=top_categories,
        grade_distribution=grade_distribution,
        abc_distribution=abc_distribution,
        low_stock_products=low_stock_products,
        abc_products=abc_products,
    )
    _dashboard_cache["data"] = stats
    _dashboard_cache["expires_at"] = time.monotonic() + get_settings().dashboard_cache_ttl
    return stats


def search_products(conn: pyodbc.Connection, q: str, limit: int = 20) -> list[ProductResponse]:
    """Busca produtos por nome ou categoria de forma parametrizada com classe ABC real."""
    safe_q = escape_sql_server_like(q)
    pattern = f"%{safe_q}%"
    abc_map = _fetch_abc_map(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT TOP (?)
            CAST(id_produto AS VARCHAR) AS sku,
            nome_produto AS description,
            categoria AS category,
            estoque_atual,
            preco
        FROM produtos
        WHERE nome_produto LIKE ? ESCAPE '\\' OR categoria LIKE ? ESCAPE '\\'
        ORDER BY nome_produto
        """,
        (limit, pattern, pattern),
    )
    return [
        ProductResponse(
            sku=r.sku,
            description=r.description,
            category=r.category,
            stock=float(r.estoque_atual),
            unit_price=float(r.preco),
            abc_curve=abc_map.get(r.sku, "C"),
        )
        for r in cursor.fetchall()
    ]


def lookup_sku(conn: pyodbc.Connection, sku: str) -> list[ProductResponse]:
    """Busca um produto exato pelo seu código SKU / id_produto com classe ABC real."""
    abc_map = _fetch_abc_map(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            CAST(id_produto AS VARCHAR) AS sku,
            nome_produto AS description,
            categoria AS category,
            estoque_atual,
            preco
        FROM produtos
        WHERE CAST(id_produto AS VARCHAR) = ?
        """,
        (sku,),
    )
    row = cursor.fetchone()
    if not row:
        return []
    return [
        ProductResponse(
            sku=row.sku,
            description=row.description,
            category=row.category,
            stock=float(row.estoque_atual),
            unit_price=float(row.preco),
            abc_curve=abc_map.get(row.sku, "C"),
        )
    ]


def get_low_stock(conn: pyodbc.Connection, threshold: int = 10) -> list[ProductResponse]:
    """Retorna os até 50 produtos com menor estoque disponível e classe ABC real."""
    abc_map = _fetch_abc_map(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT TOP 50
            CAST(id_produto AS VARCHAR) AS sku,
            nome_produto AS description,
            categoria AS category,
            estoque_atual,
            preco
        FROM produtos
        WHERE estoque_atual <= ?
        ORDER BY estoque_atual ASC, preco DESC
        """,
        (threshold,),
    )
    return [
        ProductResponse(
            sku=r.sku,
            description=r.description,
            category=r.category,
            stock=float(r.estoque_atual),
            unit_price=float(r.preco),
            abc_curve=abc_map.get(r.sku, "C"),
        )
        for r in cursor.fetchall()
    ]


def get_top_stock(conn: pyodbc.Connection, limit: int = 10) -> list[ProductResponse]:
    """Retorna os produtos com MAIOR quantidade em estoque (ordem decrescente)."""
    abc_map = _fetch_abc_map(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT TOP (?)
            CAST(id_produto AS VARCHAR) AS sku,
            nome_produto AS description,
            categoria AS category,
            estoque_atual,
            preco
        FROM produtos
        ORDER BY estoque_atual DESC
        """,
        (limit,),
    )
    return [
        ProductResponse(
            sku=r.sku,
            description=r.description,
            category=r.category,
            stock=float(r.estoque_atual),
            unit_price=float(r.preco),
            abc_curve=abc_map.get(r.sku, "C"),
        )
        for r in cursor.fetchall()
    ]


def get_expensive_products(conn: pyodbc.Connection, limit: int = 5) -> list[ProductResponse]:
    """Retorna os produtos com MAIOR preço unitário cadastrados no SQL Server."""
    abc_map = _fetch_abc_map(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT TOP (?)
            CAST(id_produto AS VARCHAR) AS sku,
            nome_produto AS description,
            categoria AS category,
            estoque_atual,
            preco
        FROM produtos
        ORDER BY preco DESC
        """,
        (limit,),
    )
    return [
        ProductResponse(
            sku=r.sku,
            description=r.description,
            category=r.category,
            stock=float(r.estoque_atual),
            unit_price=float(r.preco),
            abc_curve=abc_map.get(r.sku, "C"),
        )
        for r in cursor.fetchall()
    ]


# ===========================================================================
# BLOCO 10 — ROTAS DA API (ENDPOINTS REST)
# ===========================================================================
@app.get("/health", response_model=HealthResponse, tags=["Infra"])
def health_check(conn: pyodbc.Connection = Depends(get_db)) -> HealthResponse:
    """Verifica se a API e o SQL Server estão respondendo."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        db_status = "ok"
    except DatabaseUnavailableError:
        db_status = "unavailable"
    return HealthResponse(status="ok", db_status=db_status)


@app.get("/dashboard/stats", response_model=DashboardStats, tags=["Dashboard"])
def dashboard_stats(conn: pyodbc.Connection = Depends(get_db)) -> DashboardStats:
    """Fornece todos os KPIs e tabelas consolidados para as 4 abas do ui.py."""
    return get_dashboard_stats(conn)


@app.get("/products/search", response_model=list[ProductResponse], tags=["Products"])
def products_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    conn: pyodbc.Connection = Depends(get_db),
) -> list[ProductResponse]:
    """Endpoint direto de busca textual de produtos por nome ou categoria."""
    return search_products(conn, q, limit=limit)


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(request: ChatRequest, conn: pyodbc.Connection = Depends(get_db)) -> ChatResponse:
    """Pipeline completo do Assistente Inteligente (Retrieval -> RAG -> Fallback)."""
    message = request.message
    msg_lower = message.lower()
    sku = extract_sku(message)

    top_stock = get_top_stock(conn, limit=10)
    expensive_products = get_expensive_products(conn, limit=5)

    if sku:
        products = lookup_sku(conn, sku)
        query_type = "sku_lookup"
    elif any(palavra in msg_lower for palavra in ("caro", "maior preço", "mais valioso", "barato")):
        products = expensive_products
        query_type = "top_price"
    elif any(palavra in msg_lower for palavra in ("baixo", "ruptura", "acabando", "menor")):
        products = get_low_stock(conn)
        query_type = "low_stock"
    elif any(palavra in msg_lower for palavra in ("maior", "mais estoque", "excesso", "sobrando")):
        products = top_stock
        query_type = "top_stock"
    elif len(message) >= 3:
        products = search_products(conn, message, limit=10)
        query_type = "search" if products else "general"
    else:
        products = []
        query_type = "general"

    stats = get_dashboard_stats(conn)
    rag_answer = generate_rag_answer(message, stats, products, top_stock, expensive_products)
    answer = rag_answer if rag_answer else build_chat_answer(query_type, products, message)

    return ChatResponse(answer=answer, products=products, query_type=query_type)