
from botbuilder.core import BotFrameworkAdapterSettings
from botbuilder.core import BotFrameworkAdapter
from multiple_data_processing import initialize_all_pipelines
from botbuilder.core import ActivityHandler, TurnContext
import os
import logging

# Configure a simple logger; avoid logging secrets (never log app passwords)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("SLA_BOT_APP_ID: %s", os.getenv("SLA_BOT_APP_ID"))

# Adapter Configuration
sla_app_id = os.getenv("SLA_BOT_APP_ID", "")
sla_app_password = os.getenv("SLA_BOT_APP_PASSWORD", "")
kb_app_id = os.getenv("KB_BOT_APP_ID", "")
kb_app_password = os.getenv("KB_BOT_APP_PASSWORD", "")

# Ensure the adapter uses the correct tenant for acquiring tokens from AAD
channel_tenant = os.getenv("AZURE_TENANT_ID") or os.getenv("TENANT_ID")
print("Using channel tenant:", channel_tenant)

sla_settings = BotFrameworkAdapterSettings(
    app_id=sla_app_id or None,
    app_password=sla_app_password or None,
    channel_auth_tenant=channel_tenant,
)
kb_settings = BotFrameworkAdapterSettings(
    app_id=kb_app_id or None,
    app_password=kb_app_password or None,
    channel_auth_tenant=channel_tenant,
)

sla_adapter = BotFrameworkAdapter(sla_settings)
kb_adapter = BotFrameworkAdapter(kb_settings)

# Debug: show resolved oauth endpoint used by the adapters (helps diagnose tenant issues)
try:
    print("SLA adapter oauth endpoint:", sla_adapter.settings.oauth_endpoint)
    print("KB adapter oauth endpoint:", kb_adapter.settings.oauth_endpoint)
except Exception:
    pass

_kb_pipeline = None
_sla_pipeline = None

def _ensure_pipelines():
    global _kb_pipeline, _sla_pipeline
    if _kb_pipeline is None or _sla_pipeline is None:
        _kb_pipeline, _sla_pipeline = initialize_all_pipelines()


# Bot classes
class KB_Bot(ActivityHandler):
    def __init__(self):
        # pipeline will be set lazily on demand
        self.rag_pipeline = None

    async def on_message_activity(self, turn_context: TurnContext):
        user_message = (turn_context.activity.text or "").strip()
        if self.rag_pipeline is None:
            _ensure_pipelines()
            self.rag_pipeline = _kb_pipeline
        response = self.rag_pipeline.run(user_message)
        await turn_context.send_activity(response)


class SLA_Bot(ActivityHandler):
    def __init__(self):
        self.rag_pipeline = None

    async def on_message_activity(self, turn_context: TurnContext):
        user_message = (turn_context.activity.text or "").strip()
        if self.rag_pipeline is None:
            _ensure_pipelines()
            self.rag_pipeline = _sla_pipeline
        response = self.rag_pipeline.run(user_message)
        await turn_context.send_activity(response)


# Bot instances (note: pipelines are not initialized until first message)
kb_bot = KB_Bot()
sla_bot = SLA_Bot()
