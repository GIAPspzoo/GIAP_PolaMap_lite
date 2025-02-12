from __future__ import unicode_literals

import os
import urllib
from ast import literal_eval
import requests
import json

from qgis.gui import QgsMapLayerComboBox
from typing import Tuple, Any, List
from qgis.PyQt import QtWidgets, uic, QtCore
from qgis.core import QgsVectorLayer, QgsProject, QgsFeature, QgsGeometry, QgsPointXY, QgsFields, QgsField, \
    QgsFeatureRequest, QgsWkbTypes, QgsExpression, QgsMapLayerProxyModel, QgsDataSourceUri, QgsFeature, \
    QgsCoordinateReferenceSystem, QgsCoordinateTransform
from qgis.utils import iface
from qgis.PyQt.QtWidgets import QApplication, QProgressDialog, QDialog, QRadioButton, QStackedWidget, QMessageBox
from qgis.gui import QgsProjectionSelectionWidget

URL = "http://uldk.gugik.gov.pl/"
project = QgsProject.instance()

def get_request(iddzialki: str, request: str, result: str, srid: str or int) -> str or None:
    PARAMS = {'request': request, 'id': iddzialki, 'result': result, 'srid': srid}
    r = requests.get(url=URL, params=PARAMS)
    r_txt = r.text
    if r.status_code == 200 and r_txt[0] == '0':
        if ";" in r_txt:
            return r_txt.split('\n')[1].split(';')[1]
        else:
            return r_txt.split('\n')[1]
    return None

def get_parcel_by_id(iddzialki: str, srid: str or int) -> str or None:
    request = "GetParcelById"
    result = "geom_wkt"
    return get_request(iddzialki, request, result, srid)

def geocode(miasto: str, ulica: str, numer: str, kod: str) -> str or None:
    service = "http://services.gugik.gov.pl/uug/?"
    if not all((miasto, numer)):
        return ''
    if ulica.strip() == '' or ulica.strip() == miasto.strip():
        params = {"request": "GetAddress", "address": "%s %s %s" % (kod, miasto, str(numer).strip())}
    else:
        params = {"request": "GetAddress", "address": "%s %s, %s %s" % (kod, miasto, ulica, str(numer).strip())}
    try:
        paramsUrl = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        request = urllib.request.Request(service + paramsUrl)
        response = urllib.request.urlopen(request).read()
    except:
        return ''
    js = response.decode("utf-8")
    try:
        w = json.loads(js)
    except:
        return ''

    try:
        results = w['results']
        if not results:
            return None
        else:
            geomWkt = w['results']["1"]['geometry_wkt']
            return geomWkt
    except KeyError:
        return (str(w), 0)

class AddGeometryColumnDialog(QtWidgets.QDialog):
    def __init__(self, parent=None) -> None:
        """Constructor."""
        super(AddGeometryColumnDialog, self).__init__(parent)
        ui_file = os.path.join(os.path.dirname(__file__), 'addgeometrycolumn.ui')
        uic.loadUi(ui_file, self)

