import sys

from app.services.ai import ai_gateway_service as _ai_gateway_service

sys.modules[__name__] = _ai_gateway_service
