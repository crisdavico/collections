# Delta for Document Review

## MODIFIED Requirements

### Requirement: Eligible review queue

The system MUST queue only `collection.voucher` records that are members of the review
session's saved collection sheet, where `state` is `pending` and designated proof
(`message_main_attachment_id`) is present. Vouchers missing any eligibility criterion
MUST NOT appear. Vouchers that are not members of that sheet MUST NOT appear.
Parent-voucher `state == new` MUST NOT be an eligibility criterion. Confidence scores,
per-field stamps, and reviewer-note persistence MUST NOT be required. When the
identified sheet has no eligible members, the client MUST show an
empty/no-remaining-work state and MUST NOT fall back to a company-wide or other-sheet
queue. (Previously: Eligibility used Binary `attachment != False`, not designated
proof.)

#### Scenario: Queue eligibility

- GIVEN a saved sheet with pending members that have designated proof plus ineligible
  members (non-pending or no designated proof)
- WHEN an internal user opens Document Review for that sheet
- THEN only that sheet's eligible members MUST appear in the queue

#### Scenario: Empty queue

- GIVEN a saved sheet with no eligible members, and other sheets that have eligible
  pending vouchers with designated proof
- WHEN Document Review opens for that sheet
- THEN the client MUST show an empty/no-remaining-work state
- AND MUST NOT show vouchers from other sheets

#### Scenario: Cross-sheet isolation

- GIVEN two saved sheets that each have eligible pending vouchers with designated proof
- WHEN an internal user opens Document Review for sheet A, or attempts approve, reject,
  or rotation of a sheet B voucher using sheet A's identifier
- THEN only sheet A's eligible members MUST appear
- AND sheet B's vouchers MUST NOT appear
- AND the cross-sheet mutation MUST be refused

### Requirement: Authenticated binary attachment viewer

The client MUST render image and PDF proofs via authenticated `/web/content/{id}` for
the designated proof `ir.attachment`. The route MUST NOT use `field=attachment`. The OWL
layer MUST NOT embed attachment base64. The viewer MUST present distinct loading, error,
and empty-proof states. (Previously: Binary URLs used `model=collection.voucher` with
`field=attachment`.)

#### Scenario: Image via authenticated binary route

- GIVEN an eligible voucher with an image designated proof
- WHEN Document Review shows the proof
- THEN the image MUST load from `/web/content/{id}` of that designated proof
- AND OWL MUST NOT hold the attachment as base64

#### Scenario: PDF via authenticated binary route

- GIVEN an eligible voucher with a PDF designated proof
- WHEN Document Review shows the proof
- THEN the PDF MUST load from `/web/content/{id}` of that designated proof
- AND OWL MUST NOT hold the attachment as base64

#### Scenario: Viewer loading, error, and empty states

- GIVEN a voucher whose designated proof is loading, fails to load, or is absent/empty
- WHEN the viewer renders
- THEN it MUST show the matching loading, error, or empty state

### Requirement: Viewer rotation

The viewer MUST offer controls that rotate the current image or PDF 90 degrees clockwise
and counterclockwise. Rotation MUST be a view transform: it MUST NOT rewrite the stored
attachment bytes. The chosen angle MUST persist on the voucher and MUST be restored when
the reviewer views that same proof again (including after queue navigation or reopening
Document Review). PDF proofs MUST still load from the authenticated binary URL. Changing
or clearing `message_main_attachment_id` MUST reset rotation to 0 degrees. Extra chatter
files that do not change designated proof MUST NOT reset rotation. (Previously: Rotation
reset on Binary attachment replace or clear.)

#### Scenario: Rotate clockwise and counterclockwise

- GIVEN a ready image or PDF proof in Document Review
- WHEN the reviewer activates rotate-right or rotate-left
- THEN the proof MUST rotate 90 degrees in that direction
- AND the stored attachment bytes MUST remain unchanged
- AND the new angle MUST be saved on the voucher

#### Scenario: Restore saved rotation

- GIVEN a proof whose rotation was previously saved
- WHEN the reviewer views that proof again
- THEN the viewer MUST show it at the saved angle

#### Scenario: Attachment replace resets rotation

- GIVEN a voucher with a saved non-zero rotation
- WHEN `message_main_attachment_id` is changed or cleared
- THEN rotation MUST reset to 0 degrees

#### Scenario: Extra chatter files do not reset rotation

- GIVEN a voucher with a saved non-zero rotation and designated proof
- WHEN an extra chatter file is added without changing `message_main_attachment_id`
- THEN rotation MUST remain the saved angle
