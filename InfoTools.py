# -*- coding: utf-8 -*-

import requests
from lxml import html, etree

from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QTimer, Qt
from qgis.PyQt.QtWidgets import QLabel
from qgis.gui import QgisInterface, QgsMapToolIdentify, QgsMapCanvas, QgsRubberBand, QgsHighlight
from qgis.core import (QgsGeometry, QgsWkbTypes, QgsRectangle, QgsFeature, QgsVectorLayer, QgsRasterLayer, QgsRaster,
                       QgsDistanceArea, QgsProject, QgsMapLayer)

from .InfoToolsDialog import InfoToolsDialog


params_feature_info = {
    "REQUEST": "GetFeatureInfo",
    "SERVICE": "WMS",
    "VERSION": "1.1.1",
    "LAYERS": "integracja",
    "QUERY_LAYERS": "",
    "SRS": "",
    "FORMAT": "image/png",
    "INFO_FORMAT": "application/vnd.ogc.gml",
    "BBOX": "",
    "WIDTH": "",
    "HEIGHT": "",
    "I": "",
    "J": "",
}


class InfoTool:
    def __init__(self, iface: QgisInterface) -> None:
        self.iface = iface
        self.dialog = InfoToolsDialog(iface.mainWindow())
        self.canvas = self.iface.mapCanvas()
        self.features_dict = {}
        self.tool = None
        self.default_map_tool = None
        self.highlighter = HighlightFeatures(self.canvas, parent_tool=self)
        self.highlighter.clear()
        self.current_crs = QgsProject.instance().crs()

        QgsProject.instance().crsChanged.connect(self.update_crs)
        self.dialog.rejected.connect(self.sample)
        self.dialog.identify_feature.triggered.connect(self.activate_identify_tool)
        self.dialog.identify_feature_hover.triggered.connect(self.activate_identify_hover_tool)
        self.dialog.identify_feature_polygon.triggered.connect(self.activate_identify_polygon_tool)
        self.dialog.identify_feature_freehand.triggered.connect(self.activate_identify_freehand_tool)
        self.dialog.identify_feature_radius.triggered.connect(self.activate_identify_radius_tool)

    def get_layer(self) -> QgsMapLayer | None:
        return self.iface.activeLayer()

    def run(self) -> None:
        self.default_map_tool = self.canvas.mapTool()
        self.dialog.show()
        self.dialog.raise_()

    def sample(self) -> None:
        if self.tool:
            self.canvas.unsetMapTool(self.tool)
            self.tool = None
        if self.default_map_tool:
            self.canvas.setMapTool(self.default_map_tool)
        self.highlighter.clear()

    def update_crs(self) -> None:
        self.current_crs = QgsProject.instance().crs()
        self.highlighter.clear()
        self.dialog.get_data(None, None, None, None)
        self.canvas.refresh()

    def activate_identify_tool(self) -> None:
        if not self.iface.activeLayer():
            return
        self.highlighter.clear()
        self.tool = IdentifyFeatureTool(
            self.iface, self.canvas,
            lambda data, click_point, layer_type: self.dialog.get_data(data, click_point, layer_type, self.iface.activeLayer().name()),
            self.features_dict, self
        )
        self.canvas.unsetMapTool(self.tool)
        self.canvas.setMapTool(self.tool)

    def activate_identify_hover_tool(self) -> None:
        if not self.iface.activeLayer():
            return
        self.highlighter.clear()
        self.tool = IdentifyFeatureHoverTool(
            self.iface, self.canvas,
            lambda data, click_point, layer_type: self.dialog.get_data(data, None, layer_type, self.iface.activeLayer().name()),
            self.features_dict, self
        )
        self.canvas.unsetMapTool(self.tool)
        self.canvas.setMapTool(self.tool)

    def activate_identify_polygon_tool(self) -> None:
        if not self.iface.activeLayer():
            return
        self.highlighter.clear()
        self.tool = IdentifyFeaturePolygonTool(
            self.iface, self.canvas,
            lambda data, click_point, layer_type: self.dialog.get_data(data, None, layer_type, self.iface.activeLayer().name()),
            self.features_dict, self
        )
        self.canvas.unsetMapTool(self.tool)
        self.canvas.setMapTool(self.tool)

    def activate_identify_freehand_tool(self) -> None:
        if not self.iface.activeLayer():
            return
        self.highlighter.clear()
        self.tool = IdentifyFeatureFreehandTool(
            self.iface, self.canvas,
            lambda data, click_point, layer_type: self.dialog.get_data(data, None, layer_type, self.iface.activeLayer().name()),
            self.features_dict, self
        )
        self.canvas.unsetMapTool(self.tool)
        self.canvas.setMapTool(self.tool)

    def activate_identify_radius_tool(self) -> None:
        if not self.iface.activeLayer():
            return
        self.highlighter.clear()
        self.tool = IdentifyFeatureRadiusTool(
            self.iface, self.canvas,
            lambda data, click_point, layer_type: self.dialog.get_data(data, None, layer_type, self.iface.activeLayer().name()),
            self.features_dict, self
        )
        self.canvas.unsetMapTool(self.tool)
        self.canvas.setMapTool(self.tool)


