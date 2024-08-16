from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from flask_login import UserMixin

# Conexión a MongoDB
client = MongoClient(os.getenv('MONGO_URI', 'mongodb://mongo:27017/'))
db = client.casa_de_cambios

# Colección de usuarios
usuarios_collection = db.usuarios

class Transaccion:
    def __init__(self, tipo, moneda_origen, moneda_destino, cantidad_origen, tasa_cambio, cantidad_destino, fecha):
        self.tipo = tipo
        self.moneda_origen = moneda_origen
        self.moneda_destino = moneda_destino
        self.cantidad_origen = cantidad_origen
        self.tasa_cambio = tasa_cambio
        self.cantidad_destino = cantidad_destino
        self.fecha = fecha

    def to_dict(self):
        return {
            "tipo": self.tipo,
            "moneda_origen": self.moneda_origen,
            "moneda_destino": self.moneda_destino,
            "cantidad_origen": self.cantidad_origen,
            "tasa_cambio": self.tasa_cambio,
            "cantidad_destino": self.cantidad_destino,
            "fecha": self.fecha
        }

    @staticmethod
    def from_dict(data):
        return Transaccion(
            data["tipo"],
            data["moneda_origen"],
            data["moneda_destino"],
            data["cantidad_origen"],
            data["tasa_cambio"],
            data["cantidad_destino"],
            data["fecha"]
        )

class User(UserMixin):
    def __init__(self, username, password, id=None):
        self.id = str(id)
        self.username = username
        self.password = password

    @staticmethod
    def get(user_id):
        user_data = usuarios_collection.find_one({"_id": ObjectId(user_id)})
        if user_data:
            return User(user_data["username"], user_data["password"], id=user_data["_id"])
        return None

    @staticmethod
    def find_by_username(username):
        user_data = usuarios_collection.find_one({"username": username})
        if user_data:
            return User(user_data["username"], user_data["password"], id=user_data["_id"])
        return None

