# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os

from PyQt5.QtGui import QIcon
from qgis.PyQt import QtWidgets, uic, QtCore

from qgis.PyQt.QtWidgets import QWidgetAction, QCalendarWidget, QMenu, QToolButton

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'wydruk_dialog.ui'))


class WydrukDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent : QtWidgets=None) -> None:
        """Constructor."""
        super(WydrukDialog, self).__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)
        self.progressBar.hide()
        self.resspinBox.setValue(300)
        self.dateedit.setText(QtCore.QDateTime.currentDateTime().toString('yyyy-MM-dd'))
        self.dateedit.setInputMask('9999-99-99')
        self.dateedit.textEdited.connect(self.date_input)

        btn_action = QWidgetAction(self.date_button)
        self.calendar = QCalendarWidget(self.date_button)
        btn_action.setDefaultWidget(self.calendar)
        popup_menu = QMenu(self)
        popup_menu.addAction(btn_action)
        self.date_button.setPopupMode(QToolButton.InstantPopup)
        self.date_button.setMenu(popup_menu)
        self.date_button.setIcon(
            QIcon(os.path.join(self.plugin_dir, 'icons', 'calendar.png')))
        self.calendar.clicked.connect(self.set_date)

    def date_input(self) -> None:
        cur_pos = self.dateedit.cursorPosition()
        if self.dateedit.text() == '--':
            self.dateedit.setInputMask('')
        else:
            self.dateedit.setInputMask('9999-99-99')
            self.dateedit.setCursorPosition(cur_pos)

    def set_date(self) -> None:
        data = self.calendar.selectedDate()
        self.dateedit.setText(data.toString('yyyy-MM-dd'))
        self.date_button.menu().close()