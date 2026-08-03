import ollama

class AIService:
    @staticmethod
    def generate_pipeline_insight(pipeline_name: str, source_type: str, description: str) -> str:
        prompt = f"""
        Você é um especialista em Engenharia de Dados e Analytics.
        Análise o seguinte pipeline de dados e forneça 3 sugestões de otimização ou boas práticas em português:
        
        - Nome do Pipeline: {pipeline_name}
        - Fonte de Dados: {source_type}
        - Descrição: {description}
        """
        
        try:
            response = ollama.chat(model="phi3", messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ])
            return response["message"]["content"]
        except Exception as e:
            return f"Erro ao conectar com Ollama: {str(e)}"

