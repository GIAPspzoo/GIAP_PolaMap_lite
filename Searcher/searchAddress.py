import json
from urllib.request import urlopen
from urllib.parse import quote
from qgis.utils import iface

from qgis.core import QgsGeometry, QgsFeature, QgsField, QgsFields, \
    QgsProject, QgsVectorLayer, QgsMessageLog, Qgis
from qgis.PyQt.QtCore import QVariant

import os


from urllib.error import HTTPError, URLError

from http.client import IncompleteRead

from ..utils import tr

from ..CustomMessageBox import CustomMessageBox


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
            QgsField("stret_accuracy", QVariant.String, len=10),
            QgsField("teryt", QVariant.String, len=20),
            QgsField("ulic", QVariant.String, len=30),
            QgsField("x", QVariant.Double, "double", 10, 4),
            QgsField("y", QVariant.Double, "double", 10, 4),
        ]



    def fetch_address(self, address):
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
                tr('Error'), tr('Check if address is correct'))
            return
        self.res.decode()

    def get_layer(self):
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

        lyr = QgsProject.instance().mapLayersByName(obj_type)
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
        QgsProject.instance().addMapLayer(lyr)
        direc = os.path.dirname(__file__)
        lyr.loadNamedStyle(os.path.join(direc, qml))
        return lyr

    def process_results(self):
        try:
            self.jres = json.loads(self.res)
        except Exception:
            return False, tr('Can\'t parse results')

        if 'found objects' in self.jres:
            if self.jres['found objects'] == 0:
                return False, tr('Zero objects found')
        else:
            return False, tr('Zero objects found')

        if 'results' in self.jres:
            if self.jres['results'] is None:
                return False, CustomMessageBox(None, tr("No objects found. Please enter a valid value.")).button_ok()

        lyr = self.get_layer()
        if not lyr:
            return False, tr('Check log, problems occured')
        fnm = lyr.dataProvider().fieldNameMap()
        feats = []
        if 'only exact numbers' in self.jres.keys():    # if jezeli znajdzie dokladnie ten adres
            exact_adr = self.jres['results']['1']   # poprzednia metoda zapelniala warstwe wszystkim co znalazla
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

    def add_feats(self, feats):
        if isinstance(feats, str):
            pass
        else:
            lyr = self.get_layer()
            try:
                lyr.dataProvider().addFeatures(feats)
            except:
                return
            lyr.updateExtents()
            iface.mapCanvas().setExtent(lyr.extent())
            iface.mapCanvas().refresh()
        return True

