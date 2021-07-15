import requests
from qgis.PyQt.QtCore import QTimer
from qgis.utils import iface

from .searchAddress import SearchAddress

import json

from .searchParcel import FetchULDK, ParseResponce

from PyQt5.QtWidgets import QCompleter, QItemDelegate

from PyQt5.QtCore import Qt, QStringListModel


from urllib.request import urlopen

from urllib.parse import quote

from ..utils import tr

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
        self.fetch_voivodeship()
        # COMPLETER SETUP
        self.names = QStringListModel()
        self.completer = QCompleter(self.names)
        self.completer.setModel(self.names)
        self.dock.lineEdit_address.setCompleter(self.completer)
        self.dock.lineEdit_address.textEdited.connect(self.adress_changed)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCaseSensitivity(False)
        self.completer.setMaxVisibleItems(10)


    def adress_changed(self):
        # data storage for list of strings adresses defined by input in search bracket
        score = self.tips(self.dock.lineEdit_address)
        if score:
            self.names.setStringList(score)



    def getstreets(self, simc, city):
        try:
            url_pref = 'https://services.gugik.gov.pl/uug/?request=GetStreet&simc='
            data = json.loads(urlopen(url_pref + simc).read().decode())
            obj, score = data['results'], []
            elemscount = obj.keys()
            limit = len(elemscount)
            for i in range(1, limit + 1):
                score.append(f'{city}, {obj[str(i)]["street"]}')
            return score
        except Exception:
            return ['']


    def validatecity(self, obj, limit):
        city = obj['1']['city']
        if limit == 1:
            return self.getstreets(obj['1']['simc'], city)
        else:
            self.names.setStringList(self.pickacity(obj, limit))
            self.completer.popup().pressed.connect(lambda: self.userpick())




    def userpick(self):
        try:
            simc = self.dock.lineEdit_address.text().split(',')[2].strip()
            city = self.dock.lineEdit_address.text().split(',')[0].strip()
            self.names.setStringList(self.getstreets(simc, city))
            self.dock.lineEdit_address.setText(city)
        except:
            pass




    def pickacity(self, obj, limit):
        city = obj['1']['city']
        same_names = []
        for i in range(1, limit):
            same_names.append(f'{city}, {obj[str(i)]["county"]}, {obj[str(i)]["simc"]}')
        return same_names




    def tips(self, user_input):
        address = user_input.displayText()
        url_pref = 'http://services.gugik.gov.pl/uug/?request=GetAddress&location='
        quo_adr = quote(address)
        # trying to open link which script made above by prefix and quoting the search bracket input
        try:
            # loading json type of data from link
            data = json.loads(requests.get(url_pref + quo_adr).text)
            obj_type, limit = data['type'], data['found objects']
            # if finds nothing completion field is empty
            if limit == 0:
                return
            # dictionary with objects found on json_file
            obj = data['results']
            # if this particular address found, displays this address
            if 'only exact numbers' in data:
                return [f"{obj['1']['city']}, {obj['1']['street']} {obj['1']['number']}"]
            # there is only 1 object when obj_type == 'address' thats why variable in first bracket in obj is '1'
            # displays only one city in completer
            # TODO: when limit > 1 and obj_type == 'city' it has to display all city names in each voivodeship
            # TODO: and search for this particular but feature wont add voivodeship to search bracket
            if obj_type == 'city':
                return self.validatecity(obj, limit)
        # if any error occurred displays nothing TODO: expand errors with popups
        except Exception:
            return

    def zoom_to_feature(self):
        # feature is our new layer added by searcher tool
        layer = self.identify_layer('UUG_pkt')
        if self.iface.mapCanvas().layers() and len(layer.allFeatureIds()) > 0:
            self.iface.mapCanvas().zoomScale(500)
            layer.selectByIds([max(layer.allFeatureIds())])
            self.iface.mapCanvas().zoomToSelected()
            self.iface.mapCanvas().flashFeatureIds(layer, [max(layer.allFeatureIds())])

    def identify_layer(self, layer_to_find):
        for layer in self.iface.mapCanvas().layers():
            if layer.name() == layer_to_find:
                return layer

    def search_address(self):
        validate_address = self.validate_lineedit()
        if validate_address:
            self.searchaddress_call.fetch_address(self.dock.lineEdit_address.text())
            ok, res = self.searchaddress_call.process_results()
            if not ok:
                self.iface.messageBar().pushWarning(
                    tr('Warning'), res)
            self.searchaddress_call.add_feats(res)
            self.zoom_to_feature()
            def change_scale():
                if iface.mapCanvas().scale() < 500:
                    iface.mapCanvas().zoomScale(500)

            self.timer = QTimer()
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(change_scale)
            self.timer.start(10)



    def validate_lineedit(self):
        if self.dock.lineEdit_address.text():
            return True
        else:
            self.iface.messageBar().createMessage(tr('Invalid'), tr('Empty address field'))


    def fetch_voivodeship(self):
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

    def woj_changed(self):
        voi = self._get_voi_code()
        if not voi:
            return
        self.clear_comboBoxes()
        fe = FetchULDK()
        fe.fetch_list('powiat', voi)
        self.dock.comboBox_pow.blockSignals(True)
        self.dock.comboBox_pow.addItems(fe.responce)
        self.dock.comboBox_pow.blockSignals(False)

    def pow_changed(self):
        dis = self._get_dis_code()
        if not dis:
            return
        self.clear_comboBoxes('dis')
        fe = FetchULDK()
        fe.fetch_list('gmina', dis)
        self.dock.comboBox_gmina.blockSignals(True)
        self.dock.comboBox_gmina.addItems(fe.responce)
        self.dock.comboBox_gmina.blockSignals(False)

    def gmi_changed(self):
        mun = self._get_mun_code()
        self.clear_comboBoxes('mun')
        if not mun:
            return
        fe = FetchULDK()
        fe.fetch_list('obreb', mun)
        self.dock.comboBox_obr.blockSignals(True)
        self.dock.comboBox_obr.addItems(fe.responce)
        self.dock.comboBox_obr.blockSignals(False)

    def clear_comboBoxes(self, level=None):
        """Clear comboboxes to level where user change something"""
        self.dock.comboBox_obr.blockSignals(True)
        self.dock.comboBox_obr.clear()
        self.dock.comboBox_obr.addItem(tr('Community'))
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

    def _get_voi_code(self):
        voi_txt = self.dock.comboBox_woj.currentText()
        if '|' not in voi_txt:
            self.clear_comboBoxes()
            return False
        return voi_txt.split('|')[1]

    def _get_dis_code(self):
        dis_txt = self.dock.comboBox_pow.currentText()
        if '|' not in dis_txt:
            self.clear_comboBoxes('dis')
            return False
        return dis_txt.split('|')[1]

    def _get_mun_code(self):
        mun_txt = self.dock.comboBox_gmina.currentText()
        if '|' not in mun_txt:
            self.clear_comboBoxes('mun')
            return False
        return mun_txt.split('|')[1]

    def search_parcel(self):
        adr = ''  # ful address of parcel
        parc = self.dock.lineEdit_parcel.text()
        if '.' in parc and '_' in parc:  # user input whole address in parcel
            adr = parc
        else:
            comm = self.dock.comboBox_obr.currentText()
            if '|' not in comm:
                self.iface.messageBar().pushWarning(
                    tr('Address'), tr('Address of parcel is not valid')
                )
                return
            comm = comm.split('|')[1]
            adr = f'{comm}.{parc}'

        f = FetchULDK()
        if not f.fetch_parcel(adr):
            return
        pr = ParseResponce()
        pr.get_layer()
        pr.parse_responce(f.responce)
