import os
import webbrowser
from math import ceil
from owslib.wms import WebMapService
from PyQt5.QtWidgets import QDockWidget
from plugins.processing.tools.general import execAlgorithmDialog
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtCore import Qt, QSize, QEvent, pyqtSignal, QMimeData, QRect, \
    QTimer, QPoint, QSettings
from qgis.PyQt.QtGui import QDrag, QPainter, QPixmap, QCursor, QIcon, QFont, \
    QFontMetrics
from qgis.PyQt.QtWidgets import QWidget, QApplication, QHBoxLayout, \
    QFrame, QLabel, QPushButton, QTabBar, QToolButton, QVBoxLayout, \
    QGridLayout, QSpacerItem, QLineEdit, QWidgetItem, QAction, \
    QBoxLayout, QMessageBox, QScrollArea, QMenu, QToolBar
from qgis.core import QgsApplication, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, \
    QgsTemporalNavigationObject, QgsRasterLayer, QgsInterval, QgsMapLayer
from qgis.utils import iface
from qgis.gui import QgsMapTool

from .geocoding_tool import Geocoding
from .prng_tool import PRNGTool
from .OrtoTools import OrtoAddingTool
from .QuickPrint import PrintMapTool
from .SectionManager.CustomSectionManager import CustomSectionManager
from .SectionManager.select_section import SelectSection
from .config import Config
from .utils import STANDARD_TOOLS, DEFAULT_TABS, tr, TOOLS_HEADERS, \
    STANDARD_QGIS_TOOLS, icon_manager, CustomMessageBox, add_action_from_toolbar, identify_layer_by_name, \
    add_map_layer_to_group

from .AreaAndLengthTool.AreaAndLengthTool import AreaAndLengthTool
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'giap_dynamic_layout.ui'))


