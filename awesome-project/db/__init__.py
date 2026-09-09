from .chat import init_db, save_message, get_history, get_recent_history
from .shops import init_shops_table, load_shops_from_csv, find_shop_for_part
from .whatsapp import init_whatsapp_table, save_whatsapp_message, get_conversations, get_messages

from .requests import (
    init_requests_table, get_open_request, create_request,
    append_conversation, update_fields, set_status, get_request, missing_fields
)


def init_all():
    init_db()
    init_shops_table()
    load_shops_from_csv()
    init_whatsapp_table()
    init_requests_table()