import requests
from core.cloud.base import CloudProvider, CloudFile

API_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"
LIMIT = 150


class YandexDiskProvider(CloudProvider):
    name = "yandex"

    def list_files(self, url):
        files = []
        offset = 0
        while True:
            resp = requests.get(API_URL, params={
                "public_key": url,
                "limit": LIMIT,
                "offset": offset,
            })
            resp.raise_for_status()
            data = resp.json()

            if data.get("type") == "file":
                cf = self._to_cloud_file(data)
                if cf and cf.is_image():
                    return [cf]
                return []

            items = data.get("_embedded", {}).get("items", [])
            for item in items:
                cf = self._to_cloud_file(item)
                if cf and cf.is_image():
                    files.append(cf)

            total = data.get("_embedded", {}).get("total", 0)
            offset += LIMIT
            if offset >= total:
                break

        return files

    def download(self, cloud_file, dest_path):
        resp = requests.get(cloud_file.download_url)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return dest_path

    def _to_cloud_file(self, item):
        dl = item.get("file", "")
        if not dl:
            return None
        return CloudFile(
            name=item.get("name", ""),
            download_url=dl,
            size=item.get("size", 0),
            preview_url=item.get("preview", ""),
        )
