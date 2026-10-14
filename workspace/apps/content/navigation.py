from urllib.parse import urlsplit


def list_return(request, fallback):
    """행 저장 뒤 현재 필터로 돌아간다. 다른 경로나 외부 URL은 허용하지 않는다."""
    target = request.POST.get("return_to", "")
    try:
        parsed = urlsplit(target)
    except ValueError:
        return fallback
    if not parsed.scheme and not parsed.netloc and parsed.path == fallback:
        return target
    return fallback
