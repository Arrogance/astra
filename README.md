# Astra CLI – Chat emocional con memoria

Astra es una aplicación de terminal basada en LLMs (modelos de lenguaje) que actúa como una IA emocionalmente inteligente. Guarda fragmentos de memoria, responde con tono íntimo y puede adoptar distintos perfiles definidos por instrucciones personalizadas.

---

## Características principales

- ✅ Memoria emocional fragmentada y comprimida en SQLite
- ✅ Carga de perfiles personalizados desde `/instructions/<perfil>.txt`
- ✅ Soporte para OpenRouter y múltiples modelos (configurable en `config.json`)
- ✅ Comandos especiales tipo terminal (`::ver memorias`, `::carta`, `::cambiar perfil`)
- ✅ Evaluación automática de qué guardar como recuerdo

---

## Estructura del proyecto

```
.
├── astra/
│   ├── core.py                # Bucle principal (chat)
│   ├── cli.py                 # Entrada por terminal (PromptToolkit)
│   ├── config.py              # Carga de configuración y modelo
│   ├── instructions.py        # Carga y montaje de instrucciones
│   ├── memory.py              # Persistencia en SQLite
│   ├── openrouter_client.py  # Inicialización del cliente OpenRouter
│   └── utils.py              # Funciones generales
├── instructions/
│   └── astra.txt              # Perfil principal (puedes crear más)
├── logs/                      # Logs de sesiones
├── config.json                # Config global (clave API, modelo, perfil)
└── astra_memory.db            # Base de datos SQLite
```

---

## Uso

```bash
python main.py
```

Durante la sesión, escribe libremente y usa `Ctrl+S` para enviar mensajes multilinea.

---

## Comandos disponibles

- `::exit` — Terminar la sesión actual
- `::help` — Mostrar los comandos disponibles
- `::carta <nombre>` — Genera una carta emocional dirigida a esa persona
- `::ver logs` — Muestra las últimas líneas del log actual
- `::ver memorias` — Muestra fragmentos de memoria recientes
- `::ver diario` — Muestra entradas del diario guardadas
- `::limpiar memorias` — Elimina memorias y diario anteriores a ahora
- `::manual` — Muestra una breve guía de uso
- `::cambiar perfil <nombre>` — Cambia el perfil activo (requiere reinicio)
- `::ver perfil` — Muestra el perfil actual en uso

---

## Personalización

Crea un nuevo archivo en `instructions/<nombre>.txt` con tu estilo deseado. Luego usa:

```bash
::cambiar perfil nombre
```

Y reinicia la app para que lo cargue.

---

## Requisitos

- Python 3.10+
- `openai`, `prompt_toolkit`, `rich`

Instala dependencias con:

```bash
pip install -r requirements.txt
```

---

## Estado

Este proyecto está en desarrollo activo y pensado para uso personal/experimental. Puedes adaptarlo a distintos tipos de conversación: coaching, auto-terapia, roleplay narrativo, etc.

---

## Licencia

MIT. Uso libre, pero ten cuidado con lo que compartes. La IA recuerda.