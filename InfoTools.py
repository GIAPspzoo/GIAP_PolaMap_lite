# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import tempfile
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import QRectF, QDateTime, QSettings
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtWidgets import QFileDialog, QApplication
from qgis._core import QgsLayoutExporter, QgsWkbTypes, QgsLayoutItemMap, \
    QgsLayout, QgsProject, QgsUnitTypes, QgsLayoutSize, QgsGeometry, \
    QgsVectorLayer, QgsFeature, QgsSymbol, QgsSimpleFillSymbolLayer, \
    QgsLayoutItemLegend, QgsLayerTreeGroup, QgsLegendStyle, QgsLayoutItem, \
    QgsLayoutItemLabel, QgsLayoutItemScaleBar, QgsRectangle, QgsPointXY, QgsIdentifyContext
from qgis._gui import QgsRubberBand, QgisInterface, QgsMapToolIdentifyFeature, QgsMapCanvas, QgsMapToolIdentify
from qgis.utils import iface
from typing import Union

from .InfoToolsDialog import InfoToolsDialog
from .utils import tr, CustomMessageBox, normalize_path
from .config import Config

class InfoTool:
    def __init__(self, iface: QgisInterface, parent: QtWidgets = None) -> None:
        self.iface = iface
        self.dialog = InfoToolsDialog()
        self.canvas = self.iface.mapCanvas()
        self.dialog.identify_feature.triggered.connect(self.activate_identify_tool)
    def run(self) -> None:
        self.dialog.show()

    def activate_identify_tool(self):
        self.tool = IdentifyFeatureTool(self.canvas)
        self.canvas.setMapTool(self.tool)


class IdentifyFeatureTool(QgsMapToolIdentifyFeature):

    def __init__(self, canvas: QgsMapCanvas):
        super().__init__(canvas)
        self.canvas = canvas

    def canvasReleaseEvent(self, event):
        point = self.toMapCoordinates(event.pos())
        print(point[0],"elo",point[1])
        self.identify_features(point)
    def identify_features(self, point: QgsPointXY):
        identify_result = QgsMapToolIdentifyFeature.identify(int(point[0]), int(point[1]),self.canvas.layers(True),
                                                             QgsMapToolIdentify.DefaultQgsSetting,
                                                             QgsIdentifyContext())


        for result in identify_result:
            layer = result.layerId()
            feature = result.feature()
            print(f"Warstwa: {layer}, ID: {feature.id()}, Atrybuty: {feature.attributes()}")
