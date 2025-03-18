# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import tempfile
import random
import processing

from tempfile import mkstemp
from datetime import datetime
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import QRectF, QSettings, QVariant, NULL
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtWidgets import QFileDialog, QApplication
from qgis.core import QgsLayoutExporter, QgsWkbTypes, QgsLayoutItemMap, \
    QgsLayout, QgsProject, QgsUnitTypes, QgsLayoutSize, QgsGeometry, \
    QgsVectorLayer, QgsFeature, QgsSymbol, QgsSimpleFillSymbolLayer, \
    QgsLayoutItemLabel, QgsLayoutItemScaleBar, QgsRasterLayer, \
    QgsRasterFileWriter, QgsVectorFileWriter, QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsRectangle, \
    QgsProcessingContext, QgsMessageLog, QgsPointXY, Qgis, QgsTextFormat, QgsFillSymbol, QgsLayoutItemShape, \
    QgsLayoutMeasurement, QgsMapLayer, QgsScaleBarSettings
from qgis.gui import QgsRubberBand, QgisInterface
from qgis.utils import iface
from typing import Union

from .utils import tr, CustomMessageBox, normalize_path, IdentifyGeometryByType, transform_geometry, \
    identify_layer_by_name
from .wydruk_dialog import WydrukDialog
from .config import Config

pdf_open_error_msg = '''
    Nie znaleziono programu do otwierania plików PDF. Sprawdź, czy jest\n
    zainstalowany program do otwierania plików PDF, np. Acrobat Reader.\n
    Jeżeli tak, sprawdź, czy pliki PDF otwierają się po podwójnym kliknięciu.\n
    Jeżeli nie, ustaw skojarzenie dla plików PDF z tą przeglądarką plików PDF.
'''
project = QgsProject.instance()
root = project.layerTreeRoot()
QGIS_LTR_VERSION = 33400

def get_project_crs():
    return iface.mapCanvas().mapSettings().destinationCrs()

def only_preview_file(output_file:str) -> None:
    output_file = normalize_path(output_file)
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', output_file))
    elif os.name in ('nt', 'posix'):
        try:
            if os.name == 'nt':
                os.startfile(output_file)
            else:
                subprocess.call(('xdg-open', output_file))
        except OSError:
            CustomMessageBox(None, pdf_open_error_msg).button_ok()


def get_layer_with_selection() -> None:
    layer_with_selection = []
    for layer in list(QgsProject.instance().mapLayers().values()):
        if layer.type().value == 0 and layer.selectedFeatureCount():
            layer_with_selection.append(layer)
    return layer_with_selection


def copy_symbolization(src_layer, dest_layer):
    tmp_qml = get_tmp_symbolization_file(src_layer)
    save_symbolization_and_remove_tmp(dest_layer, tmp_qml)


def get_tmp_symbolization_file(layer):
    file_handle, tmp_qml = mkstemp(suffix='.qml')
    os.close(file_handle)
    layer.saveNamedStyle(tmp_qml)
    return tmp_qml


def save_symbolization_and_remove_tmp(layer, tmp_qml):
    layer.loadNamedStyle(tmp_qml)
    os.remove(tmp_qml)

def check_if_value_empty(value: Union[str, None, QVariant]) -> bool:
    return value in [None, NULL, 'NULL', 'None', '']