class HighlightFeatures:
    def __init__(self, canvas: QgsMapCanvas, parent_tool: InfoTool) -> None:
        """Uwydatnia zaznaczone obiekty wektorowe na mapie"""
        self.canvas = canvas
        self.parent_tool = parent_tool
        self.highlight = None

    def clear(self) -> None:
        if self.highlight:
            self.highlight.hide()
            if self.canvas and self.highlight.scene():
                self.canvas.scene().removeItem(self.highlight)
            self.highlight = None

        if self.parent_tool:
            if hasattr(self.parent_tool, "highlight") and self.parent_tool.highlight:
                self.parent_tool.highlight.hide()
                if self.canvas and self.parent_tool.highlight.scene():
                    self.canvas.scene().removeItem(self.parent_tool.highlight)
            self.parent_tool.highlight = None

    def highlight_features(self, features) -> None:
        self.clear()
        if isinstance(features, QgsFeature):
            features = [features]
        if not features:
            return
        multi_geom = QgsGeometry.unaryUnion([f.geometry() for f in features])
        self.highlight = QgsHighlight(self.canvas, multi_geom, self.parent_tool.get_layer())
        self.highlight.setColor(QColor(255,0,0))
        self.highlight.setFillColor(QColor(255,0,0))
        self.highlight.setWidth(1)
        self.highlight.show()
        if self.parent_tool:
            self.parent_tool.highlight = self.highlight


