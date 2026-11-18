"""
DataVision AI — NiceGUI Frontend (Edição Executiva)
=====================================================
Painel de inteligência de estoque full-stack com:
- Isolamento de estado por sessão (Multi-user safe)
- Internacionalização completa em 3 idiomas: Português, Español e English
- Gráficos interativos com Apache ECharts (Pareto ABC, Donut de Risco e Barras)
- Chat RAG com sugestões rápidas e tabelas responsivas sem corte lateral
- Exportação de Ordem de Compra em planilha (.csv / Excel)
"""

# ==================================================
# BLOCO 1 — IMPORTAÇÕES DE PACOTES
# ==================================================
from __future__ import annotations  # Permite anotações de tipos modernas (ex: dict | None)

# Bibliotecas padrão do Python
import csv                                # Gera planilhas CSV compatíveis com Excel sem dependências extras
import io                                 # Cria arquivos em memória para download direto no navegador
import logging                            # Registra eventos e erros da interface no terminal
from dataclasses import dataclass, field  # Cria estruturas limpas para mensagens e estado da tela
from typing import Any                    # Tipagem genérica para dicionários vindos da API

# Bibliotecas de terceiros
import httpx                              # Cliente HTTP assíncrono para conversar com o FastAPI
from nicegui import app as nicegui_app    # Gerencia ciclo de vida e armazenamento por sessão de usuário
from nicegui import ui                    # Componentes visuais, tabelas e gráficos Apache ECharts


# ==================================================
# BLOCO 2 — CONFIGURAÇÃO DE LOGS
# ==================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("datavision.ui")  # Logger exclusivo do frontend


# ==================================================
# BLOCO 3 — CONFIGURAÇÕES DA API
# ==================================================
API_BASE = "http://localhost:8000"  # Endereço local do backend FastAPI


# ==================================================
# BLOCO 4 — CLIENTE HTTP COMPARTILHADO (COM TIMEOUT DE 60s)
# ==================================================
_http_client: httpx.AsyncClient | None = None  # Instância única reutilizada entre chamadas


