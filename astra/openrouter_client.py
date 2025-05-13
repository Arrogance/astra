from openai import OpenAI

class OpenRouterClient:
    def __init__(self, config):
        # URL fija del endpoint de OpenRouter
        self.base_url = "https://openrouter.ai/api/v1/"
        # La API key vendrá de tu config.json, en el campo "api_key"
        self.api_key = config["api_key"]

        # Cada cliente se instancia con su api_key y base_url
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers={
                "HTTP-Referer": config.get("referer", "https://github.com/yourusername/astra"),
                "X-Title":     config.get("title",   "Astra Chatbot")
            }
        )

    def chat_completion(self, messages, model):
        # Llamada a la API usando la instancia de OpenAI
        response = self.client.chat.completions.create(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content

def setup_openrouter(config):
    """
    Inicializa:
      - main_client: cliente principal de OpenRouterClient
      - aux_client: cliente auxiliar (mismos parámetros)
      - profile: tu perfil desde config.json
    """
    main_client = OpenRouterClient(config)
    aux_client  = OpenRouterClient(config)
    profile     = config.get("profile", {})
    return main_client, aux_client, profile