class MainWidget(QWidget, FORM_CLASS):
    editChanged = pyqtSignal(bool)
    printsAdded = pyqtSignal()
    deletePressSignal = pyqtSignal()

    def __init__(self, parent: QtWidgets=None) -> None:
        super(MainWidget, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.setupUi(self)
        self.parent = parent
        self.tabs = []
        self.edit_session = False
        self.conf = Config()
        self.save = QMessageBox.Yes
        self.orto_add = False

        self.custom_tabbar = CustomTabBar(tr('New tab'), self.tabWidget)
        self.tabWidget.setTabBar(self.custom_tabbar)
        self.tabWidget.tabBar().tabBarClicked.connect(self.tab_clicked)
        self.tabWidget.tabBar().tabBarDoubleClicked.connect(
            self.tab_doubleclicked)
        self.icon_timer = QTimer()
        self.icon_timer.setSingleShot(True)
        self.icon_timer.timeout.connect(self.reload_add_icons)
        self.icon_timer.setInterval(1)
        iface.currentLayerChanged.connect(self.icon_timer.start)

        icon = icon_manager(['giapAreaLength'], self.parent)['giapAreaLength']
        self.area_length_event = AreaAndLengthTool(iface)
        self.area_length_action = QAction(QIcon(icon),None, iface.mainWindow())
        self.area_length_action.setCheckable(True)
        self.area_length_action.triggered.connect(self.area_length_event.run)
        self.setObjectName('giapAreaLength')

    def reload_add_icons(self) -> None:
        if hasattr(self, 'add_action'):
            self.add_action.setIcon(
                icon_manager(['mActionAddFeature'],
                             self.parent)['mActionAddFeature'])
        if hasattr(self, 'move_action'):
            self.move_action.setIcon(
                icon_manager(['mActionMoveFeature'],
                             self.parent)['mActionMoveFeature'])

    def add_tab(self, label: str=None):
        """Adds new tab at the end
        :return: tab widget
        """
        if not label:
            label = 'New tab'
        label = tr(label)

        tab = CustomTab(label, self.tabWidget)
        self.tabs.append(tab)

        self.tabWidget.setUpdatesEnabled(False)

        tab_ind = self.tabWidget.insertTab(
            self.tabWidget.count() - 1, tab, label
        )
        if self.edit_session:
            self._section_control(tab_ind)

        self.tabWidget.setCurrentIndex(tab_ind)
        right = self.tabWidget.tabBar().RightSide
        cbutton = QToolButton(self.tabWidget)
        cbutton.setObjectName('giapCloseTab')
        cbutton.setText('x')
        cbutton.setMinimumSize(QSize(16, 16))
        cbutton.setMaximumSize(QSize(16, 16))

        self.tabWidget.tabBar().setTabButton(tab_ind, right, cbutton)
        cbutton.clicked.connect(lambda: self.remove_tab(tab_ind))
        self.tabWidget.setUpdatesEnabled(True)

        return tab_ind, tab

    def remove_tab(self, tind: int) -> None:
        """Removes tab with given tab index"""

        self.tabWidget.removeTab(tind)
        if tind > 0:
            self.tabWidget.setCurrentIndex(tind - 1)

    def add_section(self, itab, lab, size=30):
        """Adds new section on tab with label and place for icons
        :itab: int
        :lab: label for section
        :size: int size of button
        :return: section widget
        """
        if itab > -1:
            itab = self.tabWidget.currentIndex()

        cwidget = self.tabWidget.widget(itab)
        if str(lab) in ['', 'False', 'None']:
            lab = tr('New section')
        self.section = CustomSection(str(lab), self.tabWidget, self)
        self.section.installEventFilter(self)
        if size > 30:
            self.section.set_size(size)

        self._section_control_remove(itab)
        cwidget.lay.addWidget(self.section)

        self.section.setVisible(True)
        self._section_control(itab)

        return self.section

    def edit_session_toggle(self, ask: bool=False) -> None:
        """Show controls for edti session"""

        self.edit_session = not self.edit_session
        if not hasattr(self, 'conf'):
            self.conf = Config()
        if 'ribbons_config' in self.conf.setts and ask and self.conf.setts[
            'ribbons_config'] != self.generate_ribbon_config():
            self.save = CustomMessageBox(None, tr(
                "Do you want to save your changes?")).button_yes_no()
            if self.save == QMessageBox.Yes:
                self.editChanged.emit(False)
            else:
                self.editChanged.emit(True)
        else:
            self.editChanged.emit(self.edit_session)

        self._tab_controls()

    def _tab_controls(self) -> None:
        """ show tab controls"""
        right = self.tabWidget.tabBar().RightSide

        if self.edit_session:
            for tab_idx in range(self.tabWidget.count()):
                self.tabWidget.tabBar().tabButton(tab_idx, right).show()
                self._section_control(tab_idx)
            self._new_tab_tab_control()
        else:
            self._new_tab_tab_control()
            for tab_idx in range(self.tabWidget.count()):
                self.tabWidget.tabBar().tabButton(tab_idx, right).hide()
                self._section_control(tab_idx)

    def _section_control(self, tabind: int) -> None:
        """add buttons to every tab for adding new section"""
        plug_dir = os.path.dirname(__file__)
        lay = self.tabWidget.widget(tabind).lay
        cnt = lay.count()

        # remove button
        it = lay.itemAt(cnt - 1)
        if it is not None:
            if isinstance(it.widget(), QPushButton):
                it.widget().hide()
                it.widget().deleteLater()
                QApplication.processEvents()

        if self.edit_session:
            self.instr = QLabel()
            self.instr.setText(
                f"""<html><head/><body><b>{tr('Edit tools within a section:')}</b><br>
<b>{tr('Moving tools')}</b> - {tr('click and hold the left mouse button')}<br>
{tr('on the icon and move it to the desired location')}<br><br>

<b>{tr('Tool removal')}</b> - {tr('double click')}<br>
{tr('tool icon and click delete button')}</body></html>""")

            scrll = QScrollArea(self)
            scrll.setWidgetResizable(True)
            scrll.setWidget(self.instr)
            if 'font_changed' in self.conf.setts.keys():
                value = QSettings().value("qgis/stylesheet/fontPointSize") if \
                    self.conf.setts["font_changed"] else 9
            else:
                value = 9
            self.instr.setStyleSheet(
                f"""QFrame, QLabel, QToolTip, QTextEdit{{
            font:{value}pt}}"""
            )
            self.instr.setTextFormat(Qt.AutoText)
            self.instr.setScaledContents(True)
            self.frm = QFrame()
            self.frm.setObjectName('giapSectionAdd')
            self.frmlay = QHBoxLayout(self.frm)
            self.secadd = CustomSectionAdd()

            self.secadd.clicked.connect(self.add_user_selected_section)
            self.frmlay.addWidget(self.secadd)
            self.frmlay.addStretch()
            self.frmlay.addStretch()
            self.frmlay.addWidget(scrll)

            lay = self.tabWidget.widget(tabind).lay
            cnt = lay.count()
            # there should always be something in layout, (controls)

            for ind in range(cnt, -1, -1):
                if isinstance(lay.itemAt(ind), QSpacerItem):
                    lay.removeItem(lay.itemAt(ind))

            self.tabWidget.widget(tabind).lay.addWidget(self.frm)
        else:
            self.tabWidget.widget(tabind).setUpdatesEnabled(False)
            self._section_control_remove(tabind)
            self.tabWidget.widget(tabind).lay.addStretch()
            if not isinstance(lay.itemAt(cnt - 1), QPushButton):
                gbut = QPushButton()
                gbut.clicked.connect(lambda x: webbrowser.open('https://giap.pl/'))
                gbut.setIcon(
                    QIcon(os.path.join(plug_dir, 'icons', 'giap.png'))
                )
                gbut.setCursor(QCursor(Qt.PointingHandCursor))
                gbut.setToolTip(tr("GIAP.pl - Website"))
                gbut.setStyleSheet(
                    'QPushButton{border-width: 0px; width: 220px; height:72px;'
                    'background-color: transparent;}'
                )
                gbut.setIconSize(QSize(220 - 4, 72 - 4))
                self.tabWidget.widget(tabind).lay.addWidget(gbut)
            self.tabWidget.widget(tabind).setUpdatesEnabled(True)

    def add_user_selected_section(self) -> None:
        """Show dialog to user and adds selected section to current ribbon
            if there should be more custom tools, here is the place to put them
        """
        self.dlg = SelectSection(self)
        self.run_select_section()
        self.dlg.show()
        response = self.dlg.exec_()
        if not response:
            return

        ind = self.tabWidget.currentIndex()
        self.custom_sections = self.conf.load_custom_sections_setup()
        section_names = [tr(name) for name in TOOLS_HEADERS]
        all_available_tools = [tool for tool in STANDARD_TOOLS]
        all_available_tools.extend([tool for tool in STANDARD_QGIS_TOOLS])
        if self.custom_sections:
            all_available_tools.extend([tool for tool in self.custom_sections])
        selected = [str(item.data(0)) for item in
                    self.dlg.treeView.selectionModel().selectedRows()
                    if str(item.data(0)) not in section_names]
        self.tabWidget.setUpdatesEnabled(True)
        print_trig = False
        for sel in selected:
            secdef = [tool for tool in all_available_tools
                      if tr(tool['label']) == sel][0]
            sec = self.add_section(ind, sel, secdef['btn_size'])
            for btn in secdef['btns']:
                child = self.parent.findChild(QAction, btn[0])
                if child is None:
                    if QgsApplication.processingRegistry().algorithmById(btn[0]) \
                            or btn[0].startswith('giap'):
                        sec.add_action(*btn)
                    add_action_from_toolbar(iface, sec, btn)
                else:
                    sec.add_action(child, *btn[1:])
                    if btn[0] in ['giapMyPrints', 'giapQuickPrint']:
                        print_trig = True

            if sec.gridLayout.count() != len(secdef['btns']):
                sec.delete_blank_button()

            if sel == 'Prints' or print_trig:
                self.printsAdded.emit()
        self.tabWidget.setUpdatesEnabled(True)

    def run_select_section(self) -> None:
        self.dlg.addSectionTab.clicked.connect(self.section_tab)
        self.dlg.searchToolTab.clicked.connect(self.search_tab)
        self.dlg.userSectionsTab.clicked.connect(self.user_section_tab)
        self.dlg.addAlgButton.clicked.connect(self.add_to_ribbon)
        self.dlg.pushButton_add_custom.clicked.connect(self.add_custom_section)
        self.dlg.pushButton_edit_custom.clicked.connect(
            self.edit_custom_section)
        self.dlg.pushButton_remove_custom.clicked.connect(
            self.remove_custom_section)
        self.dlg.searchBox.textChanged.connect(self.search_tree)
        self.dlg.add_searchBox.textChanged.connect(
            self.search_add_sections_tree)
        self.dlg.add_custom_searchBox.textChanged.connect(
            self.search_add_custom_sections_tree)
        self.connect_checking_signal()

    def add_to_ribbon(self) -> None:
        self.tabWidget.setUpdatesEnabled(True)
        sel_ind = self.dlg.algorithmTree.selectedIndexes()
        tool = {}
        for ind in sel_ind:
            alg_ind = 0
            alg = self.dlg.algorithmTree.algorithmForIndex(ind)
            if alg:
                if not alg.group() in tool:
                    tool[alg.group()] = []
                tool[alg.group()].append(alg)
            elif self.dlg.algorithmTree.algorithmForIndex(ind.child(0, 0)):
                alg = self.dlg.algorithmTree.algorithmForIndex(
                    ind.child(alg_ind, 0))
                while alg:
                    if not alg.group() in tool:
                        tool[alg.group()] = []
                    tool[alg.group()].append(alg)
                    alg_ind += 1
                    alg = self.dlg.algorithmTree.algorithmForIndex(
                        ind.child(alg_ind, 0))
            else:
                CustomMessageBox(self.dlg,
                                 tr("Select item has sub-section")).button_ok()
                return

        for group in tool:
            tool[group] = list(set(tool[group]))

        for name_sec in tool:
            section = self.add_section(self.tabWidget.currentIndex(), name_sec,
                                       30)
            row = 0
            col = 0
            for alg in tool[name_sec]:
                section.add_action(alg.id(), row, col)
                if row == 1:
                    row = 0
                    col += 1
                else:
                    row += 1
        self.tabWidget.setUpdatesEnabled(True)
        self.dlg.close()

    def search_tree(self) -> None:
        self.dlg.algorithmTree.setFilterString(self.dlg.searchBox.value())

    def search_add_sections_tree(self) -> None:
        search_text = self.dlg.add_searchBox.value()
        self.dlg.sort.setFilterRegExp(search_text)
        self.dlg.sort.setFilterKeyColumn(0)
        self.dlg.sort.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.dlg.treeView.expandAll()

    def search_add_custom_sections_tree(self) -> None:
        search_text = self.dlg.add_custom_searchBox.value()
        self.dlg.sort_custom.setFilterRegExp(search_text)
        self.dlg.sort_custom.setFilterKeyColumn(0)
        self.dlg.sort_custom.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.dlg.treeView_2.expandAll()

    def section_tab(self) -> None:
        self.dlg.stackedWidget.setCurrentIndex(0)

    def search_tab(self) -> None:
        self.dlg.stackedWidget.setCurrentIndex(1)

    def user_section_tab(self) -> None:
        self.dlg.stackedWidget.setCurrentIndex(2)

    def _section_control_remove(self, tabind: int) -> None:
        lay = self.tabWidget.widget(tabind).lay
        self.tabWidget.setUpdatesEnabled(False)
        for ind in range(lay.count() - 1, -1, -1):
            if isinstance(lay.itemAt(ind), QSpacerItem):
                lay.removeItem(lay.itemAt(ind))
                continue
            it = lay.itemAt(ind)
            if it.widget() is not None:
                if it.widget().objectName() == 'giapSectionAdd':
                    it.widget().hide()
                    lay.removeItem(it)
        QApplication.processEvents()
        self.tabWidget.setUpdatesEnabled(True)

    def _new_tab_tab_control(self) -> None:
        """Pseudo tab to control adding fully feature tab"""

        self.tabWidget.setUpdatesEnabled(False)
        if self.edit_session:
            tab = QWidget()
            tab.setObjectName('giapAddNewTabControl')
            self.tabWidget.addTab(tab, '+')
        else:
            last_tab = self.tabWidget.tabBar().count() - 1
            if self.tabWidget.widget(last_tab).objectName() == \
                    'giapAddNewTabControl':
                self.tabWidget.removeTab(last_tab)
        self.tabWidget.setUpdatesEnabled(True)

    def tab_doubleclicked(self, ind: int) -> None:
        if not self.edit_session:
            return
        self.tabWidget.tabBar().editTab(ind)

    def tab_clicked(self, ind: int) -> None:
        if self.edit_session:
            if ind == self.tabWidget.tabBar().count() - 1:
                self.add_tab()

    def connect_checking_signal(self) -> None:
        self.dlg.treeView_2.selectionModel(). \
            selectionChanged.disconnect()
        self.dlg.treeView_2.selectionModel(). \
            selectionChanged.connect(self.check_for_remove)

    def add_custom_section(self) -> None:
        self.custom_section_dlg = CustomSectionManager(self, 'add')
        if self.custom_section_dlg.exec():
            self.dlg.refresh_lists()
            self.connect_checking_signal()

    def edit_custom_section(self) -> None:
        self.custom_section_dlg = CustomSectionManager(self, 'edit')
        row = self.dlg.get_selected_row()
        if not row:
            CustomMessageBox(
                self.dlg,
                tr("Error - Unable to edit the object.")).button_ok()
            return
        self.custom_section_dlg.edit_selected_item(row)
        if self.custom_section_dlg.exec():
            self.dlg.refresh_lists()
            self.connect_checking_signal()

    def check_for_remove(self) -> None:
        if not hasattr(self, 'custom_section_dlg'):
            self.custom_section_dlg = CustomSectionManager(self, 'remove')

        row = self.dlg.get_selected_row()
        if not row:
            self.dlg.pushButton_remove_custom.setEnabled(False)
        else:
            self.dlg.pushButton_remove_custom.setEnabled(True)

    def remove_custom_section(self) -> None:
        self.custom_section_dlg = CustomSectionManager(self, 'remove')
        row = self.dlg.get_selected_row()
        if not row:
            CustomMessageBox(
                self.dlg,
                tr("Error - Unable to remove the object.")).button_ok()
            return
        req = CustomMessageBox(self, tr(
            "Do you want to delete this section?")).button_yes_no()
        if req == QMessageBox.Yes:
            self.custom_section_dlg.remove_row(row)
            self.dlg.refresh_lists()
            self.connect_checking_signal()

    def eventFilter(self, watched: QWidget, event: QEvent) -> bool:
        # turn off dragging while not in edit session
        if isinstance(watched, CustomSection) and not self.edit_session:
            if event.type() == QEvent.MouseMove:
                return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event: QEvent) ->None:
        if self.edit_session:
            if event.key() == Qt.Key_Delete:
                self.deletePressSignal.emit()

    def generate_ribbon_config(self):
        """ return ribbon setup to save in user config
        (for detail structure look in config file)
        return: list
        """
        riblist = []
        active_ind = self.tabWidget.currentIndex()
        for ind in range(self.tabWidget.count()):
            self.tabWidget.setCurrentIndex(ind)
            wid = self.tabWidget.widget(ind)
            if not isinstance(wid, CustomTab):
                continue
            tdict = wid.return_tab_config()
            # if tab name not edited by user, save eng version
            tab_name = self.tabWidget.tabText(ind)
            trans_tab_names = [tr(key) for key in DEFAULT_TABS]
            if tab_name in trans_tab_names:
                tab_name = DEFAULT_TABS[trans_tab_names.index(tab_name)]
            tdict['tab_name'] = tab_name
            riblist.append(tdict)
        self.tabWidget.setCurrentIndex(active_ind)
        return riblist


