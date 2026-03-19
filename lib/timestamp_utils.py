from datetime import datetime

CREATED_AT_FORMAT: str = "%Y_%m_%d-%H:%M:%S"


def get_current_timestamp() -> str:
    """Get the current timestamp in the contract format.

    Contract: all `created_at` string generation must use `CREATED_AT_FORMAT`.
    """

    return datetime.now().strftime(CREATED_AT_FORMAT)
