# -*- coding: utf-8 -*-
import os
import sqlite3
import pandas as pd
from pathlib import Path

ROOT = r"C:\RadarPremios"
DB_PATH = os.path.join(ROOT, "radar_premios.db")
OUT_CSV = os.path.join(ROOT, "data", "limpio", "matriz_astro_luna.csv")

def fail(msg): 
    print(f"[ERROR] {msg}")
    raise SystemExit(1)

def main():
    Path(os.path.dirname(OUT_CSV)).mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)

    # Verificación de esquema requerido
    cols = [r[1] for r in con.execute("PRAGMA table_info(astro_luna)")]
    req = {"fecha","numero","signo"}
    if not req.issubset(set(cols)):
        fail(f"astro_luna sin columnas requeridas {req}. Encontradas: {cols}")

    # Trae datos base
    df = pd.read_sql_query("SELECT fecha, numero, signo FROM astro_luna", con)
    if df.empty:
        fail("astro_luna está vacío, no se puede generar matriz.")

    # ----- ejemplo simple de matriz (ajusta tu propia lógica) -----
    # matriz por fecha, conteos por signo y último número
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    pivot_signo = df.pivot_table(index="fecha", columns="signo", values="numero", aggfunc="count").fillna(0)
    pivot_signo = pivot_signo.astype(int).reset_index()

    # Une con últimos números del día (si aplica)
    last_num = df.sort_values(["fecha"]).groupby("fecha")["numero"].last().rename("numero_ultimo").reset_index()
    matriz = pivot_signo.merge(last_num, on="fecha", how="left")

    # Guarda a CSV y, en cargar_db.py, se volcará a la tabla matriz_astro_luna
    matriz.to_csv(OUT_CSV, index=False, encoding="utf-8")
    print(f"✅ Matriz generada: {OUT_CSV} ({len(matriz):,} filas)")

if __name__ == "__main__":
    main()
