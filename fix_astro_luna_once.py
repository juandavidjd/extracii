# -*- coding: utf-8 -*-
import os, sqlite3, pandas as pd
from pathlib import Path

ROOT = r"C:\RadarPremios"
DB = os.path.join(ROOT, "radar_premios.db")
CSV = os.path.join(ROOT, "data", "limpio", "astro_luna.csv")

def main():
    if not Path(CSV).exists():
        print(f"❌ No existe {CSV}")
        raise SystemExit(1)

    df = pd.read_csv(CSV)
    df.columns = [c.strip().lower() for c in df.columns]

    ren = {}
    if "fecha" not in df.columns:
        for c in ("date","Fecha","FECHA"):
            if c.lower() in df.columns: ren[c.lower()] = "fecha"; break
    if "numero" not in df.columns:
        for c in ("número","num","NUMERO","Número"):
            if c.lower() in df.columns: ren[c.lower()] = "numero"; break
    if "signo" not in df.columns:
        for c in ("zodiac","SIGNO","Signo"):
            if c.lower() in df.columns: ren[c.lower()] = "signo"; break
    if ren: df = df.rename(columns=ren)

    missing = [c for c in ("fecha","numero","signo") if c not in df.columns]
    if missing:
        print(f"❌ astro_luna.csv inválido, faltan {missing}")
        raise SystemExit(1)

    df = df[["fecha","numero","signo"]].copy()
    df["fecha"]  = pd.to_datetime(df["fecha"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["numero"] = df["numero"].astype(str).str.strip()
    df["signo"]  = df["signo"].astype(str).str.strip().str.lower()

    con = sqlite3.connect(DB)
    df.to_sql("astro_luna", con, if_exists="replace", index=False)
    con.execute("CREATE INDEX IF NOT EXISTS idx_astro_fecha ON astro_luna(fecha)")
    con.commit()
    print(f"✅ astro_luna RECREADA ({len(df):,} filas}) en {DB}")

if __name__ == "__main__":
    main()
