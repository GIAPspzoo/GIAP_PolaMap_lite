import json
from json import JSONDecodeError
from urllib.parse import quote
from urllib.request import urlopen

import requests
from PyQt5.QtCore import Qt
from qgis.PyQt.QtGui import QFont, QFontMetrics
from qgis.PyQt.QtCore import QStringListModel
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QCompleter
from qgis.core import QgsVectorLayer
from qgis.utils import iface
from typing import Union, Dict, List
########################################################################
from qgis.core import QgsField, QgsFeature, QgsGeometry, QgsPointXY, QgsMapLayer
from PyQt5.QtCore import QVariant

from qgis.gui import QgsMapToolEmitPoint
from urllib.request import urlopen
from qgis.core import Qgis
import os
########################################################################

from .searchAddress import SearchAddress
from .searchParcel import FetchULDK, ParseResponce
from ..utils import tr, CustomMessageBox, add_map_layer_to_group, \
    ProgressDialog, identify_layer_in_group, root, WFS_PRG, search_group_name, project



class SearcherTool:

    def __init__(self, dock, iface):
        self.iface = iface
        self.dock = dock
        self.searchaddress_call = SearchAddress()
        self.dock.lineEdit_address.returnPressed.connect(
            self.search_address)
        self.dock.comboBox_woj.currentIndexChanged.connect(
            self.woj_changed)
        self.dock.comboBox_pow.currentIndexChanged.connect(
            self.pow_changed)
        self.dock.comboBox_gmina.currentIndexChanged.connect(
            self.gmi_changed)
        self.dock.lineEdit_parcel.returnPressed.connect(
            self.search_parcel)
################################################################################
        self.dock.buttonParcelNr.clicked.connect(self.handle_parcel_button_click)
        self.dock.buttonAdress.clicked.connect(self.handle_address_button_click)
        self._pointTool = None
        self._previousTool = None
        self.clicked_x = None
        self.clicked_y = None

