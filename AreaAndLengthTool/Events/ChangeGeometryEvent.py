from qgis.PyQt.QtCore import pyqtSlot, QObject, QEvent
from qgis.core import QgsGeometry, QgsCoordinateTransform, QgsVectorLayer

from .BaseEventPrototype import BaseEventPrototype


class ChangeGeometryEvent(BaseEventPrototype):
    def __init__(self, iface):
        super().__init__(iface)
        self.iface = iface
        self.mapCanvas = self.iface.mapCanvas()
        self.objsToggleFilter = [self.mapCanvas.viewport()]  # Mouse
        self.layer = None
        self.coordinate_transform_geometry = None
        self.project.layerWillBeRemoved.connect(self.layerWillBeRemoved)

    def __del__(self) -> None:
        super().__del__()
        self.project.layerWillBeRemoved.disconnect(self.layerWillBeRemoved)

    def enable_event(self) -> None:
        super().enable_event()
        self.layer = self.mapCanvas.currentLayer()
        self._config_layer()

    def disable_event(self) -> None:
        super().disable_event()
        if self.layer and self.layer.type() == 0:
                self.layer.geometryChanged.disconnect(self.geometryChanged)

    def change_layer(self, layer: QgsVectorLayer) -> None:
        self.layer.geometryChanged.disconnect(self.geometryChanged)
        self.layer = layer
        self._config_layer()

    @pyqtSlot(QObject, QEvent)
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.MouseMove:
            self.annotation_handler.remove()
        return False

    @pyqtSlot(str)
    def layerWillBeRemoved(self, layer_id: int) -> None:
        if not self.layer is None and layer_id == self.layer.id() and self.layer.type() == 0:
            self.layer.geometryChanged.disconnect(self.geometryChanged)
            self.layer = None

    @pyqtSlot('QgsFeatureId', QgsGeometry)
    def geometryChanged(self, fid: int, geometry: QgsGeometry) -> None:
        if not self.isEnabled:
            return

        geometry.transform(self.coordinate_transform_geometry)
        msg = self.string_measures(geometry)
        point_xy = self.mapCanvas.getCoordinateTransform().toMapCoordinates(
            self.mapCanvas.mouseLastXY())
        self.annotation_handler.setText(msg, point_xy)

    def _config_layer(self):
        if self.layer and self.layer.type() == 0:
            self.layer.geometryChanged.connect(self.geometryChanged)
            self.coordinate_transform_geometry = QgsCoordinateTransform(
                self.layer.sourceCrs(), self.measure.sourceCrs(), self.project)
