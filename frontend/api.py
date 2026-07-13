def get_token(page) -> str:
    return page.session.store.get("session_token") or ""