def get_http_client() -> httpx.AsyncClient:
    """Retorna um cliente HTTP assíncrono persistente com folga de 60s para o Ollama local."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            base_url=API_BASE,
            timeout=60.0,  # Evita erro de timeout quando o qwen2.5:3b carrega na memória RAM
            headers={"Accept": "application/json"},
        )
        logger.info("Cliente HTTP inicializado (base_url=%s, timeout=60s)", API_BASE)
    return _http_client


@nicegui_app.on_shutdown
async def _close_http_client() -> None:
    """Encerra o cliente HTTP com segurança ao desligar o servidor NiceGUI."""
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        logger.info("Cliente HTTP encerrado.")


# ==================================================
# BLOCO 5 — INTERNACIONALIZAÇÃO COMPLETA (PT / ES / EN)
# ==================================================
I18N: dict[str, dict[str, str]] = {
    # ---- Português (Padrão) --------------------------------------------------
    "pt": {
        "app_title": "DataVision AI",
        "app_subtitle": "Retail & Supply Chain Analytics",
        "nav_refresh": "Atualizar",
        "tab_exec": "Executivo",
        "tab_stock": "Estoque & Grade",
        "tab_abc": "Curva ABC",
        "tab_purchase": "Inteligência de Compras",
        "chat_title": "Copiloto de Estoque (RAG)",
        "chat_welcome": "Olá! Consulte SKUs, rupturas, Curva ABC ou peça recomendações de compra.",
        "chat_placeholder": "Pergunte sobre produtos, SKUs ou estoque…",
        "chat_processing": "Analisando base SQL…",
        "chat_error": "Erro ao contatar o servidor. Tente novamente.",
        "chip_1": "Estoque baixo",
        "chip_2": "Produto mais caro",
        "chip_3": "Maior estoque",
        "card_total_products": "Total de Produtos",
        "card_stock_value": "Valor em Estoque",
        "card_avg_stock": "Estoque Médio",
        "card_low_stock": "Estoque Crítico",
        "card_categories": "Categorias",
        "chart_top_categories": "Capital Imobilizado por Categoria (R$)",
        "chart_stock_health": "Saúde Operacional & Risco de Ruptura",
        "health_critical": "Estoque Crítico (<= 10 un.)",
        "health_healthy": "Estoque Adequado (> 10 un.)",
        "chart_pareto_title": "Análise de Pareto — Top 15 Produtos (Valor R$ vs % Acumulado)",
        "pareto_bar": "Valor em Estoque (R$)",
        "pareto_line": "% Acumulado",
        "abc_a_title": "CLASSE A (Até 80% do Capital)",
        "abc_a_desc": "Prioridade máxima de reposição e controle",
        "abc_b_title": "CLASSE B (80% a 95% do Capital)",
        "abc_b_desc": "Giro intermediário e revisão quinzenal",
        "abc_c_title": "CLASSE C (Últimos 5% do Capital)",
        "abc_c_desc": "Baixo impacto financeiro no estoque",
        "abc_items_suffix": "produtos",
        "stock_by_cat_title": "Distribuição de Volume Físico por Categoria (Unidades)",
        "table_sku": "SKU",
        "table_description": "Descrição",
        "table_category": "Categoria",
        "table_stock": "Estoque",
        "table_price": "Preço Unit.",
        "table_total_val": "Valor Total",
        "table_cum_pct": "% Acum.",
        "table_abc": "Curva ABC",
        "table_grade": "Grade",
        "table_count": "Qtd",
        "table_value": "Valor",
        "table_curve": "Curva",
        "no_data": "Sem dados disponíveis.",
        "purchase_title": "Produtos com Estoque Crítico — Plano de Reposição",
        "export_btn": "Exportar Ordem de Compra (.CSV)",
        "health_ok": "Sistema operacional",
        "health_degraded": "BD indisponível",
        "lang_label": "Idioma",
        "bot_name": "DataVision IA",
        "you": "Você",
    },
    # ---- Español (Portfólio Espanha) -----------------------------------------
    "es": {
        "app_title": "DataVision AI",
        "app_subtitle": "Analítica de Retail y Cadena de Suministro",
        "nav_refresh": "Actualizar",
        "tab_exec": "Ejecutivo",
        "tab_stock": "Stock & Tallas",
        "tab_abc": "Curva ABC",
        "tab_purchase": "Inteligencia de Compras",
        "chat_title": "Copiloto de Inventario (RAG)",
        "chat_welcome": "¡Hola! Consulta SKUs, roturas de stock, Curva ABC o recomendaciones de compra.",
        "chat_placeholder": "Pregunte sobre productos, SKUs o stock…",
        "chat_processing": "Analizando base SQL…",
        "chat_error": "Error al contactar el servidor. Intente de nuevo.",
        "chip_1": "Stock bajo",
        "chip_2": "Producto más caro",
        "chip_3": "Mayor stock",
        "card_total_products": "Total de Productos",
        "card_stock_value": "Valor en Stock",
        "card_avg_stock": "Stock Medio",
        "card_low_stock": "Stock Crítico",
        "card_categories": "Categorías",
        "chart_top_categories": "Capital Inmovilizado por Categoría (R$)",
        "chart_stock_health": "Salud Operativa y Riesgo de Rotura",
        "health_critical": "Stock Crítico (<= 10 ud.)",
        "health_healthy": "Stock Adecuado (> 10 ud.)",
        "chart_pareto_title": "Análisis de Pareto — Top 15 Productos (Valor vs % Acumulado)",
        "pareto_bar": "Valor en Stock (R$)",
        "pareto_line": "% Acumulado",
        "abc_a_title": "CLASE A (Hasta 80% del Capital)",
        "abc_a_desc": "Prioridad máxima de reposición y control",
        "abc_b_title": "CLASE B (80% a 95% del Capital)",
        "abc_b_desc": "Rotación intermedia y revisión quincenal",
        "abc_c_title": "CLASE C (Últimos 5% del Capital)",
        "abc_c_desc": "Bajo impacto financiero en el inventario",
        "abc_items_suffix": "productos",
        "stock_by_cat_title": "Distribución de Volumen Físico por Categoría (Unidades)",
        "table_sku": "SKU",
        "table_description": "Descripción",
        "table_category": "Categoría",
        "table_stock": "Stock",
        "table_price": "Precio Unit.",
        "table_total_val": "Valor Total",
        "table_cum_pct": "% Acum.",
        "table_abc": "Curva ABC",
        "table_grade": "Talla",
        "table_count": "Cant.",
        "table_value": "Valor",
        "table_curve": "Curva",
        "no_data": "Sin datos disponibles.",
        "purchase_title": "Productos con Stock Crítico — Plan de Reposición",
        "export_btn": "Exportar Orden de Compra (.CSV)",
        "health_ok": "Sistema operativo",
        "health_degraded": "BD no disponible",
        "lang_label": "Idioma",
        "bot_name": "DataVision IA",
        "you": "Usted",
    },
    # ---- English -------------------------------------------------------------
    "en": {
        "app_title": "DataVision AI",
        "app_subtitle": "Retail & Supply Chain Analytics",
        "nav_refresh": "Refresh",
        "tab_exec": "Executive",
        "tab_stock": "Stock & Sizes",
        "tab_abc": "ABC Curve",
        "tab_purchase": "Purchase Intelligence",
        "chat_title": "Inventory Copilot (RAG)",
        "chat_welcome": "Hello! Ask about SKUs, stockouts, ABC Curve, or purchasing insights.",
        "chat_placeholder": "Ask about products, SKUs or stock levels…",
        "chat_processing": "Querying SQL Server…",
        "chat_error": "Failed to reach server. Please try again.",
        "chip_1": "Low stock items",
        "chip_2": "Most expensive item",
        "chip_3": "Highest stock",
        "card_total_products": "Total Products",
        "card_stock_value": "Stock Value",
        "card_avg_stock": "Average Stock",
        "card_low_stock": "Critical Stock",
        "card_categories": "Categories",
        "chart_top_categories": "Capital Tied Up by Category (R$)",
        "chart_stock_health": "Operational Health & Stockout Risk",
        "health_critical": "Critical Stock (<= 10 units)",
        "health_healthy": "Healthy Stock (> 10 units)",
        "chart_pareto_title": "Pareto Analysis — Top 15 Products (Value vs Cumulative %)",
        "pareto_bar": "Stock Value (R$)",
        "pareto_line": "Cumulative %",
        "abc_a_title": "CLASS A (Up to 80% of Capital)",
        "abc_a_desc": "Top priority for replenishment and control",
        "abc_b_title": "CLASS B (80% to 95% of Capital)",
        "abc_b_desc": "Moderate turnover and biweekly review",
        "abc_c_title": "CLASS C (Bottom 5% of Capital)",
        "abc_c_desc": "Low financial impact on inventory",
        "abc_items_suffix": "products",
        "stock_by_cat_title": "Physical Volume Distribution by Category (Units)",
        "table_sku": "SKU",
        "table_description": "Description",
        "table_category": "Category",
        "table_stock": "Stock",
        "table_price": "Unit Price",
        "table_total_val": "Total Value",
        "table_cum_pct": "Cum. %",
        "table_abc": "ABC Curve",
        "table_grade": "Size",
        "table_count": "Count",
        "table_value": "Value",
        "table_curve": "Curve",
        "no_data": "No data available.",
        "purchase_title": "Critical Low-Stock Products — Replenishment Plan",
        "export_btn": "Export Purchase Order (.CSV)",
        "health_ok": "System operational",
        "health_degraded": "DB unavailable",
        "lang_label": "Language",
        "bot_name": "DataVision AI",
        "you": "You",
    },
}


def t(key: str, lang: str = "pt") -> str:
    """Devolve o texto traduzido para o idioma da sessão atual."""
    return I18N.get(lang, I18N["pt"]).get(key, key)


# ==================================================
# BLOCO 6 — ESTADO ISOLADO POR SESSÃO (MULTI-USER SAFE)
# ==================================================
@dataclass
class ChatMessage:
    """Representa uma mensagem enviada pelo usuário ou respondida pela IA."""
    role: str
    text: str
    products: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class UIState:
    """Estado exclusivo de cada aba/usuário conectado (sem conflito global)."""
    lang: str = "pt"
    dark_mode: bool = True
    is_loading: bool = False
    dashboard: dict[str, Any] | None = None
    messages: list[ChatMessage] = field(default_factory=list)

    # Referências aos componentes visuais da sessão
    send_btn: Any = None
    chat_input: Any = None
    chat_column: Any = None
    status_label: Any = None
    dashboard_container: Any = None
    health_label: Any = None


# ==================================================
# BLOCO 7 — FUNÇÃO AUXILIAR PARA CHAMADAS À API
# ==================================================
async def api_call(method: str, endpoint: str, **kwargs: Any) -> Any | None:
    """Executa requisições HTTP ao FastAPI e registra detalhes completos se houver erro."""
    client = get_http_client()
    try:
        response = await client.request(method, endpoint, **kwargs)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "API %s %s → HTTP %s: %s",
            method, endpoint, exc.response.status_code, exc.response.text[:200],
        )
    except httpx.RequestError as exc:
        logger.error("API %s %s → erro de rede/timeout: %r", method, endpoint, exc)
    except Exception as exc:
        logger.exception("Erro inesperado em %s %s: %s", method, endpoint, exc)
    return None


# ==================================================
# BLOCO 8 — FORMATAÇÃO, EXPORTAÇÃO E COMPONENTES VISUAIS
# ==================================================
def _fmt_currency(value: float, symbol: str = "R$") -> str:
    """Formata valores monetários no padrão brasileiro (ex: R$ 136.719,74)."""
    texto = f"{float(value):,.2f}"
    return f"{symbol} " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_int(value: int | float) -> str:
    """Formata números inteiros com separador de milhar."""
    return f"{int(value):,}".replace(",", ".")


def _card_classes(is_dark: bool) -> str:
    """Define explicitamente o fundo, borda e cor do texto do cartão conforme o tema ativo."""
    if is_dark:
        return "bg-[#111827] border border-slate-800 text-slate-100"
    return "bg-white border border-slate-200 text-slate-800"


def _export_purchase_csv(low_stock_products: list[dict[str, Any]]) -> None:
    """Gera e baixa uma planilha CSV (compatível com Excel) com sugestão de reposição."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["SKU", "Produto", "Categoria", "Estoque_Atual", "Sugestao_Compra", "Preco_Unitario", "Custo_Estimado"])

    for p in low_stock_products:
        atual = int(float(p.get("stock", 0)))
        preco = float(p.get("unit_price", 0))
        sugestao = max(15 - atual, 5)
        custo_total = round(sugestao * preco, 2)
        writer.writerow([
            p.get("sku", ""),
            p.get("description", ""),
            p.get("category", ""),
            atual,
            sugestao,
            f"{preco:.2f}".replace(".", ","),
            f"{custo_total:.2f}".replace(".", ","),
        ])

    conteudo_bytes = buffer.getvalue().encode("utf-8-sig")
    ui.download(conteudo_bytes, filename="ordem_compra_datavision.csv")


