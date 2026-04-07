import re
import requests
from core.cloud.base import CloudProvider, CloudFile

API_KEY = "AIzaSyDummyKeyReplaceLater"
FILES_URL = "https://www.googleapis.com/drive/v3/files"


class GoogleDriveProvider(CloudProvider):
    name = "google"

    def list_files(self, url):
        file_id = self._extract_id(url)
        if not file_id:
            raise ValueError("Cannot extract ID from Google Drive URL")

        is_folder = "/drive/folders/" in url

        if is_folder:
            return self._list_folder(file_id)
        else:
            return self._list_single(file_id)

    def _list_folder(self, folder_id):
        resp = requests.get(FILES_URL, params={
            "q": f"'{folder_id}' in parents and trashed=false",
            "key": API_KEY,
            "fields": "files(id,name,mimeType,size)",
            "pageSize": 1000,
        })
        resp.raise_for_status()
        files = []
        for item in resp.json().get("files", []):
            if item.get("mimeType", "").startswith("image/"):
                files.append(self._to_cloud_file(item))
        return files

    def _list_single(self, file_id):
        resp = requests.get(f"{FILES_URL}/{file_id}", params={
            "key": API_KEY,
            "fields": "id,name,mimeType,size",
        })
        resp.raise_for_status()
        item = resp.json()
        if item.get("mimeType", "").startswith("image/"):
            return [self._to_cloud_file(item)]
        return []

    def download(self, cloud_file, dest_path):
        resp = requests.get(cloud_file.download_url)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return dest_path

    def _to_cloud_file(self, item):
        fid = item["id"]
        return CloudFile(
            name=item.get("name", ""),
            download_url=f"{FILES_URL}/{fid}?alt=media&key={API_KEY}",
            size=int(item.get("size", 0)),
            preview_url=f"https://drive.google.com/thumbnail?id={fid}&sz=w200",
        )

    def _extract_id(self, url):
        m = re.search(r"/folders/([^/?]+)", url)
        if m:
            return m.group(1)
        m = re.search(r"/file/d/([^/?]+)", url)
        if m:
            return m.group(1)
        return None
