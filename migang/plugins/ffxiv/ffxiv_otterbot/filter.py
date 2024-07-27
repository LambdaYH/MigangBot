def command_filter(message: str):
    if not message.startswith("/"):
        return False
    if message.startswith(("/hh", "/market", "/mitem", "/nn", "/nuannuan", "/luck")):
        return False
    return True
