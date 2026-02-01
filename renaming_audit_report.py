import pandas as pd
import os
import sys

# La ruta y archivo de log que contiene los registros de renombrado
LOG_FILE = "log_inconsistencias.csv"
OUTPUT_REPORT = "image_renaming_audit_report.csv"

def generate_renaming_report(log_path):
    """
    Lee el log de inconsistencias y genera un reporte de las operaciones de renombrado.
    """
    try:
        if not os.path.exists(log_path):
            print(f"[ERROR] No se encontró el archivo de log en la ruta: {log_path}", file=sys.stderr)
            return None

        # Cargar el log completo
        df_log = pd.read_csv(log_path, dtype=str)

        # Filtrar solo los registros generados por la función rename_local_images
        df_renames = df_log[df_log['tipo'].isin(['RENAME_SUCCESS', 'RENAME_FAIL', 'RENAME_ERROR', 'RENAME_SKIP'])].copy()

        if df_renames.empty:
            print("[INFO] No se encontraron registros de RENOMBRADO en el log. El script pudo no haber ejecutado la fase de renombrado, o no hubo errores.")
            return None

        # Consolidar y limpiar columnas para el reporte
        df_renames = df_renames[['tipo', 'Original_Name', 'New_Name', 'detalle']].fillna('')
        df_renames.rename(columns={'tipo': 'ESTADO_OPERACION', 
                                   'Original_Name': 'RUTA_ORIGINAL', 
                                   'New_Name': 'RUTA_RENOMBRADA',
                                   'detalle': 'DETALLE'}, inplace=True)
        
        # Métrica de Conteo
        summary = df_renames['ESTADO_OPERACION'].value_counts().to_frame('Conteo')
        summary['Porcentaje'] = (summary['Conteo'] / summary['Conteo'].sum() * 100).round(1).astype(str) + '%'

        print("\n--- RESUMEN DE LA AUDITORÍA DE RENOMBRADO ---")
        print(summary.to_markdown())
        
        return df_renames

    except Exception as e:
        print(f"[ERROR] Fallo al procesar el log: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    # Suponemos que el script se ejecuta en la carpeta raíz, como antes
    root_dir = os.getcwd() 
    log_path = os.path.join(root_dir, LOG_FILE)
    output_path = os.path.join(root_dir, OUTPUT_REPORT)

    df_report = generate_renaming_report(log_path)

    if df_report is not None:
        df_report.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n✅ Reporte de auditoría de renombrado generado en: {output_path}")