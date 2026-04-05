import os
from core.constants import SUPPORTED_FORMATS

def filter_image_files(file_paths):
    return [f for f in file_paths if os.path.splitext(f)[1].lower() in SUPPORTED_FORMATS]

def scan_folder(folder_path):
    all_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path)]
    return filter_image_files(all_files)
