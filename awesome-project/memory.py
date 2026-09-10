import inspect
import db

def with_memory(limit: int = 10):
    def decorator(func):
        async def wrapper(msg):
            history = db.get_recent_history(limit=limit)
            context = "".join(
                f"User: {h['user_message']}\nAssistant: {h['bot_response']}\n"
                for h in history
            )
            context += f"User: {msg.text}\nAssistant:"

            response = await func(msg, context)

            db.save_message(msg.text, str(response))
            return response

        wrapper.__name__ = func.__name__
        wrapper.__signature__ = inspect.Signature(
            parameters=[inspect.signature(func).parameters["msg"]]
        )
        return wrapper
    return decorator
