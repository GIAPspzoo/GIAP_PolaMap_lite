# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import json

from qgis.gui import QgsMapToolPan
from qgis.PyQt import QtWidgets, uic
from qgis.core import (QgsVectorLayer, QgsProject, QgsGeometry,
                       QgsRectangle, QgsVectorFileWriter, QgsDataSourceUri,
                       QgsCoordinateReferenceSystem, QgsField, QgsEditFormConfig,
                       QgsCoordinateTransform, QgsFeatureRequest, QgsFeature)
from datetime import datetime
from qgis.utils import iface
from qgis.PyQt.QtWidgets import QFileDialog, QApplication
from qgis.PyQt.QtCore import Qt, QVariant, QSortFilterProxyModel
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem
from owslib.wfs import WebFeatureService

from .utils import tr, project, ProgressDialog, TmpCopyLayer, IdentifyGeometry, get_simple_progressbar, \
    CustomMessageBox, add_map_layer_to_group, unpack_nested_lists, get_project_config, set_project_config

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'wfs_dialog.ui'))


def identify_layer_by_name(layername_to_find):
    for layer in list(project.mapLayers().values()):
        if layer.name() == layername_to_find:
            return layer

def combine_geoms(geoms_list):
    geoms_list_len = len(geoms_list)
    if geoms_list_len == 0:
        return
    elif geoms_list_len == 1:
        return geoms_list[0]
    elif geoms_list_len > 1:
        union_geoms = geoms_list[0]
        for geometry in geoms_list[1:]:
            if geometry.isGeosValid():
                union_geoms = union_geoms.combine(geometry)
        return union_geoms

CONFIG_SCOPE = 'WMS_WMTS'
CONFIG_KEY = 'json_file'

def get_wms_config() -> dict:
    current_config = get_project_config(CONFIG_SCOPE, CONFIG_KEY)
    if current_config:
        return json.loads(current_config)
    else:
        json_dict = read_json_file()
        if json_dict:
            return json_dict

def set_wms_config(data: dict) -> None:
    set_project_config(CONFIG_SCOPE, CONFIG_KEY, json.dumps(data))

def get_json_path() -> str:
    return os.path.join(os.path.dirname(__file__), 'Wms_wmts', 'WMS_WMTS.json')

def read_json_file(json_name: str = None) -> dict:
    if json_name is None:
        json_path = get_json_path()
    with open(json_path, "r+") as json_read:
        return json.load(json_read)


