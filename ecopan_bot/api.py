import frappe
import openai
import redis
import json

@frappe.whitelist(allow_guest=True)
def get_chatbot_response(session_id: str, prompt_message: str) -> str:
    # Recupera la chiave API di OpenAI dal file di configurazione del sito
    openai_api_key = frappe.conf.get("openai_api_key")
    if not openai_api_key:
        frappe.throw("Imposta 'openai_api_key' nel file di configurazione del sito.")

    # Recupera il modello dalle impostazioni personalizzate, con un valore predefinito
    openai_model = frappe.db.get_single_value("ecopanBot Settings", "openai_model") or "gpt-3.5-turbo"

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
                    "La seguente è una conversazione amichevole tra un umano e un'IA. "
                    "L'IA è loquace e fornisce molti dettagli specifici dal suo contesto. "
                    "Il nome dell'IA è ecopanbot e la sua data di nascita è il 24 aprile 2023. "
                    "Se l'IA non conosce la risposta a una domanda, lo dice sinceramente."
                )
            }
        ]

    # Aggiunge il nuovo messaggio dell'utente
    messages.append({"role": "user", "content": prompt_message})

    try:
        # Richiesta all'API di OpenAI
        response = openai.chat.completions.create(
            model=openai_model,
            messages=messages,
            temperature=0.7,
        )

        # Estrae la risposta dell'assistente
        assistant_message = response.choices[0].message.content

        # Aggiunge la risposta dell'assistente alla cronologia
        messages.append({"role": "assistant", "content": assistant_message})

        # Salva la cronologia aggiornata in Redis
        r.set(redis_key, json.dumps(messages))

        return assistant_message

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Errore nell'API di OpenAI")
        frappe.throw("Si è verificato un errore durante la generazione della risposta.")


