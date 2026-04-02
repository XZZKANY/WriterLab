import sys

from app.services.context import context_service as _context_service

sys.modules[__name__] = _context_service
