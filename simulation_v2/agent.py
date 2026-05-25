import random

from pydantic import BaseModel

PROB_LIKE_POST = 0.25
PROB_WRITE_POST = 0.05
PROB_FOLLOW_USER = 0.02

MAX_POSTS_TO_LIKE_PER_TURN = 10
MAX_POSTS_TO_WRITE_PER_TURN = 5
MAX_USERS_TO_FOLLOW_PER_TURN = 5

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

def propose_like_posts(user, feed):
    proposed_action = propose_action()
    proposed_action = validate_action(proposed_action)
    # generate the like records to return
    return 

def propose_write_post():
    # propose writing a post. Single LLM call. Give details about
    # the user and then the posts in their feed and ask the LLM
    # to write a post about it.
    pass

def propose_follow_user():
    # non-agentic, just creates a follow record.
    pass


def determine_posts_to_like(user, feed):
    candidate_posts_to_like = propose_like_posts(user, feed)
    filtered_posts_to_like = []
    for candidate_like in candidate_posts_to_like:
        if random.random() < PROB_LIKE_POST:
            filtered_posts_to_like.append(candidate_like)
    return candidate_posts_to_like
   
# let's just say users can only write 1 post per turn, and for a given
# turn they may decide up to `MAX_POSTS_TO_WRITE_PER_TURN` times if
# they want to write a post or not (and at each interval, they choose to
# write a post with p=PROB_WRITE_POST).
def determine_posts_to_write(user, feed):
    candidate_posts_to_write = []
    for i in range(MAX_POSTS_TO_WRITE_PER_TURN):
        if random.random() > PROB_WRITE_POST:
            proposed_post = propose_write_post()
            candidate_posts_to_write.append(proposed_post)
    return candidate_posts_to_write

def determine_users_to_follow(user, feed):
    candidate_follow_records = []
    for post in feed:
        if random.random() > PROB_FOLLOW_USER:
            proposed_follow = propose_follow_user()
            candidate_follow_records.append(proposed_follow)
    return candidate_follow_records


def get_agent_actions(user, feed):
    like_posts = determine_posts_to_like(user, feed)
    pass

def get_agents_actions():
    pass

def validate_action(proposed_action: ProposedAction) -> ProposedAction | None:
    # returns either proposed action or None if it doesn't pass proposal.
    return None
