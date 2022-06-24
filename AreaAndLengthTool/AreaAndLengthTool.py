from typing import Any, Union

from qgis.PyQt.QtCore import pyqtSlot, QObject
from qgis.core import QgsMapLayerType, QgsWkbTypes, QgsMapLayer
from qgis.gui import QgsMapTool

from .Events.AddFeatureEvent import AddFeatureEvent
from .Events.ChangeGeometryEvent import ChangeGeometryEvent

class AreaAndLengthTool(QObject):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.mapCanvas = self.iface.mapCanvas()

        self.add_feature_event = AddFeatureEvent(self.iface)
        self.change_geometry_event = ChangeGeometryEvent(self.iface)
        self.current_event = None

        self.add_feature_event.isValidLayer = \
            self._is_valid_layer(self.mapCanvas.currentLayer())

        self.mapCanvas.mapToolSet.connect(self.changeMapTool)
        self.iface.currentLayerChanged.connect(self.currentLayerChanged)

    def __del__(self) -> None:
        if self.add_feature_event.isEnabled:
            self.add_feature_event.disable_event()
        if self.add_feature_event.isEventFiltered:
            self.add_feature_event.toggleEventFilter()

        if self.change_geometry_event.isEnabled:
            self.change_geometry_event.disable_event()

        self.mapCanvas.mapToolSet.disconnect(self.changeMapTool)
        self.iface.currentLayerChanged.disconnect(self.currentLayerChanged)

    def run(self, checked: bool) -> None:
        for event in (self.add_feature_event, self.change_geometry_event):
            if checked and not event.isEnabled:
                event.enable_event()
            elif not checked and event.isEnabled:
                event.disable_event()

    @pyqtSlot(QgsMapTool, QgsMapTool)
    def changeMapTool(self, new_tool: Union[QgsMapTool, Any],
                      old_tool: Union[QgsMapTool, None] = None) -> None:
        self.current_event = None
        self._disable_current_events()

        if not isinstance(new_tool, QgsMapTool):
            new_tool = self.mapCanvas.mapTool()

        if not new_tool or not new_tool.flags() == QgsMapTool.EditTool or \
                not self._is_valid_layer(self.mapCanvas.currentLayer()):
            return

        self.current_event = self.add_feature_event \
            if new_tool.action().objectName() == 'mActionAddFeature' \
            else self.change_geometry_event
        self._handle_event(self.current_event)

    def _handle_event(self, event: Union[AddFeatureEvent, ChangeGeometryEvent],
                      enabled: bool = True) -> None:
        # Enable: if not isEventFiltered
        # Disable: if isEventFiltered
        func_valid = (lambda filter: not filter) if enabled else (
            lambda filter: filter)
        if func_valid(event.isEventFiltered):
            event.toggleEventFilter()

    def _disable_current_events(self) -> None:
        for event in (self.add_feature_event, self.change_geometry_event):
            event.annotation_handler.remove()
        self._handle_event(self.add_feature_event, False)
        self._handle_event(self.change_geometry_event, False)

    @pyqtSlot('QgsMapLayer*')
    def currentLayerChanged(self, layer: QgsMapLayer) -> None:
        is_valid = self._is_valid_layer(layer)
        self.add_feature_event.isValidLayer = is_valid

        if not is_valid and not self.current_event is None:
            self.current_event.annotation_handler.remove()

        if is_valid and self.current_event == self.change_geometry_event and \
                self.change_geometry_event.isEnabled and \
                not self.change_geometry_event.layer == layer:
            self.change_geometry_event.change_layer(layer)

    def _is_valid_layer(self, layer: QgsMapLayer) -> bool:
        return False if layer is None or \
            not layer.type() == QgsMapLayerType.VectorLayer or \
            not layer.geometryType() in (QgsWkbTypes.LineGeometry,
                                         QgsWkbTypes.PolygonGeometry) \
            else True
