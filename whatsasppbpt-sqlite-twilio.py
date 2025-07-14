from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# === FUNCIONES AUXILIARES ===

def init_db():
    conn = sqlite3.connect('user_states.db')  # Conexión a la base de datos SQLite
    c = conn.cursor()
    
    # Crear la tabla si no existe
    c.execute('''
    CREATE TABLE IF NOT EXISTS user_states (
        user_id TEXT PRIMARY KEY,
        state TEXT,
        last_active TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def get_user_state(user_id):
    conn = sqlite3.connect('user_states.db')
    c = conn.cursor()
    c.execute("SELECT state, last_active FROM user_states WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()

    if result:
        return {"state": result[0], "last_active": result[1]}
    return None

def save_user_state(user_id, state, last_active):
    conn = sqlite3.connect('user_states.db')
    c = conn.cursor()
    c.execute('''
    INSERT OR REPLACE INTO user_states (user_id, state, last_active)
    VALUES (?, ?, ?)
    ''', (user_id, state, last_active))
    conn.commit()
    conn.close()

def send_main_menu(msg):
    msg.body(
        "¡Hola! ¿En qué te podemos ayudar hoy?\n\n"
        "1⃣ Quiero ver el catálogo\n"
        "2⃣ Quiero cotizar\n"
        "3⃣ ¿Cuál es su horario y ubicación?\n"
        "4⃣ Quiero hablar con alguien\n\n"
        "Responde solamente con un número (1, 2, 3 o 4).\n"
        "Si quieres regresar a las opciones, escribe la palabra 'menú'."
    )

def send_menu_out_of_work(msg):
    msg.body(
        "¡Hola! Gracias por contactar con Game Army, te comentamos que estamos fuera de horario de servicio pero puedes decirnos cómo te podemos ayudar y te responderemos lo antes posible...\n\n"
        "1⃣ Quiero ver el catálogo\n"
        "2⃣ Quiero cotizar\n"
        "3⃣ ¿Cuál es su horario y ubicación?\n"
        "Responde solamente con un número (1, 2, 3 o 4).\n"
        "Si quieres regresar a las opciones, escribe la palabra 'menú'."
    )

init_db()

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip().lower()
    user_id = request.values.get("From")

    state = get_user_state.get(user_id)

    hora_actual = datetime.now().hour

    resp = MessagingResponse()
    msg = resp.message()

    if not state:
        state = {
            "state": "new",
            "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    last_active = datetime.strptime(state["last_active"], "%Y-%m-%d %H:%M:%S")
    if datetime.now() - last_active > timedelta(days=14):
        state["state"] = "new"

    current_state = state["state"]

    # === FLUJO PRINCIPAL ===

    if current_state == "new" and not (10 <= hora_actual < 16):
       send_menu_out_of_work(msg)
       state["state"] = "awaiting_option"

    elif current_state == "new":
        send_main_menu(msg)
        state["state"] = "awaiting_option"
    
    elif current_state == "awaiting_option":
        if incoming_msg == "1":
            msg.body("Claro, aquí está nuestro catálogo. Los precios aplican para tienda física. Quedamos pendientes...")
            msg.media("https://drive.google.com/uc?export=download&id=1DPABOXacxJbpxstjSisoX3OXCQsvjqsr")
            state["state"] = "completed"
        elif incoming_msg == "2":
            msg.body("Por favor indícanos:\n- Tipo de prenda\n- Cantidad\n- Tallas\n- Si van lisas o estampadas\nY te enviaremos tu cotización lo antes posible.")
            state["state"] = "completed"
        elif incoming_msg == "3":
            msg.body("Nuestro horario es:\n🕒 Lunes a Viernes: 10am a 4pm\n🕒 Sábado: 10am a 12:30pm\n📍 San Antonio el Desmonte, Pachuca: https://maps.app.goo.gl/iKoSvcPSUZ8zFPkn9")
            state["state"] = "completed"
        elif incoming_msg == "4":
            hora_actual = datetime.now().hour
            if 10 <= hora_actual < 16:
                msg.body("Claro, te atenderemos lo antes posible...")
            else:
                msg.body("Le recordamos que nuestro horario es:\n🕒 Lunes a Viernes: 10am a 4pm\n🕒 Sábado: 10am a 12:30pm.\nTe responderemos lo antes posible cuando estemos de vuelta.")
            state["state"] = "completed"
        else:
            if current_state == "awaiting_option":
                msg.body("Por favor responde con una opción válida (1, 2, 3 o 4).")
                state["state"] = "warned_invalid"
            else:
                state ["state"] = "completed"
                return str(resp)

    #elif current_state == "awaiting_quote":
        #msg.body("\u00a1Gracias! En breve te enviaremos tu cotización personalizada.\nSi necesitas algo más, responde con 'hola'.")
        #state["state"] = "completed"
        
    elif current_state == "completed":
        if incoming_msg.lower() in ["menú", "menu"]:
            if 10 <= hora_actual < 16:
                send_main_menu(msg)
            else:
                send_menu_out_of_work(msg)
            state["state"] = "awaiting_option"
        else:
            return str(resp)  # no responder

    state["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    save_user_state(user_id, state["state"], state["last_active"])

    return str(resp)

if __name__ == "__main__":
    init_db()  # Aseguramos que la base de datos se cree antes de iniciar el servidor
    app.run(debug=True)