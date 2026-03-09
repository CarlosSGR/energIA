import os
import json
import pdfplumber
import pandas as pd
from openai import OpenAI

# ==========================================
# CONFIGURACIÓN API
# ==========================================

client = OpenAI(api_key="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")
DATASET_FILE = "dataset_consumo.csv"

# ==========================================
# VALIDAR SI ES RECIBO CFE
# ==========================================

def validar_recibo_cfe(ruta_pdf):

    texto = ""

    with pdfplumber.open(ruta_pdf) as pdf:
        for page in pdf.pages:
            texto += page.extract_text() or ""

    palabras_clave = [
        "CFE",
        "Comisión Federal de Electricidad",
        "Número de servicio",
        "Total a pagar"
    ]

    for palabra in palabras_clave:
        if palabra.lower() in texto.lower():
            return True, "Recibo CFE válido"

    return False, "No parece recibo CFE"


# ==========================================
# ANALIZAR CON OPENAI
# ==========================================

def extraer_datos_recibo_openai(ruta_pdf):

    archivo = client.files.create(
        file=open(ruta_pdf, "rb"),
        purpose="assistants"
    )

    prompt = """
Analiza este recibo de CFE.

Devuelve JSON con esta estructura:

{
"numero_servicio":"",
"direccion":"",
"tarifa":"",
"periodo":"",
"energia_kwh":"",
"total_pagar":"",
"historial_consumos":[
  {"periodo":"","kwh":""}
]
}

El historial debe contener todos los meses visibles.

Devuelve SOLO JSON válido.
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_file", "file_id": archivo.id}
            ]
        }]
    )

    return response.output_text


# ==========================================
# GUARDAR DATASET
# ==========================================

def guardar_dataset(datos_json):

    import json

    # limpiar markdown ```json ```
    datos_json = datos_json.replace("```json", "").replace("```", "").strip()

    try:
        datos = json.loads(datos_json)
    except Exception as e:
        print("Error leyendo JSON:", e)
        print("Contenido recibido:")
        print(datos_json)
        return

    historial = datos.get("historial_consumos", [])

    filas = []

    for consumo in historial:

        try:
            kwh = float(str(consumo.get("kwh", "")).replace(",", ""))
        except:
            kwh = None

        filas.append({
            "numero_servicio": datos.get("numero_servicio"),
            "direccion": datos.get("direccion"),
            "tarifa": datos.get("tarifa"),
            "periodo": consumo.get("periodo"),
            "consumo_kwh": kwh
        })

    df_nuevo = pd.DataFrame(filas)

    if os.path.exists(DATASET_FILE) and os.path.getsize(DATASET_FILE) > 0:

        try:
            df_existente = pd.read_csv(DATASET_FILE)
            df_total = pd.concat([df_existente, df_nuevo], ignore_index=True)
        except:
            df_total = df_nuevo

    else:
        df_total = df_nuevo

    df_total.to_csv(DATASET_FILE, index=False)

    print("\nDataset actualizado correctamente")
    print(df_total.tail())


# ==========================================
# PROCESAR RECIBO
# ==========================================

def procesar_recibo(archivo):

    print("\n==========================")
    print("Procesando:", archivo)

    valido, mensaje = validar_recibo_cfe(archivo)

    print("Validación:", mensaje)

    if not valido:
        return

    print("\nAnalizando con OpenAI...\n")

    datos = extraer_datos_recibo_openai(archivo)

    print("Datos extraídos:\n")
    print(datos)

    guardar_dataset(datos)


# ==========================================
# PROCESAR CARPETA
# ==========================================

def procesar_carpeta():

    carpeta = "recibos"

    if not os.path.exists(carpeta):
        print("La carpeta 'recibos' no existe.")
        return

    for archivo in os.listdir(carpeta):

        if archivo.lower().endswith(".pdf"):

            ruta = os.path.join(carpeta, archivo)
            procesar_recibo(ruta)


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":

    procesar_carpeta()