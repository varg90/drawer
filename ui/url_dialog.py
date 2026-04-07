import os
import requests
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                              QPushButton, QLabel, QListWidget, QListWidgetItem,
                              QProgressBar, QCheckBox)
from PyQt6.QtGui import QPixmap, QIcon, QImage
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from core.cloud import detect_provider
from core.cloud.cache import CacheManager
from core.cloud.base import CloudFile
from core.models import ImageItem


class FetchWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, provider, url):
        super().__init__()
        self._provider = provider
        self._url = url

    def run(self):
        try:
            files = self._provider.list_files(self._url)
            self.finished.emit(files)
        except Exception as e:
            self.error.emit(str(e))


class PreviewWorker(QThread):
    preview_ready = pyqtSignal(int, QImage)  # index, image

    def __init__(self, files):
        super().__init__()
        self._files = files

    def run(self):
        for i, cf in enumerate(self._files):
            if not cf.preview_url:
                continue
            try:
                resp = requests.get(cf.preview_url, timeout=5)
                resp.raise_for_status()
                img = QImage()
                img.loadFromData(resp.content)
                if not img.isNull():
                    self.preview_ready.emit(i, img)
            except Exception:
                pass


class DownloadWorker(QThread):
    progress = pyqtSignal(int, int)  # current, total
    file_done = pyqtSignal(object, str)  # CloudFile, local_path
    finished = pyqtSignal()
    error = pyqtSignal(str)

    PARALLEL = 4

    def __init__(self, provider, files, cache):
        super().__init__()
        self._provider = provider
        self._files = files
        self._cache = cache

    def _download_one(self, cf):
        cached = self._cache.get(cf)
        if cached:
            return cf, cached
        resp = requests.get(cf.download_url, headers=self._headers(cf))
        resp.raise_for_status()
        path = self._cache.put(cf, resp.content)
        return cf, path

    def _headers(self, cf):
        rk = getattr(cf, "resource_key", "")
        fid = getattr(cf, "file_id", "")
        if rk and fid:
            return {"X-Goog-Drive-Resource-Keys": f"{fid}/{rk}"}
        return {}

    def run(self):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        total = len(self._files)
        done = 0
        with ThreadPoolExecutor(max_workers=self.PARALLEL) as pool:
            futures = {pool.submit(self._download_one, cf): cf for cf in self._files}
            for future in as_completed(futures):
                done += 1
                try:
                    cf, path = future.result()
                    self.file_done.emit(cf, path)
                except Exception:
                    pass
                self.progress.emit(done, total)
        self.finished.emit()


