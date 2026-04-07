import os
import hashlib


class CacheManager:
    def __init__(self, cache_dir=None):
        if cache_dir is None:
            from core.session import APP_DIR
            cache_dir = os.path.join(APP_DIR, "cache")
        self._dir = cache_dir

    def _key(self, cloud_file):
        h = hashlib.md5(cloud_file.download_url.encode()).hexdigest()[:12]
        return f"{h}_{cloud_file.name}"

    def get(self, cloud_file):
        path = os.path.join(self._dir, self._key(cloud_file))
        return path if os.path.isfile(path) else None

    def put(self, cloud_file, data):
        os.makedirs(self._dir, exist_ok=True)
        path = os.path.join(self._dir, self._key(cloud_file))
        with open(path, "wb") as f:
            f.write(data)
        return path

    def clear(self):
        if not os.path.isdir(self._dir):
            return
        for name in os.listdir(self._dir):
            path = os.path.join(self._dir, name)
            if os.path.isfile(path):
                os.remove(path)

    def size(self):
        if not os.path.isdir(self._dir):
            return 0
        total = 0
        for name in os.listdir(self._dir):
            path = os.path.join(self._dir, name)
            if os.path.isfile(path):
                total += os.path.getsize(path)
        return total

    @staticmethod
    def format_size(n):
        if n < 1024:
            return f"{n} Б"
        elif n < 1024 * 1024:
            return f"{n / 1024:.1f} КБ"
        else:
            return f"{n / (1024 * 1024):.1f} МБ"
