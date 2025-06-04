from typing import Dict
import re

import requests
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QApplication
from owslib.wfs import WebFeatureService
from owslib.wms import WebMapService
from owslib.wmts import WebMapTileService, ServiceException
from qgis.core import QgsLayerTreeGroup, QgsLayerTree, QgsRasterLayer, QgsVectorLayer, QgsProject, QgsLayerTreeLayer
from . import online_layers_dialog
from .utils import get_wms_config

from ..utils import CustomMessageBox, get_simple_progressbar, tr

WFS_EXAMPLE_SRC = "pagingEnabled='true' preferCoordinatesForWfsT11='false' " \
                  "srsname='{crs}' typename='{table_name}' url='{url}' version='auto' OGC WFS (Web Feature Service)"
WMS_EXAMPLE_SRC = "contextualWMSLegend=0&crs={crs}&dpiMode=7&featureCount=10&format={image_type}" \
                  "&layers={table_name}&styles&url={url}"
WMTS_EXAMPLE_SRC = "contextualWMSLegend=0&crs={crs}&dpiMode=7&featureCount=10&format={image_type}" \
                   "&layers={table_name}&styles=default&tileMatrixSet={crs}&url={url}"

WMTS_ARC_EXAMPLE_SRC = "contextualWMSLegend=0&crs={crs}&dpiMode=7&featureCount=10&format={image_type}" \
                       "&layers={table_name}&styles=default&tileMatrixSet={type}&url={url}"

project = QgsProject.instance()
root = project.layerTreeRoot()
temp_group_name = "Dane dodatkowe - temp"


