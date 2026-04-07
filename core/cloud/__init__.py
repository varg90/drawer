import re


def detect_provider(url):
    if not url or not isinstance(url, str):
        return None

    if re.search(r"(disk\.yandex\.\w+/d/|yadi\.sk/d/)", url):
        from core.cloud.yandex import YandexDiskProvider
        return YandexDiskProvider()

    if re.search(r"drive\.google\.com/(drive/folders/|file/d/)", url):
        from core.cloud.google import GoogleDriveProvider
        return GoogleDriveProvider()

    return None
