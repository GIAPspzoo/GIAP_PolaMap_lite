import pytest
from qgis.testing import start_app
from qgis.PyQt.QtCore import QSettings

from ..tools import StyleManager

QGIS_APP = start_app()


def test_set_default_style(qtbot):
    app = QGIS_APP

    expected = 'foobar'
    app.setStyleSheet(expected)
    app.processEvents()

    assert app.styleSheet() == expected


def test_stylemanager_get_styles(qtbot):
    sm = StyleManager()
    styles = sm.get_styles()
    assert styles == ['blueglass',
                      'coffee',
                      'darkblue',
                      'darkorange',
                      'giap',
                      'lightblue',
                      'wombat']


def test_stylemanager_set_default_style():
    app = QGIS_APP
    sm = StyleManager()
    sm.activate_style('default')

    assert app.styleSheet() == ''


def test_stylemanager_set_giap_style():
    app = QGIS_APP
    sm = StyleManager()
    sm.activate_style('giap')

    assert len(app.styleSheet()) > 2000


def test_stylemanager_set_active_style():
    app = QGIS_APP
    sm = StyleManager()
    sm.set_active_style('foobar')
    sm.set_active_style('giap')

    assert QSettings().value('giapStyle/active') == 'giap'

