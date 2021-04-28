from .searchAddress import SearchAddress
from .searchParcel import FetchULDK, ParseResponce

from ..utils import tr


class SearcherTool:
    def __init__(self, dock, iface):
        self.iface = iface
        self.dock = dock

    def run(self):
        self.dock.toolButton_address.clicked.connect(
            self.search_address)
        self.dock.lineEdit_address.returnPressed.connect(
            self.search_address)
        self.dock.comboBox_woj.currentIndexChanged.connect(
            self.woj_changed)
        self.dock.comboBox_pow.currentIndexChanged.connect(
            self.pow_changed)
        self.dock.comboBox_gmina.currentIndexChanged.connect(
            self.gmi_changed)
        self.dock.toolButton_parcel.clicked.connect(self.search_parcel)
        self.dock.lineEdit_parcel.returnPressed.connect(
            self.search_parcel)

        self.fetch_voivodeship()

    def search_address(self):
        se = SearchAddress()
        if not self.dock.lineEdit_address.text():
            self.iface.messageBar().pushWarning(
                tr('Invalid'), tr('Empty address field'))

        se.fetch_address(self.dock.lineEdit_address.text())
        ok, res = se.process_results()
        if not ok:
            self.iface.messageBar().pushWarning(
                tr('Warning'), res)
            return
        se.add_feats(res)

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
