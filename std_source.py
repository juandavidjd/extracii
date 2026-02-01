# -*- coding: utf-8 -*-
"""
std_source.py
Capa de acceso estándar para RadarPremios.

Proporciona:
- connect(db_path) -> sqlite3.Connection
- sanity_check_source(conn, game)
- load_draws(conn, game) -> lista [(fecha, 'NNNN'), ...] para juegos 4D
- load_n5sb(conn, game) -> lista [(fecha, n1,n2,n3,n4,n5,sb), ...] para N5+SB
- runs_has_column(conn, col) -> bool

Diseño:
- Evita depender de 'all_std'. En su lugar, elige vistas específicas por juego.
- Acepta tanto vistas como tablas para *_std.
- Soporta 'num' o 'numero' y lo expone como 'num'.
- Para astro_luna: prioriza 'astro_luna_std', luego 'v_matriz_astro_luna_std'.
- Para n5+sb: usa 'baloto_n5sb_std', 'revancha_n5sb_std' o 'all_n5sb_std'.
"""

import os
import re
import sqlite3
from typing import List, Tuple, Optional, Iterable, Dict

# ---------------- Conexión ----------------

def connect(db_path: str) -> sqlite3.Connection:
    """
    Abre conexión SQLite con pragmas seguros por defecto.
    """
    cnx = sqlite3.connect(db_path)
    try:
        cnx.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    try:
        cnx.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    try:
        cnx.execute("PRAGMA foreign_keys=ON;")
    except Exception:
        pass
    return cnx


# ---------------- Utilidades internas ----------------

def _has_obj(cnx: sqlite3.Connection, name: str) -> bool:
    q = "SELECT 1 FROM sqlite_master WHERE (type='view' OR type='table') AND name=? LIMIT 1"
    return cnx.execute(q, (name,)).fetchone() is not None

def _columns(cnx: sqlite3.Connection, name: str) -> List[str]:
    try:
        return [r[1] for r in cnx.execute(f"PRAGMA table_info({name})")]
    except Exception:
        return []

def _pick_num_col(cols: Iterable[str]) -> Optional[str]:
    cols_set = {c.lower() for c in cols}
    if "num" in cols_set:
        return "num"
    if "numero" in cols_set:
        return "numero"
    return None

def _quote_ident(name: str) -> str:
    # Escapa " por "" y rodea con comillas dobles
    return '"' + name.replace('"', '""') + '"'

def _is_4d_view(cnx: sqlite3.Connection, name: str) -> bool:
    """
    Heurística: vista/tabla con 'fecha' y ('num'|'numero').
    """
    cols = _columns(cnx, name)
    if not cols:
        return False
    cols_low = {c.lower() for c in cols}
    if "fecha" in cols_low and ("num" in cols_low or "numero" in cols_low):
        return True
    return False

def _discover_4d_views(cnx: sqlite3.Connection) -> List[str]:
    """
    Descubre vistas/tablas *_std que cumplan con (fecha, num|numero).
    """
    names = [r[0] for r in cnx.execute("SELECT name FROM sqlite_master WHERE (type='view' OR type='table') AND name LIKE '%_std'")]
    out = []
    for n in names:
        try:
            if _is_4d_view(cnx, n):
                out.append(n)
        except Exception:
            continue
    # Orden estable: astro_luna primero si existe
    out.sort()
    if "astro_luna_std" in out:
        out.remove("astro_luna_std")
        out.insert(0, "astro_luna_std")
    return out

def _find_first(cnx: sqlite3.Connection, candidates: List[str]) -> Optional[str]:
    for n in candidates:
        if _has_obj(cnx, n):
            return n
    return None

def _normalize_num_4d(x: str) -> Optional[str]:
    """
    Deja solo dígitos y normaliza a 4 dígitos (0000..9999).
    """
    if x is None:
        return None
    s = re.sub(r"\D+", "", str(x).strip())
    if s == "":
        return None
    try:
        v = int(s)
    except Exception:
        return None
    if 0 <= v <= 9999:
        return f"{v:04d}"
    # Si trae más de 4 dígitos, no es 4D (descartamos)
    return None


