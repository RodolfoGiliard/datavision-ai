from nicegui import ui
import httpx
import plotly.graph_objects as go

# URL da sua API FastAPI
API_URL = "http://127.0.0.1:8000/api/sql/ask-products"

# Estilização global do corpo da página (Dark Mode)
ui.query('body').style('background-color: #0f172a; color: #f8fafc; font-family: Inter, sans-serif;')

# Cabeçalho Principal
with ui.header().classes('bg-slate-900 text-white p-4 justify-between items-center border-b border-slate-800'):
    ui.label('⚡ DataVision AI - Painel Executivo').classes('text-xl font-bold tracking-wide text-cyan-400')
    ui.label('Conectado: SQL Server (newstore)').classes('text-xs text-slate-400 bg-slate-800 px-3 py-1 rounded-full')

with ui.column().classes('w-full max-w-6xl mx-auto p-6 gap-6'):

    # SEÇÃO 1: AÇÕES RÁPIDAS (BOTÕES DE 1 CLIQUE)
    ui.label('Ações Rápidas (1 Clique)').classes('text-sm font-semibold text-slate-400 uppercase tracking-wider')
    
    # Função ASSÍNCRONA para não travar a conexão WebSocket da interface
    async def executar_pergunta_rapida(pergunta):
        spinner.visible = True
        resposta_card.set_text("Consultando banco de dados via FastAPI...")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(API_URL, data={"question": pergunta})
                
                if response.status_code == 200:
                    dados = response.json()
                    resposta_card.set_text(dados.get("answer", "Sem resposta da IA."))
                else:
                    resposta_card.set_text(f"Erro na API (Status {response.status_code}): {response.text}")
        except Exception as e:
            resposta_card.set_text(f"Erro ao comunicar com a API: {str(e)}")
        finally:
            spinner.visible = False

    with ui.row().classes('w-full gap-4'):
        ui.button('🏷️ Produto Mais Barato', on_click=lambda: executar_pergunta_rapida('Qual o produto mais barato?')) \
            .classes('bg-slate-800 hover:bg-cyan-600 text-white font-medium rounded-lg px-4 py-2 border border-slate-700 transition-all')
            
        ui.button('💎 Produto Mais Caro', on_click=lambda: executar_pergunta_rapida('Qual o produto mais caro?')) \
            .classes('bg-slate-800 hover:bg-cyan-600 text-white font-medium rounded-lg px-4 py-2 border border-slate-700 transition-all')
            
        ui.button('📊 Resumo por Categoria', on_click=lambda: executar_pergunta_rapida('Quais as categorias de produtos existentes e quantos produtos há em cada?')) \
            .classes('bg-slate-800 hover:bg-cyan-600 text-white font-medium rounded-lg px-4 py-2 border border-slate-700 transition-all')

    # Card onde aparece a resposta da IA/SQL
    with ui.card().classes('w-full bg-slate-900 border border-slate-800 p-4 rounded-xl'):
        with ui.row().classes('items-center gap-2'):
            ui.icon('smart_toy', size='sm', color='cyan-400')
            ui.label('Resposta da IA (Phi-3 + SQL Server)').classes('font-bold text-slate-200')
            spinner = ui.spinner(size='sm', color='cyan').classes('hidden')
            
        resposta_card = ui.label('Clique em um botão acima ou faça uma pergunta abaixo...').classes('text-slate-300 mt-2 text-sm leading-relaxed')

    # SEÇÃO 2: GRÁFICO INTERATIVO (PLOTLY)
    ui.label('Análise Visual de Dados').classes('text-sm font-semibold text-slate-400 uppercase tracking-wider mt-4')
    
    fig = go.Figure(data=[
        go.Bar(
            x=['Calça Modelo 71', 'Camiseta Dry', 'Bermuda Sport', 'Jaqueta Jeans'],
            y=[69.61, 89.90, 110.00, 250.00],
            marker_color=['#06b6d4', '#3b82f6', '#6366f1', '#8b5cf6']
        )
    ])
    fig.update_layout(
        title='Preço dos Produtos (R$)',
        paper_bgcolor='rgba(15,23,42,1)',
        plot_bgcolor='rgba(15,23,42,1)',
        font=dict(color='#94a3b8'),
        margin=dict(l=20, r=20, t=40, b=20),
        height=300
    )
    
    ui.plotly(fig).classes('w-full rounded-xl overflow-hidden border border-slate-800')

    # SEÇÃO 3: CHAT LIVRE COM A IA
    ui.label('Perguntar ao Banco SQL').classes('text-sm font-semibold text-slate-400 uppercase tracking-wider mt-4')
    
    with ui.row().classes('w-full gap-2 items-center'):
        campo_pergunta = ui.input(placeholder='Digite sua dúvida ex: Qual a média de preço dos produtos?').classes('grow bg-slate-900 text-white rounded-lg px-3')
        
        async def enviar_chat():
            texto = campo_pergunta.value.strip()
            if texto:
                campo_pergunta.value = ''
                await executar_pergunta_rapida(texto)

        ui.button('Enviar', on_click=enviar_chat).classes('bg-cyan-500 hover:bg-cyan-600 text-slate-950 font-bold px-6 py-2 rounded-lg')

# Executa o painel
ui.run(title="DataVision AI", port=8080, dark=True)