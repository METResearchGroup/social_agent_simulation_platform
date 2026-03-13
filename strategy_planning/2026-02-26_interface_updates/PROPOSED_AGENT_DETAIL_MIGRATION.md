# Create interface for editing agent details

We want to ship a way to update an individual agent's details dynamically. this will all be in the "View agents" tab as you click into individual agents.

## Flow 0: Deprecate old UI and get "Create Agent" submission to work

PR 1:

- Remove the "Link to existing agents" in the UI and from the Create Agent form.
- Remove the "History" in the Create Agent form.
- Get the "Submit" to work, so that we can create agents.
- Success here = agents can be created (and are created) and will show up in the UI.

PR 2:

- Introduce ability to delete created agents.
- This allows us to fully test creating and then deleting agents.

## Flow 1: Follows

PR 2:

- Add a "Follows" dropdown in the agent view, with a number telling the number of follows.
- Add mock data to show some follows. Let's have a paginated list of follows, hydrate default 10 rows, 5 pages. Let's get that to work first so we can see who they follow.
- Show that this works.
- We may have to think about how to persist this in DB, as follows/likes/comments currently have to be tied to a run/turn, which may be an unnecessarily hard constraint. The constraint is OK though, if we just have another field that is an enum of two values, something like "manual" and "simulation", to know if we added it manually or if it was generated during a simulation. If during a simulation, we still maintain that run/turn is mandatory.

PR 3:

- Have a "Add follows" button under the view. Have a paginated clickable list of agents who they could follow (can use the same viewer component from PR 2) and then they can click a checkbox to the left and then any that they've clicked, they can then press "Save". This should persist then in the DB and then should appear as part of the follows for that Agent (so, they should appear in that dropdown).
- This should be basically the same as what's currently in the "Link to existing agents" UI right now.
- Out-of-scope: delete follows

## Flow 2: Followers

PR 1:

- Add a "Followers" dropdown. Same details as Follows.

PR 2:

- Have a "Add followers" button.
- Out of scope: Delete followers.

## Flow 3: Likes

PR 1:

- Update the existing Likes dropdown. Make it similar to the follows/followers (paginated 10 results per page, 5 pages default).

Pr 2:

- Have a "Add likes" button. Same interface as adding follows and followers.

## Flow 4: Comments

PR 1:

- Update the existing Comments dropdown. Ditto to above.

PR 2:

- Have a "Add comments" button. Same as above.

## Flow 5: AI-generated Bios

- This can be done as part of this unit of work.

## Overall notes

- I think that there should be an updated viewer component that displays the list of posts/comments/likes/follows, and manages, e.g., showing rows and showing pagination. It can take as a row component the individual CommentRow, PostRow, LikeRow, FollowRow, FollowerRow, for example, and just display that.