class OrtoActionService(QObject):
    orto_added = pyqtSignal()
    orto_group_added = pyqtSignal()

    def __init__(self, action, url, name):
        QObject.__init__(self)
        self.button = action
        self.url = url
        self.name = name
        self.data = get_wms_config()
        try:
            self.group_name = self.data[self.name][1]
        except KeyError:
            self.group_name = None
            CustomMessageBox(None, tr('Failed to load layer'))
        self.button.triggered.connect(self.add_to_map)
        project.layerWillBeRemoved.connect(self.remove_groups_before_close)

    def __add_orto_group(self, parent_group: QgsLayerTreeGroup or QgsLayerTree = root) -> QgsLayerTreeGroup:
        if self.group_name:
            if parent_group:
                parent_group.addGroup(self.group_name)
                group = parent_group.findGroup(self.group_name)
                self.orto_group_added.emit()
                return group

    def add_to_map(self) -> None:
        rlayer = QgsRasterLayer(self.url, self.name, 'wms')
        if not rlayer.isValid():
            layers = []
            self.open_online_layers_dialog(layers)
            if self.group_name:
                self.group_name = [self.data[self.name][1], self.name]
            else:
                self.group_name = temp_group_name
            if layers:
                self.add_groups_to_project(layers)
        else:
            if not self.group_name:
                self.group_name = temp_group_name
            group = root.findGroup(self.group_name)
            if not group:
                group = self.__add_orto_group()
            if not self._orto_already_in_project():
                self.add_layer_to_group(rlayer, group)

    def open_online_layers_dialog(self, layers_list: list) -> None:
        progress = get_simple_progressbar(
            0, txt=tr('Loading layers...'))
        progress.show()
        QApplication.processEvents()
        online_layers = None
        if 'wfs' in self.url.lower():
            layers_type = 'WFS'
            online_layers = get_wfs_layers(self.url)
        elif 'arcgis' in self.url:
            layers_type = 'WMS'
            online_layers = get_wmts_arc_layers(self.url)
        elif 'wmts' in self.url.lower():
            layers_type = 'WMS'
            online_layers = get_wmts_layers(self.url)
        else:
            layers_type = 'WMS'
            online_layers = get_wms_layers(self.url)
        if not online_layers:
            progress.close()
            CustomMessageBox(
                None, f'''{tr('Cannot be added')} {self.name}.''').button_ok()
            return
        group = root.findGroup(self.name)
        if not group:
            checked_list = []
        else:
            checked_list = [layer.name() for layer in group.children()]
        select_dlg = online_layers_dialog.OnlineLayersDialog(online_layers, checked_list)
        progress.close()
        select_dlg.exec()
        diff_layers = [layer for layer in checked_list if layer not in select_dlg.checked_list]
        for layer in diff_layers:
            for lyr in project.mapLayersByName(layer):
                if root.findLayer(lyr).parent().name() == self.name:
                    project.removeMapLayer(lyr)
        for lyr_name in select_dlg.checked_list:
            lyr_uri = online_layers[lyr_name]
            if layers_type == 'WFS':
                layers_list.append(QgsVectorLayer(
                    lyr_uri, lyr_name, layers_type))
            else:
                if lyr_name not in checked_list:
                    layers_list.append(QgsRasterLayer(
                        lyr_uri, lyr_name, layers_type))
            QApplication.processEvents()

    def _orto_already_in_project(self) -> bool or None:
        layers = project.mapLayersByName(self.name)
        group = root.findGroup(self.name)
        if layers:
            for layer in layers:
                if (root.findLayer(layer).parent().name() == self.group_name and
                        layer.source() == self.url):
                    return True
        if group:
            if group.parent().name() == self.group_name:
                return True

    def add_groups_to_project(self, layers_list: list) -> None:
        parent_group = root
        if isinstance(self.group_name, list):
            for group_name in self.group_name:
                self.group_name = group_name
                parent_grp = root
                group = parent_grp.findGroup(self.group_name)
                if not group:
                    group = self.__add_orto_group(parent_grp)
                parent_group = group
                self.group_name = self.name
                break
        if not isinstance(self.group_name, list):
            group = root.findGroup(self.group_name)
            if not group:
                group = self.__add_orto_group(parent_group)
        for layer in layers_list:
            if group:
                self.add_layer_to_group(layer, group)
            else:
                group = root.findGroup(temp_group_name)
                if not group:
                    group = root.addGroup(temp_group_name)
                self.add_layer_to_group(layer, root.findGroup(temp_group_name))
        self.orto_added.emit()

    def remove_groups_before_close(self):
        def remove_empty_groups(group: QgsLayerTreeGroup):
            for child in list(group.children()):
                if isinstance(child, QgsLayerTreeGroup):
                    remove_empty_groups(child)
                    if not len(child.children()):
                        group.removeChildNode(child)

        for group in list(root.children()):
            if isinstance(group, QgsLayerTreeGroup):
                layer_children = [
                    child for child in group.children()
                    if isinstance(child, QgsLayerTreeLayer) and child.layer() is not None
                ]
                has_wms = any(
                    child.layer().dataProvider().name().lower() in ["wms", "wmts", "wfs"]
                    for child in layer_children
                )
                if not has_wms:
                    remove_empty_groups(group)
                    if not len(group.children()):
                        root.removeChildNode(group)

    def add_layer_to_group(self, layer: QgsVectorLayer or QgsRasterLayer, group: QgsLayerTreeGroup) -> None:
        project.addMapLayer(layer)
        node_layer = root.findLayer(layer.id())
        node_parent = node_layer.parent()
        clone_node_layer = node_layer.clone()
        group.insertChildNode(0, clone_node_layer)
        clone_node_layer.setItemVisibilityCheckedParentRecursive(True)
        node_parent.removeChildNode(node_layer)


def get_wfs_layers(wfs_url: str, wfs_version: str = '2.0.0') -> \
        Dict[str, str] or None:
    try:
        wfs_service = WebFeatureService(wfs_url, wfs_version)
        if wfs_service:
            layer_names = {}
            for layer_name in list(wfs_service.contents):
                lyr_src_name = wfs_service.contents[layer_name].id
                layer_title = wfs_service.contents[layer_name].title
                crs_options = [crs.getcode() for crs in
                               wfs_service.contents[layer_name].crsOptions]
                if lyr_src_name and layer_title:
                    values_map = {
                        'url': wfs_url,
                        'crs': crs_options[0] if crs_options else 'EPSG:2180',
                        'table_name': lyr_src_name
                    }
                    layer_names[layer_title] = \
                        WFS_EXAMPLE_SRC.format_map(values_map)
                QApplication.processEvents()
            return layer_names
    except Exception as e:
        if isinstance(e, requests.exceptions.MissingSchema) or isinstance(e, requests.exceptions.InvalidSchema):
            CustomMessageBox(None, tr('Invalid service address.'))
        else:
            CustomMessageBox(None, tr('An error occurred while connecting to the server.'))