# ---------------- Fuente por juego (4D) ----------------

def _source_4d_for_game(cnx: sqlite3.Connection, game: str) -> Optional[Tuple[str, str]]:
    """
    Devuelve (name, numcol) del origen 4D para el juego dado, o None si no hay.
    name puede ser vista o tabla.
    numcol ∈ {'num', 'numero'}
    """
    g = (game or "").lower().strip()

    if g in ("astro_luna", "astro", "astro luna"):
        # preferencia clara
        pref = _find_first(cnx, ["astro_luna_std", "v_matriz_astro_luna_std"])
        if pref:
            numcol = _pick_num_col(_columns(cnx, pref))
            if numcol:
                return (pref, numcol)

    elif g in ("boyaca", "huila", "manizales", "medellin", "quindio", "tolima"):
        name = f"{g}_std"
        if _has_obj(cnx, name):
            numcol = _pick_num_col(_columns(cnx, name))
            if numcol:
                return (name, numcol)

    elif g in ("all4d", "all_4d", "loterias"):
        # Unión de todas las vistas/tabl *_std con (fecha,num|numero)
        # Para sanity_check podemos fabricar un subquery UNION ALL
        # (gestionado en _source_sql_4d_union)
        views = _discover_4d_views(cnx)
        if views:
            # devolvemos un indicador especial (None) para que el caller construya la UNION
            return ("__UNION_ALL__", "num")

    # fallback dinámico: primer *_std con (fecha, num|numero)
    views = _discover_4d_views(cnx)
    if views:
        name = views[0]
        numcol = _pick_num_col(_columns(cnx, name))
        if numcol:
            return (name, numcol)

    return None


def _source_sql_4d_single(name: str, numcol: str) -> str:
    qname = _quote_ident(name)
    qnum  = _quote_ident(numcol)
    # Normalizamos a alias 'num'
    return f"SELECT fecha, {qnum} AS num FROM {qname} WHERE {qnum} IS NOT NULL"

def _source_sql_4d_union(cnx: sqlite3.Connection) -> Optional[str]:
    parts: List[str] = []
    for name in _discover_4d_views(cnx):
        numcol = _pick_num_col(_columns(cnx, name))
        if not numcol:
            continue
        parts.append(_source_sql_4d_single(name, numcol))
    if not parts:
        return None
    return " \nUNION ALL\n".join(parts)


# ---------------- Fuente por juego (N5+SB) ----------------

def _source_n5sb_for_game(cnx: sqlite3.Connection, game: str) -> Optional[str]:
    """
    Devuelve el nombre de la vista/tabla n5sb para el juego: baloto/revancha/n5sb/all_n5sb
    """
    g = (game or "").lower().strip()
    if g == "baloto":
        return _find_first(cnx, ["baloto_n5sb_std"])
    if g == "revancha":
        return _find_first(cnx, ["revancha_n5sb_std"])
    if g in ("n5sb", "all_n5sb", "baloto_revancha"):
        return _find_first(cnx, ["all_n5sb_std", "baloto_n5sb_std"])
    # fallback general
    return _find_first(cnx, ["all_n5sb_std", "baloto_n5sb_std", "revancha_n5sb_std"])


# ---------------- API pública ----------------

