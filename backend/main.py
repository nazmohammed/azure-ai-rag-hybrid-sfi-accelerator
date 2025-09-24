
from flask import Flask, request, jsonify
from botbuilder.schema import Activity
from bot_handler import sla_bot, kb_bot, sla_adapter, kb_adapter
from dotenv import load_dotenv
import asyncio
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

def _auth_header_or_bypass():
    auth_header = request.headers.get("Authorization")
    if not auth_header and os.getenv("DEV_BYPASS_AUTH", "").lower() == "true":
        # Create a fake token for local dev
        return "Bearer dev"
    return auth_header

@app.route("/api/sla-bot", methods=["POST"])
def sla_messages():
    async def process():
        try:
            auth_header = _auth_header_or_bypass()
            if not auth_header:
                return jsonify({"error": "Authorization token is missing"}), 403

            activity_obj = Activity().deserialize(request.json)
            await sla_adapter.process_activity(activity_obj, auth_header, sla_bot.on_turn)
            return jsonify({"response": "Message sent to SLA bot!"})
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    return asyncio.run(process())

@app.route("/api/kb-bot", methods=["POST"])
def kb_messages():
    async def process():
        auth_header = _auth_header_or_bypass()
        if not auth_header:
            return jsonify({"error": "Authorization token is missing"}), 403

        activity_obj = Activity().deserialize(request.json)
        await kb_adapter.process_activity(activity_obj, auth_header, kb_bot.on_turn)
        return jsonify({"response": "Message sent to KB bot!"})

    return asyncio.run(process())

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "RAG Teams Bot is running!"})

if __name__ == "__main__":
    use_tls = os.getenv("USE_HTTPS", "false").lower() == "true"
    if use_tls:
        # Self-signed cert generated at runtime
        app.run(host="0.0.0.0", port=3978, ssl_context="adhoc")
    else:
        app.run(host="0.0.0.0", port=3978)
