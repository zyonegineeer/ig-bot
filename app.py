import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "mi_token_secreto")
WHATSAPP_NUMBER = "5492262316418"

# Estado de conversación en memoria (simple)
user_states = {}

def get_message_details(mid):
    url = f"https://graph.instagram.com/v21.0/{mid}"
    params = {
        "fields": "message,from",
        "access_token": ACCESS_TOKEN
    }
    r = requests.get(url, params=params)
    data = r.json()
    print(f"Message fetch response: {data}")
    text = data.get("message", "")
    sender_id = data.get("from", {}).get("id", "")
    return text, sender_id

def send_message(recipient_id, text):
    url = f"https://graph.instagram.com/v21.0/me/messages"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
        "access_token": ACCESS_TOKEN
    }
    r = requests.post(url, headers=headers, json=payload)
    return r.json()

def handle_message(sender_id, text):
    text = text.strip().lower()
    state = user_states.get(sender_id, {"step": "inicio"})

    # Menú principal
    if state["step"] == "inicio" or text in ["hola", "hi", "buenas", "menu", "menú"]:
        user_states[sender_id] = {"step": "menu"}
        send_message(sender_id,
            "👋 ¡Hola! Soy el asistente de *ZY Engineer* — especialistas en agentes de IA para negocios.\n\n"
            "¿En qué estás interesado?\n\n"
            "1️⃣ Conocer precios\n"
            "2️⃣ Hablar con un representante\n"
            "3️⃣ Preguntas sobre chatbots / IA\n\n"
            "Respondé con el número de tu opción."
        )
        return

    # Opción 1: Precios
    if state["step"] == "menu" and text in ["1", "precios", "precio"]:
        user_states[sender_id] = {"step": "precios_tipo"}
        send_message(sender_id,
            "💼 ¡Genial! Para darte el mejor presupuesto necesito hacerte unas preguntas.\n\n"
            "¿Tu negocio es una *empresa* o un *negocio/local* (barbería, delivery, restaurante, etc.)?\n\n"
            "Respondé: *empresa* o *local*"
        )
        return

    if state["step"] == "precios_tipo":
        if "empresa" in text:
            user_states[sender_id] = {"step": "precios_complejidad", "tipo": "empresa"}
        elif "local" in text:
            user_states[sender_id] = {"step": "precios_complejidad", "tipo": "local"}
        else:
            send_message(sender_id, "Por favor respondé *empresa* o *local* 😊")
            return
        send_message(sender_id,
            "Perfecto. ¿Lo que necesitás es algo *simple* (responder preguntas frecuentes, derivar clientes) "
            "o algo más *complejo* (integraciones, múltiples flujos, base de datos)?\n\n"
            "Respondé: *simple* o *complejo*"
        )
        return

    if state["step"] == "precios_complejidad":
        tipo = state.get("tipo", "negocio")
        if "simple" in text or "complejo" in text:
            send_message(sender_id,
                f"📊 Basado en tu perfil ({tipo}, {text}):\n\n"
                f"💰 *Precio de entrada: USD 350*\n"
                f"🔧 *Mantenimiento mensual: USD 30/mes*\n"
                f"(incluye actualizaciones de contenido, ajustes de flujos, soporte)\n\n"
                f"¿Te interesa avanzar? Te conecto directo con nuestro representante 👇\n"
                f"📱 WhatsApp: https://wa.me/{WHATSAPP_NUMBER}"
            )
            user_states[sender_id] = {"step": "inicio"}
        else:
            send_message(sender_id, "Por favor respondé *simple* o *complejo* 😊")
        return

    # Opción 2: Representante
    if state["step"] == "menu" and text in ["2", "representante", "hablar", "contacto"]:
        user_states[sender_id] = {"step": "inicio"}
        send_message(sender_id,
            "🙋 ¡Con gusto! Te conecto con nuestro representante ahora mismo:\n\n"
            f"📱 WhatsApp: https://wa.me/{WHATSAPP_NUMBER}\n\n"
            "Te va a responder a la brevedad 🚀"
        )
        return

    # Opción 3: Preguntas sobre IA
    if state["step"] == "menu" and text in ["3", "preguntas", "ia", "chatbot", "agente"]:
        user_states[sender_id] = {"step": "faq"}
        send_message(sender_id,
            "🤖 ¡Buena pregunta! Aquí algunas respuestas frecuentes:\n\n"
            "*¿Qué es un agente de IA?*\nEs un sistema que atiende a tus clientes automáticamente 24/7, responde preguntas, califica leads y deriva cuando es necesario.\n\n"
            "*¿Funciona para mi negocio?*\nSí — lo adaptamos 100% a tu rubro, tono y procesos.\n\n"
            "*¿Cuánto tarda la implementación?*\nEntre 3 y 7 días hábiles.\n\n"
            "¿Querés saber algo más específico o avanzar con un presupuesto?\n\n"
            "1️⃣ Conocer precios\n"
            "2️⃣ Hablar con un representante"
        )
        user_states[sender_id] = {"step": "menu"}
        return

    # Default
    send_message(sender_id,
        "No entendí tu mensaje 😊 Escribí *menu* para ver las opciones."
    )
    user_states[sender_id] = {"step": "inicio"}


@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print(f"Incoming payload: {json.dumps(data)}")
    try:
        for entry in data.get("entry", []):
            messaging_list = entry.get("messaging", [])
            for messaging in messaging_list:
                sender = messaging.get("sender") or {}
                sender_id = sender.get("id")
                if not sender_id:
                    continue

                # Handle regular messages
                if "message" in messaging:
                    msg = messaging["message"]
                    text = msg.get("text") or msg.get("body", "")
                    if text:
                        handle_message(sender_id, text)

                # Handle message_edit (Instagram sends new messages as edits with num_edit: 0)
                elif "message_edit" in messaging:
                    msg = messaging["message_edit"]
                    mid = msg.get("mid", "")
                    num_edit = msg.get("num_edit", 1)
                    if num_edit == 0 and mid:
                        text, real_sender_id = get_message_details(mid)
                        if text and real_sender_id:
                            handle_message(real_sender_id, text)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
