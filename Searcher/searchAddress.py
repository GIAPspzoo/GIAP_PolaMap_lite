import json
import os
from http.client import IncompleteRead
from json import JSONDecodeError
from typing import Union, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsGeometry, QgsFeature, QgsField, QgsFields, \
    QgsVectorLayer, QgsMessageLog, Qgis
from qgis.utils import iface

from ..utils import tr, add_map_layer_to_group, search_group_name, project
################################################################
from qgis.core import QgsField, QgsFeature, QgsGeometry
################################################################


class SearchAddress:
    def __init__(self):
        self.address = ''
        self.adres = ''
        # fields for layer
        self.layer_fields = [
            QgsField('accuracy', QVariant.String, len=10),
            QgsField("city", QVariant.String, len=150),
            QgsField("city_accuracy", QVariant.String, len=10),
            QgsField("citypart", QVariant.String, len=150),
            QgsField("code", QVariant.String, len=6),
            QgsField("jednostka", QVariant.String, len=250),
            QgsField("number", QVariant.String, len=20),
            QgsField("simc", QVariant.String, len=30),
            QgsField("street", QVariant.String, len=250),
            QgsField("street_accuracy", QVariant.String, len=10),
            QgsField("teryt", QVariant.String, len=20),
            QgsField("ulic", QVariant.String, len=30),
            QgsField("x", QVariant.Double, "double", 10, 4),
            QgsField("y", QVariant.Double, "double", 10, 4),
        ]

    def fetch_address(self, address: str) -> None:
        self.address = address
        uug = 'https://services.gugik.gov.pl/uug?request=GetAddress&address='
        url = uug + quote(self.address)
        try:
            with urlopen(url, timeout=2) as openedurl:
                self.res = openedurl.read()
        except IncompleteRead:
            iface.messageBar().pushCritical(
                tr('Error'), tr('Service unavailable'))
            return
        except HTTPError as e:
            raise e
        except URLError:
            iface.messageBar().pushCritical(
                tr('Error'), tr('Check address'))
            return
        self.res.decode()

    def get_layer(self) -> Union[bool, Tuple[str]]:
        req_type = self.jres['type']
        if req_type in ['city', 'address']:
            org = 'MultiPoint?crs=epsg:2180&index=yes'
            obj_type = 'UUG_pkt'
            qml = os.path.join('layer_style', 'PUNKT_ADRESOWY.qml')
        elif self.jres['type'] == 'street':
            org = 'MultiLineString?crs=epsg:2180&index=yes'
            obj_type = 'UUG_ulice'
            qml = os.path.join('layer_style', 'ULICE.qml')
        else:
            QgsMessageLog.logMessage(
                'Fetched unknown object: ' + str(req_type),
                'GIAP Layout',
                Qgis.Warning
            )
            return False
        return org, obj_type, qml

    def get_layer_data(self, org: str, obj_type: str,
                       qml: str) -> QgsVectorLayer:
        lyr = project.mapLayersByName(obj_type)
        if lyr:
            return lyr[0]

        lyr = QgsVectorLayer(org, obj_type, 'memory')
        flds = QgsFields()
        if 'only exact numbers' in self.jres.keys():
            for fld in self.layer_fields:
                flds.append(fld)
        else:
            for fld in self.layer_fields:
                flds.append(fld)
        lyr.dataProvider().addAttributes(flds)
        lyr.updateFields()
        # QgsProject.instance().addMapLayer(lyr)
        add_map_layer_to_group(lyr, search_group_name, force_create=True)
        direc = os.path.dirname(__file__)
        lyr.loadNamedStyle(os.path.join(direc, qml))
        return lyr

    def process_results(self) -> Union[
        Tuple[bool, str], Tuple[bool, QgsFeature]]:
        try:
            self.jres = json.loads(self.res)
        except JSONDecodeError:
            return False, tr('Cannot parse results.')

        if 'found objects' in self.jres:
            if self.jres['found objects'] == 0:
                return False, tr(
                    'Service did not find any objects for this query.')
        else:
            return False, tr('Zero objects found.')

        if 'results' in self.jres:
            if self.jres['results'] is None:
                return False, tr("No objects found. Please enter valid value.")
        org, obj_type, qml = self.get_layer()
        lyr = self.get_layer_data(org, obj_type, qml)
        if not lyr:
            return False, tr('Check log, problems occured.')
        fnm = lyr.dataProvider().fieldNameMap()
        feats = []
        
        
        if 'only exact numbers' in self.jres.keys():  # if jezeli znajdzie dokladnie ten adres
            exact_adr = self.jres['results'][
                '1']  # poprzednia metoda zapelniala warstwe wszystkim co znalazla
            feat = QgsFeature()
            feat.setFields(lyr.fields())
            for column in feat.fields():
                name = column.name()
                if name in exact_adr.keys():
                    feat[name] = exact_adr[name]
            geom = QgsGeometry()
            geom = geom.fromWkt(exact_adr['geometry_wkt'])
            feat.setGeometry(geom)
            if feat.isValid():
                feats.append(feat)
        else:
            for res in self.jres['results'].values():
                feat = QgsFeature()
                feat.setFields(lyr.fields())
                for col in fnm.keys():
                    if col in res:
                        feat[col] = res[col]
                geom = QgsGeometry()
                geom = geom.fromWkt(res['geometry_wkt'])
                feat.setGeometry(geom)
                if feat.isValid():
                    feats.append(feat)

        return True, feats
        
    def zoom_to_feature(self, layer: str) -> None:
        layer = project.mapLayersByName(layer)[0]
        iface.mapCanvas().zoomScale(500)
        layer.selectByIds([len(layer)])
        iface.mapCanvas().zoomToSelected(layer)
        layer.removeSelection()

    def add_feats(self, feats: QgsFeature) -> Union[bool, None]:
        if isinstance(feats, str):
            pass
        else:
            org, obj_type, qml = self.get_layer()
            if not self.get_layer():
                return
            lyr = self.get_layer_data(org, obj_type, qml)
            lyr.dataProvider().addFeatures(feats)
            self.zoom_to_feature(obj_type)
        return True
    
    
    