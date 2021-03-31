from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from http.client import IncompleteRead
from qgis.core import QgsGeometry, QgsFeature, \
    QgsProject, QgsVectorLayer, Qgis

from qgis.utils import iface
from ..utils import tr


class FetchULDK:
    def __init__(self, params=None):
        self.params = params
        self.responce = []

    def fetch_list(self, area, teryt):
        map(str, teryt)
        if area not in {'powiat', 'gmina', 'obreb'}:
            self.responce = []
            return False
        self.params = f'obiekt={area}&wynik=nazwa%2Cteryt&teryt={teryt}&'
        return self.fetch()

    def fetch_voivodeships(self):
        self.params = 'obiekt=wojewodztwo&wynik=nazwa%2Cteryt&teryt=&'
        return self.fetch()

    def fetch_parcel(self, teryt):
        self.responce = []
        if not isinstance(teryt, str):
            return False
        self.params = f'request=GetParcelById&id={teryt}&result=' + \
            'geom_wkt,teryt,voivodeship,county,region,commune,parcel'
        return self.fetch()

    def fetch_in_point(self, coords):
        # TODO: Dodac pobieranie działki w pkt po kliknieciu
        pass

    def fetch(self):
        url = f'https://uldk.gugik.gov.pl/?{self.params}'
        self.responce = []
        try:
            with urlopen(url, timeout=19) as r:
                content = r.read()
        except IncompleteRead:
            iface.messageBar().pushMessage(
                tr('Error'), tr('Service returned incompleted responce'),
                Qgis.Warning
            )
            return False
        except HTTPError:
            iface.messageBar().pushMessage(
                tr('Error'), tr('Service error'), Qgis.Warning
            )
            return False
        except URLError:
            iface.messageBar().pushMessage(
                tr('Error'), tr('Service not responding'), Qgis.Warning
            )
            return False

        content = content.decode()
        res = content.split('\n')
        if res[0] != '0':
            iface.messageBar().pushMessage(
                tr('INFO'), tr('Service returned: {}').format(str(res[0])),
                Qgis.Warning
            )
            return False

        self.responce = [x for x in res[1:] if x != '']
        return True


class ParseResponce:
    def __init__(self):
        self.lyr_name = 'ULDK_działki'
        self.not_valid = 0  # not valid feats returned

        self.lyr = QgsVectorLayer(
            'MultiPolygon?crs=epsg:2180&index=yes&field=teryt:string(50)'
            '&field=woj:string(100)&field=powiat:string(100)'
            '&field=gmina:string(100)&field=obreb:string(100)'
            '&field=nr_dz:string(50)&field=pow_graf:double(10,4)',
            self.lyr_name, 'memory'
        )

    def get_layer(self):
        lyr = QgsProject.instance().mapLayersByName(self.lyr_name)
        if len(lyr) > 0:
            self.lyr = lyr[0]
            return
        QgsProject.instance().addMapLayer(self.lyr)

    def parse_responce(self, resp):
        feats = []
        for row in resp:
            ft = self._create_feature(row)
            if ft.isValid():
                feats.append(ft)
            else:
                self.not_valid += 1

        self.lyr.dataProvider().addFeatures(feats)
        self.lyr.updateExtents()
        iface.mapCanvas().setExtent(self.lyr.extent())
        iface.mapCanvas().refresh()
        if self.not_valid > 0:
            iface.messageBar().pushMessage(
                tr('Warning'),
                tr('Service return {} not valid features'
                   ).format(self.not_valid),
                Qgis.Warning
            )
        if len(feats) > 0:
            lfeats = len(feats)
            mess = tr('Service return {} feature')
            if lfeats > 1:
                mess = tr('Service return {} features')
            iface.messageBar().pushMessage(
                'OK', mess.format(lfeats),
                Qgis.Success
            )

    def _create_feature(self, row):
        if row[:4].upper() == 'SRID':
            row = row[row.index(';')+1:]

        feat = QgsFeature()
        lrow = row.split('|')
        geom = QgsGeometry().fromWkt(lrow[0])
        feat.setGeometry(geom)
        feat.setFields(self.lyr.fields())
        cols = ['teryt', 'woj', 'powiat', 'gmina', 'obreb', 'nr_dz']

        for eni, val in enumerate(lrow[1:]):
            if val:
                feat[cols[eni]] = val
        feat['pow_graf'] = geom.area()

        return feat