class UrlDialog(QDialog):
    images_loaded = pyqtSignal(list)  # list of ImageItem

    def __init__(self, theme, timer=300, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Загрузка по URL")
        self.theme = theme
        self._timer = timer
        self._provider = None
        self._cloud_files = []
        self._cache = CacheManager()
        self._worker = None
        self._dl_worker = None
        self._preview_worker = None

        self._build_ui()
        self._apply_theme()
        self.adjustSize()
        self.setMinimumWidth(400)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        # URL input row
        url_row = QHBoxLayout()
        url_row.setSpacing(6)
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("Вставьте ссылку Yandex Disk или Google Drive")
        self._url_input.returnPressed.connect(self._fetch)
        url_row.addWidget(self._url_input)
        self._fetch_btn = QPushButton("Загрузить")
        self._fetch_btn.clicked.connect(self._fetch)
        url_row.addWidget(self._fetch_btn)
        root.addLayout(url_row)

        # Status
        self._status = QLabel("")
        root.addWidget(self._status)

        # File list with checkboxes
        self._file_list = QListWidget()
        self._file_list.setIconSize(QSize(0, 0))
        self._file_list.setMinimumHeight(200)
        root.addWidget(self._file_list)

        # Select all / deselect all
        sel_row = QHBoxLayout()
        sel_row.setSpacing(6)
        self._sel_all_btn = QPushButton("Выбрать все")
        self._sel_all_btn.clicked.connect(self._select_all)
        sel_row.addWidget(self._sel_all_btn)
        self._sel_none_btn = QPushButton("Снять все")
        self._sel_none_btn.clicked.connect(self._select_none)
        sel_row.addWidget(self._sel_none_btn)
        self._preview_cb = QCheckBox("Превью")
        self._preview_cb.setChecked(False)
        self._preview_cb.toggled.connect(self._toggle_previews)
        sel_row.addWidget(self._preview_cb)
        sel_row.addStretch()
        self._count_label = QLabel("")
        sel_row.addWidget(self._count_label)
        root.addLayout(sel_row)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # Add button
        self._add_btn = QPushButton("Добавить")
        self._add_btn.clicked.connect(self._download_selected)
        self._add_btn.setEnabled(False)
        root.addWidget(self._add_btn)

        # Initially hide file list controls
        self._file_list.setVisible(False)
        self._sel_all_btn.setVisible(False)
        self._sel_none_btn.setVisible(False)
        self._preview_cb.setVisible(False)
        self._count_label.setVisible(False)
        self._add_btn.setVisible(False)

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"background-color: {t.bg}; color: {t.text_primary};")

        input_s = (f"background-color: {t.bg_secondary}; color: {t.text_primary}; "
                   f"border: 1px solid {t.border}; padding: 6px; font-size: 11px;")
        self._url_input.setStyleSheet(input_s)

        btn_s = (f"background-color: {t.bg_button}; color: {t.text_button}; "
                 f"border: 1px solid {t.border}; font-size: 10px; font-weight: 500; "
                 f"padding: 3px 6px;")
        for btn in [self._fetch_btn, self._sel_all_btn, self._sel_none_btn, self._add_btn]:
            btn.setStyleSheet(btn_s)

        self._preview_cb.setStyleSheet(
            f"color: {t.text_secondary}; font-size: 10px; font-weight: 500;")

        self._status.setStyleSheet(
            f"color: {t.text_secondary}; font-size: 10px; font-weight: 500;")
        self._count_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: 10px; font-weight: 500;")

        list_s = (f"QListWidget {{ background-color: {t.bg_secondary}; border: none; "
                  f"font-size: 11px; color: {t.text_primary}; }}"
                  f"QListWidget::item {{ padding: 3px; }}"
                  f"QListWidget::item:selected {{ background-color: {t.bg_active}; }}")
        self._file_list.setStyleSheet(list_s)

        self._progress.setStyleSheet(
            f"QProgressBar {{ background-color: {t.bg_secondary}; border: 1px solid {t.border}; "
            f"height: 8px; }} "
            f"QProgressBar::chunk {{ background-color: {t.text_secondary}; }}")

    def _fetch(self):
        url = self._url_input.text().strip()
        if not url:
            return

        self._provider = detect_provider(url)
        if not self._provider:
            self._status.setText("Неизвестный сервис. Поддерживаются Yandex Disk и Google Drive")
            return

        self._status.setText("Загрузка списка файлов...")
        self._fetch_btn.setEnabled(False)
        self._file_list.clear()

        self._worker = FetchWorker(self._provider, url)
        self._worker.finished.connect(self._on_fetch_done)
        self._worker.error.connect(self._on_fetch_error)
        self._worker.start()

    def _on_fetch_done(self, files):
        self._cloud_files = files
        self._file_list.clear()
        self._fetch_btn.setEnabled(True)

        if not files:
            self._status.setText("Изображений не найдено")
            return

        for cf in files:
            item = QListWidgetItem(cf.name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, cf)
            self._file_list.addItem(item)

        self._status.setText(f"Найдено изображений: {len(files)}")
        self._file_list.setVisible(True)
        self._sel_all_btn.setVisible(True)
        self._sel_none_btn.setVisible(True)
        self._preview_cb.setVisible(True)
        self._count_label.setVisible(True)
        self._add_btn.setVisible(True)
        self._add_btn.setEnabled(True)
        self._update_count()
        self._file_list.itemChanged.connect(self._update_count)
        self.adjustSize()

        if self._preview_cb.isChecked():
            self._start_previews()

    def _start_previews(self):
        if self._preview_worker and self._preview_worker.isRunning():
            return
        self._file_list.setIconSize(QSize(48, 48))
        self._preview_worker = PreviewWorker(self._cloud_files)
        self._preview_worker.preview_ready.connect(self._on_preview_ready)
        self._preview_worker.start()

    def _toggle_previews(self, checked):
        if checked:
            self._start_previews()
        else:
            if self._preview_worker and self._preview_worker.isRunning():
                self._preview_worker.terminate()
            for i in range(self._file_list.count()):
                self._file_list.item(i).setIcon(QIcon())
            self._file_list.setIconSize(QSize(0, 0))

    def _on_preview_ready(self, index, image):
        if not self._preview_cb.isChecked():
            return
        if index < self._file_list.count():
            pix = QPixmap.fromImage(image).scaled(
                48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self._file_list.item(index).setIcon(QIcon(pix))

    def _on_fetch_error(self, msg):
        self._fetch_btn.setEnabled(True)
        if "404" in msg or "403" in msg:
            self._status.setText("Нет доступа. Убедитесь что ссылка публичная")
        else:
            self._status.setText("Ошибка сети. Проверьте подключение к интернету")

    def _select_all(self):
        for i in range(self._file_list.count()):
            self._file_list.item(i).setCheckState(Qt.CheckState.Checked)

    def _select_none(self):
        for i in range(self._file_list.count()):
            self._file_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _update_count(self):
        checked = sum(1 for i in range(self._file_list.count())
                      if self._file_list.item(i).checkState() == Qt.CheckState.Checked)
        total = self._file_list.count()
        self._count_label.setText(f"{checked} / {total}")
        self._add_btn.setEnabled(checked > 0)

    def _get_selected_files(self):
        selected = []
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.data(Qt.ItemDataRole.UserRole))
        return selected

    def _download_selected(self):
        files = self._get_selected_files()
        if not files:
            return

        self._add_btn.setEnabled(False)
        self._fetch_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setMaximum(len(files))
        self._progress.setValue(0)
        self._status.setText("Скачивание...")

        self._results = []
        url = self._url_input.text().strip()
        self._dl_worker = DownloadWorker(self._provider, files, self._cache)
        self._dl_worker.progress.connect(self._on_dl_progress)
        self._dl_worker.file_done.connect(self._on_file_done)
        self._dl_worker.finished.connect(self._on_dl_finished)
        self._dl_worker.start()

    def _on_dl_progress(self, current, total):
        self._progress.setValue(current)
        self._status.setText(f"Скачивание... {current}/{total}")

    def _on_file_done(self, cf, local_path):
        url_text = self._url_input.text().strip()
        img = ImageItem(path=local_path, timer=self._timer, source_url=url_text)
        self._results.append(img)

    def _on_dl_finished(self):
        self._progress.setVisible(False)
        if self._results:
            self.images_loaded.emit(self._results)
            self.accept()
            return
        else:
            self._status.setText("Не удалось скачать файлы")
        self._add_btn.setEnabled(True)
        self._fetch_btn.setEnabled(True)
