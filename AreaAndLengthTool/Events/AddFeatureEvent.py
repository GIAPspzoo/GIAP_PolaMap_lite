from PyQt5.QtCore import Qt
from qgis.PyQt.QtCore import pyqtSlot, QObject, QEvent
from qgis.core import QgsCoordinateTransform, QgsPointXY

from .BaseEventPrototype import BaseEventPrototype
from ..PolygonGeometryHandler import PolygonGeometryHandler


class AddFeatureEvent(BaseEventPrototype):
    def __init__(self, iface):
        super().__init__(iface)
        self.iface = iface
        self.mapCanvas = self.iface.mapCanvas()

        self.objsToggleFilter = [
            self.mapCanvas,  # Keyboard
            self.mapCanvas.viewport()  # Mouse
        ]

        self.geom_polygon = PolygonGeometryHandler(self.iface)
        self.move_point = None
        self.isValidLayer = False

    def __del__(self) -> None:
        super().__del__()
        del self.geom_polygon

    @pyqtSlot(QObject, QEvent)
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        def xy_cursor() -> QgsPointXY:
            x_pos = event.localPos().x()
            y_pos = event.localPos().y()
            return self.mapCanvas.getCoordinateTransform().toMapCoordinates(
                int(x_pos), int(y_pos))

        def show_measure() -> None:
            geom = self.geom_polygon.geometry(
                self.coordinate_transform.transform(self.move_point))
            label = self.string_measures(geom)

            self.annotation_handler.setText(label, self.move_point)

        def event_mouse_move() -> None:
            if not self.isValidLayer or not self.isEnabled:
                return
            if self.geom_polygon.count() < 1:
                self.annotation_handler.remove()
                return

            self.move_point = xy_cursor()
            show_measure()

        def event_mouse_release() -> None:
            def left_press() -> None:
                self.geom_polygon.add(
                    self.coordinate_transform.transform(xy_cursor()))

            def right_press() -> None:
                if self.isEnabled and self.geom_polygon.count() > 2:
                    if self.geom_polygon.is_middle_point():
                        self.geom_polygon.pop()
                    xy_point = self.coordinate_transform.transform(
                        self.geom_polygon.coordinate(-1),
                        QgsCoordinateTransform.ReverseTransform)
                    label = self.string_measures(self.geom_polygon.geometry())
                    self.annotation_handler.setText(label, xy_point)
                self.geom_polygon.clear()

            if not self.isValidLayer:
                return

            key_pressed = event.button()
            key_pressed_map = {
                Qt.LeftButton: left_press,
                Qt.RightButton: right_press
            }
            if key_pressed in key_pressed_map:
                key_pressed_map[key_pressed]()

        def event_key_release() -> None:
            def key_escape():
                self.geom_polygon.clear()
                self.annotation_handler.remove()

            def key_delete() -> None:
                if self.geom_polygon.count() > 1:
                    self.geom_polygon.pop(True)
                    self.annotation_handler.remove()

            key_pressed = event.key()
            key_pressed_map = {
                Qt.Key_Escape: key_escape,
                Qt.Key_Delete: key_delete
            }
            if key_pressed in key_pressed_map:
                key_pressed_map[key_pressed]()

        event_type = event.type()
        event_type_map = {
            QEvent.MouseMove: event_mouse_move,
            QEvent.MouseButtonRelease: event_mouse_release,
            QEvent.KeyRelease: event_key_release
        }
        if event_type in event_type_map:
            event_type_map[event_type]()

        return False
