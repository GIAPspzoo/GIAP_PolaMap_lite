# -*- coding: utf-8 -*-
import os.path
import subprocess
import webbrowser
import urllib.request
import re
import time

from typing import List
from urllib.error import URLError
from datetime import datetime
from platform import python_version

import qgis
from qgis.PyQt.QtCore import QTranslator, QCoreApplication, QSize, \
    QRect, QPropertyAnimation, QEasingCurve, QSettings, QObject
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolBar, QToolButton, QWidget, \
    QHBoxLayout, QMenu, QMessageBox, QApplication
from qgis.PyQt.QtWidgets import QDockWidget, QVBoxLayout
from qgis.PyQt.QtWidgets import QPushButton
from qgis.core import QgsProject, Qgis, QgsSettings, QgsApplication
from qgis.utils import iface

from .Kompozycje.Kompozycje import CompositionsTool
from .OrtoTools import OrtoAddingTool
from .QuickPrint import PrintMapTool
from .Searcher.searchTool import SearcherTool
from .Settings.settings_layout import SettingsDialog
from .StyleManager.stylemanager import StyleManagerDialog
from .config import Config
from .giap_dynamic_layout import MainWidget, CustomLabel
from .kompozycje_widget import kompozycjeWidget
from .ribbon_config import RIBBON_DEFAULT
from .tools import StyleManager
from .utils import tr, Qt, icon_manager, CustomMessageBox, add_action_from_toolbar, GIAP_NEWS_WEB_PAGE
from qgis.gui import QgsMapTool
import re
project = QgsProject.instance()


