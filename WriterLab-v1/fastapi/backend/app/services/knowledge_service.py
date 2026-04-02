import sys

from app.services.knowledge import knowledge_service as _knowledge_service

sys.modules[__name__] = _knowledge_service
