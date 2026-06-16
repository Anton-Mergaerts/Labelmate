from __future__ import annotations

from app_data.settings import printer_store
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QInputDialog,
    QLineEdit,
)

from src import db
from src import printing
from src import requirements_check
from src import setup_help
from src.paths import db_path


APP_BG = '#f4f7fb'
PANEL_BG = '#ffffff'
TEXT_PRIMARY = '#172033'
TEXT_SECONDARY = '#617087'
ACCENT = '#2f6fed'
ACCENT_DARK = '#2559bb'
BORDER = '#dbe3ee'
SUCCESS = '#1f8a70'
SOFT_BLUE = '#eef4ff'


def _card_frame(name: str) -> QFrame:
    frame = QFrame()
    frame.setObjectName(name)
    frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    return frame


def _field_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName('FieldLabel')
    return label


def _pil_to_qpixmap(image) -> QPixmap:
    rgb = image.convert('RGB')
    data = rgb.tobytes('raw', 'RGB')
    qimage = QImage(
        data,
        rgb.width,
        rgb.height,
        rgb.width * 3,
        QImage.Format.Format_RGB888,
    )
    return QPixmap.fromImage(qimage.copy())


def _compose_preview_pixmap(label: QPixmap) -> QPixmap:
    """Show the printable label on 62 mm tape, with approximate printer feed margins."""
    if label.isNull():
        return label

    label_w = label.width()
    label_h = label.height()
    side_margin = max(
        1,
        int(round(label_w * (printing.TAPE_WIDTH_PX - printing.PRINTABLE_WIDTH_PX) / printing.PRINTABLE_WIDTH_PX / 2)),
    )
    feed_top = max(4, int(round(label_h * printing.PREVIEW_FEED_TOP_RATIO)))
    feed_bottom = max(4, int(round(label_h * printing.PREVIEW_FEED_BOTTOM_RATIO)))

    canvas_w = label_w + side_margin * 2
    canvas_h = label_h + feed_top + feed_bottom
    framed = QPixmap(canvas_w, canvas_h)
    framed.fill(QColor('#ffffff'))

    painter = QPainter(framed)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    tape_color = QColor('#b7c0cc')
    painter.fillRect(0, 0, side_margin, canvas_h, tape_color)
    painter.fillRect(side_margin + label_w, 0, side_margin, canvas_h, tape_color)
    painter.drawPixmap(side_margin, feed_top, label)
    painter.setPen(QPen(QColor('#8fa0b3'), 1))
    painter.drawRect(side_margin, feed_top, label_w - 1, label_h - 1)
    painter.end()

    return framed


def apply_theme(app: QApplication):
    app.setStyle('Fusion')
    app.setFont(QFont('Segoe UI', 10))
    app.setStyleSheet(
        f'''
        QMainWindow {{ background: {APP_BG}; }}
        QMenuBar {{
            background: {PANEL_BG};
            border-bottom: 1px solid {BORDER};
            padding: 4px 8px;
        }}
        QMenuBar::item {{
            background: transparent;
            padding: 6px 10px;
            border-radius: 8px;
        }}
        QMenuBar::item:selected {{
            background: {SOFT_BLUE};
        }}
        QMenu {{
            background: {PANEL_BG};
            border: 1px solid {BORDER};
            padding: 6px;
        }}
        QMenu::item {{
            padding: 8px 24px 8px 12px;
            border-radius: 8px;
        }}
        QMenu::item:selected {{
            background: {ACCENT};
            color: white;
        }}
        QWidget {{ color: {TEXT_PRIMARY}; }}
        QFrame#Card, QFrame#PreviewCard, QFrame#DialogCard {{
            background: {PANEL_BG};
            border: 1px solid {BORDER};
            border-radius: 18px;
        }}
        QLabel#AppTitle {{
            color: {TEXT_PRIMARY};
            font-size: 30px;
            font-weight: 700;
        }}
        QLabel#AppSubtitle {{
            color: {TEXT_SECONDARY};
            font-size: 10pt;
        }}
        QLabel#CardTitle {{
            color: {TEXT_PRIMARY};
            font-size: 15pt;
            font-weight: 700;
        }}
        QLabel#CardSubTitle, QLabel#StatusLabel, QLabel#SectionHint {{
            color: {TEXT_SECONDARY};
        }}
        QLabel#PreviewHeading {{
            color: {TEXT_SECONDARY};
            font-size: 9pt;
            font-weight: 700;
            letter-spacing: 1px;
        }}
        QFrame#PreviewCanvas {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #f3f6fa, stop:1 #e4eaf2
            );
            border: 1px solid {BORDER};
            border-radius: 16px;
        }}
        QFrame#PreviewStage {{
            background: transparent;
        }}
        QLabel#PreviewTapeCaption {{
            color: {TEXT_SECONDARY};
            font-size: 8pt;
            font-weight: 600;
        }}
        QLabel#PreviewImage {{
            background: transparent;
        }}
        QLabel#SetupChecklist {{
            color: {TEXT_PRIMARY};
            background: {SOFT_BLUE};
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 12px 14px;
        }}
        QLabel#SetupNote {{
            color: {TEXT_SECONDARY};
            background: #f8fafc;
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 12px 14px;
            font-size: 9pt;
        }}
        QLabel#SetupWarning {{
            color: #8a2b2b;
            background: #fff1f1;
            border: 1px solid #f0c7c7;
            border-radius: 12px;
            padding: 12px 14px;
        }}
        QLabel#PreviewMeta {{
            color: {TEXT_SECONDARY};
            font-size: 9pt;
        }}
        QLabel#TinyBadge {{
            color: {SUCCESS};
            background: #edf9f4;
            border: 1px solid #d9f0e5;
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 9pt;
            font-weight: 600;
        }}
        QLabel#FieldLabel {{
            color: {TEXT_PRIMARY};
            font-weight: 700;
        }}
        QComboBox, QLineEdit {{
            background: white;
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 9px 12px;
            min-height: 18px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 22px;
        }}
        QComboBox QAbstractItemView {{
            background: white;
            border: 1px solid {BORDER};
            selection-background-color: {ACCENT};
            selection-color: white;
            outline: 0;
        }}
        QTabWidget::pane {{
            border: 1px solid {BORDER};
            border-radius: 14px;
            background: {PANEL_BG};
            top: -1px;
        }}
        QTabBar::tab {{
            background: #edf2fb;
            color: {TEXT_SECONDARY};
            border: 1px solid {BORDER};
            border-bottom: none;
            padding: 9px 14px;
            margin-right: 6px;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }}
        QTabBar::tab:selected {{
            background: {PANEL_BG};
            color: {TEXT_PRIMARY};
            font-weight: 700;
        }}
        QListWidget {{
            background: white;
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 6px;
            outline: none;
        }}
        QListWidget::item {{
            padding: 8px 10px;
            border-radius: 10px;
        }}
        QListWidget::item:selected {{
            background: {ACCENT};
            color: white;
        }}
        QPushButton {{
            border: 1px solid #c5d0e0;
            border-radius: 12px;
            background: white;
            color: {TEXT_PRIMARY};
            font-weight: 600;
            padding: 10px 16px;
            min-height: 18px;
        }}
        QPushButton:hover {{
            background: #f0f5fc;
            border-color: {ACCENT};
        }}
        QPushButton:pressed {{
            background: #e4edfb;
        }}
        QPushButton#PrimaryButton {{
            border: 2px solid {ACCENT_DARK};
            background: {ACCENT};
            color: white;
            font-weight: 700;
            font-size: 11pt;
            padding: 12px 24px;
            min-height: 22px;
        }}
        QPushButton#PrimaryButton:hover {{
            background: {ACCENT_DARK};
            border-color: #1d4fb8;
        }}
        QPushButton#PrimaryButton:pressed {{
            background: #1d4fb8;
        }}
        QPushButton#SecondaryButton {{
            border: 2px solid {ACCENT};
            background: {SOFT_BLUE};
            color: {ACCENT_DARK};
            font-weight: 700;
            font-size: 11pt;
            padding: 12px 24px;
            min-height: 22px;
        }}
        QPushButton#SecondaryButton:hover {{
            background: #dfeaff;
            border-color: {ACCENT_DARK};
        }}
        QPushButton#SecondaryButton:pressed {{
            background: #d0e2ff;
        }}
        QPushButton#GhostButton {{
            background: white;
            border: 1px solid #c5d0e0;
            color: {TEXT_PRIMARY};
            font-weight: 600;
        }}
        QPushButton#GhostButton:hover {{
            background: #f8fbff;
            border-color: {ACCENT};
            color: {ACCENT_DARK};
        }}
        QDialog {{
            background: {APP_BG};
        }}
        ''')


