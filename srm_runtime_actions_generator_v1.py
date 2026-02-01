# ======================================================================
# srm_runtime_actions_generator_v1.py
# Generador de acciones .BAT para el SRM Runtime Dashboard
# ======================================================================
# Crea automáticamente los archivos .bat que permiten ejecutar:
#   - Diagnósticos
#   - Update Manager
#   - Frontend Sync
#   - Integrator
#   - Reinicio del Runtime
#
# Estos .bat serán accesibles desde el panel visual:
# C:\SRM_ADSI\05_pipeline\runtime_dashboard\index.html
# ======================================================================

import os

BASE = r"C:\SRM_ADSI\05_pipeline"

ACTIONS = {
    "run_diagnostics.bat": "python srm_diagnostics_v1.py",
    "run_updates.bat": "python srm_update_manager_v1.py",
    "run_frontend_sync.bat": "python srm_frontend_sync_v1.py",
    "run_integrator.bat": "python srm_integrator_v1.py",
    "restart_runtime.bat": "python srm_runtime_controller_v1.py",
}

def generate_actions():
    print("\n=====================================================")
    print("        SRM — Runtime Actions Generator v1")
    print("=====================================================\n")

    for filename, command in ACTIONS.items():
        path = os.path.join(BASE, filename)

        with open(path, "w", encoding="utf-8") as f:
            f.write(f"@echo off\n")
            f.write(f"cd {BASE}\n")
            f.write(f"{command}\n")
            f.write("pause\n")

        print(f"✔ Archivo generado: {path}")

    print("\n=====================================================")
    print("✔ Todos los .BAT generados correctamente")
    print("=====================================================\n")


if __name__ == "__main__":
    generate_actions()