def _render_kpi_card(label: str, value: str, icon: str, accent_hex: str, is_dark: bool) -> None:
    """Renderiza um cartão executivo com contraste garantido no tema escuro e claro."""
    value_color = "text-white" if is_dark else "text-slate-900"

    with ui.card().classes(f"flex-1 min-w-44 p-4 rounded-xl shadow-sm {_card_classes(is_dark)}"):
        with ui.row().classes("items-center justify-between w-full no-wrap"):
            with ui.column().classes("gap-1"):
                ui.label(label).classes("text-xs font-medium uppercase tracking-wider text-slate-400")
                ui.label(value).classes(f"text-2xl font-bold {value_color}")
            with ui.element("div").style(
                f"background-color: {accent_hex}22; color: {accent_hex}; padding: 10px; border-radius: 12px;"
            ):
                ui.icon(icon, size="1.6rem")


def _render_product_table(products: list[dict[str, Any]], lang: str, compact: bool = False) -> None:
    """Renderiza a tabela de produtos (modo compacto para o chat ou completo para o painel)."""
    if not products:
        ui.label(t("no_data", lang)).classes("text-gray-400 italic p-4")
        return

    if compact:
        columns = [
            {"name": "sku", "label": t("table_sku", lang), "field": "sku", "align": "left"},
            {"name": "description", "label": t("table_description", lang), "field": "description", "align": "left"},
            {"name": "stock", "label": t("table_stock", lang), "field": "stock", "align": "right"},
            {"name": "unit_price", "label": t("table_price", lang), "field": "unit_price", "align": "right"},
        ]
    else:
        columns = [
            {"name": "sku", "label": t("table_sku", lang), "field": "sku", "sortable": True, "align": "left"},
            {"name": "description", "label": t("table_description", lang), "field": "description", "sortable": True, "align": "left"},
            {"name": "category", "label": t("table_category", lang), "field": "category", "sortable": True, "align": "left"},
            {"name": "stock", "label": t("table_stock", lang), "field": "stock", "sortable": True, "align": "right"},
            {"name": "unit_price", "label": t("table_price", lang), "field": "unit_price", "sortable": True, "align": "right"},
            {"name": "abc_curve", "label": t("table_abc", lang), "field": "abc_curve", "sortable": True, "align": "center"},
        ]

    rows = [
        {
            "sku": p.get("sku", ""),
            "description": p.get("description", ""),
            "category": p.get("category", ""),
            "stock": _fmt_int(p.get("stock", 0)),
            "unit_price": _fmt_currency(p.get("unit_price", 0)),
            "abc_curve": p.get("abc_curve", ""),
        }
        for p in products
    ]

    wrapper_cls = "w-full overflow-x-auto rounded-xl border border-slate-700 mt-1" if compact else "w-full rounded-xl shadow-sm"
    with ui.element("div").classes(wrapper_cls):
        ui.table(columns=columns, rows=rows, pagination=5 if compact else 10).props("dense flat" if compact else "").classes("w-full")

    