class IdentifyFeatureTool(QgsMapToolIdentify):
    def __init__(self, iface: QgisInterface, canvas: QgsMapCanvas, callback, features_dict, parent_tool: InfoTool) -> None:
        super().__init__(canvas)
        self.iface = iface
        self.canvas = canvas
        self.callback = callback
        self.features_dict = features_dict
        self.parent_tool = parent_tool
        self.highlighter = HighlightFeatures(self.canvas, self.parent_tool)
        self.highlighter.clear()
        self.start_point = None
        self.end_point = None
        self.dragging = False
        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setColor(QColor(0,0,255,50))
        self.rubber_band.setFillColor(QColor(0,0,255,50))
        self.rubber_band.setWidth(2)

    def deactivate(self) -> None:
        super().deactivate()
        if not hasattr(self.parent_tool.dialog, 'is_closing') or not self.parent_tool.dialog.is_closing:
            self.highlighter.clear()

    def canvasPressEvent(self, event) -> None:
        self.start_point = self.toMapCoordinates(event.pos())
        self.dragging = False

    def canvasMoveEvent(self, event) -> None:
        layer = self.parent_tool.get_layer()
        if not self.start_point:
            return
        self.end_point = self.toMapCoordinates(event.pos())
        if isinstance(layer, QgsVectorLayer):
            self.dragging = True
        else:
            return
        rect = QgsRectangle(self.start_point, self.end_point)
        self.rubber_band.setToGeometry(QgsGeometry.fromRect(rect), None)
        self.rubber_band.show()

    def canvasReleaseEvent(self, event) -> None:
        layer = self.parent_tool.get_layer()
        if not self.start_point:
            return
        self.rubber_band.hide()
        self.highlighter.clear()
        if self.dragging:
            self.end_point = self.toMapCoordinates(event.pos())
            rect = QgsRectangle(self.start_point, self.end_point)
            rect_geom = QgsGeometry.fromRect(rect)
            features = [f for f in layer.getFeatures() if f.geometry().intersects(rect_geom)]
            if features:
                self.features_dict.clear()
                for f in features:
                    self.features_dict[f.id()] = f
                self.callback(features, None, layer.dataProvider().name())
                self.highlighter.highlight_features(features)
            else:
                self.highlighter.clear()
                self.callback(None, None, None)
        else:
            if isinstance(layer, QgsVectorLayer):
                result = self.identify(event.pos().x(), event.pos().y(), [layer], self.TopDownStopAtFirst)
                if result:
                    feature = result[0].mFeature
                    if feature.isValid():
                        self.features_dict[feature.id()] = feature
                        self.highlighter.highlight_features([feature])
                        self.callback([feature], self.start_point, layer.dataProvider().name())
                else:
                    self.highlighter.clear()
                    self.callback(None, None, None)

            elif isinstance(layer, QgsRasterLayer):
                if not layer.extent().contains(self.start_point):
                    self.highlighter.clear()
                    self.start_point = None
                    self.callback(None, None, None)
                    return

                if layer.dataProvider().name() == 'wms':
                    layer_metadata = layer.htmlMetadata()
                    metadata_tree = html.fromstring(layer_metadata)
                    url = metadata_tree.xpath("//a/@href")[0]
                    params_feature_info["SRS"] = layer.crs().authid()
                    params_feature_info["BBOX"] = (
                        f"{self.canvas.extent().xMinimum()},{self.canvas.extent().yMinimum()},"
                        f"{self.canvas.extent().xMaximum()},{self.canvas.extent().yMaximum()}"
                    )
                    params_feature_info["WIDTH"] = self.canvas.width()
                    params_feature_info["HEIGHT"] = self.canvas.height()
                    params_feature_info["I"] = event.pos().x()
                    params_feature_info["J"] = event.pos().y()
                    response = requests.get(url, params=params_feature_info)
                    response.encoding = "utf-8"
                    response = response.text
                    response = response.split(">", 1)[1].strip()
                    xml_file = etree.fromstring(response)
                    xml_attributes = xml_file.findall(".//{http://www.intergraph.com/geomedia/gml}Attribute")
                    attributes_dict = {}
                    for attr in xml_attributes:
                        attributes_dict[attr.get("Name")] = attr.text.strip() if attr.text else ''
                    self.callback(attributes_dict, None, layer.dataProvider().name()) if attributes_dict else self.callback(None, None, None)

                elif layer.dataProvider().name() == 'gdal':
                    ident = layer.dataProvider().identify(self.start_point, QgsRaster.IdentifyFormatValue)
                    values = ident.results()
                    no_data_pxl = layer.dataProvider().sourceNoDataValue(1)
                    pxl_value = values.get(1, None)
                    if pxl_value is None or pxl_value == no_data_pxl:
                        self.callback(None, None, None)
                    else:
                        col = int((self.start_point[0] - layer.extent().xMinimum()) / layer.rasterUnitsPerPixelX())
                        row = int((layer.extent().yMaximum() - self.start_point[1]) / layer.rasterUnitsPerPixelY())
                        self.callback([values, self.start_point, col, row], None, layer.dataProvider().name())
        self.start_point = None
        self.end_point = None
        self.dragging = False


class IdentifyFeatureHoverTool(QgsMapToolIdentify):
    def __init__(self, iface: QgisInterface, canvas: QgsMapCanvas, callback, features_dict, parent_tool: InfoTool) -> None:
        super().__init__(canvas)
        self.iface = iface
        self.canvas = canvas
        self.callback = callback
        self.features_dict = features_dict
        self.parent_tool = parent_tool
        self.highlighter = HighlightFeatures(self.canvas, self.parent_tool)
        self.highlighter.clear()
        self.start_point = None
        self.last_mouse_event = None
        self.throttle_timer = QTimer()
        self.throttle_timer.setInterval(200)
        self.throttle_timer.setSingleShot(True)
        self.throttle_timer.timeout.connect(self.do_identify)

    def deactivate(self) -> None:
        super().deactivate()
        if not hasattr(self.parent_tool.dialog, 'is_closing') or not self.parent_tool.dialog.is_closing:
            self.highlighter.clear()

    def canvasMoveEvent(self, event) -> None:
        self.last_mouse_event = event
        self.start_point = event
        if not self.throttle_timer.isActive():
            self.throttle_timer.start()

    def do_identify(self) -> None:
        layer = self.iface.activeLayer()
        if not self.last_mouse_event:
            return
        if isinstance(layer, QgsVectorLayer):
            result = self.identify(self.last_mouse_event.pos().x(), self.last_mouse_event.pos().y(), [layer], self.TopDownStopAtFirst)
            if result:
                feature = result[0].mFeature
                if feature.isValid():
                    self.features_dict[feature.id()] = feature
                    self.highlighter.highlight_features([feature])
                    # self.callback([feature])
                    self.callback([feature], None, layer.dataProvider().name())
                else:
                    self.highlighter.clear()
                    self.callback(None, None, None)

        elif isinstance(layer, QgsRasterLayer):
            self.start_point = self.toMapCoordinates(self.last_mouse_event.pos())
            if not layer.extent().contains(self.start_point):
                self.callback(None, None, None)
                return
            ident = layer.dataProvider().identify(self.start_point, QgsRaster.IdentifyFormatValue)
            if ident.isValid():
                values = ident.results()
                no_data_pxl = layer.dataProvider().sourceNoDataValue(1)
                pxl_value = values.get(1, None)
                if pxl_value is None or pxl_value == no_data_pxl:
                    self.callback(None, None, None)
                else:
                    col = int((self.start_point[0] - layer.extent().xMinimum()) / layer.rasterUnitsPerPixelX())
                    row = int((layer.extent().yMaximum() - self.start_point[1]) / layer.rasterUnitsPerPixelY())
                    self.callback([values, self.start_point, col, row], None, layer.dataProvider().name())
            self.highlighter.clear()


