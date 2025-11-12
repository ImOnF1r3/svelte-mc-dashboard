from __future__ import annotations

import eventlet
eventlet.monkey_patch()  # Necessario per flask-socketio async

import os
import time
import subprocess
import psutil
import logging
import sys
import datetime
import json
from typing import Any
from dataclasses import dataclass, asdict

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from mcrcon import MCRcon
from flask_socketio import SocketIO, join_room, leave_room, emit

# --- Setup App, CORS e SocketIO ---

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# CORS per gli endpoint HTTP (da File 1)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Configurazione SocketIO (da File 2)
socketio = SocketIO(app, cors_allowed_origins="*", path="/ws", async_mode="eventlet")

ws_logger = logging.getLogger("ws")
ws_logger.setLevel(level=logging.INFO)

# --- Configurazione Minecraft (da File 1) ---
PID_FILE = "server.pid"
LOG_FILE = "logs/latest.log"
START_SCRIPT = "./start.sh"

RCON_HOST = "10.144.64.195"  # Assicurati che questo IP sia corretto!
RCON_PASS = "SuperDuperServer_Mk23022006fire"
RCON_PORT = 25575
# ---------------------------------------------

# --- Configurazione Gestione File TODO (da File 2) ---
TODO_FILE = "todos.json"

if os.path.exists(TODO_FILE):
    with open(TODO_FILE, "r") as f:
        try:
            TODOS = json.load(f)
        except:
            TODOS = []
else:
    TODOS = []

def save_todos():
    with open(TODO_FILE, "w") as f:
        json.dump(TODOS, f)
# ---------------------------------------------

# --- Funzioni Helper (da File 1 e 2) ---

def get_process_from_pidfile():
    """Controlla se il server è in esecuzione controllando il PID file."""
    if not os.path.exists(PID_FILE):
        return None
    
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        
        # Aggiunto 'name()' per compatibilità
        if psutil.pid_exists(pid) and 'java' in psutil.Process(pid).name():
            return psutil.Process(pid)
        else:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
            return None
    except (IOError, psutil.NoSuchProcess, ValueError, AttributeError): # Aggiunto AttributeError
        if os.path.exists(PID_FILE):
             os.remove(PID_FILE)
        return None

def error(message: str, *, status_code: int = 400, **data) -> Response:
    response = jsonify(data | {"success": False, "error": message})
    response.status_code = status_code
    return response

def success(**data: Any) -> Response:
    return jsonify(data | {"success": True})

def ws_success(*, status_code: int = 200, **data: Any) -> dict[str, Any]:
    return data | {"status_code": status_code, "success": True}

def ws_error(error: str, *, status_code: int = 400, **data) -> dict[str, Any]:
    return data | {"status_code": status_code, "success": False, "error": error}


#######################################
##                                   ##
##    ENDPOINT CONTROLLO MINECRAFT   ##
##           (da File 1)             ##
##                                   ##
#######################################

@app.route('/start', methods=['POST', 'OPTIONS'])
def start_server():
    if get_process_from_pidfile():
        return jsonify(error="Server già in esecuzione"), 400

    try:
        p = subprocess.Popen(
            [START_SCRIPT], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL, 
            preexec_fn=os.setpgrp
        )
        
        with open(PID_FILE, "w") as f:
            f.write(str(p.pid))
            
        return jsonify(status=f"Server in avvio (PID: {p.pid})...")
    except Exception as e:
        return jsonify(error=f"Errore avvio: {str(e)}"), 500

@app.route('/stop', methods=['POST', 'OPTIONS'])
def stop_server():
    process = get_process_from_pidfile()
    if not process:
        return jsonify(error="Server non in esecuzione"), 400
    
    try:
        # NOTA: Se il server MC è NELLO STESSO container, RCON_HOST dovrebbe essere '127.0.0.1'
        with MCRcon(RCON_HOST, RCON_PASS, RCON_PORT) as mcr:
            mcr.command("stop")
        
        process.wait(timeout=30)
        
        return jsonify(status="Server fermato correttamente.")
    except psutil.TimeoutExpired:
        process.terminate()
        time.sleep(1)
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return jsonify(status="Server non rispondeva, arresto forzato.")
    except Exception as e:
        try:
            process.terminate()
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
            return jsonify(status=f"Errore RCON ({e}), arresto forzato.")
        except Exception as kill_e:
            return jsonify(error=f"Errore anche nell'arresto forzato: {kill_e}"), 500

@app.route('/restart', methods=['POST', 'OPTIONS'])
def restart_server():
    process = get_process_from_pidfile()
    if process:
        stop_response = stop_server().get_json()
        if "error" in stop_response:
             return jsonify(error=f"Errore nella fase di stop: {stop_response['error']}"), 500
        
        try:
            process.wait(timeout=10)
        except psutil.TimeoutExpired:
            pass

    start_response = start_server().get_json()
    if "error" in start_response:
         return jsonify(error=f"Errore nella fase di start: {start_response['error']}"), 500

    return jsonify(status="Server riavviato.")

