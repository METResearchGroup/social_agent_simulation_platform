from datetime import datetime


def get_current_timestamp() -> str:
    """Get the current timestamp in the format YYYY_MM_DD-HH:MM:SS."""
    return datetime.now().strftime("%Y_%m_%d-%H:%M:%S")
