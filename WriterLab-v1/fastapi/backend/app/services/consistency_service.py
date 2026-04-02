import sys

from app.services.consistency import consistency_service as _consistency_service

sys.modules[__name__] = _consistency_service
