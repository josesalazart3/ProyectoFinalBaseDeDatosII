from flask import Flask, render_template, request, send_file
from db import get_connection
import pandas as pd
import io

app = Flask(__name__)

# Página principal: afiliados activos
@app.route('/')
def index():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT CUI, PRIMER_NOMBRE || ' ' || PRIMER_APELLIDO AS NOMBRE
        FROM IGSS_ADMIN.AFILIADO
        WHERE ESTADO = 'A'
    """)
    afiliados = cursor.fetchall()
    conn.close()
    return render_template('index.html', afiliados=afiliados)

# Reporte de presupuesto anual
@app.route('/reporte-presupuesto')
def reporte_presupuesto():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ANIO, MONTO_ASIGNADO, MONTO_EJECUTADO
        FROM IGSS_ADMIN.PRESUPUESTO_ANUAL
        ORDER BY ANIO
    """)
    datos = cursor.fetchall()
    conn.close()

    anios = [row[0] for row in datos]
    asignado = [float(row[1]) for row in datos]
    ejecutado = [float(row[2]) for row in datos]

    return render_template('reporte_presupuesto.html', anios=anios, asignado=asignado, ejecutado=ejecutado)

# Reporte de enfermedades más comunes
@app.route('/reporte-enfermedades')
def reporte_enfermedades():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.NOMBRE_ENFERMEDAD, COUNT(*) AS TOTAL
        FROM IGSS_ADMIN.SUSPENSION s
        JOIN IGSS_ADMIN.ENFERMEDAD e ON s.CODIGO_ENFERMEDAD = e.CODIGO_ENFERMEDAD
        GROUP BY e.NOMBRE_ENFERMEDAD
        ORDER BY TOTAL DESC
    """)
    resultados = cursor.fetchall()
    conn.close()

    enfermedades = [fila[0] for fila in resultados]
    totales = [fila[1] for fila in resultados]

    return render_template('reporte_enfermedades.html',
                           enfermedades=enfermedades,
                           totales=totales)

# Reporte de pagos por afiliado
@app.route('/reporte-pagos-afiliado')
def reporte_pagos_afiliado():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            a.CUI,
            a.PRIMER_NOMBRE || ' ' || a.PRIMER_APELLIDO AS NOMBRE_COMPLETO,
            NVL(SUM(dp.MONTO), 0) AS TOTAL_PAGADO
        FROM IGSS_ADMIN.AFILIADO a
        LEFT JOIN IGSS_ADMIN.SUSPENSION s ON a.CUI = s.CUI
        LEFT JOIN IGSS_ADMIN.DETALLE_PAGO dp ON s.ID_SUSPENSION = dp.ID_SUSPENSION
        GROUP BY a.CUI, a.PRIMER_NOMBRE, a.PRIMER_APELLIDO
        ORDER BY TOTAL_PAGADO DESC
    """)
    resultados = cursor.fetchall()
    conn.close()

    return render_template('reporte_pagos_afiliado.html', datos=resultados)



# Exportar reporte a Excel
@app.route('/exportar-reporte')
def exportar_reporte():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            a.CUI,
            a.PRIMER_NOMBRE || ' ' || a.PRIMER_APELLIDO AS NOMBRE_COMPLETO,
            NVL(SUM(dp.MONTO), 0) AS TOTAL_PAGADO
        FROM IGSS_ADMIN.AFILIADO a
        LEFT JOIN IGSS_ADMIN.SUSPENSION s ON a.CUI = s.CUI
        LEFT JOIN IGSS_ADMIN.DETALLE_PAGO dp ON s.ID_SUSPENSION = dp.ID_SUSPENSION
        GROUP BY a.CUI, a.PRIMER_NOMBRE, a.PRIMER_APELLIDO
        ORDER BY TOTAL_PAGADO DESC
    """)
    resultados = cursor.fetchall()
    conn.close()

    df = pd.DataFrame(resultados, columns=['CUI', 'Nombre Completo', 'Total Pagado (Q)'])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Pagos Afiliado')
    output.seek(0)

    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     download_name='pagos_afiliado.xlsx',
                     as_attachment=True)
@app.route('/reporte-fechas', methods=['GET', 'POST'])
def reporte_fechas():
    datos = []
    fecha_inicio = ''
    fecha_fin = ''

    if request.method == 'POST':
        fecha_inicio = request.form['fecha_inicio']
        fecha_fin = request.form['fecha_fin']

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                a.CUI,
                a.PRIMER_NOMBRE || ' ' || a.PRIMER_APELLIDO AS NOMBRE_COMPLETO,
                NVL(SUM(dp.MONTO), 0) AS TOTAL_PAGADO
            FROM IGSS_ADMIN.AFILIADO a
            JOIN IGSS_ADMIN.SUSPENSION s ON a.CUI = s.CUI
            JOIN IGSS_ADMIN.DETALLE_PAGO dp ON s.ID_SUSPENSION = dp.ID_SUSPENSION
            WHERE dp.FECHA_PAGO BETWEEN TO_DATE(:1, 'YYYY-MM-DD') AND TO_DATE(:2, 'YYYY-MM-DD')
            GROUP BY a.CUI, a.PRIMER_NOMBRE, a.PRIMER_APELLIDO
            ORDER BY TOTAL_PAGADO DESC
        """, [fecha_inicio, fecha_fin])
        datos = cursor.fetchall()
        conn.close()

    return render_template('reporte_fechas.html',
                           datos=datos,
                           fecha_inicio=fecha_inicio,
                           fecha_fin=fecha_fin)
@app.route('/dashboard')
def dashboard():
    conn = get_connection()
    cursor = conn.cursor()

    # Total afiliados activos
    cursor.execute("SELECT COUNT(*) FROM IGSS_ADMIN.AFILIADO WHERE ESTADO = 'A'")
    total_afiliados = cursor.fetchone()[0]

    # Total suspensiones
    cursor.execute("SELECT COUNT(*) FROM IGSS_ADMIN.SUSPENSION")
    total_suspensiones = cursor.fetchone()[0]

    # Total pagado
    cursor.execute("SELECT NVL(SUM(MONTO), 0) FROM IGSS_ADMIN.DETALLE_PAGO")
    total_pagado = cursor.fetchone()[0]

    # Total asignado presupuesto
    cursor.execute("SELECT NVL(SUM(MONTO_ASIGNADO), 0) FROM IGSS_ADMIN.PRESUPUESTO_ANUAL")
    total_asignado = cursor.fetchone()[0]

    conn.close()

    return render_template('dashboard.html',
                           total_afiliados=total_afiliados,
                           total_suspensiones=total_suspensiones,
                           total_pagado=total_pagado,
                           total_asignado=total_asignado)


if __name__ == '__main__':
    app.run(debug=True)
