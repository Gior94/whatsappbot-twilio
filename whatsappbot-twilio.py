from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import json
import os
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

STATE_FILE = "user_states.json"

# === FUNCIONES AUXILIARES ===
def load_user_states():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_states(states):
    with open(STATE_FILE, "w") as f:
        json.dump(states, f)

def send_main_menu(msg):
    msg.body(
        "¡Hola, somos Game Army! ¿En qué te podemos ayudar hoy?\n\n"
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

user_states = load_user_states()

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip().lower()
    user_id = request.values.get("From")

    user_states = load_user_states()
    state = user_states.get(user_id)

    zona_cdmx = pytz.timezone('America/Mexico_City')
    hora_actual = datetime.now(zona_cdmx).hour

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
            msg.media("https://drive.google.com/uc?export=download&id=19vSvYWPQ362RcJU-sJxRN9kEk3BYxtmo")
            state["state"] = "completed"
        elif incoming_msg == "2":
            msg.body("Por favor indícanos:\n- Tipo de prenda\n- Cantidad\n- Tallas\n- Si van lisas o estampadas\nY te enviaremos tu cotización lo antes posible.")
            state["state"] = "completed"
        elif incoming_msg == "3":
            msg.body("Nuestro horario es:\n🕒 Lunes a Viernes: 10am a 4pm\n🕒 Sábado: 10am a 12:30pm\n📍 San Antonio el Desmonte, Pachuca: https://maps.app.goo.gl/iKoSvcPSUZ8zFPkn9")
            state["state"] = "completed"
        elif incoming_msg == "4":
            hora_actual = datetime.now(zona_cdmx).hour
            if 10 <= hora_actual < 16:
                msg.body("Claro, te atenderemos lo antes posible...")
            else:
                msg.body("Le recordamos que nuestro horario de atención es:\n🕒 Lunes a Viernes: 10am a 4pm\n🕒 Sábado: 10am a 12:30pm.\nTe responderemos lo antes posible cuando estemos de vuelta.")
            state["state"] = "completed"
        else:
            msg.body("Puedes decirnos cómo podemos ayudarte y si quieres regresar a las opciones solo escribe la palabra 'menú'.")
            state["state"] = "completed"

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
    user_states[user_id] = state
    save_user_states(user_states)

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
