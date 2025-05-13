# main.py

from astra.core import chat

if __name__ == "__main__":
    try:
        chat()
    except KeyboardInterrupt:
        print("\nInterrupción detectada. Cerrando Astra.")
