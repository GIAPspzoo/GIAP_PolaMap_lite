import os.path
import re
import socket
from http.client import IncompleteRead
from typing import List
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from qgis.core import QgsGeometry, QgsFeature, \
    QgsVectorLayer, Qgis
from qgis.utils import iface

from ..utils import tr, CustomMessageBox, search_group_name, \
    add_map_layer_to_group, project


class FetchULDK:
    def __init__(self, params=None):
        self.params = params
        self.responce = []

    def fetch_list(self, area: str, teryt: str) -> bool:
        map(str, teryt)
        if area not in {'powiat', 'gmina', 'obreb'}:
            self.responce = []
            return False
        self.params = f'obiekt={area}&wynik=nazwa%2Cteryt&teryt={teryt}&'
        return self.fetch()

    def fetch_voivodeships(self) -> bool:
        self.params = 'obiekt=wojewodztwo&wynik=nazwa%2Cteryt&teryt=&'
        return self.fetch()

    def fetch_parcel(self, teryt: str) -> bool:
        self.responce = []
        if not isinstance(teryt, str):
            return False
        self.params = f'request=GetParcelById&id={teryt}&result=' + \
                      'geom_wkt,teryt,voivodeship,county,region,commune,parcel'
        return self.fetch()

    def fetch(self, url=None) -> bool:
        if url is None:
            if '- gmina' in self.params or '- miasto' in self.params:
                flag = self.params.find('-')
                self.params = self.params[0:flag]
            url = f'https://uldk.gugik.gov.pl/?{self.params}'
        self.responce = []
        try:
            with urlopen(url, timeout=19) as url_handler:
                content = url_handler.read()
        except IncompleteRead:
            CustomMessageBox(None,
                             f"{tr('Error!')} {tr('Service returned incomplete responce.')}").button_ok()
            return False
        except HTTPError:
            CustomMessageBox(None,
                             f"{tr('Error')} {tr('Service error')}").button_ok()
            return False
        except URLError:
            CustomMessageBox(None,
                             f"{tr('Error!')} {tr('Service is not responding.')}").button_ok()
            return False
        except socket.timeout:
            CustomMessageBox(None,
                             f"{tr('Error!')} {tr('Service temporary unvailiable on the ULDK side.')}").button_ok()
            return False

        content = content.decode()
        res = content.split('\n')
        if res[0] != '0':
            CustomMessageBox(None,
                             f"{tr('Service did not find any matches, wrong plot number.')}").button_ok()
            return False

        self.responce = self.natural_sort(
            [ter for ter in res[1:] if ter != ''])
        return True

    def natural_sort(self, list: List[str]) -> List[str]:
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alpha_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
        return sorted(list, key=alpha_key)


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

    def get_layer(self) -> None:
        lyr = project.mapLayersByName(self.lyr_name)
        if len(lyr) > 0:
            self.lyr = lyr[0]
            return
        add_map_layer_to_group(self.lyr, search_group_name, force_create=True)
        direc = os.path.dirname(__file__)
        self.lyr.loadNamedStyle(
            os.path.join(direc, 'layer_style', 'dzialki.qml'))

    def parse_responce(self, resp: List[str]) -> None:
        feats = []
        for row in resp:
            ft = self._create_feature(row)
            if ft.isValid():
                feats.append(ft)
            else:
                self.not_valid += 1

        self.lyr.dataProvider().addFeatures(feats)

        self.zoom_to_feature(self.lyr.name())

        if self.not_valid > 0:
            iface.messageBar().pushMessage(
                tr('Warning'),
                tr('Service return {} not valid features.'
                   ).format(self.not_valid),
                Qgis.Warning
            )

    def zoom_to_feature(self, layer: str) -> None:
        layer = project.mapLayersByName(layer)[0]
        iface.mapCanvas().zoomScale(500)
        layer.selectByIds([len(layer)])
        iface.mapCanvas().zoomToSelected(layer)
        layer.removeSelection()
        iface.messageBar().pushMessage(
            'GIAP-PolaMap(lite)',
            tr('The object has been downloaded!'),
            Qgis.Info,
            duration=1
        )

    def _create_feature(self, row: str) -> QgsFeature:
        if row[:4].upper() == 'SRID':
            row = row[row.index(';') + 1:]
        feat = QgsFeature()
        lrow = row.split('|')
        geom = QgsGeometry().fromWkt(lrow[0])
        feat.setGeometry(geom)
        feat.setFields(self.lyr.fields())
        cols = ['teryt', 'woj', 'powiat', 'obreb', 'gmina', 'nr_dz']

        for eni, val in enumerate(lrow[1:]):
            if val:
                feat[cols[eni]] = val
        feat['pow_graf'] = geom.area()

        return feat
