from qgis.PyQt.QtCore import QTimer
from qgis.utils import iface

from .searchAddress import SearchAddress

import json

from .searchParcel import FetchULDK, ParseResponce

from PyQt5.QtWidgets import QCompleter

from PyQt5.QtCore import Qt

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
        self.names = []
        self.completer = QCompleter(self.names)
        self.dock.lineEdit_address.setCompleter(self.completer)
        self.dock.lineEdit_address.textEdited.connect(self.adress_changed)
        self.completer.setFilterMode(Qt.MatchContains)



    def adress_changed(self):
        # data storage for list of strings adresses defined by input in search bracket
        score = self.tips(self.dock.lineEdit_address)
        # setting completer as None and deleting previous completer
        self.dock.lineEdit_address.setCompleter(None)
        self.completer.deleteLater()

        # new completer for actual purposes
        self.completer = QCompleter(score)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.popup().pressed.connect(self.search_address)
        self.dock.lineEdit_address.setCompleter(self.completer)
        self.completer.setFilterMode(Qt.MatchContains)




    def tips(self, user_input):
        address = user_input.displayText()
        if len(address.split(',')) == 1:
            return ['']

        url_pref = 'http://services.gugik.gov.pl/uug/?request=GetAddress&location='
        quo_adr = quote(address)

        # trying to open link which script made above by prefix and quoting the search bracket input
        with urlopen(url_pref + quo_adr) as json_file:
            try:
                # loading json type of data from link
                data = json.loads(json_file.read().decode())
                obj_type, limit = data['type'], data['found objects']
                counter, score= 1, []
                # if finds nothing completion field is empty
                if limit == 0:
                    return ['']
                # dictionary with objects found on json_file
                obj = data['results']

                # if this particular address found, displays this address
                if 'only exact numbers' in data:
                    return [f"{obj['1']['city']}, {obj['1']['street']} {obj['1']['number']}"]

                # there is only 1 object when obj_type == 'address' thats why variable in first bracket in obj is '1'
                if obj_type == 'address': # and data['returned objects'] == 1:
                    return [f"{obj['1']['city']}, {obj['1']['street']}"]


                # it has to iterate through streets, we don't know how many streets might be in search result
                # when we put full name of street it displays only this particular one
                if obj_type == 'street':
                    if limit == 1:
                        return [f"{obj['1']['city']}, {obj['1']['street']}"]
                    else:
                        validate = obj[str(counter)]['street'].split()
                        if len(validate) > 1 and validate[0] == 'ulica':
                            # loop for streets with 'Miasto, ulica xxx' json coding
                            while counter <= limit:
                                street=obj[str(counter)]['street'].split()
                                score.append(f"{obj[str(counter)]['city']}, {street[1]}")
                                counter += 1
                                if len(score) == 3:
                                    return score

                        else:
                            # loop for streets with 'Miasto, xxx' json coding
                            while counter <= limit:
                                score.append(f"{obj[str(counter)]['city']}, {obj[str(counter)]['street']}")
                                counter += 1
                                if len(score) == 3:
                                    return score


                # displays only one city in completer
                # TODO: when limit > 1 and obj_type == 'city' it has to display all city names in each voivodeship
                # TODO: and search for this particular but feature wont add voivodeship to search bracket
                if obj_type == 'city':
                    print('city')
                    return [obj['1']['city']]


            # if any error occurred displays nothing TODO: expand errors with popups
            except (TypeError, IndexError):
                return ['']

    def zoom_to_feature(self):
        # feature is our new layer added by searcher tool
        if self.iface.mapCanvas().layers():
            self.iface.mapCanvas().zoomScale(500)
            layer = self.identify_layer('UUG_pkt')
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