class MainTabQgsWidget:

    def __init__(self, iface: iface) -> None:
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """

        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.install_translator()
        self.main_widget = MainWidget(self.iface.mainWindow())
        self.kompozycje_widget = kompozycjeWidget()
        self.left_docks = []
        self.config = Config()
        self.searcher = SearcherTool(self.main_widget, self.iface)
        self.sett = QgsSettings()


        self.style_manager = StyleManager(self)
        self.print_map_tool = PrintMapTool(self.iface)
        self.iface.projectRead.connect(self.projekt_wczytany)
        self.iface.newProjectCreated.connect(self.projekt_wczytany)
        self.iface.initializationCompleted.connect(self.load_ribbons)
        self.iface.newProjectCreated.connect(self.missingCorePlugins)
        self.set_dlg = SettingsDialog()
        self.set_dlg.groupBox_5.hide()
        self.set_dlg.adjustSize()
        self.style_manager_dlg = StyleManagerDialog(self.style_manager)
        self.font_size = QSettings().value("qgis/stylesheet/fontPointSize")
        self.kompozycje = CompositionsTool(self.iface, self)
        if "font_changed" not in self.config.setts:
            self.config.set_value('font_changed', False)
            self.config.save_config()
        if self.config.setts['font_changed']:
            CustomLabel(tr('New section')).setStyleSheet(
                f'font: {self.font_size}pt;')
            self.kompozycje_widget.setStyleSheet(
                f'font: {self.font_size}pt;')
            self.main_widget.pokaz_warstwy.setStyleSheet(
                f'font: {self.font_size}pt;')
            self.setfont_settings_dialog()
            self.setfont_styles_dialog()


    def setfont_settings_dialog(self) -> None:
        self.set_dlg.frame_main.setStyleSheet(
            f'{self.set_dlg.frame_main.styleSheet()}'
            f' QGroupBox, QPushButton, QSpinBox, QRadioButton {{font: {self.font_size}pt;}}')

        attributes = [self.set_dlg.frame_title, self.set_dlg.label_side]
        for attr in attributes:
            attr.setStyleSheet(f'{attr.styleSheet()} font: {self.font_size}pt;')
        attributes = [self.set_dlg.label_contact_left, self.set_dlg.label_contact_right]
        for attr in attributes:
            for repl in (re.findall(r'font-size:\d+', attr.text())):
                replaced = attr.text().replace(f'{repl}', f'font-size: {self.font_size}')
                attr.setText(replaced)

    def setfont_styles_dialog(self) -> None:
        attributes = [self.style_manager_dlg.title_label, self.style_manager_dlg.pushButton_cancel,
                      self.style_manager_dlg.label_side]
        for attr in attributes:
            attr.setStyleSheet(f'font: {self.font_size}pt;')
        self.style_manager_dlg.frame_main.setStyleSheet(
            f'{self.style_manager_dlg.frame_main.styleSheet()} QLabel, QPushButton {{font: {self.font_size}pt;}}')
        self.style_manager_dlg.frame_style.setStyleSheet(
            f'{self.style_manager_dlg.frame_style.styleSheet()}font: {self.font_size}pt;')

    def missingCorePlugins(self) -> None:
        if len(iface.mainWindow().findChild(
                QToolBar, 'mVectorToolBar').actions()) == 0:
            CustomMessageBox(None,
                             f'{tr("Switch on manually missing core plugin: Topology Checker")}').button_ok()

    def initGui(self) -> None:
        # set default style and active style if config.json doesn't extists
        dic_style = self.style_manager.get_style_dictionary()
        self.config.set_default_style(dic_style)

        style = self.main_widget.styleSheet()
        self.iface.mainWindow().statusBar().setStyleSheet(
            style + """ QSpinBox {height: 20px;}""")
        self.save_default_user_layout()
        self.style_manager.run_last_style()

        self.toolbar = QToolBar('GiapToolBar', self.iface.mainWindow())
        self.toolbar.setObjectName('GiapToolBar')
        self.iface.mainWindow().addToolBar(self.toolbar)
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.addWidget(self.main_widget)
        self.ustaw_legende()

        self.menuButton = QToolButton()
        self.menuButton.setText(tr("Show menu"))
        self.menuButton.setCheckable(True)
        self.menuButton.setBaseSize(QSize(80, 25))
        self.menuButton.toggled.connect(self.menu_show)

        self.editButton = QToolButton()
        self.editButton.setText(tr("Edit menu"))
        self.editButton.setCheckable(True)
        self.editButton.setBaseSize(QSize(25, 25))
        self.editButton.toggled.connect(self.set_edit_session)
        self.menu_show()

        self.styleButton = QToolButton()
        self.styleButton.setText(tr("Change Theme"))
        self.styleButton.setBaseSize(QSize(25, 25))
        self.styleButton.clicked.connect(self.show_style_manager_dialog)
        self.styleButton.setObjectName('ThemeButton')

        self.settingsButton = QToolButton()
        self.settingsButton.setText(tr("Settings"))
        self.settingsButton.setBaseSize(QSize(25, 25))
        self.settingsButton.clicked.connect(self.show_settings_dialog)
        self.settingsButton.setObjectName('SettingsButton')

        corner_widget = QWidget(self.main_widget.tabWidget)
        corner_layout = QHBoxLayout()
        corner_layout.setContentsMargins(0, 0, 0, 0)
        corner_layout.addWidget(self.menuButton)
        corner_layout.addWidget(self.editButton)
        corner_layout.addWidget(self.styleButton)
        corner_layout.addWidget(self.settingsButton)
        # logo icon
        plug_dir = os.path.dirname(__file__)
        gbut = QPushButton()
        gbut.clicked.connect(lambda: webbrowser.open('https://giap.pl/'))
        gbut.setIcon(
            QIcon(os.path.join(plug_dir, 'icons', 'giap.png'))
        )
        gbut.setCursor(QCursor(Qt.PointingHandCursor))
        gbut.setToolTip(tr("GIAP.pl - Website"))
        gbut.setStyleSheet(
            'QPushButton{border-width: 0; width: 153px; height:50px;'
            'background-color: transparent;}'
        )
        gbut.setIconSize(QSize(153, 50))

        # self.logo_toolbar = QToolBar('GiapLogoBar', self.iface.mainWindow())
        # self.logo_toolbar.setObjectName('GiapLogoBar')
        # self.iface.mainWindow().addToolBar(self.logo_toolbar)
        # self.logo_toolbar.setMovable(False)
        # self.logo_toolbar.setFloatable(True)
        # self.logo_toolbar.addWidget(gbut)
        # self.logo_toolbar.visibilityChanged.connect(self.lock_logo_Toolbar)
        # self.toolbar.visibilityChanged.connect(self.visible_logo_giap_toolbar)
        # self.logo_toolbar.setLayoutDirection(Qt.RightToLeft)

        corner_widget.setLayout(corner_layout)
        self.main_widget.tabWidget.setCornerWidget(corner_widget)
        self.iface.mapCanvas().refresh()

        self.main_widget.editChanged.connect(self.save_user_ribbon_config)
        self.main_widget.editChanged.connect(self.kompozycje.update_buttons)
        self.main_widget.printsAdded.connect(self.custom_prints)
        self.main_widget.editChanged.connect(self.custom_prints)
        self.project_path = os.path.dirname(
            os.path.abspath(project.fileName()))
        self.toolbar.show()

        self.main_widget.runQuickPrintButton.clicked.connect(
            self.print_map_tool.run)
        self.main_widget.runQuickPrintButton.setToolTip(tr("Map quick print"))
        self.main_widget.runQuickPrintButton.setIcon(
            QIcon(os.path.join(self.plugin_dir, 'icons', 'quick_print.png')))

        self.main_widget.runCompositionButton.clicked.connect(
            self.kompozycje.config)
        self.main_widget.runCompositionButton.setIcon(
            QIcon(os.path.join(self.plugin_dir, 'icons', 'compositions_giap.png')))
        self.main_widget.runCompositionButton.setToolTip(
            tr("Composition settings"))

        area_length_tool = QgsMapTool(self.iface.mapCanvas())
        area_length_tool.setAction(self.main_widget.area_length_action)
        self.main_widget.runArea.setDefaultAction(self.main_widget.area_length_action)

        orto_button = self.main_widget.runOrtoTool
        orto_button.setIcon(QIcon(os.path.join(self.plugin_dir, 'icons', 'orto_icon2.png')))
        self.orto_add = OrtoAddingTool(self.main_widget, orto_button, self.iface)

        self.visibility_search_tool = False
        self.main_widget.offOnSearchButton.clicked.connect(
            lambda: self.off_on_search_tool(self.visibility_search_tool))
        self.main_widget.offOnSearchButton.setIcon(
            QIcon(os.path.join(self.plugin_dir, 'styles', 'GIAP Navy Blue', 'icons', 'close.png')))

        self.main_widget.setFocusPolicy(Qt.StrongFocus)
        try:
            new = self.html_div_from_url(GIAP_NEWS_WEB_PAGE)
            self.add_news_from_dict(new)
        except:
            pass

        process = qgis.utils.plugins.get('processing')
        if process:
            process.initGui()
            process.initProcessing()
            self.load_ribbons()
        self.run_logger()

    def run_logger(self):
        current_time = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        dirn = os.path.dirname
        self.log_folder = os.path.join(dirn(dirn(dirn(self.plugin_dir))), 'GIAP_lite_logs')
        print(self.log_folder)
        if not os.path.exists(self.log_folder):
            os.makedirs(self.log_folder)
        self.new_txt_file = os.path.join(self.log_folder, f"qgis_logs_{current_time}.txt")
        qgis_version = Qgis.QGIS_VERSION
        plugin_version = self.get_version()
        self.remove_old_logs()
        with open(self.new_txt_file, 'a') as logfile:
            logfile.write(f'''Data:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n''')
            logfile.write(f'''Wersja Qgis:  {qgis_version} \n''')
            logfile.write(f'''Wersja Python:  {python_version()} \n''')
            logfile.write('''Wtyczka:  GIAP-PolaMap (lite)\n''')
            logfile.write(f'''Wersja wtyczki:  {plugin_version}''')
        QgsApplication.messageLog().messageReceived.connect(self.write_log_message)

    def get_version(self):
        meta_file = os.path.join(os.path.dirname(__file__), "metadata.txt")
        with open(meta_file, 'r') as mf:
            for line in mf:
                if 'subversion=' in line:
                    return line.replace('subversion=', '')

    def remove_old_logs(self):
        treshold = time.time() - 10 * 86400 # 10 dni
        for tmp_dir in os.listdir(self.log_folder):
            creation_time = os.stat(os.path.join(self.log_folder, tmp_dir)).st_ctime
            if creation_time < treshold:
                os.remove(os.path.join(self.log_folder, tmp_dir))

    def write_log_message(self, message, tag, level):
        with open(self.new_txt_file, 'a') as logfile:
            logfile.write(f'''{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:  {tag} ({level}):  {message} \n\n''')

    def ustaw_legende(self) -> None:
        self.layer_panel = \
            self.iface.mainWindow().findChildren(QDockWidget, 'Layers')[0]

        self.layer_view = self.iface.layerTreeView()
        self.layer_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layer_toolbar = self.layer_view.parent().children()[1]
        widget_w_warstwach = QWidget()
        layout_widgetu = QVBoxLayout()
        layout_widgetu.addWidget(layer_toolbar)
        layout_widgetu.addWidget(self.kompozycje_widget)
        layout_widgetu.addWidget(self.layer_view)
        layout_widgetu.setContentsMargins(0, 7, 0, 4)
        widget_w_warstwach.setLayout(layout_widgetu)
        self.layer_panel.setWidget(widget_w_warstwach)
        self.layer_panel.setTitleBarWidget(QWidget())
        self.main_widget.pokaz_warstwy.toggled.connect(self.warstwy_show)

    def load_ribbons(self) -> None:
        self.main_widget.area_length_action.setToolTip(tr("Area and length"))
        self.main_widget.edit_session_toggle()
        ribbon_conf = self.config.load_user_ribbon_setup()
        if not ribbon_conf:
            ribbon_conf = RIBBON_DEFAULT
        for dtab in ribbon_conf:
            itab, tab = self.main_widget.add_tab(dtab['tab_name'])
            for dsec in dtab['sections']:
                sec = self.main_widget.add_section(
                    itab, tr(dsec['label']), dsec['btn_size']
                )
                for btn in dsec['btns']:
                    child = self.iface.mainWindow().findChild(QAction, btn[0])
                    if child is None:
                        if QgsApplication.processingRegistry().algorithmById(btn[0]) \
                                or btn[0].startswith('giap'):
                            sec.add_action(*btn)
                        add_action_from_toolbar(self.iface, sec, btn)
                    else:
                        if btn[0] == 'mActionShowAlignRasterTool':
                            child.setIcon(
                                icon_manager([btn[0]], self.main_widget)[
                                    btn[0]])
                        sec.add_action(child, *btn[1:])

                if sec.gridLayout.count() != len(dsec['btns']):
                    sec.delete_blank_button()

                if dsec['label'] == 'Prints':
                    self.custom_prints()

        self.main_widget.tabWidget.setCurrentIndex(0)
        self.main_widget.edit_session_toggle()

    def html_div_from_url(self, url: str) -> List[dict]:
        try:
            url_handler = urllib.request.urlopen(url)
        except URLError:
            return
        html = url_handler.read().decode('utf-8')
        if not html:
            return
        html = html.split('<main>')[1].split('</main>')[0]
        divs = html.split('<div class="post-excerpt">')
        news = []
        for div in divs:
            lines = [div.strip() for div in div.split('\n') if div.strip()]
            if not lines[0] == '<div class="row post-row">':
                continue
            for line in lines:
                if '<a href' in line and not 'czytaj dalej...' in line:
                    link = re.search('="(.*)">', line).group(1)
                    pk = link.split('/')[-2]
                if '<img src' in line:
                    img_link = re.search('="(.*)" c', line).group(1)
                if '<h2>' in line:
                    title = re.search('>(.*)<', line).group(1)
                if '<p>' in line:
                    content = line
            news.append({"pk": int(f'999{pk}'),
                         "publish_from": None,
                         "publish_to": None,
                         "title": title,
                         "image": f'https://www.giap.pl{img_link}',
                         "content": content,
                         "url": f'https://www.giap.pl{link}',
                         "sticky": 'false'
                         })
            if len(news) == 5:
                break

        url_handler.close()
        return news

    def add_news_from_dict(self, news: List[dict]) -> None:
        if not news:
            return
        edited = False
        for ele in news:

            pk = ele['pk']
            key = f'core/NewsFeed/httpsfeedqgisorg/{pk}'
            title = ele['title']
            img = ele['image']
            url = ele['url']
            sticky = ele['sticky']
            content = ele['content']

            news_eles = {'title': title, 'content': content, 'imageUrl': img, 'link': url, "sticky": sticky}
            for news_ele in news_eles:
                if f'{key}/{news_ele}' not in self.sett.allKeys():
                    self.sett.setValue(f'{key}/{news_ele}', news_eles[news_ele])
                    edited = True
                    last_news = int(key.split('/')[-1]) - 5
                    key_remove = key.split('/')
                    key_remove[-1] = str(last_news)
                    key_remove = '/'.join(key_remove)
                    self.sett.remove(key_remove)
                elif self.sett.value(f'{key}/{news_ele}') != news_eles[news_ele]:
                    self.sett.setValue(f'{key}/{news_ele}', news_eles[news_ele])
                    edited = True

            if edited:
                self.sett.setValue('core/NewsFeed/httpsfeedqgisorg/lastFetchTime', 0)

    # def visible_logo_giap_toolbar(self, visible: bool) -> None:
    #     self.logo_toolbar.setVisible(not visible)

    # def lock_logo_Toolbar(self) -> None:
    #     if not self.logo_toolbar.isVisible() and not self.toolbar.isVisible():
    #         self.logo_toolbar.setVisible(True)

    def off_on_search_tool(self, visibility) -> None:
        elements = ['comboBox_woj', 'comboBox_pow', 'comboBox_gmina',
                    'comboBox_obr', 'buttonParcelNr', 'buttonAdress',
                    'lineEdit_parcel', 'lineEdit_address', 'line',
                    'wyszukaj_pushButton', 'wyszukaj_adres_pushButton']

        for elem in elements:
            getattr(self.main_widget, elem).setVisible(visibility)
        self.visibility_search_tool = not visibility

    def custom_prints(self) -> None:
        """Load custom tools to qgis"""

        b_mprints = self.main_widget.findChildren(QToolButton, 'giapMyPrints')
        for b_mprint in b_mprints:
            b_mprint.setIcon(icon_manager(['giapMyPrints'], self.main_widget)[
                                 'giapMyPrints'])
        self.my_prints_setup()

    def save_default_user_layout(self):
        """ Saves active user toolbars in qgis user settings. Saves as string
        under flag org_toolbars in json config file (user scope).
        Assumes that all toolbars have specified name if not, we can't find
        them, and therefore will not be loaded again
        :return:
        """

        active_toolbars = []
        for toolbar in self.iface.mainWindow().findChildren(QToolBar):
            try:
                if toolbar.parent().windowTitle() == \
                        self.iface.mainWindow().windowTitle() and \
                        toolbar.isVisible():
                    active_toolbars.append(toolbar)
            except Exception:
                pass

        for toolbr in active_toolbars:
            toolbr.hide()

        tbars_names = [tb.objectName() for tb in active_toolbars
                       if tb.objectName() not in ['', None, 'NULL',
                                                  'GiapToolBar']]
        self.config.save_original_toolbars(tbars_names)

    def save_user_ribbon_config(self, opt):
        """Saves user ribbon setup to config on exit
        :opt: bool for edit session, False will save config
        :return: None
        """

        if not opt:
            ribbon_conf = self.main_widget.generate_ribbon_config()
            sections_conf = self.config.load_custom_sections_setup()
            self.config.save_user_ribbon_setup(ribbon_conf, sections_conf)

    def load_default_user_layout(self):
        """Restores original user toolbars to qgis window from settings
        :return:
        """

        toolbars_name = self.config.get_original_toolbars()
        for tname in toolbars_name:
            tbar = self.iface.mainWindow().findChild(QToolBar, tname)
            if tbar is not None:
                tbar.show()
        self.iface.mainWindow().menuBar().show()

    def my_prints_setup(self) -> None:
        btns = self.iface.mainWindow().findChildren(
            QToolButton, 'giapMyPrints')
        for btn in btns:
            btn.setToolTip(tr("My Prints"))
            btn.setPopupMode(QToolButton.InstantPopup)
            self.action_my_prints_menu()
            self.projectLayoutManager.layoutAdded.connect(
                self.action_my_prints_menu
            )
            self.projectLayoutManager.layoutRemoved.connect(
                self.action_my_prints_menu
            )

    def action_my_prints_menu(self) -> None:
        btns = self.iface.mainWindow().findChildren(
            QToolButton, 'giapMyPrints')
        for btn in btns:
            main_widget = self.main_widget
            menu = QMenu(main_widget)
            actions = []
            projectInstance = QgsProject.instance()
            self.projectLayoutManager = projectInstance.layoutManager()
            for layout in self.projectLayoutManager.layouts():
                title = layout.name()
                action = QAction(title, main_widget)
                action.triggered.connect(
                    lambda checked, item=action:
                    self.open_layout_by_name(item.text()))
                actions.append(action)
            actions.sort(key=lambda x: x.text())
            list(map(menu.addAction, actions))
            btn.setMenu(menu)

    def open_layout_by_name(self, action_name: str) -> None:
        layout = self.projectLayoutManager.layoutByName(action_name)
        self.iface.openLayoutDesigner(layout)

    def unload(self) -> None:
        self.iface.mainWindow().menuBar().show()
        self.style_manager.activate_style('')
        self.save_user_ribbon_config(False)
        self.kompozycje.unload()
        self.toolbar.hide()
        self.kompozycje_widget.hide()
        self.load_default_user_layout()

        self.iface.messageBar().pushMessage(
            'GIAP-PolaMap(lite)',
            tr('Please, restart QGIS!'),
            Qgis.Info,
            0
        )

    def menu_show(self) -> None:
        """Toggle visiblity of menubar"""
        mbar = self.iface.mainWindow().menuBar()
        splitter_start = QRect(0, -20, mbar.width(), 20)
        splitter_end = QRect(0, 0, mbar.width(), 20)
        if self.menuButton.isChecked():
            mbar.show()
            self.set_animation(mbar, splitter_start, splitter_end, 200)
        else:
            self.set_animation(mbar, splitter_end, splitter_start, 200)
            mbar.hide()

    def set_edit_session(self) -> None:
        if self.editButton.isChecked():
            self.editButton.setText(tr("Finish editing"))
            self.main_widget.edit_session_toggle()
        else:
            self.editButton.setText(tr("Edit menu"))
            self.main_widget.edit_session_toggle(True)
            if self.main_widget.save == QMessageBox.No:
                for tabind in range(len(self.main_widget.tabs)):
                    self.main_widget.remove_tab(0)
                self.load_ribbons()

    def warstwy_show(self) -> None:
        splitter_start = QRect(-self.layer_panel.width(), self.layer_panel.y(),
                               self.layer_panel.width(),
                               self.layer_panel.height())
        splitter_end = QRect(0, self.layer_panel.y(),
                             self.layer_panel.width(),
                             self.layer_panel.height())
        if self.main_widget.pokaz_warstwy.isChecked():
            self.layer_panel.show()
            self.set_animation(
                self.layer_panel, splitter_start, splitter_end, 200)
            self.layer_view.resizeColumnToContents(0)
        else:
            self.set_animation(
                self.layer_panel, splitter_end, splitter_start, 200, 'out')

    def resize_layer_view(self) -> None:
        canvas_geom = self.iface.mapCanvas().geometry()
        self.layer_view.setGeometry(0, 79, 280, canvas_geom.height() - 79)

    def set_animation(
            self, widget: QObject, qrect_start: QRect, qrect_end: QRect, duration: int, mode: str='in') -> None:
        animation_in = QPropertyAnimation(widget, b"geometry")
        animation_in.setStartValue(qrect_start)
        animation_in.setEndValue(qrect_end)
        animation_in.setDuration(duration)
        animation_in.setEasingCurve(QEasingCurve.InOutQuad)
        animation_in.start()
        animation_in.finished.connect(
            lambda: self.delete_animation(animation_in, widget, mode)
        )

    def repair_layers_names_for_compositions(self) -> None:
        for layer in list(project.mapLayers().values()):
            layer.setName(layer.name().replace(':', '_'))

    def projekt_wczytany(self) -> None:
        """
            setup after loading new project
        """

        self.repair_layers_names_for_compositions()
        self.kompozycje.start()
        self.kompozycje.modify_tool.check_for_changes_in_comps()

    def delete_animation(self, animation: QPropertyAnimation, widget: QObject, mode: str) -> None:
        del animation
        if mode == 'out':
            widget.hide()

    def show_style_manager_dialog(self) -> None:
        """Show dialog to manage qgis styles"""
        self.style_manager_dlg.setWindowFlags(
            Qt.Window | Qt.WindowCloseButtonHint
        )
        self.style_manager_dlg.exec_()

    def show_settings_dialog(self) -> None:
        self.set_dlg.pushButton_restore.clicked.connect(
            self.restore_default_ribbon_settings)
        self.set_dlg.radioButton_pl.clicked.connect(self.set_polish)
        self.set_dlg.radioButton_en.clicked.connect(self.set_english)
        self.set_dlg.radioButton_sys.clicked.connect(self.restore_overrideFlag)
        if str(QSettings().value('locale/overrideFlag')) == "false":
            self.set_dlg.radioButton_sys.setChecked(True)
        elif str(QSettings().value('locale/userLocale')) == "en":
            self.set_dlg.radioButton_en.setChecked(True)
        elif str(QSettings().value('locale/userLocale')) == "pl_PL":
            self.set_dlg.radioButton_pl.setChecked(True)
        self.set_dlg.spinBox_font.setValue(int(self.font_size or 5))
        self.set_dlg.spinBox_button.clicked.connect(self.set_size)
        self.set_dlg.restart_button.clicked.connect(self.restart_font_size)
        self.set_dlg.exec_()

    def set_polish(self) -> None:
        self.check_lang_win_flag()
        str(QSettings().setValue('locale/userLocale', 'pl_PL'))
        self.iface.messageBar().pushMessage(
            'GIAP-PolaMap(lite)',
            tr('Please, restart QGIS!'),
            Qgis.Info,
            0
        )
        self.restart_qgis()

    def set_english(self) -> None:
        self.check_lang_win_flag()
        str(QSettings().setValue('locale/userLocale', 'en'))
        self.iface.messageBar().pushMessage(
            'GIAP-PolaMap(lite)',
            tr('Please, restart QGIS!'),
            Qgis.Info,
            0
        )
        self.restart_qgis()

    def restore_overrideFlag(self) -> None:
        str(QSettings().setValue('locale/overrideFlag', "false"))
        self.iface.messageBar().pushMessage(
            'GIAP-PolaMap(lite)',
            tr('Please, restart QGIS!'),
            Qgis.Info,
            0
        )
        self.restart_qgis()

    def set_size(self) -> None:
        value = self.set_dlg.spinBox_font.value()
        self.set_dlg.spinBox_font.setValue(value)
        QSettings().setValue('qgis/stylesheet/fontPointSize', value)
        self.config.set_value('font_changed', True)
        self.iface.messageBar().pushMessage(
            'GIAP-PolaMap(lite)',
            tr('Please, restart QGIS!'),
            Qgis.Info,
            0
        )
        self.restart_qgis()

    def restart_font_size(self):
        QSettings().setValue('qgis/stylesheet/fontPointSize', 8)
        self.config.set_value('font_changed', False)
        self.iface.messageBar().pushMessage(
            'GIAP-PolaMap(lite)',
            tr('Please, restart QGIS!'),
            Qgis.Info,
            0
        )
        self.restart_qgis()


    def restore_default_ribbon_settings(self) -> None:
        self.set_dlg.pushButton_restore.clicked.disconnect()
        edit_ses_on_start = self.main_widget.edit_session
        if edit_ses_on_start: self.main_widget.edit_session_toggle()
        for tabind in range(len(self.main_widget.tabs)):
            self.main_widget.remove_tab(0)
        self.save_user_ribbon_config(False)
        self.load_ribbons()
        if edit_ses_on_start: self.main_widget.edit_session_toggle()
        self.set_dlg.pushButton_restore.clicked.connect(
            self.restore_default_ribbon_settings)

    def check_lang_win_flag(self) -> None:
        QgsSettings().setValue('locale/overrideFlag', 'true')

    def restart_qgis(self) -> None:
        if project.write():
            res = CustomMessageBox(
                None,
                tr("The program must be restarted for the changes to take effect. Restart now?")).button_yes_no()
            if res == QMessageBox.Yes:
                project.setDirty(
                    False)  # workaround - mimo poprawnego zapisu nadal pyta o zapis
                subprocess.Popen(
                    f'{QgsApplication.arguments()[0]} {project.fileName()}')
                self.iface.actionExit().trigger()

    def install_translator(self) -> None:
        locale = 'en'
        try:
            loc = str(QSettings().value('locale/userLocale'))
            if len(locale) > 1:
                locale = loc[:2]
        except Exception:
            # do not install translator -> english
            return
        if 'pl' in locale:
            trans_path = os.path.join(self.plugin_dir, 'i18n',
                                      f'giap_pl.qm')
        else:
            return
        if not os.path.exists(trans_path):
            return
        self.translator = QTranslator()
        self.translator.load(trans_path)
        QCoreApplication.installTranslator(self.translator)