def sanity_check_source(cnx: sqlite3.Connection, game: str) -> None:
    """
    Verifica que existe una fuente válida para el juego y que expone 'fecha' y 'num' (si es 4D),
    o 'fecha, n1..n5, sb' (si es n5+sb). Lanza RuntimeError con detalle si falla.
    """
    g = (game or "").lower().strip()
    is_4d = g in ("astro_luna","astro","astro luna","boyaca","huila","manizales","medellin","quindio","tolima","all4d","all_4d","loterias")
    is_n5 = g in ("baloto","revancha","n5sb","all_n5sb","baloto_revancha")

    if is_4d:
        src = _source_4d_for_game(cnx, g)
        if not src:
            raise RuntimeError(f"No se encontró fuente 4D válida para '{game}'. Verifica vistas *_std.")
        name, numcol = src
        if name == "__UNION_ALL__":
            sql = _source_sql_4d_union(cnx)
            if not sql:
                raise RuntimeError("No hay componentes para la unión all4d.")
            probe = f"SELECT fecha, num FROM ({sql}) LIMIT 1"
        else:
            sql = _source_sql_4d_single(name, numcol)
            probe = f"SELECT fecha, num FROM ({sql}) LIMIT 1"
        try:
            cnx.execute(probe).fetchone()
        except Exception as e:
            raise RuntimeError(f"Error verificando fuente 4D '{game}': {e}")

    elif is_n5:
        name = _source_n5sb_for_game(cnx, g)
        if not name:
            raise RuntimeError(f"No se encontró fuente n5+sb válida para '{game}'.")
        cols = {c.lower() for c in _columns(cnx, name)}
        needed = {"fecha","n1","n2","n3","n4","n5","sb"}
        if not needed.issubset(cols):
            raise RuntimeError(f"'{name}' no contiene columnas requeridas {sorted(needed)} (tiene {sorted(cols)}).")
        try:
            probe = f'SELECT fecha,n1,n2,n3,n4,n5,sb FROM "{name}" LIMIT 1'
            cnx.execute(probe).fetchone()
        except Exception as e:
            raise RuntimeError(f"Error verificando fuente n5+sb '{game}': {e}")

    else:
        # Por defecto, intentamos como 4D (comportamiento más común en tu pipeline)
        return sanity_check_source(cnx, "astro_luna")


def load_draws(cnx: sqlite3.Connection, game: str) -> List[Tuple[str, str]]:
    """
    Retorna lista de (fecha_iso, 'NNNN') ordenada por fecha (asc) para juegos 4D.
    Si el juego no es 4D, retorna lista vacía.
    """
    g = (game or "").lower().strip()
    is_4d = g in ("astro_luna","astro","astro luna","boyaca","huila","manizales","medellin","quindio","tolima","all4d","all_4d","loterias")
    if not is_4d:
        return []

    src = _source_4d_for_game(cnx, g)
    if not src:
        return []
    name, numcol = src

    if name == "__UNION_ALL__":
        sql = _source_sql_4d_union(cnx)
        if not sql:
            return []
        base = f"SELECT fecha, num FROM ({sql})"
    else:
        base = _source_sql_4d_single(name, numcol)

    q = f"""
    SELECT fecha, num
    FROM ({base})
    WHERE num IS NOT NULL
    ORDER BY fecha ASC
    """
    out: List[Tuple[str, str]] = []
    for (fecha, numero) in cnx.execute(q):
        s = _normalize_num_4d(numero)
        if s is None:
            continue
        out.append((str(fecha), s))
    return out


def load_n5sb(cnx: sqlite3.Connection, game: str) -> List[Tuple[str,int,int,int,int,int,int]]:
    """
    Retorna lista de (fecha, n1,n2,n3,n4,n5,sb) ordenada por fecha ASC para juegos N5+SB.
    Si el juego no es N5+SB, retorna lista vacía.
    """
    g = (game or "").lower().strip()
    is_n5 = g in ("baloto","revancha","n5sb","all_n5sb","baloto_revancha")
    if not is_n5:
        return []

    name = _source_n5sb_for_game(cnx, g)
    if not name:
        return []

    qname = _quote_ident(name)
    q = f"SELECT fecha,n1,n2,n3,n4,n5,sb FROM {qname} ORDER BY fecha ASC"
    out: List[Tuple[str,int,int,int,int,int,int]] = []
    for row in cnx.execute(q):
        try:
            fecha, n1,n2,n3,n4,n5,sb = row
            out.append((str(fecha), int(n1),int(n2),int(n3),int(n4),int(n5),int(sb)))
        except Exception:
            continue
    return out


def runs_has_column(cnx: sqlite3.Connection, col: str) -> bool:
    """
    Devuelve True si la tabla 'runs' tiene la columna 'col'.
    Tolerante a errores (retorna False si no existe runs).
    """
    try:
        cols = [r[1] for r in cnx.execute("PRAGMA table_info(runs)")]
        return col in cols
    except Exception:
        return False
