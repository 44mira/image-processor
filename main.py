import os
import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


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


class ImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Image Viewer")
        self.setGeometry(100, 100, 800, 600)

        # Create UI
        self.create_menu()
        self.create_central_widget()
        self.create_info_bar()

    def create_menu(self):
        menubar = self.menuBar()
        assert menubar is not None

        file_menu = menubar.addMenu("File")
        assert file_menu is not None

        open_action = QAction("Open New Image File", self)
        open_action.triggered.connect(self.open_image)
        file_menu.addAction(open_action)

    def create_central_widget(self):
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        self.image_label = ImageLabel()
        self.image_label.pixelHovered.connect(self.update_info_bar)
        layout.addWidget(self.image_label, stretch=1)

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

        if file_path[-4:].lower() == ".pcx":
            pass  # TODO: process pcx

        if file_path:
            try:
                # Load image
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

    def update_info_bar(self, x, y, r, g, b):
        self.info_bar.showMessage(f"X:{x}, Y:{y}  RGB:({r}, {g}, {b})")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = ImageViewer()
    viewer.show()
    sys.exit(app.exec())
