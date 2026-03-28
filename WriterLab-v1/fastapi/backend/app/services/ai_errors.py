class AIErrorType:
    NETWORK = "NETWORK_ERROR"
    MODEL_OUTPUT = "MODEL_OUTPUT_ERROR"
    VALIDATION = "VALIDATION_ERROR"
    UNKNOWN = "UNKNOWN_ERROR"


class AIServiceError(Exception):
    def __init__(self, error_type: str, message: str, run_id=None):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.run_id = run_id