@app.route('/logs', methods=['GET', 'OPTIONS'])
def get_logs():
    """Legge le ultime 30 righe del file di log."""
    try:
        with open(LOG_FILE, "r", encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()[-30:]
        return jsonify(lines)
    except FileNotFoundError:
        return jsonify(["File di log non ancora creato."])
    except Exception as e:
        return jsonify([f"Errore lettura log: {str(e)}"])

@app.route('/stats', methods=['GET', 'OPTIONS'])
def get_stats():
    """Ottiene statistiche vitali del server e del sistema."""
    system_mem = psutil.virtual_memory()
    system_ram_usage = f"{system_mem.used / (1024**3):.1f}"
    system_ram_total = f"{system_mem.total / (1024**3):.1f}"
    
    process = get_process_from_pidfile()
    
    if not process:
        return jsonify(
            status="Offline",
            process_ram="0",
            system_ram=f"{system_ram_usage} / {system_ram_total} GB"
        )
    
    try:
        process_mem = process.memory_info().rss / (1024 * 1024)
        return jsonify(
            status="Online",
            process_ram=f"{process_mem:.0f} MB",
            system_ram=f"{system_ram_usage} / {system_ram_total} GB"
        )
    except psutil.NoSuchProcess:
         if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
         return jsonify(status="Offline", process_ram="0", system_ram=f"{system_ram_usage} / {system_ram_total} GB")

@app.route('/ping', methods=['GET', 'OPTIONS'])
def ping():
    """Endpoint semplice per testare la connessione."""
    return jsonify(status="ok", message="Server Flask attivo")


#####################
##                 ##
##    EVENTI WS    ##
##    (da File 2)    ##
##                 ##
#####################

@socketio.on('connect')
def handle_connect(*a):
    ws_logger.info("Client connected %s", a)

@socketio.on('disconnect')
def handle_disconnect(*a):
    ws_logger.info("Client disconnected %s", a)

@socketio.on('message')
def handle_message(msg):
    ws_logger.info("Message: %r", msg)

@socketio.on("custom_event")
def my_custom_event(data):
    ws_logger.info("Custom event: %r", data)
    return ws_success()


#########################
##                     ##
##    API ENDPOINTS    ##
##     (da File 2)     ##
##                     ##
#########################


@app.get("/api/status")
def status():
    return success(the_status_is="ok!")

@app.post("/api/message")
def msg():
    socketio.emit("message", "hello!")
    return success()


##################
###            ###
###  API TODO  ###
### (da File 2)  ###
###            ###
##################

@app.get("/api/todos")
def get_todos():
    return jsonify({"success": True, "todos": TODOS})

@socketio.on("get_todos")
def get_todos_ws(data, callback=None):
    """Invia la lista di todos al client tramite callback"""
    ws_logger.info("get_todos richiesto, invio %d todos", len(TODOS))
    response = {"todos": TODOS, "success": True}
    if callback:
        callback(response)
    return response

@socketio.on("add_todo")
def add_todo(data):
    # Aggiungiamo anche i campi opzionali 'completed' e 'date'
    todo = {
        "id": data["id"], 
        "title": data["title"], 
        "text": data["text"],
        "completed": data.get("completed", False),
        "date": data.get("date") # Può essere None o una stringa data
    }
    TODOS.append(todo)
    save_todos()
    socketio.emit("update_todos", TODOS)

@socketio.on("delete_todo")
def delete_todo(data):
    global TODOS
    TODOS = [t for t in TODOS if t["id"] != data["id"]]
    save_todos()
    socketio.emit("update_todos", TODOS)

@socketio.on("update_todos")
def update_todos(data):
    global TODOS
    TODOS = data.get("todos", [])
    save_todos()
    socketio.emit("update_todos", TODOS)

def on_starting(server):
    """function called by gunicorn"""
    if server is None:
        logging.warning("Starting in dev mode ...")
    else:
        logging.info("Starting in prod mode ...")


# --- Avvio Server ---

if __name__ == "__main__":

    on_starting(None)

    # Rende eseguibile lo script di avvio di MC (da File 1)
    os.system(f"chmod +x {START_SCRIPT}")
    
    print("--- Server Flask Unito in Avvio ---")
    print(f"Avvio su 0.0.0.0:8000 con SocketIO e Eventlet")
    print("CORS abilitato per tutte le origini (HTTP)")
    print("CORS SocketIO abilitato per * (WS)")
    print("---------------------------------")

    # Usa socketio.run() per supportare sia REST che WS (da File 2)
    socketio.run(
        app=app,
        host="0.0.0.0",
        port=8000,
        debug=True,
    )