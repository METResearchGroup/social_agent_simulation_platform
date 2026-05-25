
from pydantic import BaseModel

LIKE_POST_PROMPT = ""
WRITE_POST_PROMPT = ""

class ProposedAction(BaseModel):
    pass

def propose_action():
    # use langchain to get a proposal for an action.
    # something something chat completion?
    # TODO later: also add telemetry here so we can
    # see how it looks?
    # Out-of-scope: async support (unnecessary in v1).
    pass

def validate_action(proposed_action: ProposedAction):
    pass