################################################################################
        self.fetch_voivodeship()
        
        
        # TIMER
        self.typing_timer = QTimer()
        self.typing_timer.setSingleShot(True)
        self.typing_timer.timeout.connect(self.tips)
        # COMPLETER SETUP
        self.names = QStringListModel()
        self.completer = QCompleter(self.names)
        self.completer.setModel(self.names)
        self.dock.lineEdit_address.setCompleter(self.completer)
        self.dock.lineEdit_address.textEdited.connect(self.textChanged)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCaseSensitivity(False)
        self.completer.setMaxVisibleItems(15)
        self.dock.setStyleSheet("QComboBox{combobox-popup: 0;}")
        self.dock.comboBox_gmina.setMaxVisibleItems(15)
        self.dock.comboBox_obr.setMaxVisibleItems(15)
        self.dock.comboBox_pow.setMaxVisibleItems(15)
        self.dock.comboBox_woj.setMaxVisibleItems(17)
        self.font = QFont('Agency FB')
        self.fontm = QFontMetrics(self.font)

    def textChanged(self) -> None:
        self.typing_timer.start(300)

    def tips(self) -> None:
        address = self.dock.lineEdit_address.displayText()
        url_pref = 'http://services.gugik.gov.pl/uug/?request=GetAddress&address='
        quo_adr = quote(address)
        try:
            data = json.loads(requests.get(url_pref + quo_adr).text)
            obj_type, limit = data['type'], data['found objects']
            obj = data['results']
            if obj_type == 'street':
                city = obj['1']['city']
                if data['found objects'] == 1:
                    self.names.setStringList([f"{city}, {obj['1']['street']}"])
                else:
                    self.names.setStringList(
                        [f"{city}, {obj[element]['street']}" for element in
                         obj])
            if obj_type == 'city':
                if data["found objects"] > 1:
                    self.validateCity(data['results'])
                else:
                    self.getStreets(obj['1']['simc'], obj['1']['city'])
            if obj_type == 'address':
                self.names.setStringList([
                    f"{obj['1']['city']}, {obj['1']['street']} {obj['1']['number']}"])
            if not limit:
                return
            self.completer.setCompletionPrefix(f"{address.split(',')[0]}, ")
            self.completer.complete()
        except (JSONDecodeError, TypeError):
            return

    def getStreets(self, simc: str, city: str) -> None:
        try:
            data = json.loads(urlopen(
                'https://services.gugik.gov.pl/uug/?request=GetStreet&simc=' + simc).read().decode())
            obj = data['results']
            self.names.setStringList(
                [f"{city}, {obj[element]['street']}" for element in obj])
        except TypeError:
            self.names.setStringList([])

    def validateCity(self, obj: Dict[str, Dict[str, int]]) -> None:
        city = obj['1']['city']
        self.names.setStringList(
            [f"{city}, {obj[element]['simc']} {obj[element]['county']}" for
             element in obj])
        self.completer.popup().pressed.connect(lambda: self.userPick())

    def userPick(self) -> None:
        line = self.dock.lineEdit_address.text().split()
        self.completer.popup().pressed.disconnect()
        if len(line) == 3:
            simc = line[1].strip()
            city = self.dock.lineEdit_address.text().split(',')[0].strip()
            self.dock.lineEdit_address.setText(city)
            self.getStreets(simc, city)
            self.completer.popup().setFixedHeight(200)
        else:
            return

    def search_address(self) -> None:
        validate_address = self.validate_lineedit()
        if validate_address:
            lineedit = self.dock.lineEdit_address.text().split(',')
            if len(lineedit) == 3:
                correct_lineedit = f"{lineedit[0].strip()}, {lineedit[1].strip()}, {lineedit[2].strip()}"
            if len(lineedit) == 2:
                correct_lineedit = f"{lineedit[0].strip()}, {lineedit[1].strip()}"
            else:
                correct_lineedit = f"{lineedit[0].strip()}"
            self.searchaddress_call.fetch_address(correct_lineedit)
            ok, res = self.searchaddress_call.process_results()
            if not ok:
                CustomMessageBox(None, f'{tr("Warning!")} {res}').button_ok()
            self.searchaddress_call.add_feats(res)

            def change_scale():
                if iface.mapCanvas().scale() < 500:
                    iface.mapCanvas().zoomScale(500)

            self.timer = QTimer()
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(change_scale)
            self.timer.start(10)

    def validate_lineedit(self) -> bool:
        if self.dock.lineEdit_address.text():
            return True
        else:
            CustomMessageBox(None,
                             f" {tr('Invalid')} {tr('Empty address field')}").button_ok()

    def add_chosen_border(self, mess: str) -> None:
        lay_data = {'Obręby_ewidencyjne': ["A06_Granice_obrebow_ewidencyjnych",
                                           self.dock.comboBox_obr],
                    'Gminy': ["A03_Granice_gmin", self.dock.comboBox_gmina],
                    'Powiaty': ["A02_Granice_powiatow",
                                self.dock.comboBox_pow],
                    'Województwa': ["A01_Granice_wojewodztw",
                                    self.dock.comboBox_woj]}
        for lay_key in lay_data:
            if lay_data[lay_key][1].currentIndex():
                _, jpt_kod_je = lay_data[lay_key][1].currentText().split("|")
                if lay_key == "Gminy":
                    jpt_kod_je = jpt_kod_je.replace("_", "")
                adres = lay_data[lay_key][0]
                lay_name = lay_key
                break
        if 'jpt_kod_je' not in locals() or 'adres' not in locals()\
                or 'lay_name' not in locals():
            CustomMessageBox(self.iface.mainWindow(),
                             mess).button_ok()
            return
        prg_dlg = ProgressDialog(self.iface.mainWindow())
        prg_dlg.start_steped(tr("Adding layers..."))
        prg_dlg.start()
        url = f"{WFS_PRG}?SERVICE=WFS&REQUEST=GetFeature&VERSION=2.0.0&TYPENAME=ms:{adres}&TYPENAMES=ms:{adres}"
        vlayer = QgsVectorLayer(url, "wfs_lay", "WFS")
        vlayer.setSubsetString(f"""SELECT * FROM {adres}
                                   WHERE JPT_KOD_JE = '{jpt_kod_je}'""")
        group_name = "GRANICE"
        granice_group = root.findGroup(group_name)
        if not granice_group:
            root.addGroup(group_name)
        lay = identify_layer_in_group(group_name, lay_name)
        if not lay:
            lay = QgsVectorLayer("Polygon", lay_name, "memory")
            attr = vlayer.dataProvider().fields().toList()
            lay.dataProvider().addAttributes(attr)
            lay.updateFields()
            add_map_layer_to_group(lay, "GRANICE")
        vlayer.selectAll()
        feat = vlayer.selectedFeatures()[0]
        lay.dataProvider().addFeature(feat)
        lay.updateExtents()
        self.searchaddress_call.zoom_to_feature(lay.name())
        prg_dlg.stop()

    def widthforview(self, result: List[str]) -> int:
        longest = max(result, key=len)
        width = 2 * self.fontm.width(longest)
        return width

    def fetch_voivodeship(self) -> None:
        """Fetching voivodeship list from GUGiK"""
        voi_list = [
            'Dolnośląskie|02',
            'Kujawsko-Pomorskie|04',
            'Lubelskie|06',
            'Lubuskie|08',
            'Łódzkie|10',
            'Małopolskie|12',
            'Mazowieckie|14',
            'Opolskie|16',
            'Podkarpackie|18',
            'Podlaskie|20',
            'Pomorskie|22',
            'Śląskie|24',
            'Świętokrzyskie|26',
            'Warmińsko-Mazurskie|28',
            'Wielkopolskie|30',
            'Zachodniopomorskie|32',
        ]
        self.dock.comboBox_woj.blockSignals(True)
        self.dock.comboBox_woj.addItems(voi_list)
        self.dock.comboBox_woj.blockSignals(False)
        self.clear_comboBoxes('voi')

    def woj_changed(self) -> None:
        voi = self._get_voi_code()
        if not voi:
            return
        self.clear_comboBoxes()
        fe = FetchULDK()
        fe.fetch_list('powiat', voi)
        self.dock.comboBox_pow.blockSignals(True)
        result = fe.responce
        self.dock.comboBox_pow.addItems(result)
        self.dock.comboBox_pow.view().setFixedWidth(self.widthforview(result))
        self.dock.comboBox_pow.blockSignals(False)

    def pow_changed(self) -> None:
        dis = self._get_dis_code()
        if not dis:
            return
        self.clear_comboBoxes('dis')
        fe = FetchULDK()
        fe.fetch_list('gmina', dis)
        self.dock.comboBox_gmina.blockSignals(True)
        result, communities = fe.responce, []
        multiples = [powiat.split('|')[0] for powiat in result]
        for district in result:
            end = district[-2:]
            if multiples.count(district.split('|')[0]) > 1:
                if end == '_1':
                    new_ds = district.replace('|', ' - miasto |')
                    communities.append(new_ds)
                if end == '_2':
                    new_ds = district.replace('|', ' - gmina |')
                    communities.append(new_ds)
            else:
                communities.append(district)
        self.dock.comboBox_gmina.addItems(communities)
        self.dock.comboBox_gmina.view().setFixedWidth(
            self.widthforview(communities))
        self.dock.comboBox_gmina.blockSignals(False)

    def gmi_changed(self) -> None:
        mun = self._get_mun_code()
        self.clear_comboBoxes('mun')
        if not mun:
            return
        fe = FetchULDK()
        fe.fetch_list('obreb', mun)
        self.dock.comboBox_obr.blockSignals(True)
        result = fe.responce
        self.dock.comboBox_obr.addItems(result)
        self.dock.comboBox_obr.view().setFixedWidth(self.widthforview(result))
        self.dock.comboBox_obr.blockSignals(False)

    def clear_comboBoxes(self, level: str = None) -> None:
        """Clear comboboxes to level where user change something"""
        self.dock.comboBox_obr.blockSignals(True)
        self.dock.comboBox_obr.clear()
        self.dock.comboBox_obr.addItem(tr('Cadastral district'))
        self.dock.comboBox_obr.blockSignals(False)
        if level == 'mun':
            return

        self.dock.comboBox_gmina.blockSignals(True)
        self.dock.comboBox_gmina.clear()
        self.dock.comboBox_gmina.addItem(tr('Municipality'))
        self.dock.comboBox_gmina.blockSignals(False)
        if level == 'dis':
            return

        self.dock.comboBox_pow.blockSignals(True)
        self.dock.comboBox_pow.clear()
        self.dock.comboBox_pow.addItem(tr('District'))
        self.dock.comboBox_pow.blockSignals(False)

    def _get_voi_code(self) -> Union[str, bool]:
        voi_txt = self.dock.comboBox_woj.currentText()
        if '|' not in voi_txt:
            self.clear_comboBoxes()
            return False
        return voi_txt.split('|')[1]

    def _get_dis_code(self) -> Union[str, bool]:
        dis_txt = self.dock.comboBox_pow.currentText()
        if '|' not in dis_txt:
            self.clear_comboBoxes('dis')
            return False
        return dis_txt.split('|')[1]

    def _get_mun_code(self) -> Union[str, bool]:
        mun_txt = self.dock.comboBox_gmina.currentText()
        if '|' not in mun_txt:
            self.clear_comboBoxes('mun')
            return False
        return mun_txt.split('|')[1]

    def search_parcel(self) -> None:
        parc = self.dock.lineEdit_parcel.text()
        if '.' in parc and '_' in parc:  # user input whole address in parcel
            adr = parc
        else:
            comm = self.dock.comboBox_obr.currentText()
            if not parc:
                self.add_chosen_border(
                    f"{tr('Address of parcel is not valid.')}")
                return
            if '|' not in comm:
                CustomMessageBox(None,
                                 f"{tr('Address of parcel is not valid.')}").button_ok()
                return
            comm = comm.split('|')[1]
            adr = f'{comm}.{parc}'

        feULDK = FetchULDK()
        if not feULDK.fetch_parcel(adr):
            return
        pr = ParseResponce()
        pr.get_layer()
        pr.parse_responce(feULDK.responce)

    def handle_parcel_button_click(self):
        if self._pointTool is not None:
            self.iface.mapCanvas().unsetMapTool(self._pointTool)
            self._pointTool = None
        canvas = self.iface.mapCanvas()
        self._previousTool = canvas.mapTool()
        self._pointTool = PrintClickedPoint(canvas, self)
        canvas.setMapTool(self._pointTool)
        
    
    def handle_address_button_click(self):
        if self._pointTool is not None:
            self.iface.mapCanvas().unsetMapTool(self._pointTool)
            self._pointTool = None
        canvas = self.iface.mapCanvas()
        self._previousTool = canvas.mapTool()
        self._pointTool = PrintClickedPoint(canvas, self, mode='address')
        canvas.setMapTool(self._pointTool)
    
    

    def on_point_callback(self, point, mode='parcel'):
        self.clicked_x = round(point.x(), 2)
        self.clicked_y = round(point.y(), 2)
        if mode == 'parcel':
            self.fetch_parcel_by_xy()
        elif mode == 'address':
            self.fetch_address_by_xy()


    def fetch_address_by_xy(self):
        if self.clicked_x is not None and self.clicked_y is not None:
            url = f'https://services.gugik.gov.pl/uug/?request=GetAddressReverse&location=POINT({self.clicked_x} {self.clicked_y})&srid=2180'
            try:
                response = requests.get(url, verify = False)
                response.raise_for_status()
                data = response.json()
                if 'results' in data and data['results']:
                    first_key = list(data['results'].keys())[0]
                    address = data['results'][first_key]
                    
                    self.add_address_point(address)
                    
                else:
                    CustomMessageBox(None, tr('No address found.')).button_ok()
            except requests.RequestException as e:
                CustomMessageBox(None, tr('Error.')).button_ok()
        else:
            CustomMessageBox(None, tr('Error. Invalid coordinates.')).button_ok()

    def add_address_point(self, address):
        self.flds = [
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
        # Check the existing layer
        org = 'MultiPoint?crs=epsg:2180&index=yes'
        obj_type = 'UUG_pkt'
        qml = os.path.join('layer_style', 'PUNKT_ADRESOWY.qml')
        layer = self.get_layer_data(org, obj_type, qml) 

        fet = QgsFeature()
        geometry = QgsGeometry.fromPointXY(QgsPointXY(self.clicked_x, self.clicked_y))
        fet.setGeometry(geometry)
        fet.setFields(layer.fields())

        for field in self.flds:
            field_name = field.name()
            if field_name in layer.fields().names():  # Ensure the field exists in the layer
                if field_name in address:
                    # Check if the value is "null" and replace it with "Null"
                    value = address[field_name]
                    if value == "null":
                        value = None
                    fet.setAttribute(field_name, value)
                else:
                    fet.setAttribute(field_name, None)  # Set default value to None

        pr = layer.dataProvider()
        pr.addFeature(fet)
        layer.updateExtents()
        layer.triggerRepaint()

        
    def get_layer_data(self, org: str, obj_type: str,
                       qml: str) -> QgsVectorLayer:
        lyr = project.mapLayersByName(obj_type)
        if lyr:
            return lyr[0]

        lyr = QgsVectorLayer(org, obj_type, 'memory')
        
        
        lyr.dataProvider().addAttributes(self.flds)
        lyr.updateFields()
        add_map_layer_to_group(lyr, search_group_name, force_create=True)
        direc = os.path.dirname(__file__)
        lyr.loadNamedStyle(os.path.join(direc, qml))
        return lyr
    
    def fetch_parcel_by_xy(self):
        if self.clicked_x is not None and self.clicked_y is not None:
            params = '&result=geom_wkt,teryt,voivodeship,county,region,commune,parcel'
            url = f'https://uldk.gugik.gov.pl/?request=GetParcelByXY&xy={self.clicked_x},{self.clicked_y}{params}'
            fetcher = FetchULDK()
            if fetcher.fetch(url):
                parser = ParseResponce()
                parser.get_layer()  # Ensure the layer is initialized
                parser.parse_responce(fetcher.responce)
        else:
            iface.messageBar().pushMessage("Error", "Failed to fetch parcel", level=Qgis.Critical)


class PrintClickedPoint(QgsMapToolEmitPoint):
    def __init__(self, canvas, searcher_tool, mode='parcel'):
        super().__init__(canvas)
        self.canvas = canvas
        self.searcher_tool = searcher_tool
        self.mode = mode

    def canvasPressEvent(self, e):
        point = self.toMapCoordinates(self.canvas.mouseLastXY())
        self.searcher_tool.on_point_callback(point, self.mode)