# ==================================================
# BLOCO 9 — CONTEÚDO DAS 4 ABAS DO DASHBOARD (ECHARTS + PT-BR + NOMES NO PARETO)
# ==================================================
def _build_tab_executive(data: dict[str, Any], lang: str, is_dark: bool) -> None:
    """Aba 1: 5 KPIs no topo + Grid 2 colunas de gráficos interativos Apache ECharts."""
    axis_color = "#cbd5e1" if is_dark else "#475569"
    split_color = "#1e293b" if is_dark else "#e2e8f0"

    with ui.row().classes("w-full flex-wrap gap-4 mb-4"):
        _render_kpi_card(t("card_total_products", lang), _fmt_int(data.get("total_products", 0)), "inventory_2", "#3b82f6", is_dark)
        _render_kpi_card(t("card_stock_value", lang), _fmt_currency(data.get("total_stock_value", 0)), "payments", "#10b981", is_dark)
        _render_kpi_card(t("card_avg_stock", lang), _fmt_int(data.get("avg_stock", 0)), "bar_chart", "#f59e0b", is_dark)
        _render_kpi_card(t("card_low_stock", lang), _fmt_int(data.get("low_stock_count", 0)), "warning_amber", "#ef4444", is_dark)
        _render_kpi_card(t("card_categories", lang), _fmt_int(data.get("category_count", 0)), "category", "#8b5cf6", is_dark)

    top_cats = data.get("top_categories", [])
    nomes_cat = [str(c.get("category", "")) for c in top_cats][::-1]
    valores_cat = [round(float(c.get("stock_value", 0)), 2) for c in top_cats][::-1]

    total_prod = int(data.get("total_products", 0))
    criticos = int(data.get("low_stock_count", 0))
    saudaveis = max(total_prod - criticos, 0)

    with ui.grid(columns=2).classes("w-full gap-4"):
        with ui.card().classes(f"w-full p-4 rounded-xl {_card_classes(is_dark)}"):
            ui.label(t("chart_top_categories", lang)).classes("text-base font-semibold mb-2")
            ui.echart({
                "backgroundColor": "transparent",
                "tooltip": {
                    "trigger": "axis",
                    "axisPointer": {"type": "shadow"},
                    ":formatter": "function(params) { const p = params[0]; return p.name + '<br/><b>R$ ' + Number(p.value).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '</b>'; }",
                },
                "grid": {"left": "3%", "right": "18%", "bottom": "4%", "top": "6%", "containLabel": True},
                "xAxis": {
                    "type": "value",
                    "splitLine": {"lineStyle": {"color": split_color}},
                    "axisLabel": {
                        "color": axis_color,
                        ":formatter": "function(val) { return Number(val).toLocaleString('pt-BR'); }",
                    },
                },
                "yAxis": {
                    "type": "category",
                    "data": nomes_cat,
                    "axisLabel": {"color": axis_color, "fontWeight": "bold"},
                },
                "series": [{
                    "name": "R$",
                    "type": "bar",
                    "data": valores_cat,
                    "barWidth": "55%",
                    "itemStyle": {"borderRadius": [0, 6, 6, 0], "color": "#3b82f6"},
                    "label": {
                        "show": True,
                        "position": "right",
                        "color": "#60a5fa",
                        ":formatter": "function(p) { return 'R$ ' + Number(p.value).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}); }",
                    },
                }],
            }).classes("w-full h-72")

        with ui.card().classes(f"w-full p-4 rounded-xl {_card_classes(is_dark)}"):
            ui.label(t("chart_stock_health", lang)).classes("text-base font-semibold mb-2")
            ui.echart({
                "backgroundColor": "transparent",
                "tooltip": {
                    "trigger": "item",
                    ":formatter": "function(p) { return p.name + ': <b>' + Number(p.value).toLocaleString('pt-BR') + ' SKUs</b> (' + Number(p.percent).toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1}) + '%)'; }",
                },
                "legend": {"bottom": "0%", "textStyle": {"color": axis_color}},
                "series": [{
                    "type": "pie",
                    "radius": ["48%", "74%"],
                    "center": ["50%", "44%"],
                    "itemStyle": {"borderRadius": 8, "borderColor": "#111827" if is_dark else "#ffffff", "borderWidth": 2},
                    "label": {"show": False},
                    "data": [
                        {"value": criticos, "name": t("health_critical", lang), "itemStyle": {"color": "#ef4444"}},
                        {"value": saudaveis, "name": t("health_healthy", lang), "itemStyle": {"color": "#10b981"}},
                    ],
                }],
            }).classes("w-full h-72")


