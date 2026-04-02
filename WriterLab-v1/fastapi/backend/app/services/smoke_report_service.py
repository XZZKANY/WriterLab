import sys

from app.services.runtime import smoke_report_service as _smoke_report_service

sys.modules[__name__] = _smoke_report_service
