import requests
from qgis.PyQt.QtCore import QTimer
from qgis.utils import iface

from .searchAddress import SearchAddress

import json

from .searchParcel import FetchULDK, ParseResponce
from ..CustomMessageBox import CustomMessageBox
from qgis.PyQt.QtWidgets import QCompleter
from qgis.PyQt.QtCore import QStringListModel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontMetrics

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

    def textChanged(self):
        self.typing_timer.start(300)


    def tips(self):
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
                    self.names.setStringList([f"{city}, {obj[element]['street']}" for element in obj])
            if obj_type == 'city':
                if data["found objects"] > 1:
                    self.validateCity(data['results'])
                else:
                    self.getStreets(obj['1']['simc'], obj['1']['city'])
            if obj_type == 'address':
                self.names.setStringList([f"{obj['1']['city']}, {obj['1']['street']} {obj['1']['number']}"])
            if limit == 0:
                return
            self.completer.setCompletionPrefix(f"{address.split(',')[0]}, ")
            self.completer.complete()
        except Exception:
            return

    def getStreets(self, simc, city):
        try:
            data = json.loads(urlopen('https://services.gugik.gov.pl/uug/?request=GetStreet&simc=' + simc).read().decode())
            obj = data['results']
            self.names.setStringList([f"{city}, {obj[element]['street']}" for element in obj])
        except Exception:
            self.names.setStringList([])

    def validateCity(self, obj):
        city = obj['1']['city']
        self.names.setStringList([f"{city}, {obj[element]['simc']} {obj[element]['county']}" for element in obj])
        self.completer.popup().pressed.connect(lambda: self.userPick())

    def userPick(self):
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

    def search_address(self):
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

    def validate_lineedit(self):
        if self.dock.lineEdit_address.text():
            return True
        else:
            CustomMessageBox(None, f" {tr('Invalid')} {tr('Empty address field')}").button_ok()

    def widthforview(self, result):
        longest = max(result, key=len)
        width = 2 * self.fontm.width(longest)
        return width

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
        result = fe.responce
        self.dock.comboBox_pow.addItems(result)
        self.dock.comboBox_pow.view().setFixedWidth(self.widthforview(result))
        self.dock.comboBox_pow.blockSignals(False)

    def pow_changed(self):
        dis = self._get_dis_code()
        if not dis:
            return
        self.clear_comboBoxes('dis')
        fe = FetchULDK()
        fe.fetch_list('gmina', dis)
        self.dock.comboBox_gmina.blockSignals(True)
        result, communities = fe.responce, []
        multiples = [e.split('|')[0] for e in result]
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
        self.dock.comboBox_gmina.view().setFixedWidth(self.widthforview(communities))
        self.dock.comboBox_gmina.blockSignals(False)

    def gmi_changed(self):
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

    def clear_comboBoxes(self, level=None):
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
                CustomMessageBox(None,
                    f"{tr('Address of parcel is not valid.')}").button_ok()
                return
            comm = comm.split('|')[1]
            adr = f'{comm}.{parc}'

        f = FetchULDK()
        if not f.fetch_parcel(adr):
            return
        pr = ParseResponce()
        pr.get_layer()
        pr.parse_responce(f.responce)