class PrintMapTool:
    mm_paper_sizes = {
        'A0': (841, 1189),
        'A1': (594, 841),
        'A2': (420, 594),
        'A3': (297, 420),
        'A4': (210, 297),
        'A5': (148, 210)
    }

    dict_width = {148: 50,
                  210: 90,
                  297: 145,
                  420: 220,
                  594: 335,
                  841: 475,
                  1189: 700}

    def __init__(self, iface : QgisInterface, parent : QtWidgets=None) -> None:
        self.iface = iface
        self.dialog = WydrukDialog()
        self.dialog.pdfRadioButton.setChecked(True)
        self.dialog.horizontalRadioButton.setChecked(True)
        self.dialog.verticalRadioButton.clicked.connect(self.create_composer)
        self.dialog.horizontalRadioButton.clicked.connect(self.create_composer)
        self.dialog.savePushButton.clicked.connect(self.save)
        self.dialog.previewPushButton.clicked.connect(self.preview)
        self.dialog.cancelPushButton.clicked.connect(self.dialog.reject)
        self.dialog.rejected.connect(self.rejected_dialog)
        self.dialog.legendCheckBox.hide()
        paper_format_items = sorted(self.mm_paper_sizes.keys())
        self.dialog.paperFormatComboBox.addItems(paper_format_items)
        self.dialog.paperFormatComboBox.setCurrentIndex(
            paper_format_items.index("A4"))
        self.dialog.paperFormatComboBox.currentIndexChanged.connect(
            self.create_composer)
        self.setup_rubberband()
        self.canvas_extent = iface.mapCanvas().extent()
        self.conf = Config()
        if 'font_changed' in self.conf.setts.keys():
            if self.conf.setts['font_changed']:
                self.set_font_quickprint(QSettings().value("qgis/stylesheet/fontPointSize"))
        else:
            self.conf.set_value('font_changed', False)
            self.conf.save_config()

        self.white_mask = None
        self.dialog.lineEdit_maska.hide()
        self.dialog.lineEdit_maska.setEnabled(False)
        self.dialog.wskaz_z_mapy_pb.hide()
        self.dialog.dodaj_warstwy_checkBox.hide()
        self.dialog.biezacy_widok_rb.setChecked(True)

        radioButtons = [self.dialog.maska_rb, self.dialog.pdfRadioButton, self.dialog.pngRadioButton,
                        self.dialog.jpgRadioButton, self.dialog.shpRadioButton,
                        self.dialog.tiffRadioButton]
        for btn in radioButtons:
            btn.toggled.connect(self.show_hide_items)

        self.dialog.biezacy_widok_rb.toggled.connect(self.zoom_to_frame)
        self.dialog.caly_zasieg_rb.toggled.connect(self.zoom_to_frame)
        self.dialog.maska_rb.toggled.connect(self.zoom_to_frame)

        self.dialog.wskaz_z_mapy_pb.clicked.connect(self.draw_polygon_object_from_other_layer)

    def check_if_vector_format(self):
        return self.dialog.shpRadioButton.isChecked()

    def show_hide_items(self):
        if self.dialog.maska_rb.isChecked():
            self.dialog.lineEdit_maska.show()
            self.dialog.wskaz_z_mapy_pb.show()
        else:
            self.dialog.lineEdit_maska.hide()
            self.dialog.wskaz_z_mapy_pb.hide()
        if self.check_if_vector_format():
            self.dialog.groupBox.hide()
            self.dialog.groupBox_2.hide()
            self.dialog.groupBox_4.hide()
            self.dialog.groupBox_6.hide()
            self.dialog.groupBox_5.hide()
            self.dialog.groupBox_7.hide()
            self.dialog.previewPushButton.hide()
            self.dialog.dodaj_warstwy_checkBox.show()
            if self.dialog.skala_projektu_rb.isChecked():
                self.dialog.biezacy_widok_rb.setChecked(True)
            self.dialog.skala_projektu_rb.hide()
        else:
            self.dialog.groupBox.show()
            self.dialog.groupBox_2.show()
            self.dialog.groupBox_4.show()
            self.dialog.groupBox_6.show()
            self.dialog.groupBox_5.show()
            self.dialog.groupBox_7.show()
            self.dialog.previewPushButton.show()
            self.dialog.dodaj_warstwy_checkBox.hide()
            self.dialog.skala_projektu_rb.show()

    def draw_polygon_object_from_other_layer(self):
        wkb_types_list = [QgsWkbTypes.Polygon, QgsWkbTypes.MultiPolygon]
        self.old_tool = self.iface.mapCanvas().mapTool()
        self.mapTool = IdentifyGeometryByType(self.iface.mapCanvas(), wkb_types_list)
        self.iface.mainWindow().activateWindow()
        self.mapTool.identifyMenu().setAllowMultipleReturn(False)
        self.mapTool.identifyMenu().setMaxLayerDisplay(30)
        self.mapTool.geomIdentified.connect(self.fill_lineEdit)
        self.iface.mapCanvas().unsetMapTool(self.old_tool)
        self.iface.mapCanvas().setMapTool(self.mapTool)
        self.dialog.rejected.connect(self.set_unset_map_tool)

    def fill_lineEdit(self, results):
        self.layer_list = []
        for result in results:
            copy_layer = result.mLayer
            feature = result.mFeature
            if feature:
                self.dialog.lineEdit_maska.setText(f"{copy_layer.name()}: {feature.id()}")
                self.frame_composer()
                self.zoom_to_frame()
        self.set_unset_map_tool()
        self.run()

    def frame_composer(self):
        self.create_composer()
        if not self.dialog.biezacy_widok_rb.isChecked():
            self.zoom_to_frame()
            if self.dialog.maska_rb.isChecked():
                try:
                    layer, feature = self.get_feature_from_lineedit(True)
                    geom = transform_geometry(feature.geometry(), layer)
                    self.white_mask = self.create_inverted_layer(layer, geom)
                except:
                    pass

    def get_feature_from_lineedit(self, return_layer=False):
        text = self.dialog.lineEdit_maska.text().split(": ")
        layer = identify_layer_by_name(text[0])
        if layer:
            feature_id = text[1]
            feature = layer.getFeature(int(feature_id))
            if feature:
                if return_layer:
                    return layer, feature
                else:
                    return feature
            else:
                CustomMessageBox(self.dialog, "Nie udało się stworzyć maski, wybierz inny obiekt").button_ok()
        else:
            CustomMessageBox(self.dialog, "Nie udało się stworzyć maski, wybierz inny obiekt").button_ok()

    def create_inverted_layer(self, layer, geometry):
        if not check_if_value_empty(self.rect):
            rect = QgsGeometry.fromRect(self.rect)
            inverted_geometry = rect.difference(geometry)
            layer = QgsVectorLayer(
                f"{QgsWkbTypes.displayString(layer.wkbType())}?crs={self.iface.mapCanvas().mapSettings().destinationCrs()}",
                "tmp_mask", "memory")
            feat = QgsFeature()
            feat.setGeometry(inverted_geometry)
            layer.startEditing()
            layer.addFeatures([feat])
            fill_symbol = QgsFillSymbol.createSimple({'color': '255,255,255,255'})
            fill_symbol.setOpacity(100)
            layer.renderer().setSymbol(fill_symbol)
            layer.commitChanges()
            return layer

    def set_unset_map_tool(self):
        self.iface.mapCanvas().unsetMapTool(self.mapTool)
        self.iface.mapCanvas().setMapTool(self.old_tool)

    def zoom_to_frame(self):
        self.create_composer()
        feature = False
        layer = False
        if self.dialog.caly_zasieg_rb.isChecked():
            layer = self.get_largest_extent_layer()
        if self.dialog.maska_rb.isChecked():
            if self.dialog.lineEdit_maska.text():
                layer, feature = self.get_feature_from_lineedit(True)
                geom = transform_geometry(feature.geometry(), layer)
        if layer:
            self.iface.layerTreeView().setLayerVisible(layer, True)
            if feature:
                mapExtent = geom.boundingBox()
            else:
                mapExtent = layer.extent()
            self.canvas_extent = QgsRectangle(mapExtent.xMinimum(), mapExtent.yMinimum(),
                                              mapExtent.xMaximum(), mapExtent.yMaximum()).buffered(
                (mapExtent.height() + mapExtent.width()) * 0.01)
            self.iface.mapCanvas().setExtent(self.band.buffered((mapExtent.height() + mapExtent.width()) * 0.1))
            self.iface.mapCanvas().refresh()

    def set_font_quickprint(self, font_size: str) -> None:
        attributes = [self.dialog.label_side, self.dialog.title_label,
                      self.dialog.cancelPushButton, self.dialog.previewPushButton,
                      self.dialog.savePushButton, self.dialog.calendar]
        for attr in attributes:
            attr.setStyleSheet(f'{attr.styleSheet()} font: {font_size}pt;')
        self.dialog.frame_main.setStyleSheet(
            f'{self.dialog.frame_main.styleSheet()} QGroupBox, QCheckBox, QToolButton, '
            f'QLineEdit, QRadioButton, QComboBox, QSpinBox, QProgressBar {{font: {font_size}pt;}}')

    def setup_rubberband(self) -> None:
        self.rubberband = QgsRubberBand(iface.mapCanvas(), QgsWkbTypes.PolygonGeometry)
        self.rubberband.setColor(QColor(255, 0, 0, 100))
        self.rubberband.setWidth(5)
        self.rubberband.setFillColor(QColor(255, 255, 255, 0))
        self.is_active = False

    def get_paper_size(self, paper_format=''):
        if check_if_value_empty(paper_format):
            paper_format = self.dialog.paperFormatComboBox.currentText()
        width, height = self.mm_paper_sizes[paper_format]

        if self.dialog.horizontalRadioButton.isChecked():
            return height, width
        if self.dialog.verticalRadioButton.isChecked():
            return width, height

    def set_adnotation_limit(self, width: int) -> None:
        self.dialog.adnotacje_lineEdit.setMaxLength(self.dict_width[width])

    def get_map_item(self) -> QgsLayoutItemMap:
        item_object = None
        for item in self.layout.items():
            if isinstance(item, QgsLayoutItemMap):
                item_object = item
        return item_object

    def create_composer(self) -> None:
        self.reset_rubber()
        if self.is_active:
            self.layout = QgsLayout(QgsProject.instance())
            self.layout.initializeDefaults()
            self.layout.setUnits(QgsUnitTypes.LayoutMillimeters)
            page = self.layout.pageCollection().pages()[0]

            width_a4, height_a4 = self.get_paper_size(paper_format='A4')
            width, height = self.get_paper_size()
            pos_x, pos_y = 16, 16
            page.setPageSize(QgsLayoutSize(width, height))
            if get_project_crs().authid() != QgsProject.instance().crs().authid():
                self.canvas_extent = self.transform_geometry_by_crs(self.canvas_extent,
                                                                    get_project_crs(),
                                                                    QgsProject.instance().crs())
            a4_rect = QRectF(pos_x, pos_y, width_a4 - 2 * pos_x, height_a4 - 2 * pos_y)
            current_rect = QRectF(pos_x, pos_y, width - 2 * pos_x, height - 2 * pos_y)

            map_item = QgsLayoutItemMap(self.layout)
            map_item2 = QgsLayoutItemMap(self.layout)
            for item in [map_item, map_item2]:
                item.updateBoundingRect()
                item.setRect(current_rect)
                item.setPos(pos_x, pos_y)
                item.setFrameEnabled(True)
            map_item.setLayers(project.mapThemeCollection().masterVisibleLayers())
            if self.dialog.biezacy_widok_rb.isChecked():
                self.canvas_extent = self.iface.mapCanvas().extent()
                self.scale = self.iface.mapCanvas().scale()
                map_item.setRect(a4_rect)
                map_item.setExtent(self.canvas_extent)
                map_item.setScale(round(self.scale))
                map_item.attemptSetSceneRect(current_rect, True)

            if self.dialog.skala_projektu_rb.isChecked():
                self.canvas_extent = self.iface.mapCanvas().extent()
                self.scale = self.iface.mapCanvas().scale()
                map_item.setRect(a4_rect)
                map_item.setExtent(self.canvas_extent)
                map_item.attemptSetSceneRect(current_rect, True)
                map_item.setScale(round(self.scale))
            else:
                map_item.attemptSetSceneRect(current_rect, True)
                if not self.dialog.biezacy_widok_rb.isChecked():
                    map_item.zoomToExtent(self.canvas_extent)
                if self.dialog.maska_rb.isChecked():
                    if not check_if_value_empty(self.white_mask):
                        map_item2.zoomToExtent(self.canvas_extent)
                        map_item2.setLayers([self.white_mask])
                        map_item2.attemptSetSceneRect(current_rect, True)
                        map_item2.setBackgroundColor(QColor(0, 0, 0, 0))
                        self.layout.addItem(map_item2)
            rubber_band_extent = self.get_rubber_band_extent(map_item.extent())
            self.band = rubber_band_extent
            self.rect = map_item.extent()
            self.rubberband.addGeometry(QgsGeometry.fromRect(rubber_band_extent), QgsVectorLayer())
            self.layout.addItem(map_item)

    def transform_geometry_by_crs(self, geometry, source_crs, destination_crs):
        xform = QgsCoordinateTransform(source_crs, destination_crs, project)
        if isinstance(geometry, (QgsPointXY, QgsRectangle)):
            geom_in_dest_crs = xform.transform(geometry)
        else:
            geom_in_dest_crs = QgsGeometry(geometry)
            geom_in_dest_crs.transform(xform)
        return geom_in_dest_crs

    def get_rubber_band_extent(self, map_item_extent):
        if get_project_crs().authid() != QgsProject.instance().crs().authid():
            return self.transform_geometry_by_crs(map_item_extent,
                                                  QgsProject.instance().crs(),
                                                  get_project_crs())
        return map_item_extent

    def reset_rubber(self) -> None:
        self.rubberband.reset(QgsWkbTypes.PolygonGeometry)

    def rejected_dialog(self) -> None:
        self.is_active = False
        self.reset_rubber()
        self.iface.mapCanvas().setMagnificationFactor(1)
        try:
            self.iface.mapCanvas().scaleChanged.disconnect(
                self.create_composer
            )
        except TypeError:
            pass

    def run(self) -> None:
        if not self.is_active:
            self.is_active = True
            self.iface.mapCanvas().scaleChanged.connect(self.create_composer)
            self.create_composer()
            self.dialog.show()
            self.dialog.exec_()
        else:
            self.dialog.activateWindow()

    def save(self) -> None:
        if self.dialog.maska_rb.isChecked():
            if not self.dialog.lineEdit_maska.text():
                CustomMessageBox(self.dialog, 'Sprawdz maskę przycięcia!').button_ok()
                return
        file_dialog = QFileDialog()
        dialog_text = "Zapisz Plik"
        dir_path = os.path.dirname(os.path.dirname(os.path.abspath(project.fileName())))
        if self.check_if_vector_format():
            dir_path = os.path.dirname(os.path.dirname(os.path.abspath(project.fileName())))
            dialog_text = "Wybierz folder"
            filename = file_dialog.getExistingDirectory(self.dialog, caption=dialog_text, directory=dir_path)
        else:
            filename, __ = file_dialog.getSaveFileName(self.dialog, caption=dialog_text, directory=dir_path)
        if filename:
            self.dialog.progressBar.show()
            self.dialog.progressBar.setValue(10)
            tmp_layer = self.create_tmp_layer()
            self.create_composer()
            self.dialog.progressBar.setValue(20)
            self.save_file(filename)
            root = QgsProject.instance().layerTreeRoot()
            for layer in tmp_layer:
                root.removeLayer(layer)
            self.dialog.close()

    def preview(self) -> None:
        if self.dialog.maska_rb.isChecked():
            if not self.dialog.lineEdit_maska.text():
                CustomMessageBox(self.dialog, 'Sprawdz maskę przycięcia!').button_ok()
                return
        file_handle, filename = tempfile.mkstemp(suffix='quick_print')
        os.close(file_handle)
        tmp_layer = self.create_tmp_layer()
        self.create_composer()
        self.save_file(filename)
        QgsProject.instance().removeMapLayers(tmp_layer)

    def create_tmp_layer(self) -> list:
        layers_with_selection = get_layer_with_selection()
        temps_layer_list = []
        tmp_layer = None
        for layer_with_selection in layers_with_selection:
            if layer_with_selection:
                features = layer_with_selection.selectedFeatures()
                types = {
                    QgsWkbTypes.Point: "Point",
                    QgsWkbTypes.LineString: "LineString",
                    QgsWkbTypes.Polygon: "Polygon",
                    QgsWkbTypes.MultiPoint: "MultiPoint",
                    QgsWkbTypes.MultiLineString: "MultiLineString",
                    QgsWkbTypes.MultiPolygon: "MultiPolygon"
                }
                type = layer_with_selection.wkbType()
                try:
                    tmp_type = types[type]
                except KeyError:
                    return
                tmp_layer = QgsVectorLayer('%s?crs=%s' % (
                tmp_type, layer_with_selection.crs().authid()),
                                           'tmp_layer_fast_print', "memory")
                tmp_features = []
                for feature in features:
                    qgs_feat = QgsFeature()
                    qgs_feat.setGeometry(QgsGeometry(feature.geometry()))
                    tmp_features.append(qgs_feat)
                tmp_layer.dataProvider().addFeatures(tmp_features)
                QgsProject.instance().addMapLayer(tmp_layer)
                selection_color = self.iface.mapCanvas().mapSettings().selectionColor()
                symbol = QgsSymbol.defaultSymbol(tmp_layer.geometryType())
                layer_style = {}
                color_str = ','.join([str(selection_color.red()),
                                      str(selection_color.green()),
                                      str(selection_color.blue()),
                                      str(selection_color.alpha())])
                layer_style['color'] = color_str
                layer_style['outline'] = color_str
                layer_style['color_border'] = color_str
                layer_style['style_border'] = 'no'
                symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
                symbol.changeSymbolLayer(0, symbol_layer)
                tmp_layer.renderer().setSymbol(symbol)
                QApplication.processEvents()
            temps_layer_list.append(tmp_layer)
        return temps_layer_list

    def save_file(self, filename:str) -> None:
        progress = self.dialog.progressBar
        width, height = self.get_paper_size()
        if self.dialog.scaleCheckBox.isChecked():
            map_item = self.get_map_item()
            scale_label = QgsLayoutItemLabel(self.layout)
            scale_label.setText(f'''{tr("SCALE:")} 1:{round(map_item.scale())}''')
            if Qgis.QGIS_VERSION_INT < QGIS_LTR_VERSION:
                scale_label.adjustSizeToText()
            self.layout.addItem(scale_label)
            scale_label.moveBy(16, height - 14.)

        if self.dialog.dateCheckBox.isChecked():
            date_label = QgsLayoutItemLabel(self.layout)
            date_label.setText(self.dialog.dateedit.text())
            if Qgis.QGIS_VERSION_INT < QGIS_LTR_VERSION:
                date_label.adjustSizeToText()
            self.layout.addItem(date_label)
            if self.dialog.scaleCheckBox.isChecked():
                date_label.moveBy(16, scale_label.y() + 5)
            else:
                date_label.moveBy(16, height - 14.)

        if self.dialog.titleLineEdit.text():
            title = QgsLayoutItemLabel(self.layout)
            current_text = ' '
            title.setText(self.dialog.titleLineEdit.text() + current_text)
            if Qgis.QGIS_VERSION_INT < QGIS_LTR_VERSION:
                title_font = QFont()
                title_font.setPointSize(20)
                title_font.setWeight(75)
                title.setFont(title_font)
            else:
                text_format = QgsTextFormat()
                item_font = QFont('Arial')
                text_format.setFont(item_font)
                text_format.setSize(20)
                text_format.setForcedBold(True)
                title.setTextFormat(text_format)
            title.adjustSizeToText()
            title.setPos((width / 2) - (len(self.dialog.titleLineEdit.text()) * 2),
                         3)
            self.layout.addItem(title)

        if self.dialog.adnotacje_lineEdit.text():
            adnotation = QgsLayoutItemLabel(self.layout)
            adnotation.setText(self.dialog.adnotacje_lineEdit.text())
            adnotation.adjustSizeToText()
            self.layout.addItem(adnotation)
            adnotation.moveBy(width - adnotation.rectWithFrame().width() - 16, height - 14)

        if self.dialog.line_checkBox.isChecked():
            map_item = self.get_map_item()
            scale_label = QgsLayoutItemLabel(self.layout)
            scale_label.setText("SKALA: 1:{:,.0f}".format(round(map_item.scale())).replace(",", " "))
            scale_font = QFont()
            scale_label.setFont(scale_font)
            if Qgis.QGIS_VERSION_INT < QGIS_LTR_VERSION:
                scale_label.adjustSizeToText()

            scalebar = QgsLayoutItemScaleBar(self.layout)
            scalebar.setStyle('Line Ticks Up')
            scalebar.setUnits(QgsUnitTypes.DistanceMeters)
            scalebar.setNumberOfSegments(4)
            scalebar.setNumberOfSegmentsLeft(0)
            scalebar.setSegmentSizeMode(QgsScaleBarSettings.SegmentSizeFitWidth)
            scalebar.setUnitsPerSegment(1000)
            scalebar.setLinkedMap(map_item)
            scalebar.setUnitLabel('m')
            scalebar.setMaximumBarWidth(80)
            scalebar.setFont(QFont('Arial', 8))
            scalebar.setBrush(QColor(255, 255, 255))
            scalebar.setBackgroundEnabled(True)
            scalebar.setFrameEnabled(True)
            scalebar.update()
            self.layout.addItem(scalebar)
            scalebar.moveBy(16.15, height-29.35)

        progress.show()
        progress.setValue(20)
        if filename:
            if self.dialog.jpgRadioButton.isChecked():
                ext = '.jpg'
                function = self.print_image
            elif self.dialog.pngRadioButton.isChecked():
                ext = '.png'
                function = self.print_image
            elif self.dialog.pdfRadioButton.isChecked():
                ext = '.pdf'
                function = self.print_pdf
            elif self.dialog.tiffRadioButton.isChecked():
                ext = '.tif'
                function = self.save_raster_layer
            elif self.dialog.shpRadioButton.isChecked():
                ext = ''
                function = self.save_vector_layer
            if not filename.endswith(ext):
                filename += ext
            function(filename)
            only_preview_file(filename)
        progress.setValue(100)
        progress.hide()

    def get_largest_extent_layer(self):
        layers = root.findLayers()
        max_area = 0
        largest_layer = None
        for layer_node in layers:
            layer = layer_node.layer()
            if layer and layer.type() == QgsMapLayer.VectorLayer and layer.isValid():
                extent = layer.extent()
                area = extent.width() * extent.height()
                if area > max_area:
                    if not layer.extent().isEmpty():
                        max_area = area
                        largest_layer = layer
        return largest_layer

    def layer_list_generator(self, mode='current_view', selected_layers=False):
        self.layer_list = []
        if not selected_layers:
            selected_layers = project.mapThemeCollection().masterVisibleLayers()
        overlay = None
        if mode == 'comm_view':
            overlay = self.get_largest_extent_layer()
        if mode == 'current_view':
            self.create_composer()
            if not check_if_value_empty(self.rect):
                extent = QgsRectangle(self.rect)
            else:
                extent = self.iface.mapCanvas().extent()
            geometry = QgsGeometry.fromRect(extent)
            feat = QgsFeature()
            feat.setGeometry(geometry)
            overlay = QgsVectorLayer(f"Polygon?crs={get_project_crs().toWkt()}",
                                     f"overlay_layer_{random.random()}", "memory")
            overlay.startEditing()
            overlay.addFeature(feat)
            overlay.commitChanges()
        for layer in selected_layers:
            if layer.type().value == 0 and root.findLayer(layer.id()).isVisible():
                params = {
                    'INPUT': layer,
                    'OVERLAY': overlay,
                    'OUTPUT': f'memory:temp_{layer.name()}',
                }
                context = QgsProcessingContext()
                context.setInvalidGeometryCheck(False)
                try:
                    result = processing.run('native:intersection', params, context=context)
                except:
                    QgsMessageLog.logMessage(f'SZYBKI WYDRUK - Wystąpił błąd podczas dodawania warstwy {layer.name()}',
                                             "giap_layout",
                                             Qgis.Warning)
                temp_layer = result['OUTPUT']
                copy_symbolization(layer, temp_layer)
                self.layer_list.append(temp_layer)

    def save_vector_layer(self, filename):
        paths_list = []
        ext = '.shp'
        if self.dialog.biezacy_widok_rb.isChecked():
            self.layer_list_generator(mode='current_view')
        elif self.dialog.caly_zasieg_rb.isChecked():
            self.layer_list_generator(mode='comm_view')
        elif self.dialog.maska_rb.isChecked():
            self.layer_list_from_mask(project.mapThemeCollection().masterVisibleLayers())
        now = datetime.now()
        time_str = now.strftime("%d_%m_%Y_%H_%M_%S")
        date_formatted = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
        vector_layers_path = normalize_path(os.path.join(filename, time_str))
        os.makedirs(vector_layers_path)
        path_list = []
        for vector_layer in self.layer_list:
            vector_layer_name = vector_layer.name() + ext
            layer_path = normalize_path(os.path.join(vector_layers_path, vector_layer_name))
            paths_list.append(layer_path)
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.layerName = vector_layer.name()
            if ext in ['.dgn', '.dxf']:
                options.skipAttributeCreation = True
            drvName = QgsVectorFileWriter.driverForExtension(ext)
            if drvName:
                options.driverName = drvName
            else:
                CustomMessageBox(self.dialog, "Błąd przy zapisie warstw.").button_ok()
            options.fileEncoding = 'utf-8'
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
            options.ct = QgsCoordinateTransform(QgsCoordinateReferenceSystem(vector_layer.crs().toWkt()),
                                                QgsCoordinateReferenceSystem(vector_layer.crs().toWkt()),
                                                project)
            QgsVectorFileWriter.writeAsVectorFormatV2(vector_layer, layer_path,
                                                      project.transformContext(), options)
            symbolization_path = layer_path.replace(ext, '.qml')
            vector_layer.saveNamedStyle(symbolization_path)
            path_list.append([layer_path, symbolization_path, vector_layer.name()])
        if self.dialog.dodaj_warstwy_checkBox.isChecked() and not check_if_value_empty(path_list):
            vector_group = project.layerTreeRoot().findGroup('PLIKI WEKTOROWE')
            if not vector_group:
                project.layerTreeRoot().addGroup('PLIKI WEKTOROWE')
                vector_group = project.layerTreeRoot().findGroup('PLIKI WEKTOROWE')
            vector_group.addGroup(date_formatted)
            time_group = project.layerTreeRoot().findGroup(date_formatted)
            for layer_path, symbolization_path, layer_name in path_list:
                layer_from_path = QgsVectorLayer(layer_path, layer_name, "ogr")
                layer_from_path.loadNamedStyle(symbolization_path)
                project.addMapLayer(layer_from_path, False)
                time_group.addLayer(layer_from_path)

    def layer_list_from_mask(self, selected_layers):
        feature = None
        self.layer_list = []
        if self.dialog.lineEdit_maska.text():
            mask_layer, feature = self.get_feature_from_lineedit(True)
        for layer in selected_layers:
            if feature and layer.type().value == 0 and root.findLayer(layer.id()).isVisible():
                overlay = QgsVectorLayer(f"Polygon?crs={mask_layer.crs().toWkt()}",
                                         f"overlay_layer_{random.random()}", "memory")
                overlay.dataProvider().addAttributes(mask_layer.fields())
                overlay.updateFields()
                overlay.startEditing()
                overlay.addFeature(feature)
                overlay.commitChanges()
                params = {
                    'INPUT': layer,
                    'OVERLAY': overlay,
                    'OUTPUT': f'memory:temp_{layer.name()}',
                    'OUTPUT_GEOMETRY': layer.wkbType()
                }
                context = QgsProcessingContext()
                context.setInvalidGeometryCheck(False)
                try:
                    result = processing.run('native:intersection', params, context=context)
                except Exception as err:
                    QgsMessageLog.logMessage(
                        f'SZYBKI WYDRUK - Wystąpił błąd podczas dodawania warstwy {layer.name()}: \n {str(err)}',
                        "GIAP-PolaMap",
                        Qgis.Warning)
                temp_layer = result['OUTPUT']
                fixed_layer = processing.run('native:fixgeometries',
                                             {'INPUT': temp_layer, 'OUTPUT': f'memory:tmp_{layer.name()}'})['OUTPUT']
                copy_symbolization(layer, fixed_layer)
                self.layer_list.append(fixed_layer)

    def save_raster_layer(self, filename):
        file_handle, path_to_temp_file = tempfile.mkstemp(suffix='_QGIS_image_file.tif')
        os.close(file_handle)
        self.print_image(path_to_temp_file)
        tmp_raster_layer = QgsRasterLayer(path_to_temp_file, 'tmp_raster_layer')
        ext = filename.split(".")[-1]
        output_options = {'COMPRESS': 'LZW'}
        writer = QgsRasterFileWriter(filename)
        writer.setCreateOptions(output_options)
        drvName = QgsRasterFileWriter.driverForExtension(ext)
        if drvName:
            output_format = drvName
        else:
            CustomMessageBox(self.dialog, "Błąd przy zapisie pliku.").button_ok()
        writer.setOutputFormat(output_format)
        writer.writeRaster(tmp_raster_layer.pipe(), nCols=tmp_raster_layer.width(), nRows=tmp_raster_layer.height(),
                           outputExtent=tmp_raster_layer.extent(), crs=tmp_raster_layer.crs())

    def print_pdf(self, filename:str) -> None:
        progress = self.dialog.progressBar
        progress.setValue(50)
        exporter = QgsLayoutExporter(self.layout)
        pdf_settings = exporter.PdfExportSettings()
        pdf_settings.dpi = self.dialog.resspinBox.value()
        progress.setValue(90)
        exporter.exportToPdf(filename,
                             pdf_settings)
        progress.setValue(100)

    def print_image(self, filename:str) -> None:
        progress = self.dialog.progressBar
        progress.setValue(50)
        exporter = QgsLayoutExporter(self.layout)
        pdf_settings = exporter.ImageExportSettings()
        pdf_settings.dpi = self.dialog.resspinBox.value()
        progress.setValue(90)
        exporter.exportToImage(filename,
                               pdf_settings)
        progress.setValue(100)
