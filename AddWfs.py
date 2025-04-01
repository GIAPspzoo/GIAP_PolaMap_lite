# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
from qgis.PyQt import QtWidgets, uic
from qgis.core import (QgsVectorLayer, QgsProject, QgsGeometry,
                       QgsRectangle, QgsVectorFileWriter, QgsDataSourceUri, 
                       QgsCoordinateReferenceSystem, QgsField, QgsEditFormConfig, 
                       QgsCoordinateTransform, QgsFeatureRequest)
from datetime import datetime
from qgis.utils import iface
from qgis.PyQt.QtWidgets import QFileDialog, QApplication
from qgis.PyQt.QtCore import Qt, QVariant, QSortFilterProxyModel
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem
from owslib.wfs import WebFeatureService

from .utils import tr, project, ProgressDialog, TmpCopyLayer, IdentifyGeometry, get_simple_progressbar, \
    CustomMessageBox, add_map_layer_to_group

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'wfs_dialog.ui'))


def identify_layer_by_name(layername_to_find):
    for layer in list(project.mapLayers().values()):
        if layer.name() == layername_to_find:
            return layer


class AddWfsTool(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(AddWfsTool, self).__init__(parent)
        self.setupUi(self)

        self.connectButton.clicked.connect(self.connect_to_service)
        self.addToMapButton.clicked.connect(self.add_selected_layers_to_map)
        self.chooseLayerEdit.textChanged.connect(self.search_available_layers)
        self.entireLayerButton.clicked.connect(self.handle_entire_layer)
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

    def connect_to_service(self):
        service_url = self.serviceAddressEdit.text().strip()
        try:
            wfs = WebFeatureService(url=service_url, version='2.0.0')
            layers = list(wfs.contents.keys())
            self.populate_layer_list(layers)
        except Exception:
            CustomMessageBox(self, f"""{tr('Please provide a valid service address.')}""").button_ok()
            return

    def populate_layer_list(self, layers):
        model = QStandardItemModel()
        for layer in layers:
            item = QStandardItem(layer)
            item.setCheckable(True)
            item.setCheckState(Qt.Unchecked)
            model.appendRow(item)
        self.availableLayer = QSortFilterProxyModel()
        self.availableLayer.setSourceModel(model)
        self.availableLayer.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.availableLayer.sort(1, Qt.AscendingOrder)
        self.listView.setModel(self.availableLayer)
        
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
        dsu.setParam('srsname', 'EPSG:2180')
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
            bbox_geom.transform(QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:2180'), layer.crs(), QgsProject.instance()))
            request = QgsFeatureRequest().setFilterRect(bbox_geom.boundingBox()).setSubsetOfAttributes([])
            intersected_features = []
            for feature in identify_layer_by_name(layer.name()).getFeatures(request):
                if feature.geometry().intersects(bbox_geom):
                    feat = next(identify_layer_by_name(layer.name()).getFeatures(QgsFeatureRequest().setFilterFid(int(feature.id()))))
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
        date_formatted = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
        for index, layer_name in enumerate(self.selected_layers, start=1):
            layer = self.create_WFS_layer(layer_name, group_name=date_formatted)
            if layer:
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
        self.update_bbox()

    def handle_single_object(self):
        if self.singleObjectButton.isChecked():
            self.previous_tool = iface.mapCanvas().mapTool()
            iface.mainWindow().activateWindow()
            self.mapTool = IdentifyGeometry(iface.mapCanvas())
            self.mapTool.geomIdentified.connect(self.process_selected_object)
            iface.mapCanvas().setMapTool(self.mapTool)
        else:
            self.mapTool.deactivate()
            iface.mapCanvas().setMapTool(self.previous_tool)

    def process_selected_object(self, results):
        if not results:
            CustomMessageBox(self, tr('Failed to locate object!')).button_ok()
            self.activateWindow()
            return
        feature = results[0].mFeature
        layer = results[0].mLayer
        geometry = feature.geometry()
        transformed_geom = self.transform_feature_geometry(geometry, layer.crs().postgisSrid(), 2180)
        bounding_box = transformed_geom.boundingBox()
        x_min, y_min, x_max, y_max = bounding_box.xMinimum(), bounding_box.yMinimum(), bounding_box.xMaximum(), bounding_box.yMaximum()
        self.bbox = f"{x_min}, {y_min}, {x_max}, {y_max}"
        iface.mapCanvas().setMapTool(self.previous_tool)
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
        
    def start_polygon_drawing(self):
        if self.yourObjectButton.isChecked():
            if not self.tmp_layer:
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
        
    def add_drawed_geom(self, point):
        geom = next(self.tmp_layer.getFeatures(QgsFeatureRequest().setFilterFid(point))).geometry()
        transformed_geom  = self.transform_feature_geometry(
            geom, self.tmp_layer.crs().postgisSrid(), 2180)
        bounding_box = transformed_geom.boundingBox()
        x_min, y_min, x_max, y_max = bounding_box.xMinimum(), bounding_box.yMinimum(), bounding_box.xMaximum(), bounding_box.yMaximum()
        self.bbox = f"{x_min}, {y_min}, {x_max}, {y_max}"
        iface.mapCanvas().setMapTool(self.previous_tool)
        self.activateWindow()
        self.yourObjectButton.setChecked(False)

    def handle_entire_wfs(self):
        self.bbox = None

    def add_results_to_map(self):
        progress_dialog = ProgressDialog(title=tr('Adding Results to Map'))
        progress_dialog.start()
        date_formatted = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
        for layer_path, layer_name in self.layer_dir:
            layer_from_path = QgsVectorLayer(layer_path, layer_name, "ogr")
            add_map_layer_to_group(layer_from_path, date_formatted, force_create=True)
        progress_dialog.stop()

        # self.get_selected_layers()
        # layers = self.selected_layers
        # progress_dialog = ProgressDialog(title='Adding Results to Map')
        # progress_dialog.start()
        # if self.entireRangeButton.isChecked():
        #     for i, layer_name in enumerate(layers):
        #         layer = self.create_WFS_layer(layer_name)
        #         if layer:
        #             QgsProject.instance().addMapLayer(layer)
        #             progress_dialog.make_percent_step(step=int((i + 10) / len(layers) * 100), new_text=f'Adding layer: {layer_name}')
        #     progress_dialog.stop()
        # else:
        #     if self.entireLayerButton.isChecked():
        #         if not self.bbox:
        #             CustomMessageBox(self,
        #                              f"""{tr('Please determine the entire range to determine the bounding box.')}""").button_ok()
        #             return
        #     elif self.singleObjectButton.isChecked():
        #         if not self.bbox:
        #             CustomMessageBox(self,
        #                              f"""{tr('Please select a single object to determine the bounding box.')}""").button_ok()
        #             return
        #     elif self.yourObjectButton.isChecked():
        #         if not self.bbox:
        #             CustomMessageBox(self, f"""{tr('Please draw a polygon to determine the bounding box.')}""").button_ok()
        #             return
        #     for i, layer_name in enumerate(layers):
        #         layer = self.create_WFS_layer(layer_name)
        #         if layer:
        #             processed_layer = self.apply_bbox_to_layer(layer)
        #             QgsProject.instance().addMapLayer(processed_layer)
        #             QgsProject.instance().removeMapLayer(layer.id())
        #             progress_dialog.make_percent_step(step=int((i + 10) / len(layers) * 100), new_text=f'Processing layer: {layer_name}')
        #     progress_dialog.stop()

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
        date_formatted = datetime.strftime(datetime.now(), '%Y-%m-%d %H_%M_%S')
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
        save_options.ct = QgsCoordinateTransform(crs, crs, QgsProject.instance())
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

    def run(self):
        self.show()
        self.exec_()