class CustomTabBar(QTabBar):
    def __init__(self, label: str='New tab', parent: QtWidgets=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._editor = QLineEdit(self)
        self._editor.setWindowFlags(Qt.Popup)
        self._editor.editingFinished.connect(self.handleEditingFinished)
        self._editor.installEventFilter(self)

    def eventFilter(self, widget: QtWidgets, event: QEvent) -> bool:
        if ((event.type() == QEvent.MouseButtonPress and
             not self._editor.geometry().contains(event.globalPos())) or
                (event.type() == QEvent.KeyPress and
                 event.key() == Qt.Key_Escape)):
            self.handleEditingFinished()
            self._editor.hide()
        return super().eventFilter(widget, event)

    def editTab(self, index: int) -> None:
        rect = self.parent().tabBar().tabRect(index)
        self._editor.setFixedSize(rect.size())
        self._editor.move(self.parent().mapToGlobal(rect.topLeft()))
        self._editor.setText(self.parent().tabText(index))
        if not self._editor.isVisible():
            self._editor.show()

    def handleEditingFinished(self):
        index = self.parent().currentIndex()
        if index >= 0:
            self._editor.hide()
            self.parent().setTabText(index, self._editor.text())


class CustomTab(QWidget):
    def __init__(self, lab: str, parent: QtWidgets =None) -> None:
        super(CustomTab, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.lab = lab
        self.lay = QHBoxLayout()
        self.lay.setSpacing(0)
        self.lay.setMargin(6)
        self.setLayout(self.lay)
        self.setObjectName('giapTab')

        self.lay.addStretch()
        self.lay.setDirection(QBoxLayout.LeftToRight)

        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QEvent) -> None:
        event.accept()

    def dragMoveEvent(self, event: QEvent) -> None:
        event.accept()

    def dropEvent(self, event: QEvent) -> None:
        # accept only Custom Sections
        if not isinstance(event.source(), CustomSection):
            if isinstance(event.source(), CustomToolButton):
                event.source().drag_state = False
            event.setAccepted(False)
            return

        try:
            lay = event.source().parent().lay
        except AttributeError:
            return

        source = None
        for ind in range(lay.count()):
            if not isinstance(lay.itemAt(ind).widget(), CustomSection):
                continue

            it = lay.itemAt(ind)
            if it.widget() is event.source():
                source = ind
                break

        if source is None:
            return

        max_section_ind = lay.count() - 2
        if ind == max_section_ind:
            event.setAccepted(False)
            return

        sec_cont = lay.takeAt(lay.count() - 1)
        addsec = lay.takeAt(lay.count() - 1)
        item = lay.takeAt(ind)
        lay.addItem(addsec)
        lay.addItem(item)
        lay.addItem(sec_cont)
        event.setAccepted(True)

    def return_tab_config(self):
        """Returns config for current tab with all sections,
        (description in config file)
        :return: dict
        """
        sec_conf = []
        for ind in range(self.lay.count()):
            it = self.lay.itemAt(ind)
            if it is None:
                continue
            wid = it.widget()
            if not isinstance(wid, CustomSection):
                continue

            sec_conf.append(wid.return_section_config())

        return {
            'tab_name': self.lab,
            'sections': sec_conf,
        }


class CustomSection(QWidget):
    def __init__(self, name: str ='New Section', parent: QtWidgets =None, main_widgets=None) -> None:
        super(CustomSection, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.edit = True
        self.main_widgets = main_widgets
        self.setAcceptDrops(True)
        self.setMaximumSize(QSize(99999, 110))
        self.setMinimumSize(QSize(80, 110))

        if parent is not None:
            parent.parent().editChanged.connect(self.edit_toggle)
            parent.parent().deletePressSignal.connect(self.key_pressed)

        self.setObjectName('giapSection')

        # target of drop
        self.target = None

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setContentsMargins(7, 0, 7, 0)
        self.button_size = 30

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.horizontalLayout_2.setSpacing(0)

        self.clabel = CustomLabel(tr(name), self)
        self.clabel.setObjectName("giapSectionLabel")
        self.clabel.setMaximumSize(QSize(100000, 20))
        self.clabel.setMinimumSize(QSize(50, 20))
        self.clabel.setAlignment(Qt.AlignCenter)
        charakter = len(self.clabel.text())
        self.clabel.setMinimumSize(QSize(charakter * 8, 20))

        self.pushButton_close_sec = QToolButton(self)
        self.pushButton_close_sec.setObjectName("giapSectionClose")
        self.pushButton_close_sec.setText('x')
        self.pushButton_close_sec.setStyleSheet(
            'border-radius: 3px; font: 7pt;'
        )
        self.pushButton_close_sec.show()
        self.pushButton_close_sec.setMaximumSize(QSize(18, 18))

        self.horizontalLayout_2.addWidget(self.clabel)
        self.horizontalLayout_2.addWidget(self.pushButton_close_sec)

        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.VLine)
        self.sep.setFrameShadow(QFrame.Raised)
        self.sep.setObjectName('giapLine')
        self.sep.setMinimumSize(QSize(6, 100))

        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.gridLayout = QGridLayout()
        self.gridLayout.setSpacing(10)
        self.gridLayout.setContentsMargins(0, 6, 0, 8)
        self.gridLayout.setObjectName(u"gridLayout")

        self.verticalLayout.addLayout(self.gridLayout)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.addLayout(self.verticalLayout)
        self.horizontalLayout.addWidget(self.sep)
        self.horizontalLayout.setContentsMargins(4, 0, 4, 2)

        self.setLayout(self.horizontalLayout)
        self.pushButton_close_sec.clicked.connect(self.unload)

    def unload(self) -> None:
        self.hide()
        self.deleteLater()
        QApplication.processEvents()

    def return_section_config(self):
        """return config for current section
        :return: {}
        """
        blist = []
        for row in range(self.gridLayout.rowCount()):
            for col in range(self.gridLayout.columnCount()):
                it = self.gridLayout.itemAtPosition(row, col)
                if it is None:
                    continue
                itw = it.widget()
                ind = self.gridLayout.indexOf(itw)
                wid = self.gridLayout.itemAt(ind).widget()
                if wid.objectName()[:4].lower() == 'giap' or not wid.actions()\
                        or wid.menu():
                    act = wid.objectName()
                else:
                    act = wid.actions()[0].objectName()
                blist.append([act, row, col])

        lab = self.clabel.text()
        untra_lab = [ll['id'] for ll in STANDARD_TOOLS
                     if tr(ll['label']) == lab]
        if untra_lab:
            lab = untra_lab[0]
        return {
            'label': lab, 'btn_size': self.button_size, 'btns': blist,
        }

    def edit_toggle(self, state: bool) -> None:
        if state:
            self.show_edit_options()
        else:
            self.hide_edit_options()

    def key_pressed(self) -> None:
        """user pressed delete, and we are in edit session"""
        if not self.edit:
            return

        # remove selected buttons
        for col in range(self.gridLayout.columnCount()):
            for row in [0, 1]:
                it = self.gridLayout.itemAtPosition(row, col)
                if it is None:
                    continue
                if not it.widget().selected:
                    continue

                ind = self.gridLayout.indexOf(it.widget())
                wid = self.gridLayout.takeAt(ind)
                wid.widget().turn_off_edit()
                wid.widget().deleteLater()

        self.clean_grid_layout()

    def clean_grid_layout(self) -> None:
        """ move all icons to left, after some where deleted"""
        items = [[], []]  # both rows
        for col in range(self.gridLayout.columnCount()):
            for row in [0, 1]:
                itl = self.gridLayout.itemAtPosition(row, col)
                if itl is None:
                    continue
                it = itl.widget()
                ind = self.gridLayout.indexOf(it)
                it = self.gridLayout.takeAt(ind)
                if it is not None:
                    items[row].append(it)

        for irow, row in enumerate(items):
            for icol, it in enumerate(row):
                if isinstance(it, QWidgetItem):
                    self.gridLayout.addItem(it, irow, icol, 1, 1)
                else:
                    self.gridLayout.addWidget(it, irow, icol, 1, 1)
        self.gridLayout.update()

    def add_action(self, action: QAction, row: int, col: int, menu: QMenu = None):
        self.tbut = CustomToolButton(self)
        if menu:
            name_tool = action.objectName()
            name_tool = name_tool.replace(':', '_')
            self.tbut.setObjectName(name_tool)
            self.tbut.org_state = action.isEnabled()
            self.set_new_giap_icons(self.tbut, name_tool, action)
            self.tbut.setDefaultAction(action)
            self.tbut.setPopupMode(QToolButton.MenuButtonPopup)
            self.tbut.setMenu(menu)
        elif isinstance(action, QAction):
            name_tool = action.objectName()
            name_tool = name_tool.replace(':', '_')
            self.tbut.setObjectName(name_tool)
            self.tbut.org_state = action.isEnabled()
            self.set_new_giap_icons(self.tbut, name_tool, action)
            self.tbut.setObjectName('gp_' + action.objectName())
            self.tbut.setDefaultAction(action)
        elif QgsApplication.processingRegistry().algorithmById(action):
            alg = QgsApplication.processingRegistry().algorithmById(action)
            self.tbut.setObjectName(alg.id())
            newAct = QAction(alg.icon(), alg.displayName(), self)

            def open_window():
                execAlgorithmDialog(newAct.objectName())

            newAct.setObjectName(alg.id())
            newAct.triggered.connect(open_window)
            self.tbut.setDefaultAction(newAct)
            self.tbut.org_state = True
            self.tbut.setText(alg.id())
            action = action.replace(':', '_')
            lista = [file_name.split('.')[0] for file_name in os.listdir(
                os.path.join(os.path.dirname(__file__), 'icons'))]
            if action in lista:
                self.tbut.setIcon(QIcon(
                    os.path.join(os.path.dirname(__file__), 'icons', action)))
        elif isinstance(action, str):
            self.tbut.setObjectName(action)
            self.set_custom_action()

        self.tbut.setMaximumSize(QSize(self.button_size, self.button_size))
        self.tbut.setMinimumSize(QSize(self.button_size, self.button_size))
        if self.button_size == 30:
            self.tbut.setIconSize(
                QSize(self.button_size - 4, self.button_size - 4)
            )
        else:
            self.tbut.setIconSize(
                QSize(self.button_size - 5, self.button_size - 5)
            )
        self.tbut.setEnabled(True)
        self.tbut.installEventFilter(self)
        self.gridLayout.addWidget(self.tbut, row, col, 1, 1)

        return self.tbut

    def set_new_giap_icons(self, button, name_tool: str, action: QAction) -> None:
        icon = icon_manager([name_tool], self.parent())[name_tool]
        if icon:
            action.setIcon(icon)
        if name_tool == 'mActionAddFeature':
            self.parent().parent().parent().parent().add_action = action
        if name_tool == 'mActionMoveFeature':
            self.parent().parent().parent().parent().move_action = action

    def set_custom_action(self) -> None:
        oname = self.tbut.objectName()
        tool = oname.lstrip('gp_') if "gp_" in oname else oname
        if 'giap' in oname:
            icon = icon_manager([tool], self.parent())[tool]
            if oname == 'giapWMS':
                self.orto_add = OrtoAddingTool(self, self.tbut, iface)
                connect_orto = self.orto_add.connect_ortofotomapa_group
                for service in self.orto_add.services:
                    service.orto_group_added.connect(connect_orto)
            if oname == 'giapCompositions':
                self.tbut.setToolTip(tr("Composition settings"))
            if oname == "giapQuickPrint":
                self.quick_print = PrintMapTool(iface, self)
                self.tbut.clicked.connect(self.quick_print.run)
                self.tbut.setToolTip(tr("Map quick print"))
            if oname == "giapMyPrints":
                self.tbut.setToolTip(tr("My Prints"))
            if oname == "giapAreaLength":
                giap_tool_bar = iface.mainWindow().findChildren(QToolBar, 'GiapToolBar')[0]
                try:
                    main_widget = giap_tool_bar.findChildren(MainWidget)[0]
                    iface.mapCanvas().refresh()
                    area_length_tool = QgsMapTool(iface.mapCanvas())
                    area_length_tool.setAction(main_widget.area_length_action)
                    self.tbut.setDefaultAction(main_widget.area_length_action)
                except IndexError:
                    pass
            if oname == "giapPRNG":
                self.tbut.setToolTip(tr("PRNG Tool"))
                self.prng_tool = PRNGTool(self)
                self.tbut.clicked.connect(self.prng_tool.run)
            if oname == "giapGeoportal":
                self.tbut.setToolTip(tr("Geoportal"))
                self.tbut.clicked.connect(self.open_geoportal)
            if oname == "giapOrtoContr":
                self.tbut.setToolTip(tr("Ortofotomapa archiwalna"))
                self.add_feature_menu = QMenu(iface.mainWindow())
                self.standard_res = QAction('Ortofotomapa archiwalna standardowa', iface.mainWindow())
                self.high_res = QAction('Ortofotomapa archiwalna o wysokiej rozdzielczości', iface.mainWindow())
                self.standard_res.triggered.connect(lambda: self.open_temporal_controller('StandardResolution'))
                self.high_res.triggered.connect(lambda: self.open_temporal_controller('HighResolution'))
                self.add_feature_menu.addAction(self.standard_res)
                self.add_feature_menu.addAction(self.high_res)
                self.tbut.setMenu(self.add_feature_menu)
                self.tbut.setPopupMode(QToolButton.InstantPopup)

            if oname == "giapgeokodowanie":
                self.tbut.setToolTip(tr("Geocoding"))
                self.geocoding_tool = Geocoding(self)
                self.tbut.clicked.connect(self.geocoding_tool.run)

            self.tbut.setIcon(icon)

    def unload_custom_actions(self) -> None:
        if self.orto_add:
            self.orto_add.disconnect_ortofotomapa_group()

    def change_label(self, lab) -> None:
        """Changes label
        :lab: str
        """
        if isinstance(lab, str) and lab not in ['', 'None', 'False']:
            self.label.setText(lab)

    def set_size(self, sz) -> None:
        """change size of button
        :sz: int
        """
        self.button_size = sz

    def _get_items(self):
        """return list with item stored in gridlayout
        :return: [[tool, tool], [tool, tool]]
        """
        items = [[], []]  # both rows
        for col in range(self.gridLayout.columnCount()):
            for row in [0, 1]:
                it = self.gridLayout.itemAtPosition(row, col)
                if it is not None:
                    items[row].append(it.widget())
        return items

    def get_toolbutton_layout_index_from_pos(self, pos: QPoint) -> int:
        for index in range(self.gridLayout.count()):
            rect = self.gridLayout.itemAt(index).widget()
            # recalculate rect to compatible coord system
            rect_ok = QRect(0, 0, rect.width(), rect.height())
            if rect_ok.contains(rect.mapFromGlobal(pos)) and \
                    index != self.target:
                return index

    def eventFilter(self, watched, event: QEvent) -> bool:
        if event.type() == QEvent.MouseButtonPress:
            self.mousePressEvent(event)
        elif event.type() == QEvent.MouseMove and \
                isinstance(watched, CustomSection):
            self.mouseMoveEvent(event)
        elif event.type() == QEvent.MouseButtonRelease:
            self.mouseReleaseEvent(event)

        # prevent default action from qtoolbutton
        if isinstance(watched, CustomToolButton) and self.edit:
            if event.type() == QEvent.MouseButtonPress:
                watched.setDown(False)

        if event.type() == QEvent.HoverEnter:
            # if tooltip should show wtihout delay code place here
            pass
        return super().eventFilter(watched, event)

    def mouseReleaseEvent(self, event: QEvent) -> None:
        event.accept()

    def mouseMoveEvent(self, event: QEvent):
        if not self.edit:
            return

        drag = QDrag(self)
        drag.setDragCursor(QPixmap("images/drag.png"), Qt.MoveAction)
        mimedata = QMimeData()

        pixmap = QPixmap(self.size())  # Get the size of the object
        painter = QPainter(pixmap)  # Set the painter’s pixmap
        painter.drawPixmap(self.rect(), self.grab())
        painter.end()

        drag.setMimeData(mimedata)
        drag.setHotSpot(event.pos())
        drag.setPixmap(pixmap)
        drag.exec_(Qt.MoveAction)
        event.accept()

    def dragEnterEvent(self, event: QEvent) -> None:
        event.accept()

    def dropEvent(self, event: QEvent) -> None:  # noqa
        gpos = QCursor().pos()

        if isinstance(event.source(), CustomToolButton):
            move = False
            # check if source and target are in the same gridlayout
            if event.source().parent() is not self:
                event.source().drag_state = False
                return

            source = self.get_toolbutton_layout_index_from_pos(gpos)
            glay = event.source().parent().gridLayout
            self.target = None
            for lay_id in range(glay.count()):
                item = glay.itemAt(lay_id)
                if item.widget() is event.source():
                    self.target = lay_id
                    break

            if source == self.target:
                try:
                    item.widget().drag_state = False
                except Exception:
                    pass
                return

            if None not in [source, self.target] and not move:
                max_ind, min_ind, = max(self.target, source), min(self.target, source)
                pos1 = self.gridLayout.getItemPosition(max_ind)
                pos2 = self.gridLayout.getItemPosition(min_ind)
                it1 = self.gridLayout.takeAt(max_ind)
                it2 = self.gridLayout.takeAt(min_ind)
                it1.widget().setDown(False)
                it2.widget().setDown(False)
                it1.widget().drag_state = False
                it2.widget().drag_state = False
                self.gridLayout.addItem(it1, *pos2)
                self.gridLayout.addItem(it2, *pos1)

        if isinstance(event.source(), CustomSection):
            lay = self.parent().lay

            target = None
            source = None
            for index in range(lay.count()):
                if not isinstance(lay.itemAt(index).widget(), CustomSection):
                    continue

                it = lay.itemAt(index)
                if it.widget() is event.source():
                    source = index
                if it.widget().geometry().contains(
                        it.widget().parent().mapFromGlobal(gpos)):
                    target = index

            if source == target or None in [source, target]:
                return

            item = lay.takeAt(source)
            if target > source:
                target -= 1

            it_list = []
            for index in range(lay.count() - 1, target - 1, -1):
                it_list.append(lay.takeAt(index))
            it_list.reverse()
            lay.addItem(item)
            for it in it_list:
                lay.addItem(it)
            self.target = target

    def show_edit_options(self) -> None:
        self.pushButton_close_sec.show()
        self.edit = True
        self.clean_grid_layout()
        itms = self._get_items()
        for row in [0, 1]:
            for it in itms[row]:
                it.turn_on_edit()
                it.edit = True

    def hide_edit_options(self) -> None:
        self.pushButton_close_sec.hide()
        self.edit = False
        self.clean_grid_layout()
        itms = self._get_items()
        for row in [0, 1]:
            for it in itms[row]:
                it.turn_off_edit()

    def delete_blank_button(self) -> None:
        max_col = ceil(self.gridLayout.count()/2)
        for ind in range(0, self.gridLayout.count()):
            item = self.gridLayout.takeAt(0).widget()
            if ind < max_col:
                self.gridLayout.addWidget(item, 0, ind, 1, 1)
            else:
                self.gridLayout.addWidget(item, 1, ind -max_col, 1, 1)

    def open_geoportal(self):
        crs = iface.mapCanvas().mapSettings().destinationCrs()
        extent = iface.mapCanvas().extent()
        crsDest = QgsCoordinateReferenceSystem("EPSG:2180")
        transformContext = QgsProject.instance().transformContext()
        xform = QgsCoordinateTransform(crs, crsDest, transformContext)
        extent_2180 = xform.transformBoundingBox(extent)
        xmin_2180 = extent_2180.xMinimum()
        ymin_2180 = extent_2180.yMinimum()
        xmax_2180 = extent_2180.xMaximum()
        ymax_2180 = extent_2180.yMaximum()
        url = f"https://mapy.geoportal.gov.pl/imap/Imgp_2.html?composition=default&bbox={str(xmin_2180)},{str(ymin_2180)},{str(xmax_2180)},{str(ymax_2180)}"
        webbrowser.open(url, new=2)

    def remove_raster(self):
        project = QgsProject.instance()
        root = project.layerTreeRoot()
        group = root.findGroup('ORTOFOTOMAPA ARCHIWLANA')
        if not group:
            return
        for child in group.children():
            if isinstance(child, QgsMapLayer):
                project.removeMapLayer(child)
        group.removeAllChildren()
        root.removeChildNode(group)

    def open_temporal_controller(self, resolution):
        self.remove_raster()

        for obj in iface.mainWindow().findChildren(QDockWidget):
            if obj.objectName() == 'Temporal Controller':
                obj.setVisible(True)
                obj.visibilityChanged.connect(self.remove_raster)
                break

        temporalController = iface.mapCanvas().temporalController()
        temporalController.setNavigationMode(QgsTemporalNavigationObject.Animated)
        WMS_EXAMPLE_SRC = "IgnoreGetMapUrl=1" \
                          "&allowTemporalUpdates=true" \
                          "&contextualWMSLegend=0" \
                          "&crs={crs}" \
                          "&enableTime=true" \
                          "&dpiMode=7" \
                          "&featureCount=10" \
                          "&format={image_type}" \
                          "&layers={table_name}" \
                          "&styles&temporalSource=provider" \
                          "&timeDimensionExtent={time_dimis}" \
                          "&type=wmst" \
                          "&url={url}?TIME={time}"
        if resolution == 'StandardResolution':
            wms_url = 'https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMS/StandardResolutionTime'
            img_ras = 'Raster'
        else:
            wms_url = 'https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMS/HighResolutionTime'
            img_ras = 'Image'
        try:
            wms_service = WebMapService(wms_url, '1.3.0')
        except:
            for obj in iface.mainWindow().findChildren(QDockWidget):
                if obj.objectName() == 'Temporal Controller':
                    obj.setVisible(False)
            CustomMessageBox(None, "Brak połączenia z usługą WMS.").button_ok()
            return
        lyr_src_name = wms_service.contents[img_ras].id
        image_type = wms_service.getOperationByName('GetMap').formatOptions[0]
        crs_options = wms_service.contents[img_ras].crsOptions

        try:
            time_dimis = wms_service.contents[img_ras].timepositions[0]
        except TypeError:
            CustomMessageBox(None, "Brak znacznika czasu dla wybranej warstwy.").button_ok()
            for obj in iface.mainWindow().findChildren(QDockWidget):
                if obj.objectName() == 'Temporal Controller':
                    obj.setVisible(False)
            return

        values_map = {
            'url': wms_url,
            'crs': ('EPSG:2180' if 'EPSG:2180' in crs_options
                    else crs_options[0]) if crs_options else 'EPSG:2180',
            'table_name': lyr_src_name,
            'image_type': image_type,
            'time_dimis': time_dimis,
            'time': time_dimis.split('/')[1]
        }

        ls = WMS_EXAMPLE_SRC.format_map(values_map)
        raster_layer_from_cos = QgsRasterLayer(ls, 'ORTOFOTOMAPA ARCHIWLANA', 'wms')

        interval = QgsInterval()
        interval.setYears(1.0)
        temporalController.setFrameDuration(interval)

        add_map_layer_to_group(raster_layer_from_cos, 'ORTOFOTOMAPA ARCHIWLANA', force_create=True)


class CustomToolButton(QToolButton):
    def __init__(self, parent:QtWidgets) -> None:
        super(CustomToolButton, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.edit = True
        self.selected = False
        self.selected_style = '*{border: 3px solid red}'
        self.org_state = True  # True - enabled for click outside edit sesion
        self.drag_state = False
        self.setMinimumSize(QSize(30, 30))
        self.setMaximumSize(QSize(30, 30))

    def eventFilter(self, widget: QWidget, event: QEvent) -> bool:
        if event.type() == QEvent.MouseButtonRelease and self.edit:
            return True
        if self.edit and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                return True
        return super().eventFilter(widget, event)

    def turn_on_edit(self) -> None:
        """ toggle standard behaviour, from clicking to select"""
        self.org_state = self.isEnabled()
        self.setEnabled(True)
        self.blockSignals(True)
        self.setDown(False)

    def turn_off_edit(self) -> None:
        """ toggle standard behaviour, from clicking to select"""
        self.setStyleSheet('')
        self.selected = False
        self.setEnabled(self.org_state)
        self.blockSignals(False)
        self.edit = False

    def mouseClickEvent(self, event: QEvent) -> None:
        if self.edit:
            event.accept()
            event.source.setDown(False)
        else:
            super(CustomToolButton, self).mouseClickEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self.edit:
            if self.selected:
                self.selected = False
                self.setStyleSheet('')
            else:
                self.setStyleSheet(self.selected_style)
                self.selected = True
            self.drag_state = False

    def mouseMoveEvent(self, event: QEvent) -> None:
        if not self.edit or not self.drag_state:
            return
        drag = QDrag(self)
        drag.setDragCursor(QPixmap("images/drag.png"), Qt.MoveAction)
        mimedata = QMimeData()

        pixmap = QPixmap(self.size())  # Get the size of the object
        painter = QPainter(pixmap)  # Set the painter’s pixmap
        painter.drawPixmap(self.rect(), self.grab())
        painter.end()

        drag.setMimeData(mimedata)
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        drag.exec_(Qt.MoveAction)

    def mousePressEvent(self, event: QEvent) -> None:
        if self.edit:
            event.accept()
            self.setDown(False)
            self.drag_state = not self.drag_state
            return
        else:
            super(CustomToolButton, self).mousePressEvent(event)

    def dragEnterEvent(self, event: QEvent) -> None:
        event.accept()


class CustomSectionAdd(QToolButton):
    def __init__(self, parent: QtWidgets=None) -> None:
        super(CustomSectionAdd, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setObjectName('giapSectionAddButton')
        self.setMinimumSize(QSize(30, 30))
        self.setMaximumSize(QSize(30, 30))
        self.setText('+')
        self.setStyleSheet('font: 14px; font-weight: bold;')

        self.button_size = 30

    def bigButtons(self):
        """Set size of tools button to big"""
        self.button_size = 60


class CustomLabel(QLabel):
    def __init__(self, lab: str, parent: QtWidgets=None) -> None:
        super(CustomLabel, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setText(lab)
        self.conf = Config()
        if 'font_changed' in self.conf.setts.keys():
            value = QSettings().value("qgis/stylesheet/fontPointSize") if \
                self.conf.setts["font_changed"] else 10
        else:
            value = 10
        self.setStyleSheet(
            f'font:{value}pt "Segoe UI"; font-weight: normal; '
        )
        self.cinput = QLineEdit(self)
        self.cinput.setWindowFlags(Qt.Popup)
        self.cinput.editingFinished.connect(self.handleEditingFinished)
        self.cinput.installEventFilter(self)
        self.setAlignment(Qt.AlignCenter)
        self.font = QFont('Segoe UI')
        self.fontm = QFontMetrics(self.font)

    def mousePressEvent(self, event) -> None:
        if not self.parent().edit:
            return

        rect = self.rect()
        self.cinput.setFixedSize(rect.size())
        self.cinput.move(self.mapToGlobal(rect.topLeft()))
        self.cinput.setText(self.text())
        if not self.cinput.isVisible():
            self.cinput.show()

    def eventFilter(self, widget, event: QEvent) -> bool:
        if ((event.type() == QEvent.MouseButtonPress and
             not self.cinput.geometry().contains(event.globalPos())) or
                (event.type() == QEvent.KeyPress and
                 event.key() == Qt.Key_Escape)):
            self.handleEditingFinished()
            self.cinput.hide()
        return super().eventFilter(widget, event)

    def handleEditingFinished(self):
        self.cinput.hide()
        self.setText(self.cinput.text())
        charakter = self.cinput.text()
        self.setMinimumSize(
            QSize(self.fontm.width(charakter), self.fontm.height()))
