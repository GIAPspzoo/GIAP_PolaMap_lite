# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import tempfile
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import QRectF, QDateTime, QSettings
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtWidgets import QFileDialog, QApplication
from qgis._core import QgsLayoutExporter, QgsWkbTypes, QgsLayoutItemMap, \
    QgsLayout, QgsProject, QgsUnitTypes, QgsLayoutSize, QgsGeometry, \
    QgsVectorLayer, QgsFeature, QgsSymbol, QgsSimpleFillSymbolLayer, \
    QgsLayoutItemLegend, QgsLayerTreeGroup, QgsLegendStyle, QgsLayoutItem, \
    QgsLayoutItemLabel, QgsLayoutItemScaleBar, QgsRectangle
from qgis._gui import QgsRubberBand, QgisInterface
from qgis.utils import iface
from typing import Union

from .utils import tr, CustomMessageBox, normalize_path
from .wydruk_dialog import WydrukDialog
from .config import Config

pdf_open_error_msg = '''
    Nie znaleziono programu do otwierania plików PDF. Sprawdź, czy jest\n
    zainstalowany program do otwierania plików PDF, np. Acrobat Reader.\n
    Jeżeli tak, sprawdź, czy pliki PDF otwierają się po podwójnym kliknięciu.\n
    Jeżeli nie, ustaw skojarzenie dla plików PDF z tą przeglądarką plików PDF.
'''


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