class Geocoding(QtWidgets.QDialog):
    def __init__(self, parent=None) -> None:
        """Constructor."""
        super(Geocoding, self).__init__(parent)
        ui_file = os.path.join(os.path.dirname(__file__), 'geocoding_tool_new.ui')
        uic.loadUi(ui_file, self)
        setup_resize(self)
        self.frame_many.hide()
        self.setModal(False)
        self.setWindowModality(QtCore.Qt.ApplicationModal)

        self.geocode = {}

        self.stacked_widget = self.findChild(QStackedWidget, 'stackedWidget_2')
        self.geocoding_adress = self.findChild(QRadioButton, 'geocoding_adress')
        self.geocoding_parcels = self.findChild(QRadioButton, 'geocoding_parcels')
        self.geocoding_XY = self.findChild(QRadioButton, 'geocoding_XY')

        self.geocoding_adress.toggled.connect(self.switch_page)
        self.geocoding_parcels.toggled.connect(self.switch_page)
        self.geocoding_XY.toggled.connect(self.switch_page)

        self.map_layer_cbbx = self.findChild(QgsMapLayerComboBox, 'map_layer_cbbx')
        self.populate_layer_combobox()

        self.geocoding_selected_only_cb = self.findChild(QtWidgets.QCheckBox, 'geocoding_selected_only')

        self.adress_col_cbbx = self.findChild(QtWidgets.QComboBox, 'adress_col_cbbx')
        self.adress_pattern_cbbx = self.findChild(QtWidgets.QComboBox, 'adress_pattern')
        self.adress_separator_cbbx = self.findChild(QtWidgets.QComboBox, 'adress_separator_cbbx')

        self.adress_city_cbbx = self.findChild(QtWidgets.QComboBox, 'adress_city_cbbx')
        self.adress_postal_cbbx = self.findChild(QtWidgets.QComboBox, 'adress_postal_cbbx')
        self.adress_street_cbbx = self.findChild(QtWidgets.QComboBox, 'adress_street_cbbx')
        self.adress_building_cbbx = self.findChild(QtWidgets.QComboBox, 'adress_building_cbbx')

        self.iddzialki_col_cbbx = self.findChild(QtWidgets.QComboBox, 'iddzialki_col')
        self.iddzialki_separator_cbbx = self.findChild(QtWidgets.QComboBox, 'iddzialki_separator')

        self.col_name_xy_cbbx = self.findChild(QtWidgets.QComboBox, 'col_name_xy')
        self.col_x_cbbx = self.findChild(QtWidgets.QComboBox, 'col_x')
        self.col_y_cbbx = self.findChild(QtWidgets.QComboBox, 'col_y')
        self.col_geom_crs_xy = self.findChild(QgsProjectionSelectionWidget, 'col_geom_crs_xy')

        self.map_layer_cbbx.layerChanged.connect(self.cbbx_menager)

        self.add_geometry_column_button = self.findChild(QtWidgets.QPushButton, 'add_geometry_column')
        self.add_geometry_column_button.clicked.connect(self.show_add_geometry_column_dialog)

        self.geocoding_button = self.findChild(QtWidgets.QPushButton, 'geocoding')
        self.geocoding_button.clicked.connect(self.perform_geocoding)

        self.geocoding_results = []

    def switch_page(self):
        if self.geocoding_adress.isChecked():
            self.stacked_widget.setCurrentIndex(0)
        elif self.geocoding_parcels.isChecked():
            self.stacked_widget.setCurrentIndex(1)
        elif self.geocoding_XY.isChecked():
            self.stacked_widget.setCurrentIndex(2)

    def cbbx_menager(self):
        cbbx_lyr = self.map_layer_cbbx.currentLayer()
        cbbx_nm = cbbx_lyr.fields().names()
        cbbx_list = [
            'adress_col_cbbx',
            'adress_city_cbbx',
            'adress_postal_cbbx',
            'adress_street_cbbx',
            'adress_building_cbbx',
            'iddzialki_col',
            'col_name_xy',
            'col_x',
            'col_y'
        ]
        for combobox_name in cbbx_list:
            cbbx_name = getattr(self, combobox_name)
            cbbx_name.clear()
            cbbx_name.addItems(cbbx_nm)

    def populate_layer_combobox(self):
        if self.map_layer_cbbx:
            self.map_layer_cbbx.setFilters(QgsMapLayerProxyModel.VectorLayer)
            self.map_layer_cbbx.setCurrentIndex(-1)

    def collect_objects_from_layer(self) -> List[QgsFeature]:
        self.current_layer = self.map_layer_cbbx.currentLayer()
        if self.geocoding_selected_only_cb.isChecked():
            return self.current_layer.selectedFeatures()
        return [feat for feat in self.current_layer.getFeatures()]

    def perform_geocoding(self):
        self.geocoding_results.clear()
        if self.geocoding_adress.isChecked():
            if self.findChild(QRadioButton, 'adress_single_column').isChecked():
                self.geocode_by_single_address_column()
            elif self.findChild(QRadioButton, 'adress_multi_column').isChecked():
                self.geocode_by_multi_address_column()
        elif self.geocoding_parcels.isChecked():
            self.geocode_by_parcel()
        elif self.geocoding_XY.isChecked():
            self.geocode_by_xy()
        self.update_layer_with_geocoding_results()
        self.show_geocoding_result_message()

    def geocode_by_single_address_column(self):
        separator = self.adress_separator_cbbx.currentText()
        address_field = self.adress_col_cbbx.currentText()
        features = self.collect_objects_from_layer()
        for feature in features:
            address = feature[address_field]
            address_parts = address.split(separator)
            if len(address_parts) >= 3:
                city, street, number = address_parts[:3]
                postal_code = address_parts[3] if len(address_parts) > 3 else ''
            else:
                city, street, number, postal_code = address_parts[0], '', '', ''
            wkt = geocode(city, street, number, postal_code)
            self.geocoding_results.append((feature.id(), wkt))

    def geocode_by_multi_address_column(self):
        features = self.collect_objects_from_layer()
        for feature in features:
            city = feature[self.adress_city_cbbx.currentText()]
            postal_code = feature[self.adress_postal_cbbx.currentText()]
            street = feature[self.adress_street_cbbx.currentText()]
            building = feature[self.adress_building_cbbx.currentText()]
            wkt = geocode(city, street, building, postal_code)
            self.geocoding_results.append((feature.id(), wkt))

    def geocode_by_parcel(self):
        separator = self.iddzialki_separator_cbbx.currentText()
        parcel_id_field = self.iddzialki_col_cbbx.currentText()
        features = self.collect_objects_from_layer()
        for feature in features:
            parcel_id = feature[parcel_id_field]
            wkt = get_parcel_by_id(parcel_id, srid='4326')
            self.geocoding_results.append((feature.id(), wkt))

    def geocode_by_xy(self):
        name_field = self.col_name_xy_cbbx.currentText()
        x_field = self.col_x_cbbx.currentText()
        y_field = self.col_y_cbbx.currentText()
        separator = self.col_x_cbbx.currentText()
        features = self.collect_objects_from_layer()
        crs = self.col_geom_crs_xy.crs()
        transform = QgsCoordinateTransform(crs, QgsCoordinateReferenceSystem('EPSG:4326'), QgsProject.instance())
        for feature in features:
            x = feature[x_field]
            y = feature[y_field]
            try:
                point = QgsPointXY(float(x), float(y))
                transformed_point = transform.transform(point)
                wkt = f"POINT ({transformed_point.x()} {transformed_point.y()})"
            except ValueError:
                wkt = None
            self.geocoding_results.append((feature.id(), wkt))

    def update_layer_with_geocoding_results(self):
        self.current_layer.startEditing()
        for feature_id, wkt in self.geocoding_results:
            if wkt:
                geom = QgsGeometry.fromWkt(wkt)
                self.current_layer.changeGeometry(feature_id, geom)
        self.current_layer.commitChanges()

    def show_geocoding_result_message(self):
        success_count = sum(1 for _, wkt in self.geocoding_results if wkt)
        total_count = len(self.geocoding_results)
        if success_count == total_count:
            QMessageBox.information(self, "Geokodowanie zakończone", "Geokodowanie zakończone sukcesem.")
        else:
            QMessageBox.warning(self, "Geokodowanie zakończone", f"Geokodowanie zakończone z problemami.\nSukces: {success_count}/{total_count}")

    def run(self):
        self.show()
        self.activateWindow()

    def show_add_geometry_column_dialog(self):
        dialog = AddGeometryColumnDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            print("Git")
        else:
            print("Nie git")

