import os
import sys

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import point_processing as pp
from pcx_header import PCXHeader
from pcx_utils import create_palette_image, pcx_to_qimage


class RightDockPanel(QWidget):
    """A VS Code–style dockable side panel on the right, with icon buttons
    and smooth slide animation."""

    def __init__(self):
        super().__init__()
        self._expanded_width = 300
        self._collapsed = False
        self._anim = None
        self.setMinimumWidth(50)
        self.setStyleSheet("background-color: #2b2b2b; color: white;")

        # --- main horizontal layout ---
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- sidebar with icons ---
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(50)
        self.sidebar.setStyleSheet("background-color: #202020;")

        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(5, 10, 5, 10)
        self.sidebar_layout.setSpacing(8)
        self.sidebar_layout.addStretch()

        # --- stack area for panels ---
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #2b2b2b;")
        self.stack.setVisible(False)

        # add to layout
        main_layout.addWidget(self.stack, 1)
        main_layout.addWidget(self.sidebar)

        self.buttons = []
        self.current_index = None

    # ------------------------------------------------------------
    def add_panel(
        self, widget: QWidget, tooltip: str, icon_path: str | None = None
    ):
        """Add a new panel with an icon to the right sidebar."""
        index = self.stack.addWidget(widget)

        btn = QToolButton()
        btn.setIcon(QIcon(icon_path) if icon_path else QIcon())
        btn.setIconSize(QSize(22, 22))
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self._toggle_panel(index))
        btn.setStyleSheet(
            """
            QToolButton {
                background-color: transparent;
                border: none;
                padding: 6px;
            }
            QToolButton:checked {
                background-color: #3a3d41;
                border-radius: 6px;
            }
            QToolButton:hover {
                background-color: #4b4f55;
            }
        """
        )

        self.sidebar_layout.insertWidget(len(self.buttons), btn)
        self.buttons.append(btn)

    # ------------------------------------------------------------
    def _toggle_panel(self, index: int):
        """Handle icon button click: toggle or switch panels."""
        if self.current_index == index:
            # collapse if same panel
            self._collapse()
            self.buttons[index].setChecked(False)
            self.current_index = None
        else:
            if self.current_index is not None:
                self.buttons[self.current_index].setChecked(False)
            self.current_index = index
            self.buttons[index].setChecked(True)
            self.stack.setCurrentIndex(index)
            self._expand()

    # ------------------------------------------------------------
    def _expand(self):
        self.stack.setVisible(True)
        anim = QPropertyAnimation(self, b"maximumWidth")
        anim.setDuration(250)
        anim.setStartValue(self.width())
        anim.setEndValue(self._expanded_width)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.start()
        self._anim = anim

    def _collapse(self):
        anim = QPropertyAnimation(self, b"maximumWidth")
        anim.setDuration(250)
        anim.setStartValue(self.width())
        anim.setEndValue(50)  # keep just the icon bar visible
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.finished.connect(lambda: self.stack.setVisible(False))
        anim.start()
        self._anim = anim


class ImageLabel(QLabel):
    # Custom signal: emit coordinates + color
    pixelHovered = pyqtSignal(int, int, int, int, int)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: gray;")
        self.setMouseTracking(True)
        self.image = None  # QImage backing for pixel lookup

    def setImage(self, pixmap):
        self.setPixmap(pixmap)
        self.image = pixmap.toImage()

    def mouseMoveEvent(self, ev):
        assert ev is not None

        if self.image is not None and self.pixmap() is not None:
            # Scale mapping (like before)
            scaled_pixmap = self.pixmap().scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            x_ratio = self.image.width() / scaled_pixmap.width()
            y_ratio = self.image.height() / scaled_pixmap.height()

            # Center offset
            x_offset = (self.width() - scaled_pixmap.width()) // 2
            y_offset = (self.height() - scaled_pixmap.height()) // 2

            x = int((ev.pos().x() - x_offset) * x_ratio)
            y = int((ev.pos().y() - y_offset) * y_ratio)

            if 0 <= x < self.image.width() and 0 <= y < self.image.height():
                color = self.image.pixelColor(x, y)
                # Emit RGB + coords
                self.pixelHovered.emit(
                    x,
                    y,
                    color.red(),
                    color.green(),
                    color.blue(),
                )
        super().mouseMoveEvent(ev)


class PCXInfoPanel(QWidget):
    """Widget to display PCX header information and color palette"""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header title
        title = QLabel("<b>PCX Information</b>")
        layout.addWidget(title)

        # Header info text
        self.header_text = QTextEdit()
        self.header_text.setReadOnly(True)
        self.header_text.setMaximumHeight(300)
        layout.addWidget(QLabel("Header Information:"))
        layout.addWidget(self.header_text)

        # Palette visualization
        layout.addWidget(QLabel("Color Palette:"))
        self.palette_label = QLabel()
        self.palette_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.palette_label.setStyleSheet("border: 1px solid gray;")

        # Scroll area for palette
        scroll = QScrollArea()
        scroll.setWidget(self.palette_label)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

    def set_pcx_info(self, header: PCXHeader, file_path: str):
        """Update panel with PCX header information and palette"""
        # Set header text
        self.header_text.setPlainText(str(header))

        # Create and set palette image
        try:
            palette_img = create_palette_image(file_path, header)
            pixmap = QPixmap.fromImage(palette_img)
            self.palette_label.setPixmap(pixmap)
        except Exception as e:
            self.palette_label.setText(f"Failed to load palette: {e}")


class ImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Image Viewer")
        self.setGeometry(100, 100, 800, 600)

        # Create UI
        self.create_menu()
        self.create_central_widget()
        self.create_info_bar()

    def _filter_menu(self, menubar):
        filter_menu = menubar.addMenu("Filter")

        grayscale_action = QAction("Grayscale", self)
        grayscale_action.triggered.connect(self.apply_grayscale)
        filter_menu.addAction(grayscale_action)

        negative_action = QAction("Negative", self)
        negative_action.triggered.connect(self.apply_negative)
        filter_menu.addAction(negative_action)

        threshold_action = QAction("Manual Threshold", self)
        threshold_action.triggered.connect(self.apply_threshold)
        filter_menu.addAction(threshold_action)

        gamma_action = QAction("Gamma Correction", self)
        gamma_action.triggered.connect(self.apply_gamma)
        filter_menu.addAction(gamma_action)

        histogram_action = QAction("Histogram Equalization", self)
        histogram_action.triggered.connect(self.apply_histogram)
        filter_menu.addAction(histogram_action)

    def create_menu(self):
        menubar = self.menuBar()
        assert menubar is not None

        file_menu = menubar.addMenu("File")
        open_action = QAction("Open New Image File", self)
        open_action.triggered.connect(self.open_image)
        file_menu.addAction(open_action)

        self._filter_menu(menubar)

    def create_central_widget(self):
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.image_label = ImageLabel()
        self.image_label.pixelHovered.connect(self.update_info_bar)
        self.splitter.addWidget(self.image_label)

        self.right_panel = RightDockPanel()
        self.splitter.addWidget(self.right_panel)

        self.splitter.setSizes([700, 300])
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)

        layout.addWidget(self.splitter)
        self.setCentralWidget(central_widget)

    def create_info_bar(self):
        self.info_bar = QStatusBar()
        self.info_bar.showMessage("Ready")
        self.setStatusBar(self.info_bar)

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open New Image File",
            "",
            "Image files"
            "(*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.webp *.pcx *.PCX)"
            ";;All files (*)",
        )

        if not file_path:
            return

        try:
            # Check if it's a PCX file
            if file_path[-4:].lower() == ".pcx":
                self.open_pcx_file(file_path)
            else:
                # Load regular image
                self.pcx_info_panel.hide()
                pixmap = QPixmap(file_path)

                # Scale image to fit within the window while maintaining
                # aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

                self.image_label.setImage(scaled_pixmap)

                self.setWindowTitle(
                    f"Simple Image Viewer - {os.path.basename(file_path)}"
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open image: {str(e)}",
            )

    def open_pcx_file(self, file_path: str):
        """Load and display a PCX file with info panel"""
        try:
            # Parse PCX header
            header = PCXHeader.parse_pcx_header(file_path)

            # Convert to QImage
            qimage = pcx_to_qimage(file_path, header)

            # Convert to QPixmap and display
            pixmap = QPixmap.fromImage(qimage)
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setImage(scaled_pixmap)

            # Create PCX Info panel
            pcx_panel = PCXInfoPanel()
            pcx_panel.set_pcx_info(header, file_path)

            # Add it as a tab in the right panel (auto-switches to this tab)
            self.right_panel.add_panel(pcx_panel, "PCX Info", "icons/pcx.png")

            # Update window title
            self.setWindowTitle(f"PCX Viewer - {os.path.basename(file_path)}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load PCX file: {str(e)}",
            )

    def update_info_bar(self, x, y, r, g, b):
        self.info_bar.showMessage(f"X:{x}, Y:{y}  RGB:({r}, {g}, {b})")

    def _process_current_image(self, func, *args):
        """Helper: convert image → ndarray, apply func, convert back."""
        if not self.image_label.image:
            return

        arr = pp.qimage_to_ndarray(self.image_label.image)
        result = func(arr, *args)
        qimg = pp.ndarray_to_qimage(result)
        self.image_label.setImage(QPixmap.fromImage(qimg))

    def _process_with_greyscale(self, func, *args):
        """Helper: ensure greyscale input before processing."""
        if not self.image_label.image:
            return

        arr = pp.qimage_to_ndarray(self.image_label.image)

        if arr.ndim == 3:
            arr = pp.to_grayscale(arr)

        result = func(arr, *args)
        qimg = pp.ndarray_to_qimage(result)
        self.image_label.setImage(QPixmap.fromImage(qimg))

    def apply_grayscale(self):
        self._process_current_image(pp.to_grayscale)

    def apply_negative(self):
        self._process_current_image(pp.to_negative)

    def apply_threshold(self):
        threshold, ok = QInputDialog.getInt(
            self, "Threshold", "Enter threshold (0–255):", 128, 0, 255
        )
        if ok:
            self._process_with_greyscale(pp.manual_threshold, threshold)

    def apply_gamma(self):
        gamma, ok = QInputDialog.getDouble(
            self, "Gamma", "Enter gamma value (>0):", 1.0, 0.1, float("inf"), 2
        )
        if ok:
            self._process_current_image(pp.gamma_transform, gamma)

    def apply_histogram(self):
        """Apply histogram equalization to the current image."""
        if not self.image_label.image:
            return

        arr = pp.qimage_to_ndarray(self.image_label.image)

        # Check if image is grayscale or RGB
        if arr.ndim == 2:  # grayscale
            result = pp.histogram_equalization(arr)
        elif arr.ndim == 3 and arr.shape[2] == 3:  # color
            result = pp.histogram_equalization_rgb(arr)
        else:
            QMessageBox.warning(
                self,
                "Unsupported Format",
                "Only grayscale or RGB images are supported.",
            )
            return

        qimg = pp.ndarray_to_qimage(result)
        self.image_label.setImage(QPixmap.fromImage(qimg))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = ImageViewer()
    viewer.show()
    sys.exit(app.exec())