class IdentifyFeaturePolygonTool(QgsMapToolIdentify):
    def __init__(self, iface: QgisInterface, canvas: QgsMapCanvas, callback, features_dict, parent_tool: InfoTool) -> None:
        super().__init__(canvas)
        self.iface = iface
        self.canvas = canvas
        self.callback = callback
        self.features_dict = features_dict
        self.parent_tool = parent_tool
        self.highlighter = HighlightFeatures(self.canvas, self.parent_tool)
        self.highlighter.clear()
        self.point = None
        self.points = []
        self.is_drawing = False
        self.rubberBand = None

    def deactivate(self) -> None:
        super().deactivate()
        if not hasattr(self.parent_tool.dialog, 'is_closing') or not self.parent_tool.dialog.is_closing:
            self.highlighter.clear()

    def canvasPressEvent(self, event) -> None:
        layer = self.iface.activeLayer()
        if not layer:
            return
        self.highlighter.clear()
        if self.rubberBand is None:
            self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
            self.rubberBand.setColor(QColor(0, 0, 255, 50))
            self.rubberBand.setFillColor(QColor(0, 0, 255, 50))
            self.rubberBand.setWidth(2)
        if isinstance(layer, QgsVectorLayer):
            if event.button() == Qt.LeftButton:
                self.point = self.toMapCoordinates(event.pos())
                self.points.append(self.point)
                self.is_drawing = True
                self.rubberBand.setToGeometry(QgsGeometry.fromPolygonXY([self.points]), None)
                self.rubberBand.show()
            elif event.button() == Qt.RightButton:
                if len(self.points) < 3:
                    self.points.clear()
                    self.rubberBand.hide()
                    self.rubberBand = None
                    self.is_drawing = False
                    return
                else:
                    polygon = self.rubberBand.asGeometry()
                    features = [f for f in layer.getFeatures() if f.geometry().intersects(polygon)]
                    if features:
                        self.features_dict.clear()
                        for f in features:
                            self.features_dict[f.id()] = f
                        self.callback(features, None, layer.dataProvider().name())
                        self.highlighter.highlight_features(features)
                    else:
                        self.highlighter.clear()
                        self.callback(None, None, None)
                    self.is_drawing = False
                    self.points.clear()
                    self.rubberBand.hide()
                    self.rubberBand = None
                return

    def canvasMoveEvent(self, event) -> None:
        if not self.is_drawing or not self.points:
            return
        temp_points = self.points + [self.toMapCoordinates(event.pos())]
        self.rubberBand.setToGeometry(QgsGeometry.fromPolygonXY([temp_points]), None)


