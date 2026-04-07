import os
from dataclasses import dataclass
from core.constants import SUPPORTED_FORMATS


@dataclass
class CloudFile:
    name: str
    download_url: str
    size: int
    preview_url: str

    def is_image(self):
        ext = os.path.splitext(self.name)[1].lower()
        return ext in SUPPORTED_FORMATS


class CloudProvider:
    name = ""

    def list_files(self, url):
        raise NotImplementedError

    def download(self, cloud_file, dest_path):
        raise NotImplementedError
