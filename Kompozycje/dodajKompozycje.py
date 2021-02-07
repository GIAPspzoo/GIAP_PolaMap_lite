# -*- coding: utf-8 -*-

import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dodaj_kompozycje.ui'))


class DodajKompozycjeDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(DodajKompozycjeDialog, self).__init__(parent)
        self.setupUi(self)

        self.radioButton_1.clicked.connect(self.radio_changed)
        self.radioButton_2.clicked.connect(self.radio_changed)
        self.reset.hide()

    def radio_changed(self):
        if self.radioButton_1.isChecked():
            self.groupBox_35.setTitle(u"Kompozycje użytkownika")
            self.reset.hide()
            self.dodaj_kompozycje.show()
            self.usun_kompozycje.show()
            self.wczytaj.show()
            self.zapisz.show()
        elif self.radioButton_2.isChecked():
            self.groupBox_35.setTitle(u"Kompozycje domyślne")
            self.reset.show()
            self.dodaj_kompozycje.hide()
            self.usun_kompozycje.hide()
            self.wczytaj.hide()
            self.zapisz.hide()
