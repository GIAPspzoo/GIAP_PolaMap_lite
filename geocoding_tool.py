from __future__ import unicode_literals

import os
import urllib
from ast import literal_eval
import requests
import json
import datetime

from qgis.gui import QgsMapLayerComboBox
from typing import Tuple, List
from qgis.PyQt import QtWidgets, uic
from qgis.core import QgsProject, QgsGeometry, QgsPointXY, \
    QgsMapLayerProxyModel, QgsFeature, \
    QgsCoordinateReferenceSystem, QgsCoordinateTransform
from qgis.PyQt.QtWidgets import QDialog, QRadioButton, QStackedWidget, QMessageBox, QApplication
from qgis.gui import QgsProjectionSelectionWidget

from .utils import CustomMessageBox, TmpCopyLayer, add_map_layer_to_group, tr, ProgressDialog, get_simple_progressbar

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
            X, Y = w['results']['1']['x'],w['results']['1']['y']
            return geomWkt, X, Y
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
        ui_file = os.path.join(os.path.dirname(__file__), 'geocoding_tool.ui')
        uic.loadUi(ui_file, self)
        setup_resize(self)
        self.frame_many.hide()

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
        self.groupBox_x_and_y.toggled.connect(self.CheckBoxStateChangedXY)
        self.groupBox_x_y.toggled.connect(self.CheckBoxStateChangedXorY)

    def CheckBoxStateChangedXY(self):
        if self.groupBox_x_and_y.isChecked():
            self.groupBox_x_y.setChecked(False)

    def CheckBoxStateChangedXorY(self):
        if self.groupBox_x_y.isChecked():
            self.groupBox_x_and_y.setChecked(False)

    def switch_page(self):
        if self.geocoding_adress.isChecked():
            self.stacked_widget.setCurrentIndex(0)
        elif self.geocoding_parcels.isChecked():
            self.stacked_widget.setCurrentIndex(1)
        elif self.geocoding_XY.isChecked():
            self.stacked_widget.setCurrentIndex(2)

    def cbbx_menager(self):
        try:
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
            if hasattr(self, 'tmp_layer'):
                del self.tmp_layer
        except:
            pass

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
        if not self.map_layer_cbbx.currentLayer():
            CustomMessageBox(self, tr('Select a layer to geocode!')).button_ok()
            return
        if not self.map_layer_cbbx.currentLayer().crs().authid() and not hasattr(self, 'tmp_layer'):
            CustomMessageBox(self, tr('No layout specified in source layer! Add geometry column!')).button_ok()
            return
        rees = True
        self.geocoding_results.clear()
        self.progress = ProgressDialog(self, tr("ULDK..."))
        self.progress.start()
        QApplication.processEvents()
        if self.geocoding_adress.isChecked():
            if self.findChild(QRadioButton, 'adress_single_column').isChecked():
                self.geocode_by_single_address_column()
            elif self.findChild(QRadioButton, 'adress_multi_column').isChecked():
                self.geocode_by_multi_address_column()
        elif self.geocoding_parcels.isChecked():
            self.geocode_by_parcel()
        elif self.geocoding_XY.isChecked():
            rees = self.geocode_by_xy()
        if rees:
            self.update_layer_with_geocoding_results()
            self.show_geocoding_result_message()

    def geocode_by_single_address_column(self):
        separator = self.adress_separator_cbbx.currentText()
        address_field = self.adress_col_cbbx.currentText()

        if hasattr(self, 'tmp_layer'):
            transform = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:2180"), self.tmp_layer.crs(),
                                               QgsProject.instance())
            for feature in self.tmp_layer.getFeatures():
                QApplication.processEvents()
                address = feature[address_field]
                address_parts = address.split(separator)
                if len(address_parts) >= 3:
                    city, street, number = address_parts[:3]
                    postal_code = address_parts[3] if len(address_parts) > 3 else ''
                else:
                    city, street, number, postal_code = address_parts[0], '', '', ''
                try:
                    wkt, x, y = geocode(city, street, number, postal_code)
                except:
                    continue
                point = QgsPointXY(float(x), float(y))
                transformed_point = transform.transform(point)
                wkt = f"POINT ({transformed_point.x()} {transformed_point.y()})"
                self.geocoding_results.append((feature.id(), wkt))
        else:
            features = self.collect_objects_from_layer()
            transform = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:2180"), self.current_layer.crs(),
                                               QgsProject.instance())
            for feature in features:
                QApplication.processEvents()
                address = feature[address_field]
                address_parts = address.split(separator)
                if len(address_parts) >= 3:
                    city, street, number = address_parts[:3]
                    postal_code = address_parts[3] if len(address_parts) > 3 else ''
                else:
                    city, street, number, postal_code = address_parts[0], '', '', ''
                try:
                    wkt, x, y = geocode(city, street, number, postal_code)
                except:
                    continue
                point = QgsPointXY(float(x), float(y))
                transformed_point = transform.transform(point)
                wkt = f"POINT ({transformed_point.x()} {transformed_point.y()})"
                self.geocoding_results.append((feature.id(), wkt))

    def geocode_by_multi_address_column(self):
        if hasattr(self, 'tmp_layer'):
            transform = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:2180"), self.tmp_layer.crs(),
                                               QgsProject.instance())
            for feature in self.tmp_layer.getFeatures():
                QApplication.processEvents()
                city = feature[self.adress_city_cbbx.currentText()]
                postal_code = feature[self.adress_postal_cbbx.currentText()]
                street = feature[self.adress_street_cbbx.currentText()]
                building = feature[self.adress_building_cbbx.currentText()]
                wkt, x, y = geocode(city, street, building, postal_code)
                point = QgsPointXY(float(x), float(y))
                transformed_point = transform.transform(point)
                wkt = f"POINT ({transformed_point.x()} {transformed_point.y()})"
                self.geocoding_results.append((feature.id(), wkt))
        else:
            features = self.collect_objects_from_layer()
            transform = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:2180"), self.current_layer.crs(),
                                               QgsProject.instance())
            for feature in features:
                QApplication.processEvents()
                city = feature[self.adress_city_cbbx.currentText()]
                postal_code = feature[self.adress_postal_cbbx.currentText()]
                street = feature[self.adress_street_cbbx.currentText()]
                building = feature[self.adress_building_cbbx.currentText()]
                wkt, x, y = geocode(city, street, building, postal_code)
                point = QgsPointXY(float(x), float(y))
                transformed_point = transform.transform(point)
                wkt = f"POINT ({transformed_point.x()} {transformed_point.y()})"
                self.geocoding_results.append((feature.id(), wkt))

    def geocode_by_parcel(self):
        separator = self.iddzialki_separator_cbbx.currentText()
        parcel_id_field = self.iddzialki_col_cbbx.currentText()
        if hasattr(self, 'tmp_layer'):
            for feature in self.tmp_layer.getFeatures():
                QApplication.processEvents()
                parcel_id = feature[parcel_id_field]
                pracels_id_list = str(parcel_id).split(separator)
                feat_geom_list = []
                for parcel_id in pracels_id_list:
                    QApplication.processEvents()
                    try:
                        wkt = get_parcel_by_id(parcel_id.strip(), srid=str(self.tmp_layer.crs().postgisSrid()))
                    except ConnectionError:
                        continue
                    if wkt:
                        feat_geom_list.append(QgsGeometry().fromWkt(wkt))
                if feat_geom_list:
                    combined_geom = combine_geoms(feat_geom_list)
                    combined_geom.convertToMultiType()
                    self.geocoding_results.append((feature.id(), combined_geom))
        else:
            features = self.collect_objects_from_layer()
            for feature in features:
                QApplication.processEvents()
                parcel_id = feature[parcel_id_field]
                pracels_id_list = str(parcel_id).split(separator)
                feat_geom_list = []
                for parcel_id in pracels_id_list:
                    QApplication.processEvents()
                    try:
                        wkt = get_parcel_by_id(parcel_id.strip(), srid=str(self.current_layer.crs().postgisSrid()))
                    except ConnectionError:
                        continue
                    if wkt:
                        feat_geom_list.append(QgsGeometry().fromWkt(wkt))
                if feat_geom_list:
                    combined_geom = combine_geoms(feat_geom_list)
                    combined_geom.convertToMultiType()
                    self.geocoding_results.append((feature.id(), combined_geom))

    def geocode_by_xy(self):
        if (self.groupBox_x_and_y.isChecked() and self.groupBox_x_y.isChecked()) or \
            (not self.groupBox_x_and_y.isChecked() and not self.groupBox_x_y.isChecked()):
            CustomMessageBox(self, tr('Choose one of the options!')).button_ok()
            self.progress.stop()
            return False
        if self.groupBox_x_and_y.isChecked():
            name_field = self.col_name_xy_cbbx.currentText()
            separator = self.xy_separator.currentText()

        if self.groupBox_x_y.isChecked():
            x_field = self.col_x_cbbx.currentText()
            y_field = self.col_y_cbbx.currentText()
        crs = self.col_geom_crs_xy.crs()
        if hasattr(self, 'tmp_layer'):
            try:
                transform = QgsCoordinateTransform(crs, self.tmp_layer.crs(), QgsProject.instance())
            except:
                CustomMessageBox(self, tr('No layout specified in source layer! Add geometry column!')).button_ok()
                self.progress.stop()
                return False
            for feature in self.tmp_layer.getFeatures():
                QApplication.processEvents()
                if self.groupBox_x_y.isChecked():
                    x = feature[x_field]
                    y = feature[y_field]
                elif self.groupBox_x_and_y.isChecked():
                    xy = feature[name_field]
                    try:
                        x, y = xy.split(separator)
                    except ValueError:
                        CustomMessageBox(self,
                                         tr('Incorrect field or separator!')).button_ok()
                        self.progress.stop()
                        return False
                point = QgsPointXY(float(x), float(y))
                try:
                    transformed_point = transform.transform(point)
                    wkt = f"POINT ({transformed_point.x()} {transformed_point.y()})"
                except:
                    transformed_point = point
                    wkt = f"POINT ({transformed_point.x()} {transformed_point.y()})"
                self.geocoding_results.append((feature.id(), wkt))
        else:
            features = self.collect_objects_from_layer()
            transform = QgsCoordinateTransform(crs, self.current_layer.crs(), QgsProject.instance())
            for feature in features:
                QApplication.processEvents()
                if self.groupBox_x_y.isChecked():
                    x = feature[x_field]
                    y = feature[y_field]
                elif self.groupBox_x_and_y.isChecked():
                    xy = feature[name_field]
                    try:
                        x, y = xy.split(separator)
                    except ValueError:
                        CustomMessageBox(self,
                                         tr('Incorrect field or separator!')).button_ok()
                        self.progress.stop()
                        return False
                point = QgsPointXY(float(x), float(y))
                try:
                    transformed_point = transform.transform(point)
                    wkt = f"POINT ({transformed_point.x()} {transformed_point.y()})"
                except:
                    transformed_point = point
                    wkt = f"POINT ({transformed_point.x()} {transformed_point.y()})"
                self.geocoding_results.append((feature.id(), wkt))
        return True

    def update_layer_with_geocoding_results(self):
        if hasattr(self, 'tmp_layer'):
            self.tmp_layer.startEditing()
            for feature_id, wkt in self.geocoding_results:
                if wkt:
                    try:
                        geom = QgsGeometry.fromWkt(wkt)
                    except:
                        geom = wkt
                    self.tmp_layer.changeGeometry(feature_id, geom)
            self.tmp_layer.commitChanges()
        else:
            self.current_layer.startEditing()
            for feature_id, wkt in self.geocoding_results:
                if wkt:
                    try:
                        geom = QgsGeometry.fromWkt(wkt)
                    except:
                        geom = wkt
                    self.current_layer.changeGeometry(feature_id, geom)
            self.current_layer.commitChanges()

    def show_geocoding_result_message(self):
        success_count = sum(1 for _, wkt in self.geocoding_results if wkt)
        total_count = len(self.geocoding_results)
        self.progress.stop()
        if success_count == total_count:
            if total_count == 0:
                QMessageBox.information(self, tr("Geocoding completed"), f"""{tr('Geocoding completed with problems. Success:')} 0/0""")
            else:
                QMessageBox.information(self, tr("Geocoding completed"), tr("Geocoding completed successfully."))
            if hasattr(self, 'tmp_layer'):
                del self.tmp_layer
        else:
            QMessageBox.warning(self, tr("Geocoding completed"),
                                f"""{tr('Geocoding completed with problems. Success:')} {success_count}/{total_count}""")

    def run(self):
        self.show()
        self.activateWindow()

    def show_add_geometry_column_dialog(self):
        dialog = AddGeometryColumnDialog(self)
        dialog.geom_type.clear()
        dialog.geom_type.addItems([tr('POINT'), tr('POLYGON')])
        projCrs = QgsProject.instance().crs()
        dialog.mQgsProjectionSelectionWidget.setCrs(projCrs)
        if not self.map_layer_cbbx.currentLayer():
            CustomMessageBox(self, tr("Select layer!")).button_ok()
            return
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            crs = dialog.mQgsProjectionSelectionWidget.crs().authid()
            geom_type = ''
            if dialog.geom_type.currentText() in ['PUNKT', 'POINT']:
                geom_type = 'MultiPoint'
            elif dialog.geom_type.currentText() in ['POLIGON', 'POLYGON']:
                geom_type = 'MultiPolygon'
            data_time = str(str(datetime.datetime.now()).replace(":", "-")).replace(" ", "_")
            self.tmp_layer = TmpCopyLayer(
                "{}?crs={}".format(geom_type, crs),
                f"{self.map_layer_cbbx.currentLayer().name()}_{data_time}",
                "memory")
            self.tmp_layer.set_fields_from_layer(self.map_layer_cbbx.currentLayer())
            features_list = []
            if self.geocoding_selected_only_cb.isChecked():
                for feature in self.map_layer_cbbx.currentLayer().selectedFeatures():
                    features_list.append(feature)
            else:
                for feature in self.map_layer_cbbx.currentLayer().getFeatures():
                    features_list.append(feature)
            self.tmp_layer.add_features(features_list)
            add_map_layer_to_group(self.tmp_layer, '')
            CustomMessageBox(self, f"""{tr('Added geometry column to layer:')} {self.map_layer_cbbx.currentLayer().name()}_{data_time}""").button_ok()

def combine_geoms(geoms_list):
    geoms_list_len = len(geoms_list)
    if geoms_list_len == 0:
        return
    elif geoms_list_len == 1:
        return geoms_list[0]
    elif geoms_list_len > 1:
        union_geoms = geoms_list[0]
        for geometry in geoms_list[1:]:
            if geometry.isGeosValid():
                union_geoms = union_geoms.combine(geometry)
        return union_geoms

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
