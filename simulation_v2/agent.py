import random

from pydantic import BaseModel

LIKE_POST_PROMPT = ""
WRITE_POST_PROMPT = ""

PROB_LIKE_POST = 0.25
PROB_WRITE_POST = 0.02
PROB_FOLLOW_USER = 0.02

class ProposedAction(BaseModel):
    pass

def propose_action() -> ProposedAction:
    # use langchain to get a proposal for an action.
    # something something chat completion?
    # TODO later: also add telemetry here so we can
    # see how it looks?
    # Out-of-scope: async support (unnecessary in v1).
    # NOTE: should have (1) the LLM pydantic model output
    # and (2) the actual action proposed. LLM should return
    # the number of which post to like or which user to follow
    # or what post to write. Else the 
    return ProposedAction()

def propose_like_post() -> ProposedAction | None:
    proposed_action = propose_action()
    proposed_action = validate_action(proposed_action)
    return 

def propose_write_post():
    pass

def propose_follow_user():
    # non-agentic, just creates a follow record.
    pass


def determine_posts_to_like(user, feed):
    candidate_posts_to_like = []
    for post in feed:
        if random.random() > PROB_LIKE_POST:
            propose_like_post()
   
def determine_posts_to_write(user, feed):
    pass

def determine_users_to_follow(user, feed):
    for post in feed:
        if random.random() > PROB_FOLLOW_USER:
            propose_follow_user9)


def get_agent_actions(user, feed):
    like_posts = determine_posts_to_like(user, feed)
    pass

def get_agents_actions():
    pass

def validate_action(proposed_action: ProposedAction) -> ProposedAction | None:
    # returns either proposed action or None if it doesn't pass proposal.
    return None
