# Cloud Image Loading — Design Spec

## Summary

Add a "URL" button to the image editor that lets users load images from public cloud links (Yandex Disk, Google Drive). The app auto-detects the service, shows a file picker dialog with previews, and caches downloaded files locally.

## User Flow

1. User clicks **"URL"** button in the image editor toolbar (next to "+ Файлы", "+ Папка")
2. Dialog opens with a URL input field and "Загрузить" button
3. User pastes a public link, clicks "Загрузить"
4. App auto-detects service by URL pattern:
   - `disk.yandex.ru/d/...` → Yandex Disk
   - `drive.google.com/drive/folders/...` or `drive.google.com/file/d/...` → Google Drive
   - Unknown → error message
5. App fetches file list from the cloud (shows loading indicator)
6. Dialog displays list of images with:
   - Checkbox per file
   - Small preview icon
   - File name
   - "Выбрать все" / "Снять все" buttons
7. User selects files, clicks "Добавить"
8. Files download to local cache with progress bar
9. Images appear in the editor as normal ImageItem entries

## Architecture

### Provider System (`core/cloud/`)

```
core/cloud/
    __init__.py       — detect_provider(url) function
    base.py           — CloudProvider abstract base class
    yandex.py         — YandexDiskProvider
    google.py         — GoogleDriveProvider
    cache.py          — CacheManager
```

**CloudProvider (base class):**
```python
class CloudProvider:
    def list_files(url) -> list[CloudFile]
        # Returns list of image files at the URL
    
    def download(cloud_file, dest_path) -> Path
        # Downloads a single file to dest_path
```

**CloudFile (data class):**
```python
@dataclass
class CloudFile:
    name: str           # original filename
    download_url: str   # direct download URL
    size: int           # file size in bytes (0 if unknown)
    preview_url: str    # thumbnail URL (empty if unavailable)
```

**detect_provider(url):**
- Matches URL against known patterns
- Returns the appropriate provider instance or None

### Cache (`core/cloud/cache.py`)

- Location: `APP_DIR/cache/`
- File naming: `{service}_{hash}_{original_name}` to avoid collisions
- `CacheManager.get(cloud_file)` — returns local path if cached, None otherwise
- `CacheManager.put(cloud_file, data)` — saves to cache, returns local path
- `CacheManager.clear()` — deletes all cached files
- `CacheManager.size()` — returns total cache size in bytes

### URL Dialog (`ui/url_dialog.py`)

- Modal dialog, centered over editor window
- Components:
  - QLineEdit for URL input
  - QPushButton "Загрузить" to fetch file list
  - QLabel for status/errors
  - QListWidget with checkable items and preview icons
  - "Выбрать все" / "Снять все" buttons
  - QProgressBar for download progress
  - "Добавить" button to confirm selection
- Styled consistently with the rest of the app (uses Theme)

### ImageItem Changes (`core/models.py`)

Add optional `source_url` field:
```python
@dataclass
class ImageItem:
    path: str
    timer: int = 300
    source_url: str = ""   # empty for local files
```

This field is saved/loaded via `to_dict()`/`from_dict()` for session persistence. It identifies cloud-sourced images but doesn't change any existing behavior.

## API Details

### Yandex Disk

Public resources API (no auth needed):
- Endpoint: `https://cloud-api.yandex.net/v1/disk/public/resources?public_key={url}`
- For folders: returns `_embedded.items[]` with file list
- Each item has `name`, `preview`, `file` (download URL), `size`
- Filter by `media_type == "image"` or by extension
- Pagination: `limit` and `offset` params (default limit 20, max 150)

### Google Drive

Public folder listing (no auth needed for public folders):
- Get folder ID from URL: `drive.google.com/drive/folders/{folder_id}`
- API endpoint: `https://www.googleapis.com/drive/v3/files?q='{folder_id}'+in+parents&key={API_KEY}&fields=files(id,name,mimeType,size)`
- Download: `https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={API_KEY}`
- Thumbnail: `https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={API_KEY}` scaled
- Requires an API key (free, no OAuth)
- Filter by mimeType starts with "image/"

**Note:** Google Drive requires a free API key. Options:
- Bundle a key with the app (simple, but has quota limits)
- Ask user to provide their own key in settings (more setup, but no quota issues)
- Start with a bundled key, add "use your own key" later if needed

## Dependencies

- `requests` library — HTTP client (install via `python -m pip install requests`)
- No other new dependencies needed

## Settings Integration

- "Очистить кеш" button in the main settings window
- Shows current cache size next to the button
- Placed near "Случайный порядок" / "Поверх всех окон" checkboxes area

## Error Handling

- Invalid/unrecognized URL → "Неизвестный сервис. Поддерживаются Yandex Disk и Google Drive"
- Private/inaccessible link → "Нет доступа. Убедитесь что ссылка публичная"
- No images in folder → "Изображений не найдено"
- Network error → "Ошибка сети. Проверьте подключение к интернету"
- Download failure (single file) → skip, show warning, continue with others

## What Does NOT Change

- All existing image functionality (timers, sorting, drag-drop, list/grid view)
- Slideshow viewer — loads from file path as before (cached path)
- Session persistence format — backward compatible (source_url defaults to "")

## Future Extensibility

Adding a new provider requires:
1. Create `core/cloud/newservice.py` implementing `CloudProvider`
2. Add URL pattern to `detect_provider()` in `__init__.py`

No UI changes needed — the dialog works with any provider.
