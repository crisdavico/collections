## Manual payment vouchers for cobranzas

Backend app to register one payment voucher per proof (bank transfer, check, cash
deposit, or unsupported). Each voucher owns sequence, chatter, optional image/PDF
designated proof (`message_main_attachment_id` on chatter `ir.attachment`; no Binary
`attachment` field), and a pending → approved/rejected lifecycle.

MCP `create_collection_vouchers` creates N vouchers in one savepoint and returns
`{vouchers:[{id,name,state,document_id},...]}`. Coordinated Nebula tool
`register_latest_collection_voucher` calls that MCP name only.
