# -*- coding: utf-8 -*-

import os

import requests
from lxml import etree
from io import BytesIO

from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QMenu, QTreeWidgetItem, QLabel
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QPixmap
from qgis.core import QgsWkbTypes


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'karta_informacyjna_test.ui'))


class InfoToolsDialog(QtWidgets.QDialog, FORM_CLASS):
    dialog_closed = pyqtSignal()
    def __init__(self, parent: QtWidgets=None) -> None:
        super(InfoToolsDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlag(Qt.Window)
        self.menu = QMenu(self)
        self.is_closing = False
        self.identify_feature = self.menu.addAction("Identyfikuj obiekt(y)")
        self.identify_feature_hover = self.menu.addAction("Identyfikuj obiekty pod kursorem myszy")
        self.identify_feature_polygon = self.menu.addAction("Identyfikuj obiekty wielobokiem")
        self.identify_feature_freehand = self.menu.addAction("Identyfikuj obiekty swobodnie")
        self.identify_feature_radius = self.menu.addAction("Identyfikuj obiekty promieniem")
        self.selectObjectPushButton.setMenu(self.menu)

    def get_data(self, data=None, click_point=None, layer_type=None, layer_name=None) -> None:
        self.treeWidget.clear()
        if data is None:
            return
        if layer_type == 'ogr':
            self.show_ogr_data(data, click_point, layer_name)
        elif layer_type == 'gdal':
            self.show_gdal_data(data, layer_name)
        elif layer_type == 'wms':
            self.show_wms_data(data, layer_name)

    def show_ogr_data(self, data=None, click_point=None, layer_name=None) -> None:
        title = f"{layer_name} [{len(data)}]"
        root_item = QTreeWidgetItem([title])
        self.treeWidget.addTopLevelItem(root_item)
        for d in data:
            fields = d.fields()
            geom = d.geometry()
            attributes = d.attributes()
            for i, field_primary in enumerate(fields):
                item_primary = QTreeWidgetItem([str(field_primary.name()), str(attributes[i])])
                root_item.addChild(item_primary)
                sub_item = QTreeWidgetItem(["(pochodne)", ""])
                item_primary.addChild(sub_item)
                sub_item.addChild(QTreeWidgetItem(["ID obiektu", str(d.id())]))
                if click_point:
                    sub_item.addChild(QTreeWidgetItem(["(wskazana współrzędna X)", f"{click_point[0]:.6f}"]))
                    sub_item.addChild(QTreeWidgetItem(["(wskazana współrzędna Y)", f"{click_point[1]:.6f}"]))
                if geom.type() == QgsWkbTypes.PointGeometry:
                    if geom.isMultipart():
                        multi_points = d.geometry().asMultiPoint()
                        sub_item.addChild(QTreeWidgetItem(["X obiektu", f"{multi_points.x():.6f}"]))
                        sub_item.addChild(QTreeWidgetItem(["Y obiektu", f"{multi_points.y():.6f}"]))
                    elif geom.asPoint():
                        points = geom.asPoint()
                        sub_item.addChild(QTreeWidgetItem(["X obiektu", f"{points.x():.6f}"]))
                        sub_item.addChild(QTreeWidgetItem(["Y obiektu", f"{points.y():.6f}"]))
                elif geom.type() == QgsWkbTypes.LineGeometry:
                    if geom.isMultipart():
                        multi_polylines  = geom.asMultiPolyline()
                        sub_item.addChild(QTreeWidgetItem([
                            "X najbliższego wierzchołka", f"{geom.closestVertex(click_point)[0][0]:.6f}"
                        ]))
                        sub_item.addChild(QTreeWidgetItem([
                            "Y najbliższego wierzchołka", f"{geom.closestVertex(click_point)[0][1]:.6f}"
                        ]))
                        sub_item.addChild(QTreeWidgetItem([
                            "Odległość między wskazanym punktem a najbliższym wierzchołkiem",
                            f"{geom.closestVertex(click_point)[4]:.6f}"
                        ]))
                        sub_item.addChild(QTreeWidgetItem(["Części", str(len(multi_polylines))]))
                        sub_item.addChild(QTreeWidgetItem(["Długość (kartezjańska)", f"{geom.length():.6f} m"]))
                        # Długość elipsoidalna EPSG:7019
                        sub_item.addChild(QTreeWidgetItem(["Wierzchołki", str(len(list(geom.vertices())))]))
                        sub_item.addChild(QTreeWidgetItem([
                            "Numer najbliższego wierzchołka", str(geom.closestVertex(click_point)[1])
                        ]))
                    elif geom.asPolyline():
                        polylines = geom.asPolyline()
                        sub_item.addChild(QTreeWidgetItem(["Części", str(len(polylines))]))
                        # Długość elipsoidalna EPSG:7019
                        sub_item.addChild(QTreeWidgetItem(["Długość (kartezjańska)", f"{geom.length():.6f} m"]))
                        sub_item.addChild(QTreeWidgetItem(["Wierzchołki", str(len(list(geom.vertices())))]))
                elif geom.type() == QgsWkbTypes.PolygonGeometry:
                    if geom.isMultipart():
                        multi_polygons = geom.asMultiPolygon()
                        sub_item.addChild(QTreeWidgetItem([
                            "X najbliższego wierzchołka", f"{geom.closestVertex(click_point)[0][0]:.6f}"
                        ]))
                        sub_item.addChild(QTreeWidgetItem([
                            "Y najbliższego wierzchołka", f"{geom.closestVertex(click_point)[0][1]:.6f}"
                        ]))
                        sub_item.addChild(QTreeWidgetItem([
                            "Odległość między wskazanym punktem a najbliższym wierzchołkiem",
                            f"{geom.closestVertex(click_point)[4]:.6f}"
                        ]))
                        sub_item.addChild(QTreeWidgetItem(["Części", str(len(multi_polygons))]))
                        sub_item.addChild(QTreeWidgetItem(["Obwód (kartezjański)"]))
                        sub_item.addChild(QTreeWidgetItem(["Powierzchnia (kartezjańska)", f"{geom.area():.6f}"]))
                        sub_item.addChild(QTreeWidgetItem(["Wierzchołki", str(len(list(geom.vertices())))]))
                        sub_item.addChild(QTreeWidgetItem([
                            "Numer najbliższego wierzchołka", str(geom.closestVertex(click_point)[1])
                        ]))
                    elif geom.asPolyline():
                        polygons = geom.asPolygon()
                        sub_item.addChild(QTreeWidgetItem(["Części", str(len(polygons))]))
                        #obwod elipsoidalny
                        sub_item.addChild(QTreeWidgetItem(["Obwód (kartezjański)"]))
                        #powierzchnia elipsoidalna
                        sub_item.addChild(QTreeWidgetItem(["Powierzchnia (kartezjańska)", f"{geom.area():.6f}"]))
                        sub_item.addChild(QTreeWidgetItem(["Wierzchołki", str(len(list(geom.vertices())))]))
                sub_item.setExpanded(True)
                for j, field_secondary in enumerate(fields):
                    item_secondary = QTreeWidgetItem([str(field_secondary.name()), str(attributes[j])])
                    item_primary.addChild(item_secondary)
                item_primary.setExpanded(True)
                break
        root_item.setExpanded(True)

    def show_gdal_data(self, data=None, layer_name=None) -> None:
        title = f"{layer_name}"
        root_item = QTreeWidgetItem([title])
        self.treeWidget.addTopLevelItem(root_item)
        item = QTreeWidgetItem([str(f"Kanał: {next(iter(data[0]))}"), str(next(iter(data[0].values())))])
        root_item.addChild(item)
        sub_item = QTreeWidgetItem(["(pochodne)", ""])
        item.addChild(sub_item)
        sub_item.addChild(QTreeWidgetItem(["(wskazana współrzędna X)", str(data[1][0])]))
        sub_item.addChild(QTreeWidgetItem(["(wskazana współrzędna Y)", str(data[1][1])]))
        sub_item.addChild(QTreeWidgetItem(["Kolumna (numeracja od 0)", str(data[2])]))
        sub_item.addChild(QTreeWidgetItem(["Wiersz (numeracja od 0)", str(data[3])]))
        root_item.setExpanded(True)
        item.setExpanded(True)

    def show_wms_data(self, data=None, layer_name=None) -> None:
        title = f"{layer_name}"
        root_item = QTreeWidgetItem([title])
        self.treeWidget.addTopLevelItem(root_item)
        for k, v in data.items():
            if k != "Kod QR":
                root_item.addChild(QTreeWidgetItem([k, v]))
            else:
                qr_link = etree.XML(data.get("Kod QR")).xpath("//img/@src")
                qr_item = QTreeWidgetItem()
                root_item.addChild(qr_item)
                try:
                    response_qr_link = requests.get(qr_link[0])
                    response_qr_link.raise_for_status()
                    qr_item.setText(0, "Kod QR")
                    pixmap = QPixmap()
                    pixmap.loadFromData(BytesIO(response_qr_link.content).read())
                    label = QLabel()
                    label.setPixmap(pixmap.scaledToHeight(128)) #tu na sztywno poprawić potem
                    self.treeWidget.setItemWidget(qr_item, 1, label)
                except Exception as e:
                    qr_item.setText(0, "Kod QR")
                    qr_item.setText(1, f"Błąd ładowania: {e}")
        root_item.setExpanded(True)

    def closeEvent(self, event) -> None:
        self.treeWidget.clear()
        self.is_closing = True
        super().closeEvent(event)
        if hasattr(self, 'dialog_closed'):
            self.dialog_closed.emit()

