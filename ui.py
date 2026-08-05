import httpx
from nicegui import ui

API_URL = "http://127.0.0.1:8000"

ui.query("body").style("font-family: 'Inter', sans-serif; background-color: #f8fafc;")

with ui.header().classes("bg-slate-900 text-white p-4 flex justify-between items-center shadow-lg"):
    ui.label("DataVision AI — Code-First RAG & SQL").classes("text-xl font-bold tracking-wide")
    ui.badge("Online", color="green-6").classes("text-sm px-3 py-1")

with ui.tabs().classes("w-full bg-slate-800 text-white shadow-md") as tabs:
    tab_sql = ui.tab("Consulta SQL Server", icon="storage")
    tab_rag = ui.tab("Análise de Documentos (RAG)", icon="description")

with ui.tab_panels(tabs, value=tab_sql).classes("w-full max-w-4xl mx-auto p-6 bg-white shadow-xl rounded-b-xl my-6"):
    
    # PAINEL 1: CONSULTA SQL
    with ui.tab_panel(tab_sql):
        ui.label("Pergunte ao seu Banco de Dados (dbo.produtos)").classes("text-lg font-bold text-slate-800 mb-2")
        ui.label("O LLM e a engine traduzem sua pergunta e consultam os dados em tempo real.").classes("text-sm text-slate-500 mb-4")
        
        sql_chat_container = ui.column().classes("w-full gap-3 mb-4 max-h-96 overflow-y-auto p-4 bg-slate-50 rounded-lg border border-slate-200")
        
        with ui.row().classes("w-full items-center gap-2"):
            sql_input = ui.input(placeholder="Ex: Qual o produto mais caro?").classes("flex-1").on("keydown.enter", lambda: ask_sql())
            sql_button = ui.button("Perguntar", on_click=lambda: ask_sql()).classes("bg-blue-600 text-white font-medium px-6 py-2 rounded-lg hover:bg-blue-700")

    # PAINEL 2: RAG / DOCUMENTOS
    with ui.tab_panel(tab_rag):
        ui.label("Análise de Documentos (PDF / TXT)").classes("text-lg font-bold text-slate-800 mb-2")
        
        uploaded_file = {"file": None}

        def handle_upload(e):
            uploaded_file["file"] = e
            ui.notify(f"Arquivo '{e.name}' carregado!", type="positive")

        ui.upload(on_upload=handle_upload, max_files=1, auto_upload=True).classes("w-full mb-4")
        
        rag_chat_container = ui.column().classes("w-full gap-3 mb-4 max-h-96 overflow-y-auto p-4 bg-slate-50 rounded-lg border border-slate-200")
        
        with ui.row().classes("w-full items-center gap-2"):
            rag_input = ui.input(placeholder="Escreva sua pergunta...").classes("flex-1").on("keydown.enter", lambda: ask_rag())
            rag_button = ui.button("Analisar", on_click=lambda: ask_rag()).classes("bg-emerald-600 text-white font-medium px-6 py-2 rounded-lg hover:bg-emerald-700")


# FUNÇÕES ASSÍNCRONAS DA UI

async def ask_sql():
    question = sql_input.value.strip()
    if not question:
        ui.notify("Por favor, digite uma pergunta.", type="warning")
        return
    
    with sql_chat_container:
        ui.chat_message(question, name="Você", sent=True).classes("text-slate-800")
    
    sql_input.value = ""
    
    with sql_chat_container:
        spinner = ui.spinner(size="md").classes("my-2")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{API_URL}/api/sql/ask-products", data={"question": question})
        
        spinner.delete()
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "Sem resposta.")
            with sql_chat_container:
                ui.chat_message(answer, name="DataVision AI (SQL)", stamp="SQL Server / Phi-3").classes("bg-blue-50 text-slate-900")
        else:
            ui.notify(f"Erro na API ({response.status_code}): {response.text}", type="negative")
            
    except Exception as e:
        spinner.delete()
        ui.notify(f"Erro de comunicação: {e}", type="negative")


async def ask_rag():
    question = rag_input.value.strip()
    if not question:
        ui.notify("Digite uma pergunta sobre o documento.", type="warning")
        return
    
    if not uploaded_file["file"]:
        ui.notify("Faça o upload de um arquivo primeiro!", type="warning")
        return

    with rag_chat_container:
        ui.chat_message(question, name="Você", sent=True)
    
    rag_input.value = ""
    
    with rag_chat_container:
        spinner = ui.spinner(size="md").classes("my-2")
    
    try:
        file_obj = uploaded_file["file"]
        files = {"file": (file_obj.name, file_obj.content, file_obj.type)}
        data = {"question": question}
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{API_URL}/api/rag/ask-document", files=files, data=data)
            
        spinner.delete()
        
        if response.status_code == 200:
            res_data = response.json()
            answer = res_data.get("answer", "Sem resposta.")
            with rag_chat_container:
                ui.chat_message(answer, name="DataVision AI (RAG)", stamp="Ollama/Phi-3").classes("bg-emerald-50 text-slate-900")
        else:
            ui.notify(f"Erro no RAG: {response.text}", type="negative")
    except Exception as e:
        spinner.delete()
        ui.notify(f"Erro de execução: {e}", type="negative")


ui.run(title="DataVision AI", port=8080)