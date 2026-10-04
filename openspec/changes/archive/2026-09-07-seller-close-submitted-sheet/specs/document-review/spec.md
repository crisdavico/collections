# Delta for Document Review

## MODIFIED Requirements

### Requirement: Sheet identifier required on review operations

`get_review_queue`, `action_review_approve`, and `action_review_set_rotation` MUST
require a validated sheet identifier and MUST operate only on that sheet. The identified
sheet MUST be `open` or `submitted`. Direct or global review MUST NOT succeed. Missing,
invalid, or neither-`open`-nor-`submitted` identifiers MUST be refused (not empty-queue
success). Mutations MUST refuse non-members of that sheet. OWL MUST pass the identifier
on queue, approve, and rotation. Reject MUST NOT be an operation. (Previously: The
identified sheet MUST be `open`.)

#### Scenario: Required sheet context

- GIVEN Document Review is ON
- WHEN a review queue or mutation runs with a missing or invalid sheet identifier
- THEN MUST refuse and MUST NOT succeed as an empty queue

#### Scenario: Stale membership

- GIVEN Document Review ON and a voucher that is no longer a member of the identified
  sheet
- WHEN approve or rotation runs with that sheet identifier
- THEN the mutation MUST be refused

#### Scenario: OWL and RPC arguments include the sheet identifier

- GIVEN Document Review opened from a saved open sheet
- WHEN the client loads the queue or performs approve or rotation
- THEN each corresponding RPC MUST include that sheet's identifier

#### Scenario: Open sheet identifier still works

- GIVEN Document Review ON and a saved open sheet
- WHEN `get_review_queue` runs with that sheet identifier
- THEN the call MUST succeed (empty queue allowed when no eligible members)

#### Scenario: Submitted sheet identifier works

- GIVEN Document Review ON and a saved submitted sheet
- WHEN `get_review_queue`, `action_review_approve`, or `action_review_set_rotation` runs
  with that sheet identifier
- THEN the call MUST succeed when members are eligible (empty queue allowed)
- AND MUST NOT `sudo()`

#### Scenario: Non-reviewable sheet identifier refused

- GIVEN Document Review ON and a saved proposal, closed, or cancelled sheet
- WHEN `get_review_queue`, `action_review_approve`, or `action_review_set_rotation` runs
  with that sheet identifier
- THEN MUST refuse (not empty-queue success)
