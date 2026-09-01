# Delta for collection-vouchers

## ADDED Requirements

### Requirement: Voucher allocation membership

Each voucher MAY have `allocation_id`. Write of `allocation_id` MUST be refused
unless current and target (if set) are both `confirmed` or unset. Unlink MUST
be refused while `allocation_id` is set, including `pending`.

#### Scenario: allocation_id write and unlink

- GIVEN current and target confirmed or unset, or decided, or allocated
- WHEN `allocation_id` is written or the voucher is deleted
- THEN write succeeds only if both confirmed or unset; decided write and
  allocated unlink MUST be refused