def _build_tab_stock(data: dict[str, Any], lang: str, is_dark: bool) -> None:
    """Aba 2: Estoque & Grade."""
    axis_color = "#cbd5e1" if is_dark else "#475569"
    split_color = "#1e293b" if is_dark else "#e2e8f0"

    grade_dist = data.get("grade_distribution", [])
    top_cats = data.get("top_categories", [])

    if grade_dist:
        labels = [str(g.get("grade", "")) for g in grade_dist]
        values = [int(g.get("count", 0)) for g in grade_dist]
        chart_title = t("tab_stock", lang)
    else:
        labels = [str(c.get("category", "")) for c in top_cats]
        values = [int(c.get("product_count", 0)) for c in top_cats]
        chart_title = t("stock_by_cat_title", lang)

    with ui.card().classes(f"w-full p-4 rounded-xl mb-4 {_card_classes(is_dark)}"):
        ui.label(chart_title).classes("text-base font-semibold mb-2")
        ui.echart({
            "backgroundColor": "transparent",
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": labels, "axisLabel": {"color": axis_color}},
            "yAxis": {
                "type": "value",
                "splitLine": {"lineStyle": {"color": split_color}},
                "axisLabel": {
                    "color": axis_color,
                    ":formatter": "function(val) { return Number(val).toLocaleString('pt-BR'); }",
                },
            },
            "series": [{
                "type": "bar",
                "data": values,
                "barWidth": "45%",
                "itemStyle": {"color": "#f59e0b", "borderRadius": [6, 6, 0, 0]},
                "label": {
                    "show": True,
                    "position": "top",
                    "color": "#fbbf24",
                    ":formatter": "function(p) { return Number(p.value).toLocaleString('pt-BR'); }",
                },
            }],
        }).classes("w-full h-72")

    if grade_dist:
        cols = [{"name": "grade", "label": t("table_grade", lang), "field": "grade"}, {"name": "count", "label": t("table_count", lang), "field": "count"}]
        ui.table(columns=cols, rows=grade_dist).classes("w-full rounded-xl")
    elif top_cats:
        cols = [
            {"name": "category", "label": t("table_category", lang), "field": "category", "align": "left"},
            {"name": "product_count", "label": t("table_count", lang), "field": "product_count", "align": "right"},
            {"name": "stock_value", "label": t("table_value", lang), "field": "stock_value", "align": "right"},
        ]
        rows = [{**c, "stock_value": _fmt_currency(c.get("stock_value", 0))} for c in top_cats]
        ui.table(columns=cols, rows=rows).classes("w-full rounded-xl")


