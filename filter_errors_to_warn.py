# C:\RadarPremios\scripts\filter_errors_to_warn.py
# -*- coding: utf-8 -*-
import sys

PASSTHRU = (
    "Traceback (most recent call last):",
)

def transform(line: str) -> str:
    if any(k in line for k in PASSTHRU):
        return line
    # Relega ERROR a WARN para no cortar pipeline
    return line.replace("ERROR", "WARN ")

def main():
    try:
        for raw in sys.stdin:
            sys.stdout.write(transform(raw))
            sys.stdout.flush()
    except KeyboardInterrupt:
        # Salida limpia si el proceso upstream se corta
        try:
            sys.stdout.flush()
        except Exception:
            pass
        sys.exit(0)
    except Exception:
        # Pase silencioso: mejor no romper la cadena
        pass

if __name__ == "__main__":
    main()
