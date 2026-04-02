import sys

from app.services.workflow import workflow_service as _workflow_service

sys.modules[__name__] = _workflow_service