def _build_tab_abc(data: dict[str, Any], lang: str, is_dark: bool) -> None:
    """Aba 3: Cards das Classes A/B/C + Gráfico de Pareto com Nome dos Produtos + Tabela."""
    axis_color = "#cbd5e1" if is_dark else "#475569"
    split_color = "#1e293b" if is_dark else "#e2e8f0"
    main_val_cls = "text-lg font-bold mt-1 text-white" if is_dark else "text-lg font-bold mt-1 text-slate-900"

    abc_dist = data.get("abc_distribution", [])
    abc_products = data.get("abc_products", [])

    mapa_abc = {item.get("curve"): item for item in abc_dist}
    info_a = mapa_abc.get("A", {"count": 0, "value": 0})
    info_b = mapa_abc.get("B", {"count": 0, "value": 0})
    info_c = mapa_abc.get("C", {"count": 0, "value": 0})

    with ui.grid(columns=3).classes("w-full gap-4 mb-4"):
        with ui.card().classes(f"p-4 rounded-xl border-l-4 border-emerald-500 {_card_classes(is_dark)}"):
            ui.label(t("abc_a_title", lang)).classes("text-xs font-bold text-emerald-400")
            ui.label(f"{info_a['count']} {t('abc_items_suffix', lang)} — {_fmt_currency(info_a['value'])}").classes(main_val_cls)
            ui.label(t("abc_a_desc", lang)).classes("text-xs text-slate-400 mt-1")

        with ui.card().classes(f"p-4 rounded-xl border-l-4 border-amber-500 {_card_classes(is_dark)}"):
            ui.label(t("abc_b_title", lang)).classes("text-xs font-bold text-amber-400")
            ui.label(f"{info_b['count']} {t('abc_items_suffix', lang)} — {_fmt_currency(info_b['value'])}").classes(main_val_cls)
            ui.label(t("abc_b_desc", lang)).classes("text-xs text-slate-400 mt-1")

        with ui.card().classes(f"p-4 rounded-xl border-l-4 border-slate-500 {_card_classes(is_dark)}"):
            ui.label(t("abc_c_title", lang)).classes("text-xs font-bold text-slate-400")
            ui.label(f"{info_c['count']} {t('abc_items_suffix', lang)} — {_fmt_currency(info_c['value'])}").classes(main_val_cls)
            ui.label(t("abc_c_desc", lang)).classes("text-xs text-slate-400 mt-1")

    if abc_products:
        top_15 = abc_products[:15]
        produtos_labels = [f"{p['description']} (SKU {p['sku']})" for p in top_15]
        valores = [round(float(p["total_value"]), 2) for p in top_15]
        acumulado = [round(float(p["cumulative_pct"]), 2) for p in top_15]

        with ui.card().classes(f"w-full p-4 rounded-xl mb-4 {_card_classes(is_dark)}"):
            ui.label(t("chart_pareto_title", lang)).classes("text-base font-semibold mb-2")
            ui.echart({
                "backgroundColor": "transparent",
                "tooltip": {
                    "trigger": "axis",
                    ":formatter": "function(params) { let html = '<b>' + params[0].name + '</b>'; params.forEach(function(p) { const val = p.seriesIndex === 0 ? 'R$ ' + Number(p.value).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : Number(p.value).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '%'; html += '<br/>' + p.marker + ' ' + p.seriesName + ': <b>' + val + '</b>'; }); return html; }",
                },
                "legend": {"data": [t("pareto_bar", lang), t("pareto_line", lang)], "textStyle": {"color": axis_color}},
                "grid": {"left": "3%", "right": "3%", "top": "14%", "bottom": "18%", "containLabel": True},
                "xAxis": {
                    "type": "category",
                    "data": produtos_labels,
                    "axisLabel": {
                        "color": axis_color,
                        "rotate": 30,
                        "interval": 0,
                        ":formatter": "function(val) { const nome = val.split(' (SKU')[0]; return nome.length > 20 ? nome.slice(0, 18) + '…' : nome; }",
                    },
                },
                "yAxis": [
                    {
                        "type": "value",
                        "splitLine": {"lineStyle": {"color": split_color}},
                        "axisLabel": {
                            "color": axis_color,
                            ":formatter": "function(val) { return 'R$ ' + Number(val).toLocaleString('pt-BR'); }",
                        },
                    },
                    {
                        "type": "value",
                        "min": 0,
                        "max": 100,
                        "splitLine": {"show": False},
                        "axisLabel": {
                            "color": "#fbbf24",
                            ":formatter": "function(val) { return Number(val).toLocaleString('pt-BR') + '%'; }",
                        },
                    },
                ],
                "series": [
                    {
                        "name": t("pareto_bar", lang),
                        "type": "bar",
                        "data": valores,
                        "itemStyle": {"color": "#3b82f6", "borderRadius": [4, 4, 0, 0]},
                    },
                    {
                        "name": t("pareto_line", lang),
                        "type": "line",
                        "yAxisIndex": 1,
                        "smooth": True,
                        "data": acumulado,
                        "itemStyle": {"color": "#fbbf24"},
                        "lineStyle": {"width": 3},
                    },
                ],
            }).classes("w-full h-96")

        cols = [
            {"name": "abc_class", "label": t("table_curve", lang), "field": "abc_class", "sortable": True, "align": "center"},
            {"name": "sku", "label": t("table_sku", lang), "field": "sku", "sortable": True, "align": "left"},
            {"name": "description", "label": t("table_description", lang), "field": "description", "sortable": True, "align": "left"},
            {"name": "category", "label": t("table_category", lang), "field": "category", "sortable": True, "align": "left"},
            {"name": "stock", "label": t("table_stock", lang), "field": "stock", "sortable": True, "align": "right"},
            {"name": "total_value", "label": t("table_total_val", lang), "field": "total_value", "sortable": True, "align": "right"},
            {"name": "cumulative_pct", "label": t("table_cum_pct", lang), "field": "cumulative_pct", "sortable": True, "align": "right"},
        ]
        rows = [
            {
                "abc_class": p["abc_class"],
                "sku": p["sku"],
                "description": p["description"],
                "category": p["category"],
                "stock": _fmt_int(p["stock"]),
                "total_value": _fmt_currency(p["total_value"]),
                "cumulative_pct": f"{p['cumulative_pct']:.2f}%".replace(".", ","),
            }
            for p in abc_products
        ]
        ui.table(columns=cols, rows=rows, pagination=10).classes("w-full rounded-xl")


def _build_tab_purchase(data: dict[str, Any], lang: str, is_dark: bool) -> None:
    """Aba 4: Produtos críticos para reposição + download da Ordem de Compra."""
    low_stock = data.get("low_stock_products", [])
    title_cls = "text-base font-semibold text-white" if is_dark else "text-base font-semibold text-slate-900"

    with ui.row().classes("w-full items-center justify-between mb-3"):
        ui.label(t("purchase_title", lang)).classes(title_cls)
        if low_stock:
            ui.button(
                t("export_btn", lang),
                icon="download",
                on_click=lambda: _export_purchase_csv(low_stock),
            ).props("color=positive unelevated")

    _render_product_table(low_stock, lang, compact=False)

