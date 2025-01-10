# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
from qgis.PyQt import QtWidgets, uic
from qgis.core import (QgsVectorLayer, QgsProject, QgsFeature, QgsGeometry, 
                       QgsRectangle, QgsVectorFileWriter, QgsDataSourceUri, 
                       QgsCoordinateReferenceSystem, QgsField, QgsEditFormConfig, 
                       QgsCoordinateTransform, QgsPointXY, QgsWkbTypes, QgsFields, 
                       QgsFeatureRequest)
from qgis.gui import QgsMapCanvas, QgsMapToolEmitPoint, QgsMapToolIdentifyFeature
from qgis.utils import iface
from PyQt5.QtWidgets import QListView, QMessageBox, QFileDialog, QCheckBox
from PyQt5.QtCore import QStringListModel, Qt, pyqtSignal, QVariant, QSortFilterProxyModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from owslib.wfs import WebFeatureService

from .WFS_pomocnicze import TmpCopyLayer, IdentifyGeometry
from .SectionManager.CustomSectionManager import CustomSectionManager

from .utils import tr, add_map_layer_to_group, search_group_name, project, ProgressDialog



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
        
        # self.connectButton.setToolTip(tr("Connect"))
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
        # print(service_url)
        try:
            wfs = WebFeatureService(url=service_url, version='1.1.0')
            layers = list(wfs.contents.keys())
            self.populate_layer_list(layers)
        except Exception:
            QMessageBox.warning(self, "Unable to connect to the WFS service.", "Please provide a valid service address.")
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
        self.availableLayer.setFilterFixedString(self.chooseLayerEdit.text())
        
    
    def get_selected_layers(self):
        model = self.listView.model()
        source_model = model.sourceModel()
        self.selected_layers.clear()
        
        for index in range(model.rowCount()):
            source_index = model.mapToSource(model.index(index, 0))
            item = source_model.item(source_index.row())
            if item.checkState() == Qt.Checked:
                layer_name = item.text()
                self.selected_layers.append(layer_name)
        
        if not self.selected_layers:
            QMessageBox.warning(self, "No layers selected", "Please select at least one layer to add.")
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
    
    
    def create_WFS_layer(self, layer_name):
        service_url = self.serviceAddressEdit.text().strip()
        dsu = QgsDataSourceUri()
        dsu.setParam( 'url', service_url)
        dsu.setParam( 'version', '2.0.0' )
        dsu.setParam( 'typename', layer_name )
        dsu.setParam( 'IgnoreAxisOrientation ', '1' )
        dsu.setParam( 'srid', "4326")
        
        layer = QgsVectorLayer(dsu.uri(), layer_name, "WFS")

        if not layer.isValid():
            return None

        # print("uri")
        # print(dsu.uri())
        # print()
        
        QgsProject.instance().addMapLayer(layer)

        return identify_layer_by_name(layer_name)
    
    
    def apply_bbox_to_layer(self, layer):
        if self.bbox:
            bbox_geom = QgsGeometry.fromRect(QgsRectangle(*map(float, self.bbox.split(','))))
            bbox_geom.transform(QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'), layer.crs(), QgsProject.instance()))

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
    
    
# wersja z intersectem
#####################################################################
    # def apply_bbox_to_layer(self, base_layer, wfs_layer):
        # new_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "intersecting_features", "memory")
        # new_layer_data = new_layer.dataProvider()

        # new_layer_data.addAttributes(wfs_layer.fields())
        # new_layer.updateFields()

        # for feature in wfs_layer.getFeatures():
        #     wfs_geom = feature.geometry()
            
        #     intersects = False
        #     for base_feature in base_layer.getFeatures():
        #         base_geom = base_feature.geometry()
        #         if wfs_geom.intersects(base_geom):
        #             intersects = True
        #             break

        #     if intersects:
        #         new_layer_data.addFeature(feature)
        
        # # QgsProject.instance().addMapLayer(new_layer)
        # return new_layer
#####################################################################
    


    def add_selected_layers_to_map(self):
        self.get_selected_layers()
        
        for layer_name in self.selected_layers:
            layer = self.create_WFS_layer(layer_name)
            if layer:
                processed_layer = self.apply_bbox_to_layer(layer)
                QgsProject.instance().addMapLayer(processed_layer)
        QgsProject.instance().removeMapLayer(layer.id())

# wersja z progres barem 
################################################################################
        # self.get_selected_layers()
        # total_layers = len(self.selected_layers)
        # progress_dialog = ProgressDialog(title='Adding Layers to Map')
        # progress_dialog.start_steped()

        # for index, layer_name in enumerate(self.selected_layers, start=1):
        #     layer = self.create_WFS_layer(layer_name)
        #     if layer:
        #         processed_layer = self.apply_bbox_to_layer(layer)
        #         QgsProject.instance().addMapLayer(processed_layer)
        #     QgsProject.instance().removeMapLayer(layer.id())
        #     progress_dialog.make_percent_step(step=(100 // total_layers), new_text=f"Adding layer {index}/{total_layers}")
        
        # progress_dialog.stop()
################################################################################


    def add_layer_to_qgis(self, layer_name):
        layer = self.create_WFS_layer(layer_name)

        if layer is None or not layer.isValid():
            QMessageBox.warning(self, "Layer failed to load", f"{layer_name} failed to load!")
            return

        if self.bbox:
            
            bbox_geom = QgsGeometry.fromRect(QgsRectangle(*map(float, self.bbox.split(','))))
            bbox_geom.transform(QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'), layer.crs(), QgsProject.instance()))

            request = QgsFeatureRequest().setFilterRect(bbox_geom.boundingBox()).setSubsetOfAttributes([])
            intersected_features = []

            for feature in layer.getFeatures(request):
                if feature.geometry().intersects(bbox_geom):
                    intersected_features.append(feature)

            crs = layer.crs().authid()
            tmp_layer = QgsVectorLayer(f"Polygon?crs={crs}", f"{layer_name}_intersected", "memory")
            
            tmp_layer.dataProvider().addFeatures(intersected_features)
            layer = tmp_layer
            # print(f"layer {layer} created")

        QgsProject.instance().addMapLayer(layer)
        QgsProject.instance().removeMapLayer(layer.id())
        # print(f"Layer {layer_name} added to the QGIS project.")



    def update_bbox(self):
        chosen_layer = self.mMapLayerComboBox.currentLayer()
                
        extent = chosen_layer.extent()
        geom = QgsGeometry.fromRect(extent)
        
        transformed_geom  = self.transform_feature_geometry(
            geom, chosen_layer.crs().postgisSrid(), 4326)
        
        bounding_box = transformed_geom.boundingBox()
        x_min, y_min, x_max, y_max = bounding_box.xMinimum(), bounding_box.yMinimum(), bounding_box.xMaximum(), bounding_box.yMaximum()
        self.bbox = f"{x_min}, {y_min}, {x_max}, {y_max}"
        
        # print("update_bbox")
        # print(f"Layer bbox updated to: {self.bbox}")
        # print()
        
        # self.tmp_layer = chosen_layer
        


    def handle_entire_layer(self):
        self.update_bbox()
        # print(f"Layer bbox: {self.bbox}")


    def handle_single_object(self):
        if self.singleObjectButton.isChecked():
            self.previous_tool = iface.mapCanvas().mapTool()
            
            self.mapTool = IdentifyGeometry(iface.mapCanvas())
            self.mapTool.geomIdentified.connect(self.process_selected_object) 
            
            iface.mapCanvas().setMapTool(self.mapTool)
        else:
            self.mapTool.deactivate()
            iface.mapCanvas().setMapTool(self.previous_tool)

    def process_selected_object(self, results):
        
        if not results:
            return
        feature = results[0].mFeature
        layer = results[0].mLayer
        
        geometry = feature.geometry()
        
        transformed_geom = self.transform_feature_geometry(geometry, layer.crs().postgisSrid(), 4326)
        
        bounding_box = transformed_geom.boundingBox()
        x_min, y_min, x_max, y_max = bounding_box.xMinimum(), bounding_box.yMinimum(), bounding_box.xMaximum(), bounding_box.yMaximum()
        self.bbox = f"{x_min}, {y_min}, {x_max}, {y_max}"
        
        # print("process_selected_object")
        # print(f"Layer bbox updated to: {self.bbox}")
        # print()
        
        iface.mapCanvas().setMapTool(self.previous_tool)
        self.singleObjectButton.setChecked(False)
        self.mapTool.deactivate()
        
        # self.tmp_layer = layer
        
    
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
        
        # print("DRAWN POLYGON")
        geom = next(self.tmp_layer.getFeatures(QgsFeatureRequest().setFilterFid(point))).geometry()
        
        transformed_geom  = self.transform_feature_geometry(
            geom, self.tmp_layer.crs().postgisSrid(), 4326)
        
        bounding_box = transformed_geom.boundingBox()
        x_min, y_min, x_max, y_max = bounding_box.xMinimum(), bounding_box.yMinimum(), bounding_box.xMaximum(), bounding_box.yMaximum()
        self.bbox = f"{x_min}, {y_min}, {x_max}, {y_max}"
        
        # print(self.bbox)
        
        iface.mapCanvas().setMapTool(self.previous_tool)
        self.yourObjectButton.setChecked(False)
        


    def handle_entire_wfs(self):
        self.bbox = None
    

    def add_results_to_map(self):
        self.get_selected_layers()
        layers = self.selected_layers
        
        # progress_dialog = ProgressDialog(title='Adding Results to Map')
        # progress_dialog.start()
        
        if self.entireRangeButton.isChecked():
            for layer_name in layers:
                layer = self.create_WFS_layer(layer_name)
                if layer:
                    QgsProject.instance().addMapLayer(layer)
            QgsProject.instance().removeMapLayer(layer.id())
            
# wersja z progres barem
#########################################################################
            # for i, layer_name in enumerate(layers):
            #     layer = self.create_WFS_layer(layer_name)
            #     if layer:
            #         QgsProject.instance().addMapLayer(layer)
            #         QgsProject.instance().removeMapLayer(layer.id())
            #         progress_dialog.make_percent_step(step=int((i + 10) / len(layers) * 100), new_text=f'Adding layer: {layer_name}')
            # progress_dialog.stop()
#########################################################################            
        else:
            if self.entireLayerButton.isChecked():
                if not self.bbox:
                    QMessageBox.warning(self, "No bounding box", "Please determine the entire range to determine the bounding box.")
                    return
                base_layer = self.tmp_layer
                
            elif self.singleObjectButton.isChecked():
                if not self.bbox:
                    QMessageBox.warning(self, "No bounding box", "Please select a single object to determine the bounding box.")
                    return
                base_layer = self.tmp_layer
                
            elif self.yourObjectButton.isChecked():
                if not self.bbox:
                    QMessageBox.warning(self, "No bounding box", "Please draw a polygon to determine the bounding box.")
                    return
                base_layer = self.tmp_layer
                
            for layer_name in layers:
                layer = self.create_WFS_layer(layer_name)
                if layer:
                    processed_layer = self.apply_bbox_to_layer(layer)
                    QgsProject.instance().addMapLayer(processed_layer)
                    QgsProject.instance().removeMapLayer(layer.id())
                    # print(f"Layer {layer_name} processed and WFS layer removed.")

# wersja z progres barem
#########################################################################
            #     if layer:
            #         processed_layer = self.apply_bbox_to_layer(base_layer, layer)
            #         QgsProject.instance().addMapLayer(processed_layer)
            #         QgsProject.instance().removeMapLayer(layer.id())
            #         progress_dialog.make_percent_step(step=int((i + 10) / len(layers) * 100), new_text=f'Processing layer: {layer_name}')
            # progress_dialog.stop()
#########################################################################            

    
    
    def handle_save(self, format):
        self.get_selected_layers()
        
        if not self.selected_layers:
            return
    
        for layer_name in self.selected_layers:
            self.save_layer_as(layer_name, format)

# wersja z progres barem
#########################################################################
        # progress_dialog = ProgressDialog(title='Saving Layers')
        # progress_dialog.start()
        
        # for i, layer_name in enumerate(self.selected_layers):
        #     self.save_layer_as(layer_name, format)
        #     progress_dialog.make_percent_step(step=int((i + 10) / len(self.selected_layers) * 100), new_text=f'Saving layer: {layer_name}')
        
        # progress_dialog.stop()
#########################################################################            

# wersja z progres barem
#########################################################################
    # def save_layer_as(self, layer_name, format):
    #     options = QFileDialog.Options()
    #     file_filter = {
    #         'shp': "Shapefile (*.shp)",
    #         'xsl': "Excel (*.xlsx)",
    #         'csv': "CSV (*.csv)"
    #     }.get(format, "All Files (*)")

    #     file_path, _ = QFileDialog.getSaveFileName(self, "Save Data", f"{layer_name}.{format}", file_filter, options=options)
    #     if not file_path:
    #         return

    #     layer = self.create_WFS_layer(layer_name)

    #     if not layer.isValid():
    #         QMessageBox.warning(self, "Layer failed to load", f"{layer_name} failed to load!")
    #         return

    #     base_layer = self.tmp_layer

    #     processed_layer = self.apply_bbox_to_layer(base_layer, layer)
    #     crs = QgsProject.instance().crs()

    #     save_options = QgsVectorFileWriter.SaveVectorOptions()
    #     save_options.driverName = {
    #         'shp': 'ESRI Shapefile',
    #         'xsl': 'XLSX',
    #         'csv': 'CSV'
    #     }.get(format, 'ESRI Shapefile')

    #     save_options.fileEncoding = 'utf-8'
    #     save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
    #     save_options.ct = QgsCoordinateTransform(crs, crs, QgsProject.instance())

    #     progress_dialog = ProgressDialog(title=f'Saving Layer {layer_name}')
    #     progress_dialog.start_steped()

    #     error = QgsVectorFileWriter.writeAsVectorFormatV3(processed_layer, file_path, QgsProject.instance().transformContext(), save_options)
        
    #     progress_dialog.make_percent_step(step=100)
    #     progress_dialog.stop()

    #     if error == QgsVectorFileWriter.NoError or error[0] == 0:
    #         QMessageBox.information(self, "Success", f"Layer {layer_name} saved successfully as {format}.")
    #     else:
    #         QMessageBox.warning(self, "Error", f"Failed to save layer {layer_name}.")
        
    #     QgsProject.instance().removeMapLayer(layer.id())
#########################################################################

    def save_layer_as(self, layer_name, format):
        options = QFileDialog.Options()
        file_filter = {
            'shp': "Shapefile (*.shp)",
            'xsl': "Excel (*.xlsx)",
            'csv': "CSV (*.csv)"
        }.get(format, "All Files (*)")
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Data", f"{layer_name}.{format}", file_filter, options=options)
        if not file_path:
            return

        layer = self.create_WFS_layer(layer_name)
        
        if not layer.isValid():
            QMessageBox.warning(self, "Layer failed to load", f"{layer_name} failed to load!")
            return
        
        base_layer = self.tmp_layer
                    
        processed_layer = self.apply_bbox_to_layer(layer)
        crs = QgsProject.instance().crs()
        
        save_options = QgsVectorFileWriter.SaveVectorOptions()
        save_options.driverName = {
            'shp': 'ESRI Shapefile',
            'xsl': 'XLSX',
            'csv': 'CSV'
        }.get(format, 'ESRI Shapefile')
        
        save_options.fileEncoding = 'utf-8'
        save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        save_options.ct = QgsCoordinateTransform(crs, crs, QgsProject.instance())
        
        error = QgsVectorFileWriter.writeAsVectorFormatV3(processed_layer, file_path, QgsProject.instance().transformContext(), save_options)
        
        # print(error)
                
        if error == QgsVectorFileWriter.NoError or error[0] == 0:
            QMessageBox.information(self, "Success", f"Layer {layer_name} saved successfully as {format}.")
        else:
            QMessageBox.warning(self, "Error", f"Failed to save layer {layer_name}.")
        
        QgsProject.instance().removeMapLayer(layer.id())
        
        
    def save_selected_layers(self):
        formats = []
        if self.shpCheckBox.isChecked():
            formats.append('shp')
        if self.xslCheckBox.isChecked():
            formats.append('xsl')
        if self.csvCheckBox.isChecked():
            formats.append('csv')
        
        if not formats:
            QMessageBox.warning(self, "No formats selected", "Please select at least one format to save.")
            return
        
        for format in formats:
            self.handle_save(format)
        
        if self.addResultsCheckBox.isChecked():
            self.add_results_to_map()
        
            
    def run(self):
        self.show()
        self.exec_()