def get_wms_layers(wms_url: str, wms_version: str = '1.3.0') -> \
        Dict[str, str] or None:
    try:
        wms_service = WebMapService(wms_url, wms_version)
        if wms_service:
            layer_names = {}
            for layer_name in list(wms_service.contents):
                lyr_src_name = wms_service.contents[layer_name].id
                layer_title = wms_service.contents[layer_name].title
                image_type = \
                    wms_service.getOperationByName('GetMap').formatOptions[0]
                crs_options = wms_service.contents[layer_name].crsOptions
                if lyr_src_name and layer_title:
                    values_map = {
                        'url': wms_url,
                        'crs': ('EPSG:2180' if 'EPSG:2180' in crs_options
                                else crs_options[
                            0]) if crs_options else 'EPSG:2180',
                        'table_name': lyr_src_name,
                        'image_type': image_type
                    }
                    layer_names[layer_title] = \
                        WMS_EXAMPLE_SRC.format_map(values_map)
                QApplication.processEvents()
            return layer_names
    except Exception as e:
        if isinstance(e, requests.exceptions.MissingSchema) or isinstance(e, requests.exceptions.InvalidSchema):
            CustomMessageBox(None, tr('Invalid service address.'))
        else:
            CustomMessageBox(None, tr('An error occurred while connecting to the server.'))


def get_wmts_layers(wmts_url: str, wmts_version: str = '1.3.0') -> \
        Dict[str, str] or None:
    try:
        if '?SERVICE%3DWMTS%26REQUEST%3DGetCapabilities' not in wmts_url:
            wmts_url = '{}?SERVICE%3DWMTS%26REQUEST%3DGetCapabilities'.format(wmts_url)
        wmts_service = WebMapTileService(wmts_url, wmts_version)
        if wmts_service:
            layer_names = {}
            for layer_name_wmts in list(wmts_service.tilematrixsets):
                layer_name = list(wmts_service.contents)[0]
                lyr_src_name = wmts_service.contents[layer_name].id
                layer_title = layer_name_wmts
                type = wmts_service.contents[layer_name]._tilematrixsets[0]
                image_type = wmts_service.contents[layer_name].formats[0]
                crs_options = wmts_service.contents[layer_name]._tilematrixsets[0]
                if lyr_src_name and layer_title:
                    values_map = {
                        'url': wmts_url,
                        'crs': ('EPSG:2180' if 'EPSG:2180' in crs_options
                                else crs_options[
                            0]) if crs_options else 'EPSG:2180',
                        'table_name': lyr_src_name,
                        'image_type': image_type,
                        'type': type
                    }
                    layer_names[layer_title] = \
                        WMTS_EXAMPLE_SRC.format_map(values_map)
                QApplication.processEvents()
            return layer_names
    except Exception as e:
        if isinstance(e, requests.exceptions.MissingSchema) or isinstance(e, requests.exceptions.InvalidSchema):
            CustomMessageBox(None, 'Invalid service address..')
        else:
            CustomMessageBox(None, 'An error occurred while connecting to the server..')


def get_wmts_arc_layers(wmts_url: str, wmts_version: str = '1.0.0') -> \
        Dict[str, str] or None:
    try:
        wmts_service = WebMapTileService(wmts_url, wmts_version)
        if wmts_service:
            layer_names = {}
            for layer_name_wmts in list(wmts_service.tilematrixsets):
                layer_name = list(wmts_service.contents)[0]
                lyr_src_name = wmts_service.contents[layer_name].id
                layer_title = layer_name_wmts
                type = wmts_service.contents[layer_name]._tilematrixsets[0]
                image_type = wmts_service.contents[layer_name].resourceURLs[0]['format']
                r = wmts_service.contents[layer_name].boundingBox[0].crs
                epsg = re.split('::', r)
                crs_options = "EPSG:{}".format(epsg[1])
                if lyr_src_name and layer_title:
                    values_map = {
                        'url': wmts_url,
                        'crs': crs_options,
                        'table_name': lyr_src_name,
                        'image_type': image_type,
                        'type': type
                    }
                    layer_names[layer_title] = \
                        WMTS_ARC_EXAMPLE_SRC.format_map(values_map)
                QApplication.processEvents()
            return layer_names
    except (requests.exceptions.ConnectionError, requests.exceptions.MissingSchema, requests.HTTPError,
            ServiceException):
        return
