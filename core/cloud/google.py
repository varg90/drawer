import os
import re
import requests
from core.cloud.base import CloudProvider, CloudFile

API_KEY = os.environ.get("DRAWER_GOOGLE_API_KEY", "")
FILES_URL = "https://www.googleapis.com/drive/v3/files"


class GoogleDriveProvider(CloudProvider):
    name = "google"

    def list_files(self, url):
        file_id = self._extract_id(url)
        if not file_id:
            raise ValueError("Cannot extract ID from Google Drive URL")

        resource_key = self._extract_resource_key(url)
        is_folder = "/drive/folders/" in url

        if is_folder:
            return self._list_folder(file_id, resource_key)
        else:
            return self._list_single(file_id, resource_key)

    def _list_folder(self, folder_id, resource_key=None):
        headers = {}
        if resource_key:
            headers["X-Goog-Drive-Resource-Keys"] = f"{folder_id}/{resource_key}"

        resp = requests.get(FILES_URL, params={
            "q": f"'{folder_id}' in parents and trashed=false",
            "key": API_KEY,
            "fields": "files(id,name,mimeType,size,resourceKey,thumbnailLink)",
            "pageSize": 1000,
            "includeItemsFromAllDrives": True,
            "supportsAllDrives": True,
        }, headers=headers)
        resp.raise_for_status()
        files = []
        for item in resp.json().get("files", []):
            if item.get("mimeType", "").startswith("image/"):
                files.append(self._to_cloud_file(item))
        return files

    def _list_single(self, file_id, resource_key=None):
        headers = {}
        if resource_key:
            headers["X-Goog-Drive-Resource-Keys"] = f"{file_id}/{resource_key}"

        resp = requests.get(f"{FILES_URL}/{file_id}", params={
            "key": API_KEY,
            "fields": "id,name,mimeType,size,resourceKey,thumbnailLink",
        }, headers=headers)
        resp.raise_for_status()
        item = resp.json()
        if item.get("mimeType", "").startswith("image/"):
            return [self._to_cloud_file(item)]
        return []

    def download(self, cloud_file, dest_path):
        headers = {}
        rk = getattr(cloud_file, "resource_key", "")
        fid = getattr(cloud_file, "file_id", "")
        if rk and fid:
            headers["X-Goog-Drive-Resource-Keys"] = f"{fid}/{rk}"

        resp = requests.get(cloud_file.download_url, headers=headers)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return dest_path

    def _to_cloud_file(self, item):
        fid = item["id"]
        rk = item.get("resourceKey", "")
        cf = CloudFile(
            name=item.get("name", ""),
            download_url=f"https://drive.google.com/uc?export=download&id={fid}",
            size=int(item.get("size", 0)),
            preview_url=item.get("thumbnailLink", ""),
        )
        cf.file_id = fid
        cf.resource_key = rk
        return cf

    def _extract_id(self, url):
        m = re.search(r"/folders/([^/?]+)", url)
        if m:
            return m.group(1)
        m = re.search(r"/file/d/([^/?]+)", url)
        if m:
            return m.group(1)
        return None

    def _extract_resource_key(self, url):
        m = re.search(r"resourcekey=([^&]+)", url)
        return m.group(1) if m else None