def row_item(item_id: int, name: str) -> QListWidgetItem:
    item = QListWidgetItem(name)
    item.setData(Qt.UserRole, {'id': item_id, 'name': name})
    return item


def item_payload(item: QListWidgetItem | None):
    if item is None:
        return None
    return item.data(Qt.UserRole) or None


def blocking_check(results: list[requirements_check.CheckResult], name: str):
    return next((item for item in results if item.name == name and item.blocking), None)


def _show_print_blocked_dialog(parent, results: list[requirements_check.CheckResult]) -> None:
    driver_issue = blocking_check(results, 'Printer driver')
    if driver_issue:
        box = QMessageBox(parent)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle('Brother driver required')
        box.setText(
            'This printer is using a Microsoft Windows driver. '
            'Labelmate cannot print labels that way.'
        )
        box.setInformativeText(
            'Install the official Brother QL-820NWB driver from brother.com and add the '
            'printer again. The driver name should be “Brother QL-820NWB”, not '
            '“Microsoft IPP Class Driver”.\n\n'
            f'{driver_issue.message}'
        )
        setup_button = box.addButton('Open Printer Setup', QMessageBox.ButtonRole.ActionRole)
        download_button = box.addButton('Download Brother driver', QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked == setup_button:
            PrinterSetupDialog(parent, results=results).exec()
        elif clicked == download_button:
            setup_help.open_brother_driver_download()
        return

    brother_issue = blocking_check(results, 'Brother printer')
    if brother_issue:
        box = QMessageBox(parent)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle('Brother printer not found')
        box.setText('No Brother QL printer was found in Windows.')
        box.setInformativeText(
            'Add the printer using the official Brother driver, then pick it in '
            'Printer Settings.\n\n'
            f'{brother_issue.hint or brother_issue.message}'
        )
        setup_button = box.addButton('Open Printer Setup', QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        if box.clickedButton() == setup_button:
            PrinterSetupDialog(parent, results=results).exec()
        return

    PrinterSetupDialog(parent, results=results).exec()


class PrinterSetupDialog(QDialog):
    def __init__(self, parent=None, *, results=None):
        super().__init__(parent)
        self.setWindowTitle('Printer Setup')
        self.setMinimumWidth(620)
        self.setMinimumHeight(520)
        self.results = results or requirements_check.run_all_checks()

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title = QLabel('Printer Setup')
        title.setObjectName('CardTitle')
        layout.addWidget(title)
        layout.addWidget(QLabel('One-time Windows + Brother setup. Labelmate cannot install drivers for you.'))

        checklist = QLabel(setup_help.SETUP_CHECKLIST)
        checklist.setObjectName('SetupChecklist')
        checklist.setWordWrap(True)
        layout.addWidget(checklist)

        raster_note = QLabel(setup_help.TROUBLESHOOTING_INFO)
        raster_note.setObjectName('SetupNote')
        raster_note.setWordWrap(True)
        layout.addWidget(raster_note)

        self.ipp_warning = QLabel(setup_help.IPP_DRIVER_FIX_STEPS)
        self.ipp_warning.setObjectName('SetupWarning')
        self.ipp_warning.setWordWrap(True)
        self.ipp_warning.setVisible(self._has_ipp_driver_issue())
        layout.addWidget(self.ipp_warning)

        action_row = QHBoxLayout()
        driver_button = QPushButton('Download Brother driver')
        driver_button.setObjectName('GhostButton')
        driver_button.clicked.connect(setup_help.open_brother_driver_download)
        printers_button = QPushButton('Open Windows Printers')
        printers_button.setObjectName('GhostButton')
        printers_button.clicked.connect(setup_help.open_windows_printers)
        properties_button = QPushButton('Printer properties')
        properties_button.setObjectName('GhostButton')
        properties_button.clicked.connect(self._open_printer_properties)
        settings_button = QPushButton('Labelmate printer settings')
        settings_button.setObjectName('PrimaryButton')
        settings_button.clicked.connect(self._open_labelmate_printer_settings)
        action_row.addWidget(driver_button)
        action_row.addWidget(printers_button)
        action_row.addWidget(properties_button)
        action_row.addWidget(settings_button)
        layout.addLayout(action_row)

        ok_count, warn_count, fail_count = requirements_check.summarize(self.results)
        self.summary_label = QLabel(
            f'System check: {ok_count} passed · {warn_count} warning(s) · {fail_count} blocking issue(s)'
        )
        self.summary_label.setObjectName('CardSubTitle')
        layout.addWidget(self.summary_label)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, 1)
        self._populate_results()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        refresh_button = buttons.addButton('Re-check', QDialogButtonBox.ButtonRole.ActionRole)
        refresh_button.clicked.connect(self._refresh)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _has_ipp_driver_issue(self) -> bool:
        return any(item.name == 'Printer driver' and item.blocking for item in self.results)

    def _current_printer_name(self) -> str:
        settings = printer_store.load_settings()
        name = settings.get('conn', '').strip()
        if name:
            return name
        try:
            return printing.find_brother_printer() or ''
        except Exception:
            return ''

    def _open_printer_properties(self):
        setup_help.open_printer_properties(self._current_printer_name())

    def _open_labelmate_printer_settings(self):
        if PrinterSettingsDialog(self).exec():
            self._refresh()

    def _populate_results(self):
        self.list_widget.clear()
        for item in self.results:
            icon = {'ok': '✓', 'warn': '!', 'fail': '✗'}.get(item.status, '?')
            text = f'{icon}  {item.name}: {item.message}'
            if item.hint:
                text += f'\n     {item.hint}'
            list_item = QListWidgetItem(text)
            if item.status == 'fail':
                list_item.setForeground(Qt.GlobalColor.darkRed)
            elif item.status == 'warn':
                list_item.setForeground(Qt.GlobalColor.darkYellow)
            self.list_widget.addItem(list_item)

    def _refresh(self):
        self.results = requirements_check.run_all_checks()
        self.ipp_warning.setVisible(self._has_ipp_driver_issue())
        ok_count, warn_count, fail_count = requirements_check.summarize(self.results)
        self.summary_label.setText(
            f'System check: {ok_count} passed · {warn_count} warning(s) · {fail_count} blocking issue(s)'
        )
        self._populate_results()


class BulkPrintWorker(QThread):
    progress = Signal(int, int, str)
    finished_ok = Signal(str, int)
    failed = Signal(int, str, str)

    def __init__(self, jobs, settings):
        super().__init__()
        self.jobs = jobs
        self.settings = settings

    def run(self):
        printer_name = ''
        total = len(self.jobs)
        try:
            for index, job in enumerate(self.jobs, start=1):
                label = f"{job['brand']} / {job['model']} / {job['size']}"
                self.progress.emit(
                    index - 1,
                    total,
                    f'Printing {index} of {total}\n{label}',
                )
                printer_name = printing.print_label(
                    job['brand'],
                    job['model'],
                    job['size'],
                    self.settings.get('conn', ''),
                    ql_model=self.settings.get('model', 'QL-820NWB'),
                    label_size=self.settings.get('label_size', '62'),
                    text_scale=self.settings.get('text_scale', 'large'),
                    show_logo=self.settings.get('show_logo', True),
                    footer_spacing=self.settings.get('footer_spacing', 'normal'),
                    wait_for_queue=True,
                )
                self.progress.emit(
                    index,
                    total,
                    f'Printed {index} of {total}\n{label}',
                )
            self.finished_ok.emit(printer_name, total)
        except BaseException as exc:
            message = str(exc) or exc.__class__.__name__
            self.failed.emit(index, label, message)


class BulkPrintDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Bulk Print')
        self.setMinimumSize(520, 460)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        card = _card_frame('DialogCard')
        outer.addWidget(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel('Bulk Print')
        title.setObjectName('CardTitle')
        layout.addWidget(title)
        layout.addWidget(QLabel('Select catalog entries to print. Labels are sent one after another.'))

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.list_widget, 1)

        self.summary_label = QLabel('')
        self.summary_label.setObjectName('StatusLabel')
        layout.addWidget(self.summary_label)

        select_row = QHBoxLayout()
        select_all = QPushButton('Select all')
        select_all.setObjectName('GhostButton')
        select_all.clicked.connect(self._select_all)
        select_row.addWidget(select_all)
        clear_all = QPushButton('Clear all')
        clear_all.setObjectName('GhostButton')
        clear_all.clicked.connect(self._clear_all)
        select_row.addWidget(clear_all)
        select_row.addStretch(1)
        layout.addLayout(select_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.print_button = buttons.addButton('Print selected', QDialogButtonBox.ButtonRole.AcceptRole)
        self.print_button.setObjectName('PrimaryButton')
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self._accept_selection)
        layout.addWidget(buttons)

        self.list_widget.itemChanged.connect(self._update_summary)
        self._populate()

    def _populate(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for entry in db.list_catalog_entries():
            item = QListWidgetItem(f"{entry['brand']} / {entry['model']} / {entry['size']}")
            item.setData(Qt.ItemDataRole.UserRole, entry)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        self._update_summary()

    def _selected_entries(self) -> list[dict[str, str]]:
        entries = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                entries.append(item.data(Qt.ItemDataRole.UserRole))
        return entries

    def _select_all(self):
        self.list_widget.blockSignals(True)
        for index in range(self.list_widget.count()):
            self.list_widget.item(index).setCheckState(Qt.CheckState.Checked)
        self.list_widget.blockSignals(False)
        self._update_summary()

    def _clear_all(self):
        self.list_widget.blockSignals(True)
        for index in range(self.list_widget.count()):
            self.list_widget.item(index).setCheckState(Qt.CheckState.Unchecked)
        self.list_widget.blockSignals(False)
        self._update_summary()

    def _update_summary(self):
        selected = len(self._selected_entries())
        total = self.list_widget.count()
        if total == 0:
            self.summary_label.setText('No catalog entries yet — add labels in Database Manager.')
            self.print_button.setEnabled(False)
            return
        self.print_button.setEnabled(selected > 0)
        noun = 'label' if selected == 1 else 'labels'
        self.summary_label.setText(f'{selected} of {total} {noun} selected')

    def _accept_selection(self):
        if not self._selected_entries():
            QMessageBox.information(self, 'Bulk Print', 'Select at least one label to print.')
            return
        self.accept()

    def selected_entries(self) -> list[dict[str, str]]:
        return self._selected_entries()


class PrintWorker(QThread):
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, brand, model, size, settings):
        super().__init__()
        self.brand = brand
        self.model = model
        self.size = size
        self.settings = settings

    def run(self):
        try:
            printer_name = printing.print_label(
                self.brand,
                self.model,
                self.size,
                self.settings.get('conn', ''),
                ql_model=self.settings.get('model', 'QL-820NWB'),
                label_size=self.settings.get('label_size', '62'),
                text_scale=self.settings.get('text_scale', 'large'),
                show_logo=self.settings.get('show_logo', True),
                footer_spacing=self.settings.get('footer_spacing', 'normal'),
            )
            self.finished_ok.emit(printer_name)
        except BaseException as exc:
            self.failed.emit(str(exc) or exc.__class__.__name__)


class PrinterSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Printer Settings')
        self.setMinimumWidth(460)
        self.setModal(True)

        settings = printer_store.ensure_printer_configured()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        card = _card_frame('DialogCard')
        outer.addWidget(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel('Printer Settings')
        title.setObjectName('CardTitle')
        layout.addWidget(title)
        layout.addWidget(QLabel('Uses your existing Windows Brother printer — silent RAW printing, no popups.'))

        layout.addWidget(_field_label('Printer'))
        self.printer_combo = QComboBox()
        self.printer_combo.setEditable(True)
        layout.addWidget(self.printer_combo)

        refresh_row = QHBoxLayout()
        refresh_row.addStretch(1)
        refresh_button = QPushButton('Refresh list')
        refresh_button.setObjectName('GhostButton')
        refresh_button.clicked.connect(lambda: self.refresh_printers())
        refresh_row.addWidget(refresh_button)
        layout.addLayout(refresh_row)

        layout.addWidget(_field_label('Label roll'))
        self.label_combo = QComboBox()
        for key, meta in printing.LABEL_ROLLS.items():
            self.label_combo.addItem(meta['name'], key)
        label_size = settings.get('label_size', '62')
        label_index = self.label_combo.findData(label_size)
        if label_index >= 0:
            self.label_combo.setCurrentIndex(label_index)
        layout.addWidget(self.label_combo)

        self.driver_hint = QLabel('')
        self.driver_hint.setObjectName('SectionHint')
        self.driver_hint.setWordWrap(True)
        layout.addWidget(self.driver_hint)
        self.printer_combo.currentTextChanged.connect(self._update_driver_hint)

        selected = settings.get('conn', '')
        if selected.startswith('usb://'):
            selected = ''
        self.refresh_printers(selected)
        self._update_driver_hint()

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def refresh_printers(self, selected=''):
        current = selected or self.printer_combo.currentText().strip()
        self.printer_combo.blockSignals(True)
        self.printer_combo.clear()
        try:
            printers = printing.list_installed_printers()
        except Exception as exc:
            QMessageBox.warning(self, 'Printer Settings', str(exc))
            printers = []

        if not printers:
            self.printer_combo.addItem(current or '')
        else:
            for name in printers:
                self.printer_combo.addItem(name)
            if current:
                index = self.printer_combo.findText(current)
                if index >= 0:
                    self.printer_combo.setCurrentIndex(index)
                else:
                    self.printer_combo.setEditText(current)
        self.printer_combo.blockSignals(False)

    def _update_driver_hint(self):
        printer_name = self.printer_combo.currentText().strip()
        if not printer_name:
            self.driver_hint.setText('')
            return
        try:
            warning = printing.printer_driver_warning(printer_name)
            if warning:
                self.driver_hint.setText(f'Warning: {warning}')
            else:
                self.driver_hint.setText(
                    f'Ready: {printer_name} ({printing.get_printer_driver(printer_name)})'
                )
        except Exception:
            self.driver_hint.setText('')

    def save_and_close(self):
        printer_name = self.printer_combo.currentText().strip()
        if not printer_name:
            QMessageBox.warning(self, 'Printer Settings', 'Choose a printer first.')
            return
        try:
            printing.resolve_printer_name(printer_name)
        except RuntimeError as exc:
            QMessageBox.warning(self, 'Printer Settings', str(exc))
            return
        label_size = self.label_combo.currentData() or '62'
        printer_store.save_settings(
            {
                'type': 'windows',
                'conn': printer_name,
                'model': 'QL-820NWB',
                'label_size': label_size,
            }
        )
        self.accept()


class DatabaseManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Database Manager')
        self.resize(840, 560)

        self.brand_rows = []
        self.model_rows = []
        self.size_rows = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        card = _card_frame('DialogCard')
        outer.addWidget(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel('Database Manager')
        title.setObjectName('CardTitle')
        layout.addWidget(title)
        layout.addWidget(QLabel('Add, rename, delete, back up, or reset the label catalog.'))

        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        self.brand_list = QListWidget()
        self.model_list = QListWidget()
        self.size_list = QListWidget()

        tabs.addTab(self._build_entity_tab(self.brand_list, self._add_brand, self._rename_brand, self._delete_brand), 'Brands')
        tabs.addTab(self._build_entity_tab(self.model_list, self._add_model, self._rename_model, self._delete_model), 'Models')
        tabs.addTab(self._build_entity_tab(self.size_list, self._add_size, self._rename_size, self._delete_size), 'Sizes')
        tabs.addTab(self._build_tools_tab(), 'Tools')

        self.brand_list.currentItemChanged.connect(self._brand_changed)
        self.model_list.currentItemChanged.connect(self._model_changed)

        self.refresh_all()

    def _build_entity_tab(self, list_widget, add_action, rename_action, delete_action):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(list_widget, 1)

        button_row = QHBoxLayout()
        button_row.addWidget(self._button('Add', add_action))
        button_row.addWidget(self._button('Rename', rename_action))
        button_row.addWidget(self._button('Delete', delete_action))
        button_row.addStretch(1)
        layout.addLayout(button_row)
        return tab

    def _build_tools_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(QLabel('Catalog import / export'))
        layout.addWidget(QLabel(
            'CSV format: Brand, Model, Size, plus optional barcode/QR/RFID serial column. '
            'Semicolon or comma delimiters; multiple serials per row can be comma-separated. '
            'Edit in Excel or Google Sheets, then import here.'
        ))
        layout.addWidget(self._button('Export catalog to CSV…', self.export_catalog_csv))
        layout.addWidget(self._button('Import catalog from CSV…', self.import_catalog_csv))

        layout.addWidget(QLabel('Database file'))
        path_label = QLabel(str(db_path()))
        path_label.setObjectName('StatusLabel')
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        layout.addWidget(QLabel(
            'You can edit labelmate.db with DB Browser for SQLite or similar — '
            'close Labelmate first, back up first, and keep the brands / models / sizes tables intact.'
        ))
        layout.addWidget(self._button('Open database folder', self.open_database_folder))

        layout.addWidget(QLabel('Maintenance'))
        layout.addWidget(QLabel('Use these before major edits or when you want to return to the built-in seed data.'))
        layout.addWidget(self._button('Backup Database', self.backup_database))
        layout.addWidget(self._button('Reset Catalog to Seed Data', self.reset_catalog))
        layout.addStretch(1)
        return tab

    def _button(self, text, slot, *, primary=False, secondary=False):
        button = QPushButton(text)
        if primary:
            button.setObjectName('PrimaryButton')
        elif secondary:
            button.setObjectName('SecondaryButton')
        else:
            button.setObjectName('GhostButton')
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(slot)
        return button

    def _prompt_text(self, title, initial=''):
        value, ok = QInputDialog.getText(self, title, title, text=initial)
        if not ok:
            return None
        value = value.strip()
        return value or None

    def _selected_payload(self, list_widget):
        return item_payload(list_widget.currentItem())

    def refresh_all(self):
        self.brand_rows = db.get_brands()
        self.brand_list.clear()
        for brand_id, brand_name in self.brand_rows:
            self.brand_list.addItem(row_item(brand_id, brand_name))

        if self.brand_list.count() and self.brand_list.currentRow() < 0:
            self.brand_list.setCurrentRow(0)
        else:
            self._brand_changed()

    def _brand_changed(self):
        brand = self._selected_payload(self.brand_list)
        self.model_list.clear()
        self.size_list.clear()
        self.model_rows = []
        self.size_rows = []

        if not brand:
            return
        self.model_rows = db.get_models(brand['id'])
        for model_id, model_name in self.model_rows:
            self.model_list.addItem(row_item(model_id, model_name))

        if self.model_list.count() and self.model_list.currentRow() < 0:
            self.model_list.setCurrentRow(0)
        else:
            self._model_changed()

    def _model_changed(self):
        model = self._selected_payload(self.model_list)
        self.size_list.clear()
        self.size_rows = []
        if not model:
            return
        self.size_rows = db.get_sizes(model['id'])
        for size_id, size_name in self.size_rows:
            self.size_list.addItem(row_item(size_id, size_name))

    def _add_brand(self):
        value = self._prompt_text('New Brand')
        if not value:
            return
        try:
            db.add_brand(value)
        except Exception as exc:
            QMessageBox.critical(self, 'Database', str(exc))
        self.refresh_all()

    def _rename_brand(self):
        brand = self._selected_payload(self.brand_list)
        if not brand:
            return
        value = self._prompt_text('Rename Brand', brand['name'])
        if not value:
            return
        try:
            db.rename_brand(brand['id'], value)
        except Exception as exc:
            QMessageBox.critical(self, 'Database', str(exc))
        self.refresh_all()

    def _delete_brand(self):
        brand = self._selected_payload(self.brand_list)
        if not brand:
            return
        if QMessageBox.question(self, 'Database', f'Delete brand "{brand["name"]}" and all nested models/sizes?') != QMessageBox.Yes:
            return
        db.delete_brand(brand['id'])
        self.refresh_all()

    def _add_model(self):
        brand = self._selected_payload(self.brand_list)
        if not brand:
            QMessageBox.information(self, 'Database', 'Select a brand first.')
            return
        value = self._prompt_text('New Model')
        if not value:
            return
        try:
            db.add_model(brand['id'], value)
        except Exception as exc:
            QMessageBox.critical(self, 'Database', str(exc))
        self.refresh_all()

    def _rename_model(self):
        model = self._selected_payload(self.model_list)
        if not model:
            return
        value = self._prompt_text('Rename Model', model['name'])
        if not value:
            return
        try:
            db.rename_model(model['id'], value)
        except Exception as exc:
            QMessageBox.critical(self, 'Database', str(exc))
        self.refresh_all()

    def _delete_model(self):
        model = self._selected_payload(self.model_list)
        if not model:
            return
        if QMessageBox.question(self, 'Database', f'Delete model "{model["name"]}" and all nested sizes?') != QMessageBox.Yes:
            return
        db.delete_model(model['id'])
        self.refresh_all()

    def _add_size(self):
        model = self._selected_payload(self.model_list)
        if not model:
            QMessageBox.information(self, 'Database', 'Select a model first.')
            return
        value = self._prompt_text('New Size')
        if not value:
            return
        try:
            db.add_size(model['id'], value)
        except Exception as exc:
            QMessageBox.critical(self, 'Database', str(exc))
        self.refresh_all()

    def _rename_size(self):
        size = self._selected_payload(self.size_list)
        if not size:
            return
        value = self._prompt_text('Rename Size', size['name'])
        if not value:
            return
        try:
            db.rename_size(size['id'], value)
        except Exception as exc:
            QMessageBox.critical(self, 'Database', str(exc))
        self.refresh_all()

    def _delete_size(self):
        size = self._selected_payload(self.size_list)
        if not size:
            return
        if QMessageBox.question(self, 'Database', f'Delete size "{size["name"]}"?') != QMessageBox.Yes:
            return
        db.delete_size(size['id'])
        self.refresh_all()

    def backup_database(self):
        path = db.backup_database()
        QMessageBox.information(self, 'Database', f'Backup created:\n{path}')

    def export_catalog_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            'Export catalog to CSV',
            'labelmate-catalog.csv',
            'CSV files (*.csv)',
        )
        if not path:
            return
        if not path.lower().endswith('.csv'):
            path += '.csv'
        try:
            count = db.export_catalog_csv(path)
        except OSError as exc:
            QMessageBox.critical(self, 'Export CSV', str(exc))
            return
        QMessageBox.information(
            self,
            'Export CSV',
            f'Exported {count} label row(s) to:\n{path}',
        )

    def import_catalog_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Import catalog from CSV',
            '',
            'CSV files (*.csv)',
        )
        if not path:
            return

        replace = QMessageBox.question(
            self,
            'Import CSV',
            'Replace the entire catalog with this CSV?\n\n'
            'Yes = clear existing brands/models/sizes, then import.\n'
            'No = keep existing data and add new rows only.',
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if replace == QMessageBox.Cancel:
            return

        try:
            result = db.import_catalog_csv(path, replace=replace == QMessageBox.Yes)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, 'Import CSV', str(exc))
            return

        mode = 'replaced catalog with' if result['replaced'] else 'merged'
        QMessageBox.information(
            self,
            'Import CSV',
            f'{mode.capitalize()} {result["rows_read"]} CSV row(s).\n'
            f'New sizes added: {result["sizes_added"]}.\n'
            f'Barcodes linked: {result["barcodes_added"]}.',
        )
        self.refresh_all()

    def open_database_folder(self):
        import subprocess
        import sys

        folder = str(db_path().parent)
        if sys.platform == 'win32':
            subprocess.Popen(['explorer.exe', folder])
        else:
            subprocess.Popen(['xdg-open', folder])

    def reset_catalog(self):
        if QMessageBox.question(self, 'Database', 'Reset all catalog data back to the built-in seed set?') != QMessageBox.Yes:
            return
        db.reset_catalog()
        self.refresh_all()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Labelmate')
        self.resize(1120, 720)
        self.setMinimumSize(980, 640)

        self._build_menu_bar()

        central = QWidget()
        central.setObjectName('AppRoot')
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(16)

        header = QVBoxLayout()
        title = QLabel('Labelmate')
        title.setObjectName('AppTitle')
        subtitle = QLabel('Pick a brand, model, and size, then print or manage the catalog from one place.')
        subtitle.setObjectName('AppSubtitle')
        header.addWidget(title)
        header.addWidget(subtitle)
        outer.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(16)
        outer.addLayout(content, 1)

        self.builder_card = _card_frame('Card')
        self.preview_card = _card_frame('PreviewCard')
        content.addWidget(self.builder_card, 1)
        content.addWidget(self.preview_card, 1)

        self._build_builder_card()
        self._build_preview_card()

        printer_store.ensure_printer_configured()
        self.load_brands()
        self._preview_source = None
        self._print_worker = None
        self._bulk_print_worker = None
        self._bulk_progress = None
        self._check_results = []
        self.update_preview()
        self._apply_requirement_state(show_dialog=True)

    def _build_menu_bar(self):
        settings_menu = self.menuBar().addMenu('&Settings')
        settings_menu.addAction('Printer Setup…', self.open_printer_setup)
        settings_menu.addAction('Printer Settings…', self.open_printer_settings)
        settings_menu.addSeparator()
        settings_menu.addAction('Database Manager…', self.open_database_manager)

        file_menu = self.menuBar().addMenu('&File')
        file_menu.addAction('Bulk Print…', self.open_bulk_print)
        file_menu.addSeparator()
        file_menu.addAction('E&xit', self.close)

    def _build_builder_card(self):
        layout = QVBoxLayout(self.builder_card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title_row = QHBoxLayout()
        title_label = QLabel('Label Builder')
        title_label.setObjectName('CardTitle')
        badge = QLabel('Ready for print')
        badge.setObjectName('TinyBadge')
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        title_row.addWidget(badge)
        layout.addLayout(title_row)

        hint = QLabel('Scan a barcode or pick from the catalog below.')
        hint.setObjectName('CardSubTitle')
        layout.addWidget(hint)

        scan_row = QHBoxLayout()
        self.scan_field = QLineEdit()
        self.scan_field.setPlaceholderText('Scan barcode (ID + Enter)…')
        self.scan_field.setClearButtonEnabled(True)
        self.scan_field.returnPressed.connect(self._handle_barcode_scan)
        scan_row.addWidget(self.scan_field, 1)

        self.scan_print_check = QCheckBox('Print on scan')
        self.scan_print_check.setObjectName('ScanPrintCheck')
        scan_row.addWidget(self.scan_print_check)
        layout.addLayout(scan_row)
        self._load_scan_settings()

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        layout.addLayout(form)

        self.brand_combo = QComboBox()
        self.model_combo = QComboBox()
        self.size_combo = QComboBox()

        form.addWidget(_field_label('Brand'), 0, 0)
        form.addWidget(self.brand_combo, 1, 0)
        form.addWidget(_field_label('Model'), 2, 0)
        form.addWidget(self.model_combo, 3, 0)
        form.addWidget(_field_label('Size'), 4, 0)
        form.addWidget(self.size_combo, 5, 0)

        self.show_logo_check = QCheckBox('Show Kick logo on label')
        self.show_logo_check.setObjectName('ShowLogoCheck')
        form.addWidget(self.show_logo_check, 6, 0)
        self._load_show_logo_setting()

        self.summary_label = QLabel('Selected: Brand / Model / Size')
        self.summary_label.setObjectName('StatusLabel')
        layout.addWidget(self.summary_label)

        self.brand_combo.currentIndexChanged.connect(self.load_models)
        self.model_combo.currentIndexChanged.connect(self.load_sizes)
        self.size_combo.currentIndexChanged.connect(self.update_preview)
        self.show_logo_check.toggled.connect(self._show_logo_changed)
        self.scan_print_check.toggled.connect(self._scan_print_changed)

        button_row = QHBoxLayout()
        layout.addLayout(button_row)

        self.print_button = self._button('Print', self.print_label, primary=True)
        self.bulk_print_button = self._button('Bulk Print', self.open_bulk_print, secondary=True)
        button_row.addWidget(self.print_button)
        button_row.addWidget(self.bulk_print_button)
        button_row.addStretch(1)

    def _build_preview_card(self):
        layout = QVBoxLayout(self.preview_card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel('Live Preview')
        title.setObjectName('CardTitle')
        subtitle = QLabel('Includes approximate printer feed · white = printed tape · gray = tape edge')
        subtitle.setObjectName('CardSubTitle')
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.preview_canvas = QFrame()
        self.preview_canvas.setObjectName('PreviewCanvas')
        canvas_layout = QVBoxLayout(self.preview_canvas)
        canvas_layout.setContentsMargins(20, 20, 20, 20)
        canvas_layout.setSpacing(10)

        self.preview_tape_caption = QLabel('62 mm tape')
        self.preview_tape_caption.setObjectName('PreviewTapeCaption')
        self.preview_tape_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        canvas_layout.addWidget(self.preview_tape_caption)

        self.preview_stage = QFrame()
        self.preview_stage.setObjectName('PreviewStage')
        stage_layout = QVBoxLayout(self.preview_stage)
        stage_layout.setContentsMargins(0, 0, 0, 0)
        stage_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.preview_image = QLabel('Select brand, model, and size to preview.')
        self.preview_image.setObjectName('PreviewImage')
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image.setMinimumHeight(180)
        self.preview_image.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        stage_layout.addWidget(self.preview_image)
        canvas_layout.addWidget(self.preview_stage, 1)
        layout.addWidget(self.preview_canvas, 1)

        self.preview_meta = QLabel('')
        self.preview_meta.setObjectName('PreviewMeta')
        self.preview_meta.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview_meta)

        self.printer_status = QLabel('Printer settings are stored locally.')
        self.printer_status.setObjectName('StatusLabel')
        layout.addWidget(self.printer_status)

    def _button(self, text, slot, primary=False, secondary=False):
        button = QPushButton(text)
        if primary:
            button.setObjectName('PrimaryButton')
        elif secondary:
            button.setObjectName('SecondaryButton')
        else:
            button.setObjectName('GhostButton')
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(slot)
        return button

    def _load_show_logo_setting(self):
        settings = printer_store.load_settings()
        self.show_logo_check.blockSignals(True)
        self.show_logo_check.setChecked(settings.get('show_logo', True))
        self.show_logo_check.blockSignals(False)

    def _show_logo_changed(self, checked: bool):
        settings = printer_store.load_settings()
        settings['show_logo'] = checked
        printer_store.save_settings(settings)
        self.update_preview()

    def _load_scan_settings(self):
        settings = printer_store.load_settings()
        self.scan_print_check.blockSignals(True)
        self.scan_print_check.setChecked(settings.get('scan_to_print', True))
        self.scan_print_check.blockSignals(False)

    def _scan_print_changed(self, checked: bool):
        settings = printer_store.load_settings()
        settings['scan_to_print'] = checked
        printer_store.save_settings(settings)

    def _select_catalog_entry(self, brand: str, model: str, size: str) -> bool:
        brand_index = self.brand_combo.findText(brand, Qt.MatchFlag.MatchExactly)
        if brand_index < 0:
            return False
        self.brand_combo.blockSignals(True)
        self.brand_combo.setCurrentIndex(brand_index)
        self.brand_combo.blockSignals(False)
        self.load_models()

        model_index = self.model_combo.findText(model, Qt.MatchFlag.MatchExactly)
        if model_index < 0:
            return False
        self.model_combo.blockSignals(True)
        self.model_combo.setCurrentIndex(model_index)
        self.model_combo.blockSignals(False)
        self.load_sizes()

        size_index = self.size_combo.findText(size, Qt.MatchFlag.MatchExactly)
        if size_index < 0:
            return False
        self.size_combo.blockSignals(True)
        self.size_combo.setCurrentIndex(size_index)
        self.size_combo.blockSignals(False)
        self.update_preview()
        return True

    def _handle_barcode_scan(self):
        serial = self.scan_field.text().strip()
        self.scan_field.clear()
        if not serial:
            return

        entry = db.lookup_by_barcode(serial)
        if not entry:
            self.printer_status.setText(f'Unknown barcode: {serial}')
            self.scan_field.setFocus()
            return

        if not self._select_catalog_entry(entry['brand'], entry['model'], entry['size']):
            self.printer_status.setText(
                f'Barcode {serial} is in the database but the catalog entry is missing.'
            )
            self.scan_field.setFocus()
            return

        self.printer_status.setText(
            f'Scanned {serial} → {entry["brand"]} / {entry["model"]} / {entry["size"]}'
        )

        if self.scan_print_check.isChecked():
            self.print_label()

        self.scan_field.setFocus()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'scan_field'):
            self.scan_field.setFocus()

    def load_brands(self):
        self.brand_combo.blockSignals(True)
        self.brand_combo.clear()
        self.brand_rows = db.get_brands()
        for brand_id, brand_name in self.brand_rows:
            self.brand_combo.addItem(brand_name, {'id': brand_id, 'name': brand_name})
        self.brand_combo.blockSignals(False)
        if self.brand_combo.count():
            self.brand_combo.setCurrentIndex(0)
        else:
            self.brand_combo.setCurrentIndex(-1)
            self.model_combo.clear()
            self.size_combo.clear()
        self.load_models()

    def load_models(self):
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        brand = self.brand_combo.currentData() or None
        self.model_rows = db.get_models(brand['id']) if brand else []
        for model_id, model_name in self.model_rows:
            self.model_combo.addItem(model_name, {'id': model_id, 'name': model_name})
        self.model_combo.blockSignals(False)
        if self.model_combo.count():
            self.model_combo.setCurrentIndex(0)
        else:
            self.model_combo.setCurrentIndex(-1)
            self.size_combo.clear()
        self.load_sizes()

    def load_sizes(self):
        self.size_combo.blockSignals(True)
        self.size_combo.clear()
        model = self.model_combo.currentData() or None
        self.size_rows = db.get_sizes(model['id']) if model else []
        for size_id, size_name in self.size_rows:
            self.size_combo.addItem(size_name, {'id': size_id, 'name': size_name})
        self.size_combo.blockSignals(False)
        if self.size_combo.count():
            self.size_combo.setCurrentIndex(0)
        else:
            self.size_combo.setCurrentIndex(-1)
        self.update_preview()

    def selection_texts(self):
        brand = self.brand_combo.currentText().strip() or 'Brand'
        model = self.model_combo.currentText().strip() or 'Model'
        size = self.size_combo.currentText().strip() or 'Size'
        return brand, model, size

    def update_preview(self):
        brand, model, size = self.selection_texts()
        self.summary_label.setText(f'Selected: {brand} / {model} / {size}')
        settings = printer_store.load_settings()
        label_size = settings.get('label_size', '62')
        text_scale = settings.get('text_scale', 'large')
        show_logo = settings.get('show_logo', True)
        footer_spacing = settings.get('footer_spacing', 'normal')
        roll_name = printing.LABEL_ROLLS.get(label_size, {}).get('name', label_size)
        self.preview_meta.setText(
            f'{roll_name} · printable {printing.PRINTABLE_WIDTH_PX} px wide'
        )

        if brand == 'Brand' and not self.brand_combo.count():
            self._preview_source = None
            self.preview_image.setText('Add catalog entries to preview labels.')
            self.preview_image.setPixmap(QPixmap())
            self.preview_meta.setText('')
            return

        image = printing.render_label(
            brand,
            model,
            size,
            label_size=label_size,
            text_scale=text_scale,
            show_logo=show_logo,
            footer_spacing=footer_spacing,
        )
        self._preview_source = _pil_to_qpixmap(image)
        self.preview_meta.setText(
            f'{roll_name} · printable {image.width} × {image.height} px'
        )
        self._refresh_preview_pixmap()

    def _refresh_preview_pixmap(self):
        if self._preview_source is None or self._preview_source.isNull():
            return
        target = self.preview_stage.size()
        if target.width() < 40 or target.height() < 40:
            return

        max_w = int(target.width() * 0.98)
        max_h = int(target.height() * 0.95)
        tape_ratio = printing.TAPE_WIDTH_PX / printing.PRINTABLE_WIDTH_PX
        feed_ratio = 1 + printing.PREVIEW_FEED_TOP_RATIO + printing.PREVIEW_FEED_BOTTOM_RATIO
        max_label_w = max(40, int(max_w / tape_ratio))
        max_label_h = max(40, int(max_h / feed_ratio))
        scaled_label = self._preview_source.scaled(
            max_label_w,
            max_label_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        framed = _compose_preview_pixmap(scaled_label)
        self.preview_image.setText('')
        self.preview_image.setPixmap(framed)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_preview_pixmap()

    def _apply_requirement_state(self, *, show_dialog=False):
        self._check_results = requirements_check.run_all_checks()
        ok_count, warn_count, fail_count = requirements_check.summarize(self._check_results)
        can_print = requirements_check.can_print(self._check_results)

        self.print_button.setEnabled(can_print)
        self.bulk_print_button.setEnabled(can_print)
        if can_print and warn_count == 0:
            status = f'System check: {ok_count} passed — ready to print'
        elif can_print:
            status = f'System check: ready to print ({warn_count} warning(s))'
        else:
            status = f'System check: printing blocked ({fail_count} issue(s))'

        settings = printer_store.load_settings()
        printer_name = settings.get('conn', '').strip() or 'not set'
        label_size = settings.get('label_size', '62')
        roll_name = printing.LABEL_ROLLS.get(label_size, {}).get('name', label_size)
        self.printer_status.setText(f'{status} · {printer_name} · {roll_name}')

        if show_dialog and fail_count:
            PrinterSetupDialog(self, results=self._check_results).exec()

    def open_printer_setup(self):
        dialog = PrinterSetupDialog(self, results=self._check_results)
        dialog.exec()
        self._apply_requirement_state(show_dialog=False)

    def open_printer_settings(self):
        dialog = PrinterSettingsDialog(self)
        if dialog.exec():
            self.update_preview()
            self._load_show_logo_setting()
            self._apply_requirement_state(show_dialog=False)

    def open_database_manager(self):
        dialog = DatabaseManagerDialog(self)
        dialog.exec()
        self.load_brands()

    def _current_print_settings(self) -> dict:
        settings = printer_store.load_settings()
        settings['show_logo'] = self.show_logo_check.isChecked()
        settings['text_scale'] = 'large'
        printer_store.save_settings(settings)
        return settings

    def _ensure_can_print(self) -> bool:
        self._check_results = requirements_check.run_all_checks()
        if requirements_check.can_print(self._check_results):
            return True
        _show_print_blocked_dialog(self, self._check_results)
        self._apply_requirement_state(show_dialog=False)
        return False

    def _set_printing_active(self, active: bool):
        self.print_button.setEnabled(not active and requirements_check.can_print(self._check_results))
        self.bulk_print_button.setEnabled(not active and requirements_check.can_print(self._check_results))

    def open_bulk_print(self):
        if self._bulk_print_worker and self._bulk_print_worker.isRunning():
            return
        if self._print_worker and self._print_worker.isRunning():
            return
        if not self._ensure_can_print():
            return

        dialog = BulkPrintDialog(self)
        if not dialog.exec():
            return

        jobs = dialog.selected_entries()
        if not jobs:
            return

        if len(jobs) > 1:
            answer = QMessageBox.question(
                self,
                'Bulk Print',
                f'Print {len(jobs)} labels one after another?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer != QMessageBox.Yes:
                return

        settings = self._current_print_settings()
        self._set_printing_active(True)
        self.printer_status.setText(f'Bulk printing 0 / {len(jobs)}...')

        self._bulk_progress = QProgressDialog('Preparing bulk print...', None, 0, len(jobs), self)
        self._bulk_progress.setWindowTitle('Bulk Print')
        self._bulk_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._bulk_progress.setMinimumDuration(0)
        self._bulk_progress.setValue(0)
        self._bulk_progress.show()

        self._bulk_print_worker = BulkPrintWorker(jobs, settings)
        self._bulk_print_worker.progress.connect(self._bulk_print_progress)
        self._bulk_print_worker.finished_ok.connect(self._bulk_print_finished)
        self._bulk_print_worker.failed.connect(self._bulk_print_failed)
        self._bulk_print_worker.finished.connect(self._bulk_print_done)
        self._bulk_print_worker.start()

    def _bulk_print_progress(self, completed: int, total: int, message: str):
        if self._bulk_progress:
            self._bulk_progress.setMaximum(total)
            self._bulk_progress.setValue(completed)
            self._bulk_progress.setLabelText(message)
        self.printer_status.setText(message.replace('\n', ' — '))

    def _bulk_print_finished(self, printer_name: str, total: int):
        settings = printer_store.load_settings()
        settings['conn'] = printer_name
        settings['type'] = 'windows'
        printer_store.save_settings(settings)
        QMessageBox.information(self, 'Bulk Print', f'Printed {total} labels.')
        self._apply_requirement_state(show_dialog=False)

    def _bulk_print_failed(self, index: int, label: str, message: str):
        QMessageBox.critical(
            self,
            'Bulk Print failed',
            f'Failed on label {index}:\n{label}\n\n{message}',
        )
        self._apply_requirement_state(show_dialog=False)

    def _bulk_print_done(self):
        if self._bulk_progress:
            self._bulk_progress.close()
            self._bulk_progress = None
        self._set_printing_active(False)

    def print_label(self):
        if self._print_worker and self._print_worker.isRunning():
            return
        if self._bulk_print_worker and self._bulk_print_worker.isRunning():
            return

        if not self._ensure_can_print():
            return

        brand, model, size = self.selection_texts()
        settings = self._current_print_settings()
        self._set_printing_active(True)
        self.printer_status.setText('Printing...')
        self._print_worker = PrintWorker(brand, model, size, settings)
        self._print_worker.finished_ok.connect(self._print_finished)
        self._print_worker.failed.connect(self._print_failed)
        self._print_worker.finished.connect(lambda: self._set_printing_active(False))
        self._print_worker.start()

    def _print_finished(self, printer_name):
        settings = printer_store.load_settings()
        settings['conn'] = printer_name
        settings['type'] = 'windows'
        printer_store.save_settings(settings)
        self._apply_requirement_state(show_dialog=False)

    def _print_failed(self, message):
        QMessageBox.critical(self, 'Print failed', message)
        self.update_preview()
        self._apply_requirement_state(show_dialog=False)


def run_gui():
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    window = MainWindow()
    window.show()
    app.exec()
