# ======================================================================
# srm_update_manager_v1.py — SRM-QK-ADSI UPDATE & VERSION ENGINE v1
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Crear un sistema de versionado interno para SRM.
#   - Detectar nuevos módulos, cambios y actualizaciones.
#   - Aplicar actualizaciones de forma segura.
#   - Mantener historial y permitir rollback.
#
# Directorios clave:
#   pipeline/                  → módulos activos
#   pipeline/incoming_updates/ → módulos nuevos que se pueden instalar
#   pipeline/updates/backups/  → copias de seguridad
#   pipeline/updates/version_manifest.json → estado del sistema
#
# ======================================================================

import os
import json
import shutil
from datetime import datetime

# ----------------------------------------------------------------------
# RUTAS BASE
# ----------------------------------------------------------------------
PIPELINE = r"C:\SRM_ADSI\05_pipeline"
INCOMING = os.path.join(PIPELINE, "incoming_updates")
UPDATES_DIR = os.path.join(PIPELINE, "updates")
BACKUPS = os.path.join(UPDATES_DIR, "backups")

os.makedirs(INCOMING, exist_ok=True)
os.makedirs(UPDATES_DIR, exist_ok=True)
os.makedirs(BACKUPS, exist_ok=True)

VERSION_MANIFEST = os.path.join(UPDATES_DIR, "version_manifest.json")


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def load_manifest():
    if not os.path.exists(VERSION_MANIFEST):
        manifest = {
            "current_version": "v28",
            "installed_modules": {},
            "history": []
        }
        save_manifest(manifest)
        return manifest

    with open(VERSION_MANIFEST, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(manifest):
    with open(VERSION_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4, ensure_ascii=False)


def module_info(path):
    """Devuelve metadatos del módulo como fecha, tamaño."""
    if not os.path.exists(path):
        return None
    stat = os.stat(path)
    return {
        "modified": stat.st_mtime,
        "size": stat.st_size
    }


def backup_module(src_path):
    """Guarda un módulo antiguo antes de reemplazarlo."""
    base = os.path.basename(src_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUPS, f"{base}_{ts}.bak")
    shutil.copy2(src_path, dest)
    return dest


# ----------------------------------------------------------------------
# DETECCIÓN DE CAMBIOS
# ----------------------------------------------------------------------
def detectar_cambios(manifest):
    """Detecta módulos nuevos o modificados en incoming_updates."""
    changes = []

    for file in os.listdir(INCOMING):
        if not file.endswith(".py"):
            continue

        incoming_file = os.path.join(INCOMING, file)
        active_file = os.path.join(PIPELINE, file)

        incoming_info = module_info(incoming_file)
        active_info = module_info(active_file)

        if not active_info:
            changes.append((file, "NEW"))
        else:
            if incoming_info["modified"] != active_info["modified"]:
                changes.append((file, "MODIFIED"))

    return changes


# ----------------------------------------------------------------------
# APLICAR ACTUALIZACIONES
# ----------------------------------------------------------------------
def aplicar_updates(changes, manifest):

    update_record = {
        "timestamp": datetime.now().isoformat(),
        "updated_modules": []
    }

    for file, change_type in changes:
        src = os.path.join(INCOMING, file)
        dest = os.path.join(PIPELINE, file)

        # Backup si ya existía
        if change_type == "MODIFIED":
            backup_path = backup_module(dest)
        else:
            backup_path = None

        shutil.copy2(src, dest)

        # Registrar en manifest
        manifest["installed_modules"][file] = {
            "installed_at": datetime.now().isoformat(),
            "change_type": change_type,
            "backup": backup_path
        }

        update_record["updated_modules"].append({
            "file": file,
            "change_type": change_type,
            "backup": backup_path
        })

    manifest["history"].append(update_record)
    save_manifest(manifest)

    return update_record


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def ejecutar_update_manager():

    print("\n=====================================================")
    print("        SRM — UPDATE MANAGER v1")
    print("=====================================================\n")

    manifest = load_manifest()

    print("→ Buscando actualizaciones en incoming_updates...")
    changes = detectar_cambios(manifest)

    if not changes:
        print("✔ No hay módulos nuevos o modificados.")
        return

    print("→ Cambios detectados:")
    for file, change_type in changes:
        print(f"   - {file} → {change_type}")

    print("\n→ Aplicando actualizaciones...")
    update_record = aplicar_updates(changes, manifest)

    print("✔ Actualizaciones aplicadas con éxito.")

    print("\n→ Detalles del update:")
    print(json.dumps(update_record, indent=4, ensure_ascii=False))

    print("\n=====================================================")
    print("✔ UPDATE MANAGER — COMPLETADO")
    print(f"✔ Manifest: {VERSION_MANIFEST}")
    print("=====================================================\n")


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    ejecutar_update_manager()
