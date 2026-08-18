# Delta for Collection Sheets

## ADDED Requirements

### Requirement: Saved-sheet header action opens Document Review

A saved collection sheet MUST expose a header action that opens Document Review with
that sheet's mandatory identifier. The action MUST be available when the current
company's flag is ON, MUST be hidden and refused when OFF, and MUST NOT open from an
unsaved sheet.

#### Scenario: Header action available when flag is on

- GIVEN a saved collection sheet and Document Review ON for the current company
- WHEN an internal user views the sheet form
- THEN the header action that opens Document Review MUST be available

#### Scenario: Header action hidden or refused when flag is off

- GIVEN a saved collection sheet and Document Review OFF for the current company
- WHEN an internal user views the sheet form or invokes the header action
- THEN the action MUST be hidden
- AND invocation MUST be refused

#### Scenario: Unsaved sheet must not open review

- GIVEN a new unsaved collection sheet and Document Review ON
- WHEN an internal user attempts to open Document Review from that form
- THEN Document Review MUST NOT open

#### Scenario: Sheet action parameters

- GIVEN a saved collection sheet and Document Review ON
- WHEN the header action runs
- THEN it MUST open the Document Review client action
- AND it MUST supply that sheet's identifier as a mandatory parameter
