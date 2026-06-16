from __future__ import annotations

from app_data.settings import printer_store
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)

from src import db
from src import printing
from src import requirements_check


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
    """Wrap the printable area in a 62 mm tape frame for the on-screen preview."""
    if label.isNull():
        return label

    tape_ratio = printing.TAPE_WIDTH_PX / printing.PRINTABLE_WIDTH_PX
    label_w = label.width()
    label_h = label.height()
    side_margin = max(4, int((label_w * (tape_ratio - 1)) / 2))
    pad = max(6, label_h // 18)
    shadow = max(4, label_h // 24)

    canvas_w = label_w + side_margin * 2 + pad * 2
    canvas_h = label_h + pad * 2 + shadow
    framed = QPixmap(canvas_w, canvas_h)
    framed.fill(Qt.GlobalColor.transparent)

    painter = QPainter(framed)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    label_x = side_margin + pad
    label_y = pad
    tape_color = QColor('#b7c0cc')
    shadow_color = QColor(20, 32, 48, 55)

    painter.fillRect(label_x + 3, label_y + shadow, label_w, label_h, shadow_color)
    painter.fillRect(pad, label_y, side_margin, label_h, tape_color)
    painter.fillRect(label_x + label_w, label_y, side_margin, label_h, tape_color)
    painter.drawPixmap(label_x, label_y, label)
    painter.setPen(QPen(QColor('#94a3b8'), 1))
    painter.drawRect(label_x, label_y, label_w - 1, label_h - 1)
    painter.end()

    return framed


def apply_theme(app: QApplication):
    app.setStyle('Fusion')
    app.setFont(QFont('Segoe UI', 10))
    app.setStyleSheet(
        f'''
        QMainWindow {{ background: {APP_BG}; }}
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
            border: 1px solid {BORDER};
            border-radius: 12px;
            background: white;
            padding: 10px 14px;
        }}
        QPushButton:hover {{
            background: #f8fbff;
        }}
        QPushButton#PrimaryButton {{
            border: none;
            background: {ACCENT};
            color: white;
            font-weight: 700;
            padding: 11px 16px;
        }}
        QPushButton#PrimaryButton:hover {{
            background: {ACCENT_DARK};
        }}
        QPushButton#GhostButton {{
            background: transparent;
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


class RequirementsDialog(QDialog):
    def __init__(self, parent=None, *, results=None):
        super().__init__(parent)
        self.setWindowTitle('System Check')
        self.setMinimumWidth(560)
        self.results = results or requirements_check.run_all_checks()

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        ok_count, warn_count, fail_count = requirements_check.summarize(self.results)
        summary = QLabel(
            f'{ok_count} passed · {warn_count} warning(s) · {fail_count} issue(s) blocking print'
        )
        summary.setObjectName('CardSubTitle')
        layout.addWidget(summary)

        self.list_widget = QListWidget()
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
        layout.addWidget(self.list_widget, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        refresh_button = buttons.addButton('Re-check', QDialogButtonBox.ButtonRole.ActionRole)
        refresh_button.clicked.connect(self._refresh)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _refresh(self):
        self.results = requirements_check.run_all_checks()
        self.list_widget.clear()
        for item in self.results:
            icon = {'ok': '✓', 'warn': '!', 'fail': '✗'}.get(item.status, '?')
            text = f'{icon}  {item.name}: {item.message}'
            if item.hint:
                text += f'\n     {item.hint}'
            self.list_widget.addItem(QListWidgetItem(text))


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

        layout.addWidget(QLabel('Maintenance tools'))
        layout.addWidget(QLabel('Use these before major edits or when you want to return to the built-in seed data.'))

        layout.addWidget(self._button('Backup Database', self.backup_database))
        layout.addWidget(self._button('Reset Catalog to Seed Data', self.reset_catalog))
        layout.addStretch(1)
        return tab

    def _button(self, text, slot, *, primary=False):
        button = QPushButton(text)
        button.clicked.connect(slot)
        button.setObjectName('PrimaryButton' if primary else 'GhostButton')
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
        self.update_preview()
        self._print_worker = None
        self._check_results = []
        self.update_preview()
        self._apply_requirement_state(show_dialog=True)

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

        hint = QLabel('Use the catalog selections to compose the next label.')
        hint.setObjectName('CardSubTitle')
        layout.addWidget(hint)

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

        self.summary_label = QLabel('Selected: Brand / Model / Size')
        self.summary_label.setObjectName('StatusLabel')
        layout.addWidget(self.summary_label)

        self.brand_combo.currentIndexChanged.connect(self.load_models)
        self.model_combo.currentIndexChanged.connect(self.load_sizes)
        self.size_combo.currentIndexChanged.connect(self.update_preview)

        button_row = QHBoxLayout()
        layout.addLayout(button_row)

        self.print_button = self._button('Print', self.print_label, primary=True)
        self.check_button = self._button('System Check', self.open_system_check)
        self.database_button = self._button('Database Manager', self.open_database_manager)
        self.printer_button = self._button('Printer Settings', self.open_printer_settings)
        self.quit_button = self._button('Quit', self.close)

        button_row.addWidget(self.print_button)
        button_row.addWidget(self.check_button)
        button_row.addWidget(self.database_button)
        button_row.addWidget(self.printer_button)
        button_row.addWidget(self.quit_button)

    def _build_preview_card(self):
        layout = QVBoxLayout(self.preview_card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel('Live Preview')
        title.setObjectName('CardTitle')
        subtitle = QLabel('Print preview with 62 mm tape margins — updates as you change selections.')
        subtitle.setObjectName('CardSubTitle')
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.preview_canvas = QFrame()
        self.preview_canvas.setObjectName('PreviewCanvas')
        canvas_layout = QVBoxLayout(self.preview_canvas)
        canvas_layout.setContentsMargins(20, 20, 20, 20)
        canvas_layout.setSpacing(10)

        self.preview_tape_caption = QLabel('62 mm tape · white area = printable label')
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

    def _button(self, text, slot, primary=False):
        button = QPushButton(text)
        button.setObjectName('PrimaryButton' if primary else 'GhostButton')
        button.clicked.connect(slot)
        return button

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
        roll_name = printing.LABEL_ROLLS.get(label_size, {}).get('name', label_size)
        self.preview_meta.setText(
            f'{roll_name} · printable {printing.PRINTABLE_WIDTH_PX} px wide · tape {printing.TAPE_WIDTH_PX} px'
        )

        if brand == 'Brand' and not self.brand_combo.count():
            self._preview_source = None
            self.preview_image.setText('Add catalog entries to preview labels.')
            self.preview_image.setPixmap(QPixmap())
            self.preview_meta.setText('')
            return

        image = printing.render_label(brand, model, size, label_size=label_size)
        self._preview_source = _pil_to_qpixmap(image)
        self.preview_meta.setText(
            f'{roll_name} · printable {image.width} × {image.height} px · tape {printing.TAPE_WIDTH_PX} px wide'
        )
        self._refresh_preview_pixmap()

    def _refresh_preview_pixmap(self):
        if self._preview_source is None or self._preview_source.isNull():
            return
        target = self.preview_stage.size()
        if target.width() < 40 or target.height() < 40:
            return

        max_w = int(target.width() * 0.92)
        max_h = int(target.height() * 0.88)
        scaled_label = self._preview_source.scaled(
            max_w,
            max_h,
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

        if show_dialog and (fail_count or warn_count):
            RequirementsDialog(self, results=self._check_results).exec()

    def open_system_check(self):
        dialog = RequirementsDialog(self, results=self._check_results)
        dialog.exec()
        self._apply_requirement_state(show_dialog=False)

    def open_printer_settings(self):
        dialog = PrinterSettingsDialog(self)
        if dialog.exec():
            self.update_preview()
            self._apply_requirement_state(show_dialog=False)

    def open_database_manager(self):
        dialog = DatabaseManagerDialog(self)
        dialog.exec()
        self.load_brands()

    def print_label(self):
        if self._print_worker and self._print_worker.isRunning():
            return

        self._check_results = requirements_check.run_all_checks()
        if not requirements_check.can_print(self._check_results):
            RequirementsDialog(self, results=self._check_results).exec()
            self._apply_requirement_state(show_dialog=False)
            return

        brand, model, size = self.selection_texts()
        settings = printer_store.load_settings()
        self.print_button.setEnabled(False)
        self.printer_status.setText('Printing...')
        self._print_worker = PrintWorker(brand, model, size, settings)
        self._print_worker.finished_ok.connect(self._print_finished)
        self._print_worker.failed.connect(self._print_failed)
        self._print_worker.finished.connect(lambda: self.print_button.setEnabled(True))
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