class IdentifyFeatureFreehandTool(QgsMapToolIdentify):
    def __init__(self, iface: QgisInterface, canvas: QgsMapCanvas, callback, features_dict, parent_tool: InfoTool) -> None:
        super().__init__(canvas)
        self.iface = iface
        self.canvas = canvas
        self.callback = callback
        self.features_dict = features_dict
        self.parent_tool = parent_tool
        self.highlighter = HighlightFeatures(self.canvas, self.parent_tool)
        self.highlighter.clear()
        self.start_point = None
        self.end_point = None
        self.points = []
        self.rubberBand = None
        self.is_drawing = False
        self.wait_for_second_click = False
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(0, 0, 255, 50))
        self.rubberBand.setFillColor(QColor(0, 0, 255, 50))
        self.rubberBand.setWidth(2)

    def deactivate(self) -> None:
        super().deactivate()
        if not hasattr(self.parent_tool.dialog, 'is_closing') or not self.parent_tool.dialog.is_closing:
            self.highlighter.clear()

    def canvasPressEvent(self, event):
        layer = self.iface.activeLayer()
        if not layer:
            return
        self.highlighter.clear()
        if isinstance(layer, QgsVectorLayer):
            self.rubberBand.setToGeometry(QgsGeometry.fromPolygonXY([self.points]), None)
            self.rubberBand.show()
            if event.button() == Qt.LeftButton and not self.wait_for_second_click:
                if not self.wait_for_second_click:
                    self.is_drawing = True
                    self.wait_for_second_click = True
            elif event.button() == Qt.LeftButton and self.wait_for_second_click:
                self.wait_for_second_click = False
                polygon = self.rubberBand.asGeometry()
                features = [f for f in layer.getFeatures() if f.geometry().intersects(polygon)]
                if features:
                    self.features_dict.clear()
                    for f in features:
                        self.features_dict[f.id()] = f
                        self.callback(features, None, layer.dataProvider().name())
                        self.highlighter.highlight_features(features)
                else:
                    self.highlighter.clear()
                    self.callback(None, None, None)
                self.points.clear()
                self.rubberBand.hide()
                self.is_drawing = False
            if event.button() == Qt.RightButton:
                self.highlighter.clear()
                self.callback(None, None, None)
                self.points.clear()
                self.rubberBand.hide()
                self.is_drawing = False
                self.wait_for_second_click = False

    def canvasMoveEvent(self, event) -> None:
        if self.is_drawing:
            point = self.toMapCoordinates(event.pos())
            self.points.append(point)
            self.rubberBand.addPoint(point)


class IdentifyFeatureRadiusTool(QgsMapToolIdentify):
    def __init__(self, iface: QgisInterface, canvas: QgsMapCanvas, callback, features_dict, parent_tool: InfoTool) -> None:
        super().__init__(canvas)
        self.iface = iface
        self.canvas = canvas
        self.callback = callback
        self.features_dict = features_dict
        self.parent_tool = parent_tool
        self.highlighter = HighlightFeatures(self.canvas, self.parent_tool)
        self.highlighter.clear()
        self.center_point = None
        self.wait_for_second_click = False
        self.label = QLabel(self.canvas)
        self.label.setStyleSheet(
            """
            padding: 4px;
            border-radius: 6px;
            """
        )
        self.label.setAlignment(Qt.AlignCenter)
        self.label.adjustSize()
        self.label.move(10, 10)
        self.distance_calc = QgsDistanceArea()
        self.distance_calc.setSourceCrs(canvas.mapSettings().destinationCrs(), QgsProject.instance().transformContext())
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(0, 0, 255, 50))
        self.rubberBand.setFillColor(QColor(0, 0, 255, 50))
        self.rubberBand.setWidth(2)

    def deactivate(self) -> None:
        super().deactivate()
        if not hasattr(self.parent_tool.dialog, 'is_closing') or not self.parent_tool.dialog.is_closing:
            self.highlighter.clear()
        if self.label:
            self.label.hide()

    def canvasPressEvent(self, event) -> None:
        layer = self.iface.activeLayer()
        if not layer:
            return
        self.highlighter.clear()
        if isinstance(layer, QgsVectorLayer):
            if event.button() == Qt.LeftButton and not self.wait_for_second_click:
                self.center_point = self.toMapCoordinates(event.pos())
                self.wait_for_second_click = True
            elif event.button() == Qt.LeftButton and self.wait_for_second_click:
                polygon = self.rubberBand.asGeometry()
                features = [f for f in layer.getFeatures() if f.geometry().intersects(polygon)]
                self.label.hide()
                if features:
                    self.features_dict.clear()
                    for f in features:
                        self.features_dict[f.id()] = f
                        self.callback(features, None, layer.dataProvider().name())
                        self.highlighter.highlight_features(features)
                else:
                    self.highlighter.clear()
                    self.callback(None, None, None)
                self.center_point = None
                self.rubberBand.hide()
                self.wait_for_second_click = False
            if event.button() == Qt.RightButton:
                self.highlighter.clear()
                self.callback(None, None, None)
                self.center_point = None
                self.rubberBand.hide()
                self.wait_for_second_click = False
                self.label.hide()

    def canvasMoveEvent(self, event) -> None:
        if self.center_point:
            current_point = self.toMapCoordinates(event.pos())
            radius = self.center_point.distance(current_point)
            radius_length = self.distance_calc.measureLine(self.center_point, current_point)
            buffer_geom = QgsGeometry.fromPointXY(self.center_point).buffer(radius, 50)
            self.rubberBand.setToGeometry(buffer_geom, None)
            self.rubberBand.show()
            self.label.setText(f"Promień zaznaczenia: {radius_length:.5f}")
            self.label.adjustSize()
            self.label.show()