class PrintMapTool:
    mm_paper_sizes = {
        # '4A0': (1682, 2378),
        # '2A0': (1189, 1682),
        'A0': (841, 1189),
        'A1': (594, 841),
        'A2': (420, 594),
        'A3': (297, 420),
        'A4': (210, 297),
        'A5': (148, 210),
        # 'A6': (105, 148),
        # 'A7': (74, 105),
        # 'A8': (52, 74),
        # 'A9': (37, 52),
        # 'A10': (26, 37),
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
        self.dialog.legendCheckBox.hide()  # tymczasowe ukrycie opcji legendy
        paper_format_items = sorted(self.mm_paper_sizes.keys())
        self.dialog.paperFormatComboBox.addItems(paper_format_items)
        self.dialog.paperFormatComboBox.setCurrentIndex(
            paper_format_items.index("A4"))
        self.dialog.paperFormatComboBox.currentIndexChanged.connect(
            self.create_composer)
        self.setup_rubberband()
        if Config().setts['font_changed']:
            self.set_font_quickprint(QSettings().value("qgis/stylesheet/fontPointSize"))

    def set_font_quickprint(self, font_size):
        self.dialog.label_2.setStyleSheet(f'{self.dialog.label_2.styleSheet()} font: {font_size}pt;')
        self.dialog.frame_4.setStyleSheet(
            f'{self.dialog.frame_4.styleSheet()} QGroupBox, QCheckBox, QToolButton, '
            f'QLineEdit, QRadioButton, QComboBox, QSpinBox, QProgressBar {{font: {font_size}pt;}}')
        self.dialog.calendar.setStyleSheet(f'font: {font_size}pt;')

    def setup_rubberband(self) -> None:
        self.rubberband = QgsRubberBand(iface.mapCanvas(), QgsWkbTypes.PolygonGeometry)
        self.rubberband.setColor(QColor(255, 0, 0, 100))
        self.rubberband.setWidth(5)
        self.rubberband.setFillColor(QColor(255, 255, 255, 0))
        self.is_active = False

    def get_paper_size(self) -> tuple:
        paper_format = self.dialog.paperFormatComboBox.currentText()
        width, height = self.mm_paper_sizes[paper_format]

        if self.dialog.horizontalRadioButton.isChecked():
            self.set_adnotation_limit(height)
            return height, width
        if self.dialog.verticalRadioButton.isChecked():
            self.set_adnotation_limit(width)
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

            width, height = self.get_paper_size()
            pos_x, pos_y = 16, 16
            page.setPageSize(QgsLayoutSize(width, height))
            canvas_extent = self.iface.mapCanvas().extent()
            current_rect = QRectF(pos_x, pos_y, width - 2 * pos_x, height - 2 * pos_y)

            map_item = QgsLayoutItemMap(self.layout)
            map_item.updateBoundingRect()
            map_item.setRect(current_rect)
            map_item.setPos(pos_x, pos_y)
            map_item.setFrameEnabled(True)

            map_item.setLayers(
                QgsProject.instance(
                ).mapThemeCollection().masterVisibleLayers())
            map_item.setExtent(canvas_extent)
            map_item.attemptSetSceneRect(current_rect)
            map_item.setScale(round(self.iface.mapCanvas().scale()))
            self.rubberband.addGeometry(QgsGeometry.fromRect(map_item.extent()),
                               QgsVectorLayer())

            self.layout.addItem(map_item)


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
        filename, __ = QFileDialog.getSaveFileName(
            self.dialog, tr("Save file"))
        tmp_layer = self.create_tmp_layer()
        self.create_composer()
        self.save_file(filename)
        if isinstance(tmp_layer, str):
            QgsProject.instance().removeMapLayers(tmp_layer)

    def preview(self) -> None:
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

                # Wazne!
                # zaczekaj az wszystkie procesy w tle zostana wykonane
                QApplication.processEvents()
            temps_layer_list.append(tmp_layer)
        return temps_layer_list

    def save_file(self, filename:str) -> None:
        progress = self.dialog.progressBar
        width, height = self.get_paper_size()
        if self.dialog.legendCheckBox.isChecked():
            # TODO: Do zmiany generowanie legendy
            self.layout.setNumPages(
                2)  # utworzenie dodatkowej strony dla legendy
            self.layout.setPagesVisible(True)
            legend = QgsLayoutItemLegend(self.layout)  # inicjalizacja legendy
            layerGroup = QgsLayerTreeGroup()  # utworzenie grupy warstw
            layer_id = 0  # licznik id
            # petla iteruje po liscie aktywnych warstw
            visibleLayers = self.iface.mapCanvas().layers()
            visibleLayersCount = len(visibleLayers)
            for the_layer in visibleLayers:
                layerGroup.insertLayer(layer_id, the_layer)  # dodanie widocznej
                # warstwy do grupy warstw layerGroup
                layer_id += 1  # zwiekszanie id o 1
            legend.modelV2().setRootGroup(layerGroup)
            legend.setSymbolHeight(3.0)
            legend.setSymbolWidth(5.0)
            # zmiana odstepow pomiedzy kolejnymi warstwami w legendzie dzieki
            # czemu miesci sie duzo warstw
            legend.rstyle(QgsLegendStyle.Symbol).setMargin(
                QgsLegendStyle.Top, 0.7)
            legend.setColumnCount(3)
            legend.setSplitLayer(True)  # warstwy nie są pogrupowane względem
            #  topologii
            legendSize = legend.paintAndDetermineSize(None)
            legend.setResizeToContents(True)
            self.layout.addItem(legend)
            legend.setItemPosition(5,
                                   height + 8,
                                   legendSize.width(),
                                   legendSize.height(),
                                   QgsLayoutItem.UpperLeft,
                                   2)

        if self.dialog.scaleCheckBox.isChecked():
            scale_label = QgsLayoutItemLabel(self.layout)
            scale_label.setText(tr("SCALE:"))
            scale = QgsLayoutItemScaleBar(self.layout)
            scale.setLinkedMap(self.get_map_item())
            scale.setStyle('Numeric')
            scale_font = QFont()
            scale.setFont(scale_font)
            scale_label.setFont(scale_font)
            scale_label.adjustSizeToText()
            self.layout.addItem(scale_label)
            self.layout.addItem(scale)
            scale_height = scale_label.rectWithFrame().height() / 4
            scale_label.moveBy(16, height - 14.)
            scale.moveBy(16 + scale_label.rectWithFrame().width(), height - scale_height - 14.)

        if self.dialog.dateCheckBox.isChecked():
            date_label = QgsLayoutItemLabel(self.layout)
            date_label.setText(self.dialog.dateedit.text())
            date_font = QFont()
            date_label.setFont(date_font)
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
            title_font = QFont()
            title_font.setPointSize(20)
            title_font.setWeight(75)
            title.setFont(title_font)
            title.adjustSizeToText()
            title.setPos((width / 2) - (len(self.dialog.titleLineEdit.text()) * 2),
                         3)
            self.layout.addItem(title)

        if self.dialog.adnotacje_lineEdit.text():
            adnotation = QgsLayoutItemLabel(self.layout)
            adnotation_font = QFont()
            adnotation.setText(self.dialog.adnotacje_lineEdit.text())
            adnotation.setFont(adnotation_font)
            adnotation.adjustSizeToText()
            self.layout.addItem(adnotation)
            adnotation.moveBy(width - adnotation.rectWithFrame().width() - 16, height - 14)
        progress.show()
        progress.setValue(20)
        if filename:
            if self.dialog.jpgRadioButton.isChecked():
                ext = '.jpg'
                function = self.print_image
            elif self.dialog.pngRadioButton.isChecked():
                ext = '.png'
                function = self.print_image
            else:
                ext = '.pdf'
                function = self.print_pdf
            if not filename.endswith(ext):
                filename += ext
            function(filename)
            only_preview_file(filename)
        progress.setValue(100)
        progress.hide()

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