# ==================================================
# BLOCO 10 — RENDERIZAÇÃO DO PAINEL DE CONTROLE
# ==================================================
def _render_dashboard(container: ui.element, data: dict[str, Any] | None, lang: str, is_dark: bool) -> None:
    """Limpa e reconstrói as 4 abas do painel com os dados, idioma e tema da sessão."""
    container.clear()
    with container:
        if data is None:
            ui.label(t("no_data", lang)).classes("text-gray-400 italic p-6")
            return

        with ui.tabs().classes("w-full") as tabs:
            exec_tab = ui.tab(t("tab_exec", lang), icon="dashboard")
            stock_tab = ui.tab(t("tab_stock", lang), icon="inventory")
            abc_tab = ui.tab(t("tab_abc", lang), icon="analytics")
            purchase_tab = ui.tab(t("tab_purchase", lang), icon="shopping_cart")

        with ui.tab_panels(tabs, value=exec_tab).classes("w-full mt-2 bg-transparent"):
            with ui.tab_panel(exec_tab):
                _build_tab_executive(data, lang, is_dark)
            with ui.tab_panel(stock_tab):
                _build_tab_stock(data, lang, is_dark)
            with ui.tab_panel(abc_tab):
                _build_tab_abc(data, lang, is_dark)
            with ui.tab_panel(purchase_tab):
                _build_tab_purchase(data, lang, is_dark)


# ==================================================
# BLOCO 11 — RENDERIZAÇÃO DO CHAT (SEM CORTE DE BORDAS)
# ==================================================
def _render_chat_bubble(msg: ChatMessage, lang: str, is_dark: bool) -> None:
    """Desenha cada bolha de conversa respeitando a largura da barra lateral."""
    is_user = msg.role == "user"
    align = "items-end" if is_user else "items-start"
    if is_user:
        bubble_cls = "bg-blue-600 text-white"
    else:
        bubble_cls = (
            "bg-slate-800 text-slate-100 border border-slate-700"
            if is_dark
            else "bg-slate-100 text-slate-900 border border-slate-200"
        )
    label = t("you", lang) if is_user else t("bot_name", lang)

    with ui.column().classes(f"w-full {align} gap-1 mb-3"):
        ui.label(label).classes("text-xs text-slate-400 px-1")
        with ui.card().classes(f"max-w-[90%] {bubble_cls} shadow-sm rounded-2xl px-4 py-2 break-words"):
            ui.markdown(msg.text)

        if not is_user and msg.products:
            _render_product_table(msg.products, lang, compact=True)


def _rebuild_chat(chat_col: ui.element, state_obj: UIState) -> None:
    """Reconstrói o histórico de mensagens da sessão atual."""
    chat_col.clear()
    with chat_col:
        if not state_obj.messages:
            _render_chat_bubble(
                ChatMessage(role="bot", text=t("chat_welcome", state_obj.lang)),
                state_obj.lang,
                state_obj.dark_mode,
            )
        for msg in state_obj.messages:
            _render_chat_bubble(msg, state_obj.lang, state_obj.dark_mode)


# ==================================================
# BLOCO 12 — MANIPULADORES DE EVENTOS
# ==================================================
async def _on_send(state_obj: UIState, preset_text: str | None = None) -> None:
    """Envia a pergunta digitada (ou um botão de sugestão rápida) para o /chat."""
    if state_obj.is_loading:
        return

    raw = (preset_text if preset_text is not None else (state_obj.chat_input.value or "")).strip()
    if not raw:
        return

    state_obj.is_loading = True
    state_obj.send_btn.disable()
    state_obj.status_label.set_text(t("chat_processing", state_obj.lang))
    state_obj.status_label.set_visibility(True)
    if preset_text is None:
        state_obj.chat_input.set_value("")

    state_obj.messages.append(ChatMessage(role="user", text=raw))
    _rebuild_chat(state_obj.chat_column, state_obj)

    result = None
    try:
        result = await api_call("POST", "/chat", json={"message": raw})
    finally:
        state_obj.is_loading = False
        state_obj.send_btn.enable()
        state_obj.status_label.set_visibility(False)

    if result is None:
        state_obj.messages.append(ChatMessage(role="bot", text=t("chat_error", state_obj.lang)))
    else:
        state_obj.messages.append(
            ChatMessage(
                role="bot",
                text=result.get("answer", ""),
                products=result.get("products", []),
            )
        )

    _rebuild_chat(state_obj.chat_column, state_obj)


async def _on_refresh(state_obj: UIState) -> None:
    """Busca os indicadores atualizados no FastAPI e redesenha o dashboard."""
    data = await api_call("GET", "/dashboard/stats")
    state_obj.dashboard = data
    _render_dashboard(state_obj.dashboard_container, data, state_obj.lang, state_obj.dark_mode)
    await _update_health(state_obj)


async def _update_health(state_obj: UIState) -> None:
    """Atualiza o selo de status do SQL Server no cabeçalho."""
    result = await api_call("GET", "/health")
    db_ok = bool(result and result.get("db_status") == "ok")
    if db_ok:
        state_obj.health_label.set_text("● " + t("health_ok", state_obj.lang))
        state_obj.health_label.classes("text-emerald-400", remove="text-red-400")
    else:
        state_obj.health_label.set_text("▲ " + t("health_degraded", state_obj.lang))
        state_obj.health_label.classes("text-red-400", remove="text-emerald-400")


