from .chat import init_db, save_message, get_history, get_recent_history
from .shops import init_shops_table, load_shops_from_csv, find_shop_for_part, find_shops_for_part, get_shop_by_phone
from .whatsapp import (
    init_whatsapp_table, save_whatsapp_message, get_conversations,
    get_messages, message_already_processed
)
from .requests import (
    init_requests_table, get_open_request, create_request,
    append_conversation, update_fields, set_status, get_request,
    missing_fields, get_requests_for_phone, get_all_requests,
    mark_unread, mark_read, set_pending_dealer_question, clear_pending_dealer_question
)
from .dealer_threads import (
    init_dealer_threads_table, create_thread, append_thread_conversation,
    get_open_thread_by_phone, update_thread, get_threads_for_request,
    get_stale_threads, close_stale_thread, get_thread, close_other_threads,
    set_pending_mechanic_question, clear_pending_mechanic_question, set_alternative_offer
)
from .tickets import init_tickets_table, create_ticket, get_ticket_for_request

def init_all():
    init_db()
    init_shops_table()
    load_shops_from_csv()
    init_whatsapp_table()
    init_requests_table()
    init_dealer_threads_table()
    init_tickets_table()