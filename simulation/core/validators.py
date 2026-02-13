def validate_run_id(run_id: str):
    if not run_id or not run_id.strip():
        raise ValueError("run_id is invalid")

def validate_turn_number(turn_number: int):
    if turn_number is None or turn_number < 0:
        raise ValueError("turn_number is invalid")
