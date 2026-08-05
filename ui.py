from nicegui import ui
import httpx
import asyncio

# Configuração da Página
ui.page_title('DataVision AI — Business Intelligence & Chat')

# Cores e Estilos Customizados
DARK_BG = '#0f172a'
CARD_BG = '#1e293b'
TEXT_COLOR = '#f8fafc'
ACCENT_COLOR = '#38bdf8'

# URL do Backend FastAPI
BACKEND_URL = "http://127.0.0.1:8000"

async def fetch_kpis():
    """Busca dados agregados do backend para preencher os cartões do Dashboard."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/api/sql/kpis", timeout=5.0)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"Error fetching KPIs: {e}")
    # Dados fallback caso a API não responda
    return {
        "total_produtos": 120,
        "faturamento_estimado": "$145,200",
        "preco_medio": "$1,210",
        "top_categoria": "Electrónica"
    }

@ui.page('/')
async def main_page():
    ui.query('body').style(f'background-color: {DARK_BG}; color: {TEXT_COLOR}; margin: 0; padding: 0;')

    # --- BARRA SUPERIOR (HEADER) ---
    with ui.header().classes('bg-slate-900 text-white flex justify-between items-center px-6 py-3 border-b border-slate-800'):
        with ui.row().classes('items-center gap-3'):
            ui.icon('analytics', size='32px', color='sky-400')
            ui.label('DataVision AI').classes('text-xl font-bold tracking-wide text-sky-400')
            ui.label('| Plataforma de Inteligencia de Datos').classes('text-sm text-slate-400 hidden md:block')
        
        with ui.row().classes('items-center gap-4'):
            ui.badge('Local Engine (Phi-3)', color='emerald-600').classes('px-3 py-1 text-xs')
            ui.icon('language', size='24px').classes('text-slate-400')
            ui.label('ES').classes('text-xs text-slate-300 font-bold')

    # --- LAYOUT PRINCIPAL (DIVIDIDO EM 2 COLUNAS) ---
    with ui.row().classes('w-full h-[calc(100vh-65px)] gap-0 no-wrap'):

        # ==========================================
        # PAINEL ESQUERDO: CHAT DE IA (40% de largura)
        # ==========================================
        with ui.column().classes('w-2/5 h-full bg-slate-900 border-r border-slate-800 p-4 justify-between'):
            # Cabeçalho do Chat
            with ui.row().classes('w-full items-center justify-between pb-3 border-b border-slate-800'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('smart_toy', color='sky-400', size='24px')
                    ui.label('Asistente de Consulta').classes('font-semibold text-base text-slate-200')
                ui.button(icon='refresh', on_click=lambda: chat_messages.clear()).props('flat round dense color=slate-400')

            # Áreas de Mensagens do Chat
            chat_messages = ui.column().classes('w-full flex-grow overflow-y-auto my-3 gap-3 pr-2 custom-scroll')

            # Mensagem de Boas-Vindas Inicial
            with chat_messages:
                with ui.chat_message(name='DataVision Bot', avatar='https://robohash.org/datavision.png?set=set1', stamp='Ahora'):
                    ui.markdown('¡Hola! Soy tu asistente de datos. Puedes hacerme preguntas sobre **productos, facturación** o subir un **documento PDF** para analizar.')

            # Área de Input e Envio
            async def send_message():
                text = input_field.value.strip()
                if not text:
                    return

                input_field.value = ''
                
                # Mensagem do Usuário
                with chat_messages:
                    with ui.chat_message(name='Tú', sent=True, stamp='Ahora'):
                        ui.label(text)
                
                # Loader do Bot
                with chat_messages:
                    spinner = ui.spinner('dots', size='lg', color='sky-400')

                try:
                    async with httpx.AsyncClient() as client:
                        # Envia para a API SQL ou RAG dependendo do contexto
                        res = await client.post(f"{BACKEND_URL}/api/sql/ask-products", json={"prompt": text}, timeout=30.0)
                        bot_response = res.json().get("response", "No se pudo obtener una respuesta.")
                except Exception as ex:
                    bot_response = f"Error al conectar con el servidor: {ex}"

                spinner.delete()

                # Resposta do Bot
                with chat_messages:
                    with ui.chat_message(name='DataVision Bot', avatar='https://robohash.org/datavision.png?set=set1', stamp='Ahora'):
                        ui.markdown(bot_response)

            with ui.column().classes('w-full gap-2 pt-2 border-t border-slate-800'):
                with ui.row().classes('w-full items-center gap-2'):
                    input_field = ui.input(placeholder='Escribe tu pregunta aquí...').classes('flex-grow').props('dark rounded outlined dense bg-slate-800')
                    input_field.on('keydown.enter', send_message)
                    ui.button(icon='send', on_click=send_message).props('unelevated round color=sky-500 text-white')

                # Botão para Upload de Arquivos
                with ui.row().classes('w-full justify-between items-center text-xs text-slate-400 px-1'):
                    ui.upload(on_upload=lambda e: ui.notify(f'Archivo subido: {e.name}'), auto_upload=True).props('flat dense label="Adjuntar PDF/TXT" color=sky-400')

        # ==========================================
        # PAINEL DIREITO: DASHBOARD (60% de largura)
        # ==========================================
        with ui.column().classes('w-3/5 h-full bg-slate-950 p-6 overflow-y-auto gap-6'):
            
            # Título do Dashboard
            with ui.row().classes('w-full justify-between items-center'):
                with ui.column().classes('gap-0'):
                    ui.label('Panel de Control Operativo').classes('text-2xl font-bold text-slate-100')
                    ui.label('Métricas en tiempo real sincronizadas con SQL Server').classes('text-xs text-slate-400')
                ui.button('Actualizar Datos', icon='sync', on_click=lambda: ui.notify('Datos actualizados')).props('outline color=sky-400 size=sm')

            # --- BLOCO 1: CARTÕES DE METRICAS (KPIs) ---
            kpis = await fetch_kpis()
            with ui.grid(columns=4).classes('w-full gap-4'):
                
                # KPI 1
                with ui.card().classes('bg-slate-900 border border-slate-800 p-4 rounded-xl gap-1'):
                    ui.label('Total Productos').classes('text-xs font-medium text-slate-400 uppercase tracking-wider')
                    ui.label(str(kpis.get('total_produtos', '120'))).classes('text-2xl font-extrabold text-sky-400')
                    ui.label('↑ +12% este mes').classes('text-[10px] text-emerald-400')

                # KPI 2
                with ui.card().classes('bg-slate-900 border border-slate-800 p-4 rounded-xl gap-1'):
                    ui.label('Facturación Est.').classes('text-xs font-medium text-slate-400 uppercase tracking-wider')
                    ui.label(str(kpis.get('faturamento_estimado', '$145.200'))).classes('text-2xl font-extrabold text-emerald-400')
                    ui.label('Calculado vía SQL Engine').classes('text-[10px] text-slate-400')

                # KPI 3
                with ui.card().classes('bg-slate-900 border border-slate-800 p-4 rounded-xl gap-1'):
                    ui.label('Precio Promedio').classes('text-xs font-medium text-slate-400 uppercase tracking-wider')
                    ui.label(str(kpis.get('preco_medio', '$1.210'))).classes('text-2xl font-extrabold text-amber-400')
                    ui.label('Promedio ponderado').classes('text-[10px] text-slate-400')

                # KPI 4
                with ui.card().classes('bg-slate-900 border border-slate-800 p-4 rounded-xl gap-1'):
                    ui.label('Top Creador/Cat.').classes('text-xs font-medium text-slate-400 uppercase tracking-wider')
                    ui.label(str(kpis.get('top_categoria', 'Electrónica'))).classes('text-xl font-bold text-indigo-400 truncate')
                    ui.label('Mayor volumen').classes('text-[10px] text-slate-400')

            # --- BLOCO 2: GRÁFICOS INTERATIVOS (ECHARTS) ---
            with ui.grid(columns=2).classes('w-full gap-6 flex-grow'):
                
                # Gráfico 1: Ventas / Precios por Categoría (Bar Chart)
                with ui.card().classes('bg-slate-900 border border-slate-800 p-4 rounded-xl w-full flex-col justify-between'):
                    ui.label('Distribución de Precios por Categoría').classes('text-sm font-semibold text-slate-200 mb-2')
                    ui.echart({
                        'textStyle': {'color': '#94a3b8'},
                        'tooltip': {'trigger': 'axis'},
                        'xAxis': {
                            'type': 'category',
                            'data': ['Electrónica', 'Hogar', 'Oficina', 'Servicios', 'Software'],
                            'axisLine': {'lineStyle': {'color': '#334155'}}
                        },
                        'yAxis': {
                            'type': 'value',
                            'splitLine': {'lineStyle': {'color': '#1e293b'}}
                        },
                        'series': [{
                            'data': [1200, 850, 450, 920, 1500],
                            'type': 'bar',
                            'itemStyle': {'color': '#38bdf8', 'borderRadius': [4, 4, 0, 0]}
                        }]
                    }).classes('w-full h-64')

                # Gráfico 2: Proporción de Stock / Categorías (Doughnut Chart)
                with ui.card().classes('bg-slate-900 border border-slate-800 p-4 rounded-xl w-full flex-col justify-between'):
                    ui.label('Participación de Inventario').classes('text-sm font-semibold text-slate-200 mb-2')
                    ui.echart({
                        'textStyle': {'color': '#94a3b8'},
                        'tooltip': {'trigger': 'item'},
                        'legend': {'bottom': '0', 'textStyle': {'color': '#94a3b8'}},
                        'series': [{
                            'name': 'Productos',
                            'type': 'pie',
                            'radius': ['40%', '70%'],
                            'avoidLabelOverlap': False,
                            'itemStyle': {'borderRadius': 6, 'borderColor': '#0f172a', 'borderWidth': 2},
                            'label': {'show': False},
                            'data': [
                                {'value': 1048, 'name': 'Electrónica', 'itemStyle': {'color': '#38bdf8'}},
                                {'value': 735, 'name': 'Software', 'itemStyle': {'color': '#818cf8'}},
                                {'value': 580, 'name': 'Hogar', 'itemStyle': {'color': '#34d399'}},
                                {'value': 484, 'name': 'Oficina', 'itemStyle': {'color': '#fbbf24'}}
                            ]
                        }]
                    }).classes('w-full h-64')

# Inicialização da App
ui.run(port=8080, dark=True, reload=False)