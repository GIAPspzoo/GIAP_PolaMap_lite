# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os

import requests
from qgis.PyQt import QtWidgets, uic, QtCore
from qgis.core import QgsVectorLayer, QgsProject, QgsFeature, QgsGeometry, QgsFields, QgsField, QgsRasterLayer, \
    QgsLayerTreeGroup, QgsCoordinateTransform, QgsCoordinateReferenceSystem
from qgis.utils import iface
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QApplication, QProgressDialog

from .utils import CustomMessageBox, tr, search_group_name, add_map_layer_to_group


class PRNGTool(QtWidgets.QDialog):
    def __init__(self, parent=None) -> None:
        """Constructor."""
        super(PRNGTool, self).__init__(parent)
        ui_file = os.path.join(os.path.dirname(__file__), 'prng_tool.ui')
        uic.loadUi(ui_file, self)

        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setMinimumSize(678, 202)
        self.setMaximumSize(678, 202)
        self.setWindowOpacity(1.0)

        self.SzukajButton.clicked.connect(self.search_location)
        self.ObiektButton.clicked.connect(self.add_selected_object_to_layer)
        self.results_data = {}
        self.listView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

    def run(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def search_location(self):
        location_name = self.lineEdit.text()
        if not location_name:
            CustomMessageBox(self, tr('Please enter a location name!')).button_ok()
            return

        url = f"http://services.gugik.gov.pl/uug/?request=GetLocation&location={location_name}"

        progress_dialog = QProgressDialog(tr("Connection"), tr("Cancel"), 0, 100, self)
        progress_dialog.setWindowTitle(tr("Please wait"))
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setFixedWidth(300)
        progress_dialog.setFixedHeight(100)
        progress_dialog.setCancelButton(None)
        progress_dialog.show()
        progress_dialog.setValue(0)
        QApplication.sendPostedEvents()
        QApplication.processEvents()

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            self.results_data.clear()
            model = QtCore.QStringListModel(self.listView)
            model.setStringList([])
            self.listView.setModel(model)

            if data["found objects"] == 0:
                url = f"http://services.gugik.gov.pl/uug/?request=GetAddress&location={location_name}"
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                if data["found objects"] == 0:
                    progress_dialog.setValue(100)
                    QApplication.processEvents()
                    CustomMessageBox(self, tr('No objects found!')).button_ok()
                    return

                for key, value in data["results"].items():
                    try:
                        self.results_data[key] = {
                            "name": value["city"], "type": "miasto", "voivodeship": value["voivodeship"], "county": value["county"],
                            "commune": value["commune"], "class": "", "status": "", "x": value["x"], "y": value["y"], "geometry_wkt": value["geometry_wkt"]
                        }
                    except:
                        self.results_data[key] = {
                            "name": value["city"], "type": "miasto", "street": value["street"], "class": "", "status": "", "x": value["x"], "y": value["y"],
                            "geometry_wkt": value["geometry_wkt"]
                        }
            else:
                self.results_data = data["results"]

            items = []
            for key, value in self.results_data.items():
                try:
                    items.append(f"{value['name']} ( {value['type']}, {value['voivodeship']}, {value['county']} )")
                except:
                    items.append(f"{value['name'], value['street']}")

            model.setStringList(items)
            self.listView.setModel(model)
            progress_dialog.setValue(100)
            QApplication.processEvents()

        except requests.RequestException as e:
            progress_dialog.setValue(100)
            QApplication.processEvents()
            CustomMessageBox(self, tr('Error in query!')).button_ok()
        except ValueError:
            progress_dialog.setValue(100)
            QApplication.processEvents()
            CustomMessageBox(self, tr('Invalid server response!')).button_ok()

    def add_selected_object_to_layer(self):
        selected_index = self.listView.currentIndex()
        if not selected_index.isValid():
            CustomMessageBox(self, tr('Please select an object from the list.')).button_ok()
            return

        selected_text = selected_index.data()
        coordinates = None
        attributes = []
        for key, value in self.results_data.items():
            if f"{value['name']} ( {value['type']}, {value['voivodeship']}, {value['county']} )" == selected_text:
                coordinates = value['geometry_wkt']
                attributes = [value['name'], value['type'], value['voivodeship'], value['county'], value['commune'],
                              value['class'], value['status'], value['x'], value['y']]
                break

        if coordinates:
            x = attributes[-2]
            y = attributes[-1]
            existing_features = self.find_features_by_coordinates(x, y)
            if existing_features:
                self.zoom_to_feature(existing_features[0])
                self.close()
                return
            layer_name = "UUG_obiekty_fizjograficzne"
            layer = self.get_layer("MultiPoint?crs=epsg:2180&index=yes", layer_name, "")
            layer.setCustomProperty("do_not_save", True)
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromWkt(coordinates))
            feature.setAttributes(attributes)
            layer.dataProvider().addFeature(feature)
            layer.updateExtents()
            if not QgsProject.instance().mapLayersByName(layer_name):
                add_map_layer_to_group(layer, search_group_name, force_create=True)
            self.zoom_to_feature(feature)
            self.close()
        else:
            CustomMessageBox(self, tr('Could not obtain coordinates.')).button_ok()

    def get_layer(self, org: str, obj_type: str, qml: str) -> QgsVectorLayer:
        layer = QgsProject.instance().mapLayersByName(obj_type)
        if layer:
            return layer[0]

        layer = QgsVectorLayer(org, obj_type, 'memory')
        fields = QgsFields()
        fields.append(QgsField("name", QtCore.QVariant.String))
        fields.append(QgsField("type", QtCore.QVariant.String))
        fields.append(QgsField("voivodeship", QtCore.QVariant.String))
        fields.append(QgsField("county", QtCore.QVariant.String))
        fields.append(QgsField("commune", QtCore.QVariant.String))
        fields.append(QgsField("class", QtCore.QVariant.String))
        fields.append(QgsField("status", QtCore.QVariant.String))
        fields.append(QgsField("x", QtCore.QVariant.String))
        fields.append(QgsField("y", QtCore.QVariant.String))
        layer.dataProvider().addAttributes(fields)
        layer.updateFields()
        direc = os.path.dirname(__file__)
        layer.loadNamedStyle(os.path.join(direc, 'Searcher', 'layer_style', 'obiekt_PRNG.qml'))
        return layer

    def change_scale(self, geom):
        transform = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:2180"), QgsProject.instance().crs(),
                                           QgsProject.instance())
        geom_bbox = geom.boundingBox()
        transform_geom = transform.transformBoundingBox(geom_bbox)
        iface.mapCanvas().zoomToFeatureExtent(transform_geom)
        iface.mapCanvas().zoomScale(1000)

    def zoom_to_feature(self, feature: QgsFeature):
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(200)
        self.timer.timeout.connect(lambda: self.change_scale(feature.geometry()))
        self.timer.start()

    def find_features_by_coordinates(self, x, y):
        layer = self.get_layer("MultiPoint?crs=epsg:2180&index=yes", "UUG_obiekty_fizjograficzne", "")
        feats = [f for f in layer.getFeatures() if f.attribute('x') == x and f.attribute('y') == y]
        return feats