# ==================================================
# BLOCO 13 — LAYOUT DA PÁGINA PRINCIPAL (POR SESSÃO)
# ==================================================
@ui.page("/")
async def main_page() -> None:
    """Constrói a interface isolada por sessão de usuário."""
    saved_lang = nicegui_app.storage.user.get("lang", "pt")
    saved_dark = nicegui_app.storage.user.get("dark_mode", True)

    state = UIState(lang=saved_lang, dark_mode=saved_dark)
    dark = ui.dark_mode(state.dark_mode)

    # --------------------------
    # CABEÇALHO SUPERIOR
    # --------------------------
    with ui.header().classes(
        "flex items-center justify-between px-6 py-3 "
        "bg-slate-900 border-b border-slate-800 text-white shadow-md"
    ):
        with ui.row().classes("items-center gap-3"):
            ui.icon("insights", size="2rem").classes("text-blue-400")
            with ui.column().classes("gap-0"):
                ui.label(t("app_title", state.lang)).classes("text-lg font-bold tracking-wide leading-tight")
                ui.label(t("app_subtitle", state.lang)).classes("text-xs text-slate-400")

        with ui.row().classes("items-center gap-4"):
            state.health_label = ui.label("…").classes("text-sm font-semibold")

            # Seletor de idioma persistido na sessão do usuário
            def _change_language(e: Any) -> None:
                val = e.value if hasattr(e, "value") else str(e)
                if val in I18N:
                    nicegui_app.storage.user["lang"] = val
                    ui.navigate.reload()

            ui.label(t("lang_label", state.lang) + ":").classes("text-sm text-slate-300")
            ui.select(
                options={"pt": "Português", "es": "Español", "en": "English"},
                value=state.lang,
                on_change=_change_language,
            ).props("dense outlined dark").classes("w-32")

            # Botão de alternância de tema escuro / claro com atualização imediata dos cards
            def _toggle_theme() -> None:
                state.dark_mode = not state.dark_mode
                nicegui_app.storage.user["dark_mode"] = state.dark_mode
                dark.set_value(state.dark_mode)
                _render_dashboard(state.dashboard_container, state.dashboard, state.lang, state.dark_mode)
                _rebuild_chat(state.chat_column, state)

            ui.button(icon="contrast", on_click=_toggle_theme).props("flat round dense").classes("text-slate-200")

            # Botão de recarregar dados
            ui.button(
                t("nav_refresh", state.lang),
                icon="refresh",
                on_click=lambda: _on_refresh(state),
            ).props("outline color=primary dense").classes("px-3 font-semibold")

    # --------------------------
    # CORPO DA PÁGINA: CHAT (ESQUERDA) + DASHBOARD (DIREITA)
    # --------------------------
    with ui.row().classes("w-full gap-0 flex-nowrap overflow-hidden"):
        # COLUNA ESQUERDA — Assistente RAG
        with ui.card().classes(
            "flex flex-col w-[420px] shrink-0 h-[calc(100vh-68px)] "
            "shadow-none rounded-none border-r border-slate-800"
        ):
            with ui.row().classes("items-center gap-2 px-3 pt-2 pb-1"):
                ui.icon("smart_toy", size="1.3rem").classes("text-blue-500")
                ui.label(t("chat_title", state.lang)).classes("text-sm font-bold")

            # Botões de perguntas rápidas traduzidos nos 3 idiomas
            with ui.row().classes("w-full gap-1 px-3 pb-2 flex-wrap"):
                for chip_key in ("chip_1", "chip_2", "chip_3"):
                    chip_label = t(chip_key, state.lang)
                    ui.button(
                        chip_label,
                        on_click=lambda _, txt=chip_label: _on_send(state, preset_text=txt),
                    ).props("outline size=xs rounded").classes("text-xs")

            ui.separator()

            with ui.scroll_area().classes("flex-1 w-full px-3 py-2"):
                state.chat_column = ui.column().classes("w-full gap-0")
                _rebuild_chat(state.chat_column, state)

            ui.separator()

            state.status_label = ui.label("").classes("text-xs text-blue-400 italic px-3 py-1")
            state.status_label.set_visibility(False)

            with ui.row().classes("w-full items-center gap-2 px-3 pb-3 pt-2"):
                state.chat_input = ui.input(
                    placeholder=t("chat_placeholder", state.lang),
                ).classes("flex-1").props("outlined dense")
                state.chat_input.on("keydown.enter", lambda: _on_send(state))
                state.send_btn = ui.button(
                    icon="send",
                    on_click=lambda: _on_send(state),
                ).props("color=primary round dense")

        # COLUNA DIREITA — Painel Analítico
        with ui.scroll_area().classes("flex-1 h-[calc(100vh-68px)] p-5"):
            state.dashboard_container = ui.column().classes("w-full gap-4")
            _render_dashboard(state.dashboard_container, state.dashboard, state.lang, state.dark_mode)

    # --------------------------
    # CARGA INICIAL DOS DADOS
    # --------------------------
    await _update_health(state)
    await _on_refresh(state)

# ==================================================
# BLOCO 14 — PONTO DE ENTRADA DA APLICAÇÃO
# ==================================================
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="DataVision AI",
        host="0.0.0.0",
        port=8080,
        dark=True,
        favicon="📊",
        reload=False,
        storage_secret="datavision-ai-session-secret-2026",
    )