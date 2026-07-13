from config import URL_BACKEND


def get_token(page) -> str:
    return page.session.store.get("session_token") or ""
