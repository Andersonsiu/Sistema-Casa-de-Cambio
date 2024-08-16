from flask import Flask, render_template, Response, request, redirect, url_for, flash, jsonify
from app import app, mongo, login_manager
from flask_login import UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from bson.objectid import ObjectId
import io
import pytz
import csv

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({"_id": user_id})
    if user_data:
        return User(user_id=user_data["_id"])
    return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash('Por favor, ingrese un nombre de usuario y una contraseña', 'danger')
            return redirect(url_for('register'))
        user = mongo.db.users.find_one({"_id": username})
        if user:
            flash('El nombre de usuario ya existe', 'danger')
        else:
            mongo.db.users.insert_one({"_id": username, "password": password})
            flash('Usuario registrado exitosamente', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash('Por favor, ingrese su nombre de usuario y contraseña', 'danger')
            return redirect(url_for('login'))
        user = mongo.db.users.find_one({"_id": username, "password": password})
        if user:
            login_user(User(user_id=username))
            return redirect(url_for('index'))
        else:
            flash('Nombre de usuario o contraseña incorrectos', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/dolares', methods=['GET', 'POST'])
@login_required
def dolares():
    if request.method == 'POST':
        try:
            tipo = request.form['tipo']
            tasa_cambio = request.form['tasa_cambio']
            cantidad_origen = request.form['cantidad_origen']
            if not tasa_cambio or not cantidad_origen:
                flash('Por favor, complete todos los campos del formulario', 'danger')
                return redirect(url_for('dolares'))
            tasa_cambio = float(tasa_cambio)
            cantidad_origen = float(cantidad_origen)
            fecha = datetime.now(pytz.timezone('America/Lima')).strftime('%Y-%m-%d')

            cantidad_destino = round(cantidad_origen * tasa_cambio, 3)

            transaccion = {
                'tipo': tipo,
                'moneda_origen': 'USD' if tipo == 'compra' else 'PEN',
                'moneda_destino': 'PEN' if tipo == 'compra' else 'USD',
                'tasa_cambio': tasa_cambio,
                'cantidad_origen': cantidad_origen,
                'cantidad_destino': cantidad_destino,
                'fecha': fecha
            }

            mongo.db.dolares.insert_one(transaccion)
            flash('Transacción añadida exitosamente', 'success')
        except ValueError:
            flash('Error en los datos ingresados. Por favor, intente de nuevo.', 'danger')
        return redirect(url_for('dolares'))

    transacciones = list(mongo.db.dolares.find().sort('fecha', -1))
    return render_template('dolares.html', transacciones=transacciones)

@app.route('/euros', methods=['GET', 'POST'])
@login_required
def euros():
    if request.method == 'POST':
        try:
            tipo = request.form['tipo']
            tasa_cambio = request.form['tasa_cambio']
            cantidad_origen = request.form['cantidad_origen']
            if not tasa_cambio or not cantidad_origen:
                flash('Por favor, complete todos los campos del formulario', 'danger')
                return redirect(url_for('euros'))
            tasa_cambio = float(tasa_cambio)
            cantidad_origen = float(cantidad_origen)
            fecha = datetime.now(pytz.timezone('America/Lima')).strftime('%Y-%m-%d')

            cantidad_destino = round(cantidad_origen * tasa_cambio, 3)

            transaccion = {
                'tipo': tipo,
                'moneda_origen': 'EUR' if tipo == 'compra' else 'PEN',
                'moneda_destino': 'PEN' if tipo == 'compra' else 'EUR',
                'tasa_cambio': tasa_cambio,
                'cantidad_origen': cantidad_origen,
                'cantidad_destino': cantidad_destino,
                'fecha': fecha
            }

            mongo.db.euros.insert_one(transaccion)
            flash('Transacción añadida exitosamente', 'success')
        except ValueError:
            flash('Error en los datos ingresados. Por favor, intente de nuevo.', 'danger')
        return redirect(url_for('euros'))

    transacciones = list(mongo.db.euros.find().sort('fecha', -1))
    return render_template('euros.html', transacciones=transacciones)

@app.route('/reportes', methods=['GET', 'POST'])
@login_required
def reportes():
    if request.method == 'POST':
        try:
            tipo_reporte = request.form['tipo_reporte']
            caja_inicial_dolares = request.form['caja_inicial']
            caja_inicial_euros = request.form.get('caja_inicial_euros', 0)
            gastos = request.form.get('gastos', 0)

            if not tipo_reporte or not caja_inicial_dolares:
                flash('Por favor, complete todos los campos del formulario', 'danger')
                return redirect(url_for('reportes'))

            caja_inicial_dolares = float(caja_inicial_dolares)
            caja_inicial_euros = float(caja_inicial_euros) if caja_inicial_euros else 0
            gastos = float(gastos) if gastos else 0

            caja_dolares_compra_origen = 0
            caja_dolares_venta_origen = 0
            caja_dolares_compra_destino = 0
            caja_dolares_venta_destino = 0

            caja_euros_compra_origen = 0
            caja_euros_venta_origen = 0
            caja_euros_compra_destino = 0
            caja_euros_venta_destino = 0

            caja_final_dolares = caja_inicial_dolares
            caja_final_euros = caja_inicial_euros
            margen_compra_dolares = 0
            margen_venta_dolares = 0
            margen_compra_euros = 0
            margen_venta_euros = 0
            diferencia_margen_dolares = 0
            diferencia_margen_euros = 0
            ganancia_soles_dolares = 0
            ganancia_soles_euros = 0
            ganancia_dolares = 0
            ganancia_euros = 0

            if tipo_reporte == 'diario':
                fecha_diario = request.form['fecha_diario']
                transacciones_dolares = list(mongo.db.dolares.find({'fecha': fecha_diario}))
                transacciones_euros = list(mongo.db.euros.find({'fecha': fecha_diario}))

            elif tipo_reporte == 'semanal':
                fecha_inicio = request.form['fecha_inicio_semanal']
                fecha_fin = request.form['fecha_fin_semanal']
                transacciones_dolares = list(mongo.db.dolares.find({'fecha': {'$gte': fecha_inicio, '$lte': fecha_fin}}))
                transacciones_euros = list(mongo.db.euros.find({'fecha': {'$gte': fecha_inicio, '$lte': fecha_fin}}))

            elif tipo_reporte == 'mensual':
                mes = request.form['mes']
                anio = datetime.now().year
                fecha_inicio = f"{anio}-{mes}-01"
                fecha_fin = (datetime(anio, int(mes), 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                transacciones_dolares = list(mongo.db.dolares.find({'fecha': {'$gte': fecha_inicio, '$lte': fecha_fin.strftime('%Y-%m-%d')}}))
                transacciones_euros = list(mongo.db.euros.find({'fecha': {'$gte': fecha_inicio, '$lte': fecha_fin.strftime('%Y-%m-%d')}}))

            for transaccion in transacciones_dolares:
                if transaccion['tipo'] == 'compra':
                    caja_dolares_compra_origen += transaccion['cantidad_origen']
                    caja_dolares_compra_destino += transaccion['cantidad_destino']
                else:
                    caja_dolares_venta_origen += transaccion['cantidad_origen']
                    caja_dolares_venta_destino += transaccion['cantidad_destino']

            for transaccion in transacciones_euros:
                if transaccion['tipo'] == 'compra':
                    caja_euros_compra_origen += transaccion['cantidad_origen']
                    caja_euros_compra_destino += transaccion['cantidad_destino']
                else:
                    caja_euros_venta_origen += transaccion['cantidad_origen']
                    caja_euros_venta_destino += transaccion['cantidad_destino']

            # Calcular márgenes de compra y venta
            if caja_dolares_compra_origen != 0:
                margen_compra_dolares = caja_dolares_compra_destino / caja_dolares_compra_origen
            if caja_dolares_venta_origen != 0:
                margen_venta_dolares = caja_dolares_venta_destino / caja_dolares_venta_origen

            if caja_euros_compra_origen != 0:
                margen_compra_euros = caja_euros_compra_destino / caja_euros_compra_origen
            if caja_euros_venta_origen != 0:
                margen_venta_euros = caja_euros_venta_destino / caja_euros_venta_origen

            # Calcular diferencia de márgenes
            diferencia_margen_dolares = margen_venta_dolares - margen_compra_dolares
            diferencia_margen_euros = margen_venta_euros - margen_compra_euros

            # Calcular ganancia en soles
            ganancia_soles_dolares = caja_dolares_compra_origen * diferencia_margen_dolares
            ganancia_soles_euros = caja_euros_compra_origen * diferencia_margen_euros

            # Calcular ganancia en dólares (después de restar gastos)
            if margen_venta_dolares != 0:
                ganancia_dolares = ganancia_soles_dolares / margen_venta_dolares
            if margen_venta_euros != 0:
                ganancia_euros = ganancia_soles_euros / margen_venta_euros

            ganancia_dolares_despues_gastos = ganancia_dolares - gastos
            ganancia_euros_despues_gastos = ganancia_euros - gastos

            # Calcular caja final
            caja_final_dolares = caja_inicial_dolares + ganancia_dolares_despues_gastos
            caja_final_euros = caja_inicial_euros + ganancia_euros_despues_gastos

            # Guardar los resultados en la colección historico_caja, actualizando el último registro del día
            if tipo_reporte == 'diario':
                fecha_hoy = datetime.now(pytz.timezone('America/Lima')).strftime('%Y-%m-%d')
                mongo.db.historico_caja.update_one(
                    {'fecha': fecha_hoy},
                    {'$set': {
                        'caja_dolares': {
                            'inicial': caja_inicial_dolares,
                            'final': caja_final_dolares,
                            'ganancia_soles': ganancia_soles_dolares,
                            'ganancia_dolares': ganancia_dolares_despues_gastos
                        },
                        'caja_euros': {
                            'inicial': caja_inicial_euros,
                            'final': caja_final_euros,
                            'ganancia_soles': ganancia_soles_euros,
                            'ganancia_euros': ganancia_euros_despues_gastos
                        },
                        'gastos': gastos,
                        'updated_at': datetime.now(pytz.timezone('America/Lima'))
                    }},
                    upsert=True
                )

            return render_template('reportes.html', 
                                   caja_dolares_compra_origen=round(caja_dolares_compra_origen, 2), 
                                   caja_dolares_venta_origen=round(caja_dolares_venta_origen, 2),
                                   caja_dolares_compra_destino=round(caja_dolares_compra_destino, 2),
                                   caja_dolares_venta_destino=round(caja_dolares_venta_destino, 2),
                                   caja_euros_compra_origen=round(caja_euros_compra_origen, 2),
                                   caja_euros_venta_origen=round(caja_euros_venta_origen, 2),
                                   caja_euros_compra_destino=round(caja_euros_compra_destino, 2),
                                   caja_euros_venta_destino=round(caja_euros_venta_destino, 2),
                                   margen_compra_dolares=round(margen_compra_dolares, 4),
                                   margen_venta_dolares=round(margen_venta_dolares, 4),
                                   margen_compra_euros=round(margen_compra_euros, 4),
                                   margen_venta_euros=round(margen_venta_euros, 4),
                                   diferencia_margen_dolares=round(diferencia_margen_dolares, 4),
                                   diferencia_margen_euros=round(diferencia_margen_euros, 4),
                                   ganancia_soles_dolares=round(ganancia_soles_dolares, 2),
                                   ganancia_soles_euros=round(ganancia_soles_euros, 2),
                                   ganancia_dolares=round(ganancia_dolares, 2),
                                   ganancia_dolares_despues_gastos=round(ganancia_dolares_despues_gastos, 2),
                                   ganancia_euros=round(ganancia_euros, 2),
                                   ganancia_euros_despues_gastos=round(ganancia_euros_despues_gastos, 2),
                                   caja_final_dolares=round(caja_final_dolares, 2),
                                   caja_final_euros=round(caja_final_euros, 2),
                                   gastos=round(gastos, 2),
                                   fecha_hoy=fecha_hoy)
        except ValueError:
            flash('Error en los datos ingresados. Por favor, intente de nuevo.', 'danger')
            return redirect(url_for('reportes'))

    default_values = {
        'caja_dolares_compra_origen': 0,
        'caja_dolares_venta_origen': 0,
        'caja_dolares_compra_destino': 0,
        'caja_dolares_venta_destino': 0,
        'caja_euros_compra_origen': 0,
        'caja_euros_venta_origen': 0,
        'caja_euros_compra_destino': 0,
        'caja_euros_venta_destino': 0,
        'margen_compra_dolares': 0,
        'margen_venta_dolares': 0,
        'margen_compra_euros': 0,
        'margen_venta_euros': 0,
        'diferencia_margen_dolares': 0,
        'diferencia_margen_euros': 0,
        'ganancia_soles_dolares': 0,
        'ganancia_soles_euros': 0,
        'ganancia_dolares': 0,
        'ganancia_dolares_despues_gastos': 0,
        'ganancia_euros': 0,
        'ganancia_euros_despues_gastos': 0,
        'caja_final_dolares': 0,
        'caja_final_euros': 0,
        'gastos': 0
    }

    return render_template('reportes.html', fecha_hoy=datetime.now(pytz.timezone('America/Lima')).strftime('%Y-%m-%d'), **default_values)


@app.route('/eliminar_transaccion/<tipo>/<id>', methods=['DELETE'])
@login_required
def eliminar_transaccion(tipo, id):
    if tipo == 'dolares':
        result = mongo.db.dolares.delete_one({'_id': ObjectId(id)})
    elif tipo == 'euros':
        result = mongo.db.euros.delete_one({'_id': ObjectId(id)})
    else:
        return jsonify({'status': 'fail', 'message': 'Invalid transaction type'}), 400

    if result.deleted_count == 1:
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'fail', 'message': 'Transaction not found'}), 404

@app.route('/exportar_csv')
@login_required
def exportar_csv():
    # Obtener datos de las transacciones desde la base de datos
    transacciones_dolares = list(mongo.db.dolares.find())
    transacciones_euros = list(mongo.db.euros.find())

    # Crear un archivo CSV en memoria
    si = io.StringIO()
    cw = csv.writer(si)

    # Escribir los encabezados del CSV
    cw.writerow(['Tipo', 'Moneda Origen', 'Moneda Destino', 'Tasa de Cambio', 'Cantidad Origen', 'Cantidad Destino', 'Fecha'])

    # Escribir los datos de las transacciones en el CSV
    for transaccion in transacciones_dolares + transacciones_euros:
        cw.writerow([transaccion['tipo'], transaccion['moneda_origen'], transaccion['moneda_destino'],
                     transaccion['tasa_cambio'], transaccion['cantidad_origen'], transaccion['cantidad_destino'], transaccion['fecha']])

    # Preparar la respuesta HTTP con el archivo CSV
    output = Response(si.getvalue(), mimetype='text/csv')
    output.headers["Content-Disposition"] = "attachment; filename=reportes.csv"

    return output

@app.route('/historico', methods=['GET'])
@login_required
def historico():
    historico_data = list(mongo.db.historico_caja.find().sort('fecha', -1))
    fechas = [entry['fecha'] for entry in historico_data]
    caja_final_dolares = [entry['caja_dolares']['final'] for entry in historico_data]
    caja_final_euros = [entry['caja_euros']['final'] for entry in historico_data]
    
    return render_template('historico.html', historico_data=historico_data, fechas=fechas, caja_final_dolares=caja_final_dolares, caja_final_euros=caja_final_euros)

