# main.py

from astra.core import AstraCore

if __name__ == "__main__":
    try:
        AstraCore().run_chat()
    except KeyboardInterrupt:
        print("\nInterrupción detectada. Cerrando Astra.")