def set_project_config(parameter, key, value):
    if isinstance(project, QgsProject):
        return project.writeEntry(parameter, key, value)


def get_project_config(parameter, key, default=''):
    value = project.readEntry(parameter, key, default)[0]
    return value


def save_to_project(height: int, width: int, dlg_name: str) -> None:
    if height and width:
        set_project_config('polamap_windows_sizes', dlg_name, str((height, width)))


def load_from_project(dlg_name) -> Tuple[int, int]:
    w_h_tuple = get_project_config('polamap_windows_sizes', dlg_name, '')
    if w_h_tuple:
        w_h_tuple = literal_eval(w_h_tuple)
        return int(w_h_tuple[0]), int(w_h_tuple[1])
    else:
        return 0, 0


def setup_resize(dlg_instance: QDialog, reject_sig: bool = False) -> None:
    dlg_name = type(dlg_instance).__name__
    dlg_instance.accepted.connect(
        lambda: save_to_project(dlg_instance.height(),
                                dlg_instance.width(),
                                dlg_name)
    )
    if reject_sig:
        dlg_instance.rejected.connect(
            lambda: save_to_project(dlg_instance.height(),
                                    dlg_instance.width(),
                                    dlg_name)
        )
    height, width = load_from_project(dlg_name)
    if width and height:
        dlg_instance.resize(width, height)