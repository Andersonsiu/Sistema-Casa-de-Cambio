from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_user, login_required, logout_user, current_user, UserMixin
from app import app, mongo, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import io
import csv

main = Blueprint('main', __name__)

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({"_id": user_id})
    if user_data:
        return User(user_id=user_data["_id"])
    return None

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = mongo.db.users.find_one({"_id": username})
        if user:
            flash('Username already exists', 'danger')
        else:
            hashed_password = generate_password_hash(password, method='sha256')
            mongo.db.users.insert_one({"_id": username, "password": hashed_password})
            flash('User registered successfully', 'success')
            return redirect(url_for('main.login'))
    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = mongo.db.users.find_one({"_id": username})
        if user and check_password_hash(user['password'], password):
            login_user(User(user_id=username))
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('main.login'))

@main.route('/')
@login_required
def index():
    return render_template('index.html')

@main.route('/dolares', methods=['GET', 'POST'])
@login_required
def dolares():
    if request.method == 'POST':
        tipo = request.form['tipo']
        tasa_cambio = request.form['tasa_cambio']
        cantidad_origen = request.form['cantidad_origen']
        
        if not tasa_cambio or not cantidad_origen:
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('main.dolares'))

        try:
            tasa_cambio = float(tasa_cambio)
            cantidad_origen = float(cantidad_origen)
        except ValueError:
            flash('Por favor, ingrese valores numéricos válidos', 'danger')
            return redirect(url_for('main.dolares'))

        fecha = datetime.now().strftime('%Y-%m-%d')
        
        if tipo == 'compra':
            cantidad_destino = cantidad_origen * tasa_cambio
        else:
            cantidad_destino = cantidad_origen / tasa_cambio
        
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
        return redirect(url_for('main.dolares'))
    
    transacciones = list(mongo.db.dolares.find().sort('fecha', -1))
    return render_template('dolares.html', transacciones=transacciones)

@main.route('/euros', methods=['GET', 'POST'])
@login_required
def euros():
    if request.method == 'POST':
        tipo = request.form['tipo']
        tasa_cambio = request.form['tasa_cambio']
        cantidad_origen = request.form['cantidad_origen']
        
        if not tasa_cambio or not cantidad_origen:
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('main.euros'))

        try:
            tasa_cambio = float(tasa_cambio)
            cantidad_origen = float(cantidad_origen)
        except ValueError:
            flash('Por favor, ingrese valores numéricos válidos', 'danger')
            return redirect(url_for('main.euros'))

        fecha = datetime.now().strftime('%Y-%m-%d')
        
        if tipo == 'compra':
            cantidad_destino = cantidad_origen * tasa_cambio
        else:
            cantidad_destino = cantidad_origen / tasa_cambio
        
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
        return redirect(url_for('main.euros'))
    
    transacciones = list(mongo.db.euros.find().sort('fecha', -1))
    return render_template('euros.html', transacciones=transacciones)

@main.route('/reportes', methods=['GET', 'POST'])
@login_required
def reportes():
    transacciones_dolares = []
    transacciones_euros = []
    if request.method == 'POST':
        fecha_inicio = request.form['fecha_inicio']
        fecha_fin = request.form['fecha_fin']
        
        if not fecha_inicio or not fecha_fin:
            flash('Debe proporcionar una fecha de inicio y fin válidas', 'danger')
            return redirect(url_for('main.reportes'))

        transacciones_dolares = list(mongo.db.dolares.find({
            'fecha': {'$gte': fecha_inicio, '$lte': fecha_fin}
        }).sort('fecha', -1))
        
        transacciones_euros = list(mongo.db.euros.find({
            'fecha': {'$gte': fecha_inicio, '$lte': fecha_fin}
        }).sort('fecha', -1))
    
    return render_template('reportes.html', transacciones_dolares=transacciones_dolares, transacciones_euros=transacciones_euros)

@main.route('/exportar/<moneda>/<fecha_inicio>/<fecha_fin>')
@login_required
def exportar(moneda, fecha_inicio, fecha_fin):
    if not fecha_inicio or not fecha_fin:
        flash('Debe proporcionar una fecha de inicio y fin válidas para exportar', 'danger')
        return redirect(url_for('main.reportes'))

    if moneda == 'dolares':
        transacciones = list(mongo.db.dolares.find({
            'fecha': {'$gte': fecha_inicio, '$lte': fecha_fin}
        }).sort('fecha', -1))
    else:
        transacciones = list(mongo.db.euros.find({
            'fecha': {'$gte': fecha_inicio, '$lte': fecha_fin}
        }).sort('fecha', -1))
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    header = ['Fecha', 'Tipo', 'Moneda Origen', 'Moneda Destino', 'Tasa de Cambio', 'Cantidad Origen', 'Cantidad Destino']
    writer.writerow(header)
    
    for transaccion in transacciones:
        writer.writerow([transaccion['fecha'], transaccion['tipo'], transaccion['moneda_origen'], transaccion['moneda_destino'], transaccion['tasa_cambio'], transaccion['cantidad_origen'], transaccion['cantidad_destino']])
    
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=transacciones_{}.csv".format(moneda)})


@app.route('/dolares/editar/<id>', methods=['GET', 'POST'])
@login_required
def editar_dolares(id):
    transaccion = mongo.db.dolares.find_one({"_id": ObjectId(id)})
    if request.method == 'POST':
        mongo.db.dolares.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "tipo": request.form["tipo"],
                "tasa_cambio": float(request.form["tasa_cambio"]),
                "cantidad_origen": float(request.form["cantidad_origen"]),
                "cantidad_destino": float(request.form["cantidad_destino"]),
                "fecha": request.form["fecha"]
            }}
        )
        flash('Transacción actualizada exitosamente', 'success')
        return redirect(url_for('main.dolares'))
    return render_template('editar_dolares.html', transaccion=transaccion)

@app.route('/dolares/eliminar/<id>', methods=['POST'])
@login_required
def eliminar_dolares(id):
    mongo.db.dolares.delete_one({"_id": ObjectId(id)})
    flash('Transacción eliminada exitosamente', 'success')
    return redirect(url_for('main.dolares'))

# Repite para euros
@app.route('/euros/editar/<id>', methods=['GET', 'POST'])
@login_required
def editar_euros(id):
    transaccion = mongo.db.euros.find_one({"_id": ObjectId(id)})
    if request.method == 'POST':
        mongo.db.euros.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "tipo": request.form["tipo"],
                "tasa_cambio": float(request.form["tasa_cambio"]),
                "cantidad_origen": float(request.form["cantidad_origen"]),
                "cantidad_destino": float(request.form["cantidad_destino"]),
                "fecha": request.form["fecha"]
            }}
        )
        flash('Transacción actualizada exitosamente', 'success')
        return redirect(url_for('main.euros'))
    return render_template('editar_euros.html', transaccion=transaccion)

@app.route('/euros/eliminar/<id>', methods=['POST'])
@login_required
def eliminar_euros(id):
    mongo.db.euros.delete_one({"_id": ObjectId(id)})
    flash('Transacción eliminada exitosamente', 'success')
    return redirect(url_for('main.euros'))