class AddWfsTool(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(AddWfsTool, self).__init__(parent)
        self.setupUi(self)

        self.connectButton.clicked.connect(self.connect_to_service)
        self.addToMapButton.clicked.connect(self.add_selected_layers_to_map)
        self.chooseLayerEdit.textChanged.connect(self.search_available_layers)
        self.entireLayerButton.clicked.connect(self.handle_entire_layer)
        self.yourObjectButton.clicked.connect(self.enabled_groupbox)
        self.singleObjectButton.clicked.connect(self.handle_single_object)
        self.drawPolygonButton.clicked.connect(self.start_polygon_drawing)
        self.entireRangeButton.clicked.connect(self.handle_entire_wfs)
        self.downloadButton.clicked.connect(self.save_selected_layers)
        
        self.layer_list = []
        self.bbox = None
        self.previous_tool = None
        self.selected_layers = []
        self.tmp_layer = None
        
        self.mMapLayerComboBox.layerChanged.connect(self.update_bbox)

        self.pan_tool = QgsMapToolPan(iface.mapCanvas())
        self.pan_tool.setCursor(Qt.OpenHandCursor)

    def connect_to_service(self):
        service_url = self.serviceAddressEdit.text().strip()
        model = QStandardItemModel()
        try:
            self.crs_options = []
            wfs_service = WebFeatureService(url=service_url, version='2.0.0')
            layers = list(wfs_service.contents.keys())
            for layer_name in list(wfs_service.contents):
                self.crs_options.append([crs.getcode() for crs in
                               wfs_service.contents[layer_name].crsOptions])
                item = QStandardItem(layer_name)
                item.setCheckable(True)
                item.setCheckState(Qt.Unchecked)
                crs_list = []
                for crs in [crs.getcode() for crs in
                               wfs_service.contents[layer_name].crsOptions]:
                    crs_list.append(QStandardItem(crs))
                model.appendRow(item)
            self.populate_layer_list(model)
            self.entireRangeButton.click()
        except Exception:
            CustomMessageBox(self, f"""{tr('Please provide a valid service address.')}""").button_ok()
            return

    def populate_layer_list(self, model):
        self.availableLayer = QSortFilterProxyModel()
        self.availableLayer.setSourceModel(model)
        self.availableLayer.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.availableLayer.sort(1, Qt.AscendingOrder)
        self.listView.setModel(self.availableLayer)
        self.crs_comboBox.clear()
        self.crs_comboBox.addItems(set(unpack_nested_lists(self.crs_options)))
        
    def search_available_layers(self) -> None:
        try:
            self.availableLayer.setFilterFixedString(self.chooseLayerEdit.text())
        except AttributeError:
            pass

    def get_selected_layers(self):
        model = self.listView.model()
        if model:
            source_model = model.sourceModel()
            self.selected_layers.clear()

            for index in range(model.rowCount()):
                source_index = model.mapToSource(model.index(index, 0))
                item = source_model.item(source_index.row())
                if item.checkState() == Qt.Checked:
                    layer_name = item.text()
                    self.selected_layers.append(layer_name)

            if not self.selected_layers:
                CustomMessageBox(self, f"""{tr('Please select at least one layer to add.')}""").button_ok()
                return
        else:
            CustomMessageBox(self, f"""{tr('Please select at least one layer to add.')}""").button_ok()
            return

    def transform_feature_geometry(self, geom: QgsGeometry, input_crs: int,
                               output_crs: int) -> QgsGeometry:
        if input_crs == output_crs:
            return geom
        tmp_geom = geom
        input_crs = QgsCoordinateReferenceSystem(input_crs)
        base_crs = QgsCoordinateReferenceSystem(output_crs)
        tmp_geom.transform(QgsCoordinateTransform(input_crs, base_crs, QgsProject.instance()))
        return tmp_geom

    def create_WFS_layer(self, layer_name, group_name=None):
        service_url = self.serviceAddressEdit.text().strip()
        dsu = QgsDataSourceUri()
        dsu.setParam( 'url', service_url)
        dsu.setParam( 'version', 'auto' )
        dsu.setParam( 'typename', layer_name)
        dsu.setParam( 'IgnoreAxisOrientation ', '1' )
        dsu.setParam('srsname', self.crs_comboBox.currentText())
        layer = QgsVectorLayer(dsu.uri(), layer_name, "WFS")
        if not layer.isValid():
            return None
        if group_name:
            add_map_layer_to_group(layer, group_name, force_create=True)
        else:
            QgsProject.instance().addMapLayer(layer)
        return identify_layer_by_name(layer_name)

    def apply_bbox_to_layer(self, layer):
        if self.bbox:
            bbox_geom = QgsGeometry.fromRect(QgsRectangle(*map(float, self.bbox.split(','))))
            bbox_geom.transform(QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:2180'), layer.crs(),
                                                       QgsProject.instance()))
            request = QgsFeatureRequest().setFilterRect(bbox_geom.boundingBox()).setSubsetOfAttributes([])
            intersected_features = []
            if self.radioButton_bbox.isChecked():
                for feature in identify_layer_by_name(layer.name()).getFeatures(request):
                    if feature.geometry().intersects(bbox_geom):
                        feat = next(identify_layer_by_name(layer.name()).getFeatures(QgsFeatureRequest().setFilterFid(int(feature.id()))))
                        intersected_features.append(feat)
            elif self.radioButton_inter.isChecked():
                intersected_features = []
                if self.singleObjectButton.isChecked():
                    for feature in identify_layer_by_name(layer.name()).getFeatures(request):
                        if feature.geometry().intersects(self.transformed_geom) and \
                            feature.geometry().intersection(self.transformed_geom).area() > 0.1:
                            feat = next(identify_layer_by_name(layer.name()).getFeatures(
                                QgsFeatureRequest().setFilterFid(int(feature.id()))))
                            intersected_features.append(feat)
                elif self.entireLayerButton.isChecked():
                    chosen_layer = self.mMapLayerComboBox.currentLayer()
                    if chosen_layer:
                        for feature in identify_layer_by_name(layer.name()).getFeatures(request):
                            for feat in chosen_layer.getFeatures():
                                if feature.geometry().intersects(feat.geometry()) and \
                                        feature.geometry().intersection(feat.geometry()).area() > 0.1:
                                    feat = next(identify_layer_by_name(layer.name()).getFeatures(
                                        QgsFeatureRequest().setFilterFid(int(feature.id()))))
                                    intersected_features.append(feat)
                    pass
                elif self.yourObjectButton.isChecked():
                    source_layer = identify_layer_by_name(layer.name())
                    for feature in source_layer.getFeatures(request):
                        for feat in self.tmp_layer.getFeatures():
                            if self.tmp_layer.crs() != source_layer.crs():
                                geom = self.transform_feature_geometry(feat.geometry(), self.tmp_layer.crs().postgisSrid(), 2180)
                            else:
                                geom = feat.geometry()
                            if feature.geometry().intersects(geom) and \
                                    feature.geometry().intersection(geom).area() > 0.1:
                                feat = next(identify_layer_by_name(layer.name()).getFeatures(
                                    QgsFeatureRequest().setFilterFid(int(feature.id()))))
                                intersected_features.append(feat)
            crs = layer.crs().authid()
            tmp_layer = QgsVectorLayer(f"Polygon?crs={crs}", f"{layer.name()}_intersected", "memory")
            tmp_layer.dataProvider().addAttributes(layer.dataProvider().fields())
            tmp_layer.updateFields() 
            tmp_layer.dataProvider().addFeatures(intersected_features)
            return tmp_layer
        return layer

    def add_selected_layers_to_map(self):
        self.get_selected_layers()
        total_layers = len(self.selected_layers)
        progress_dialog = ProgressDialog(title=tr('Adding Layers to Map'))
        progress_dialog.start_steped()
        date_formatted = datetime.strftime(datetime.now(), '%Y_%m_%d %H_%M_%S')
        for index, layer_name in enumerate(self.selected_layers, start=1):
            layer = self.create_WFS_layer(layer_name, group_name=date_formatted)
            if layer:
                if not self.entireRangeButton.isChecked():
                    processed_layer = self.apply_bbox_to_layer(layer)
                    if layer != processed_layer:
                        layer.setName(f'{layer.name()} ')
                        add_map_layer_to_group(processed_layer, date_formatted, force_create=True)
            progress_dialog.make_percent_step(step=(100 // total_layers), new_text=f"""{tr('Adding layer')} {index}/{total_layers}""")
        progress_dialog.stop()

    def add_layer_to_qgis(self, layer_name):
        layer = self.create_WFS_layer(layer_name)

        if layer is None or not layer.isValid():
            CustomMessageBox(self,f"""{layer_name} {tr('failed to load!')}""").button_ok()
            return

        if self.bbox:
            bbox_geom = QgsGeometry.fromRect(QgsRectangle(*map(float, self.bbox.split(','))))
            bbox_geom.transform(QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:2180'), layer.crs(), QgsProject.instance()))
            request = QgsFeatureRequest().setFilterRect(bbox_geom.boundingBox()).setSubsetOfAttributes([])
            intersected_features = []

            for feature in layer.getFeatures(request):
                if feature.geometry().intersects(bbox_geom):
                    intersected_features.append(feature)

            crs = layer.crs().authid()
            tmp_layer = QgsVectorLayer(f"Polygon?crs={crs}", f"{layer_name}_intersected", "memory")
            
            tmp_layer.dataProvider().addFeatures(intersected_features)
            layer = tmp_layer

        QgsProject.instance().addMapLayer(layer)
        QgsProject.instance().removeMapLayer(layer.id())

    def update_bbox(self):
        chosen_layer = self.mMapLayerComboBox.currentLayer()
        if chosen_layer:
            extent = chosen_layer.extent()
            geom = QgsGeometry.fromRect(extent)
            transformed_geom  = self.transform_feature_geometry(
                geom, chosen_layer.crs().postgisSrid(), 2180)
            bounding_box = transformed_geom.boundingBox()
            x_min, y_min, x_max, y_max = bounding_box.xMinimum(), bounding_box.yMinimum(), bounding_box.xMaximum(), bounding_box.yMaximum()
            self.bbox = f"{x_min}, {y_min}, {x_max}, {y_max}"

    def handle_entire_layer(self):
        QgsProject.instance().removeMapLayer(self.tmp_layer)
        self.tmp_layer = None
        iface.mapCanvas().refresh()
        self.groupBox_3.setEnabled(True)
        self.update_bbox()

    def handle_single_object(self):
        QgsProject.instance().removeMapLayer(self.tmp_layer)
        self.tmp_layer = None
        iface.mapCanvas().refresh()
        self.groupBox_3.setEnabled(True)
        if self.singleObjectButton.isChecked():
            try:
                if not self.tmp_layer:
                    self._create_tmp_layer()
            except:
                self._create_tmp_layer()
            self.previous_tool = iface.mapCanvas().mapTool()
            iface.mainWindow().activateWindow()
            self.mapTool = IdentifyGeometry(iface.mapCanvas())
            self.mapTool.geomIdentified.connect(self.process_selected_object)
            iface.mapCanvas().setMapTool(self.mapTool)
        else:
            self.mapTool.deactivate()
            iface.mapCanvas().setMapTool(self.pan_tool)

    def process_selected_object(self, results):
        if not results:
            CustomMessageBox(self, tr('Failed to locate object!')).button_ok()
            self.activateWindow()
            return
        feature = results[0].mFeature
        layer = results[0].mLayer
        geometry = feature.geometry()
        self.transformed_geom = self.transform_feature_geometry(geometry, layer.crs().postgisSrid(), 2180)
        bounding_box = self.transformed_geom.boundingBox()
        x_min, y_min, x_max, y_max = bounding_box.xMinimum(), bounding_box.yMinimum(), bounding_box.xMaximum(), bounding_box.yMaximum()
        self.bbox = f"{x_min}, {y_min}, {x_max}, {y_max}"

        self.tmp_layer.startEditing()
        feat = QgsFeature()
        feat.setGeometry(self.transformed_geom)
        pr = self.tmp_layer.dataProvider()
        QApplication.processEvents()
        pr.addFeatures([feat])
        self.tmp_layer.commitChanges()
        self.tmp_layer.triggerRepaint()

        iface.mapCanvas().setMapTool(self.pan_tool)
        self.singleObjectButton.setChecked(False)
        self.mapTool.deactivate()
        self.activateWindow()

    def _create_tmp_layer(self):
        TMP_LAYER_NAME = "Temporary Layer"
        crs = iface.mapCanvas().mapSettings().destinationCrs().authid()
        self.tmp_layer = TmpCopyLayer(
            f"multipolygon?crs={crs}",
            TMP_LAYER_NAME,
            "memory")
        fields = [
            QgsField("ID", QVariant.Int)
        ]
        self.tmp_layer.set_fields(fields)
        QgsProject.instance().addMapLayer(self.tmp_layer)
        return self.tmp_layer

    def enabled_groupbox(self):
        QgsProject.instance().removeMapLayer(self.tmp_layer)
        self.tmp_layer = None
        iface.mapCanvas().refresh()
        self.groupBox_3.setEnabled(True)

    def start_polygon_drawing(self):
        if self.yourObjectButton.isChecked():
            self.groupBox_3.setEnabled(True)
            try:
                if not self.tmp_layer:
                    self._create_tmp_layer()
            except:
                self._create_tmp_layer()
            iface.setActiveLayer(self.tmp_layer)
            self.tmp_layer.startEditing()
            self.draw_geom()

    def draw_geom(self):
        self.canvas = iface.mapCanvas()
        iface.mainWindow().activateWindow()
        layer = self.tmp_layer
        layer.featureAdded.connect(self.add_drawed_geom)
        form_config = self.tmp_layer.editFormConfig()
        try:
            form_config.setSuppress(1)
        except:
            form_config.setSuppress(QgsEditFormConfig.SuppressOn)
        self.tmp_layer.setEditFormConfig(form_config)
        iface.actionAddFeature().trigger()
        
    def add_drawed_geom(self):
        geom_list = []
        for feat in self.tmp_layer.getFeatures():
            geom_list.append(feat.geometry())
        if geom_list:
            combined_geom = combine_geoms(geom_list)
            combined_geom.convertToMultiType()
        transformed_geom  = self.transform_feature_geometry(
            combined_geom, self.tmp_layer.crs().postgisSrid(), 2180)
        bounding_box = transformed_geom.boundingBox()
        x_min, y_min, x_max, y_max = bounding_box.xMinimum(), bounding_box.yMinimum(), bounding_box.xMaximum(), bounding_box.yMaximum()
        self.bbox = f"{x_min}, {y_min}, {x_max}, {y_max}"
        iface.mapCanvas().setMapTool(self.pan_tool)
        try:
            self.tmp_layer.featureAdded.disconnect()
        except TypeError:
            pass
        self.tmp_layer.commitChanges()
        self.tmp_layer.triggerRepaint()
        self.activateWindow()
        self.yourObjectButton.setChecked(False)

    def handle_entire_wfs(self):
        QgsProject.instance().removeMapLayer(self.tmp_layer)
        self.tmp_layer = None
        iface.mapCanvas().refresh()
        self.bbox = None
        self.groupBox_3.setEnabled(False)

    def add_results_to_map(self):
        progress_dialog = ProgressDialog(title=tr('Adding Results to Map'))
        progress_dialog.start()
        date_formatted = datetime.strftime(datetime.now(), '%Y_%m_%d %H_%M_%S')
        for layer_path, layer_name in self.layer_dir:
            layer_from_path = QgsVectorLayer(layer_path, layer_name, "ogr")
            add_map_layer_to_group(layer_from_path, date_formatted, force_create=True)
        progress_dialog.stop()

    def handle_save(self, format):
        self.get_selected_layers()
        if not self.selected_layers:
            return
        for i, layer_name in enumerate(self.selected_layers):
            self.save_layer_as(layer_name, format)

    def save_layer_as(self, layer_name, format):
        options = QFileDialog.Options()
        file_filter = {
            'shp': "Shapefile (*.shp)",
            'xlsx': "Excel (*.xlsx)",
            'csv': "CSV (*.csv)"
        }.get(format, "All Files (*)")
        date_formatted = datetime.strftime(datetime.now(), '%Y_%m_%d %H_%M_%S')
        file_path, _ = QFileDialog.getSaveFileName(self, tr("Save Data"), f"{layer_name.split(':')[1]} {date_formatted}.{format}", file_filter, options=options)
        if not file_path:
            return
        progress = get_simple_progressbar(
            0, txt=tr('Saving Layers...'))
        progress.show()
        QApplication.processEvents()
        layer = self.create_WFS_layer(layer_name)
        if not layer.isValid():
            CustomMessageBox(self, f"""{layer_name} {tr('failed to load!')} """).button_ok()
            return
        QApplication.processEvents()
        processed_layer = self.apply_bbox_to_layer(layer)
        crs = QgsProject.instance().crs()
        save_options = QgsVectorFileWriter.SaveVectorOptions()
        save_options.driverName = {
            'shp': 'ESRI Shapefile',
            'xlsx': 'XLSX',
            'csv': 'CSV'
        }.get(format, 'ESRI Shapefile')
        save_options.fileEncoding = 'utf-8'
        save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        save_options.ct = QgsCoordinateTransform(QgsCoordinateReferenceSystem(self.crs_comboBox.currentText()), crs, QgsProject.instance())
        QApplication.processEvents()
        error = QgsVectorFileWriter.writeAsVectorFormatV2(processed_layer, file_path, QgsProject.instance().transformContext(), save_options)
        if error == QgsVectorFileWriter.NoError or error[0] == 0:
            self.layer_dir.append((file_path, f"{layer_name.split(':')[1]} {date_formatted}"))
            CustomMessageBox(self, f"""{tr('Layer saved successfully')} {file_path}""").button_ok()
        else:
            CustomMessageBox(self, f"""{tr('Failed to save layer')} {file_path}.""").button_ok()
        QgsProject.instance().removeMapLayer(layer.id())
        iface.mapCanvas().refresh()
        progress.close()

    def save_selected_layers(self):
        formats = []
        self.layer_dir = []
        if self.shpCheckBox.isChecked():
            formats.append('shp')
        if self.xslCheckBox.isChecked():
            formats.append('xlsx')
        if self.csvCheckBox.isChecked():
            formats.append('csv')
        if not formats:
            CustomMessageBox(self, f"""{tr('Please select at least one format to save.')}""").button_ok()
            return
        self.get_selected_layers()
        if not self.selected_layers:
            return
        for format in formats:
            self.handle_save(format)
        if self.addResultsCheckBox.isChecked():
            self.add_results_to_map()
        QgsProject.instance().removeMapLayer(self.tmp_layer)
        self.tmp_layer = None
        iface.mapCanvas().refresh()

    def run(self):
        if not self.isActiveWindow():
            self.show()
            self.activateWindow()
            self.listlayer_comboBox.hide()
        else:
            self.show()
            self.exec_()