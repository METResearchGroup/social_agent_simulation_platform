"""API-layer exceptions for route error mapping.

Routes should not import core/db modules directly; they should translate failures from
services into consistent HTTP responses. These exceptions are intentionally simple and
carry only the data the route needs to build an error payload.
"""

from __future__ import annotations


class ApiHandleAlreadyExistsError(Exception):
    def __init__(self, handle: str):
        super().__init__(handle)
        self.handle = handle


class ApiAgentNotFoundError(Exception):
    def __init__(self, handle: str):
        super().__init__(handle)
        self.handle = handle


class ApiRunNotFoundError(Exception):
    def __init__(self, run_id: str):
        super().__init__(run_id)
        self.run_id = run_id


class ApiRunCreationFailedError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
