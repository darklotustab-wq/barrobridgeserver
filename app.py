"""
Servidor puente: recibe pedidos de impresión de etiquetas desde la web
de Barro Tal Ves, y los deja en una cola para que el celular Android
los recoja y los imprima en la Niimbot D110.

Endpoints:
  POST /pedidos          -> la web manda un pedido nuevo
  GET  /pedidos/pendientes -> el celular consulta si hay pedidos nuevos
  POST /pedidos/<id>/completado -> el celular avisa que ya imprimió
"""
import os
import time
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Cola en memoria simple. Para este volumen de uso (un local chico) alcanza,
# no hace falta una base de datos.
pedidos = {}

# Token simple para que no cualquiera pueda mandar pedidos a tu cola
TOKEN = os.environ.get("BRIDGE_TOKEN", "barrotalves2026")


def check_token(req):
    token = req.headers.get("X-Bridge-Token") or req.args.get("token")
    return token == TOKEN


@app.route("/", methods=["GET"])
def home():
    return jsonify({"ok": True, "servicio": "puente Barro Tal Ves - Niimbot"})


@app.route("/pedidos", methods=["POST"])
def crear_pedido():
    if not check_token(request):
        return jsonify({"ok": False, "error": "Token inválido"}), 401

    data = request.get_json(force=True)
    codigo = str(data.get("codigo", "")).strip()
    nombre = str(data.get("nombre", "")).strip()
    precio = str(data.get("precio", "")).strip()
    cantidad = int(data.get("cantidad", 1))

    if not codigo:
        return jsonify({"ok": False, "error": "Falta 'codigo'"}), 400

    pedido_id = str(uuid.uuid4())
    pedidos[pedido_id] = {
        "id": pedido_id,
        "codigo": codigo,
        "nombre": nombre,
        "precio": precio,
        "cantidad": cantidad,
        "estado": "pendiente",
        "creado": time.time(),
    }
    return jsonify({"ok": True, "id": pedido_id})


@app.route("/pedidos/pendientes", methods=["GET"])
def pedidos_pendientes():
    if not check_token(request):
        return jsonify({"ok": False, "error": "Token inválido"}), 401

    pendientes = [p for p in pedidos.values() if p["estado"] == "pendiente"]
    pendientes.sort(key=lambda p: p["creado"])
    return jsonify({"ok": True, "pedidos": pendientes})


@app.route("/pedidos/<pedido_id>/completado", methods=["POST"])
def marcar_completado(pedido_id):
    if not check_token(request):
        return jsonify({"ok": False, "error": "Token inválido"}), 401

    if pedido_id not in pedidos:
        return jsonify({"ok": False, "error": "Pedido no encontrado"}), 404

    pedidos[pedido_id]["estado"] = "completado"
    return jsonify({"ok": True})


@app.route("/pedidos/<pedido_id>/error", methods=["POST"])
def marcar_error(pedido_id):
    if not check_token(request):
        return jsonify({"ok": False, "error": "Token inválido"}), 401

    if pedido_id not in pedidos:
        return jsonify({"ok": False, "error": "Pedido no encontrado"}), 404

    data = request.get_json(force=True) if request.data else {}
    pedidos[pedido_id]["estado"] = "error"
    pedidos[pedido_id]["error_msg"] = data.get("mensaje", "")
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5005))
    app.run(host="0.0.0.0", port=port, debug=False)
