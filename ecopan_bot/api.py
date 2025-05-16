import frappe
import openai
import redis
import json

@frappe.whitelist(allow_guest=True)
def get_chatbot_response(session_id: str, prompt_message: str) -> str:
    # Recupera la chiave API di OpenAI dal file di configurazione del sito
    openai_api_key = frappe.conf.get("openai_api_key")
    if not openai_api_key:
        frappe.throw("Please set `openai_api_key` in site config")

    # Recupera il modello da utilizzare dalle impostazioni
    openai_model = get_model_from_settings()

    # Configura la chiave API di OpenAI
    openai.api_key = openai_api_key

    # Connessione a Redis per la gestione della cronologia della chat
    redis_url = frappe.conf.get("redis_cache") or "redis://localhost:6379/0"
    r = redis.from_url(redis_url)

    # Chiave per la sessione corrente
    redis_key = f"chat_history:{session_id}"

    # Recupera la cronologia dei messaggi dalla sessione corrente
    history_json = r.get(redis_key)
    if history_json:
        messages = json.loads(history_json)
    else:
        # Messaggio di sistema iniziale
        messages = [
            {
                "role": "system",
                "content": (
                    "The following is a friendly conversation between a human and an AI. "
                    "The AI is talkative and provides lots of specific details from its context. "
                    "The AI's name is ecopanbot and its birth date is 24th April, 2023. "
                    "If the AI does not know the answer to a question, it truthfully says it does not know. "
                
                )
            }
        ]

    # Aggiunge il nuovo messaggio dell'utente
    messages.append({"role": "user", "content": prompt_message})

    try:
        # Richiesta alla API di OpenAI
        response = openai.ChatCompletion.create(
            model=openai_model,
            messages=messages,
            temperature=0.7,
        )

        # Estrae la risposta dell'assistente
        assistant_message = response.choices[0].message["content"]

        # Aggiunge la risposta dell'assistente alla cronologia
        messages.append({"role": "assistant", "content": assistant_message})

        # Salva la cronologia aggiornata in Redis
        r.set(redis_key, json.dumps(messages))

        return assistant_message

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "OpenAI Chat Error")
        frappe.throw("Si è verificato un errore durante la generazione della risposta.")

def get_model_from_settings():
    # Recupera il modello dalle impostazioni personalizzate, con un valore predefinito
    return (
        frappe.db.get_single_value("DoppioBot Settings", "openai_model") or "gpt-3.5-turbo"
    )