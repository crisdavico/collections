## Manual payment vouchers for cobranzas

Backend app to register one payment voucher per proof (bank transfer, check, cash
deposit, or unsupported). Each voucher owns sequence, chatter, optional image/PDF
designated proof (`message_main_attachment_id` on chatter `ir.attachment`; no Binary
`attachment` field), and a pending → approved/rejected lifecycle. Collection sheets
group a seller’s vouchers (`open`/`closed`) and have their own chatter and activities.

MCP `create_collection_vouchers` creates N vouchers in one savepoint and returns
`{vouchers:[{id,name,state,document_id},...]}`. Each payment may nest `raw_ocr` and
`seller_confirmed` (typed review fields; both omitted leaves empty provenance).
Coordinated Nebula tool `register_latest_collection_voucher` calls that MCP name only.
