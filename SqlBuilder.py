#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from PyQt4.QtGui import *
from PyQt4.QtCore import pyqtSignal, pyqtSlot, QObject, Qt
from PyQt4.QtSql import *


class FieldType:
    """Search field type enum"""
    TEXT_INPUT, COMBOBOX = 0, 1


class SearchParamType:
    """Input search type enum"""
    typeDict = {0: ' = ', 1: ' REGEXP ', 2: ' LIKE '}


class CirilicDict:
    """dict that assigns a field name and a query filter parameter"""
    c_dict = {'Фамилия': 'lastname', 'Имя': 'firstname', 'Отчество': 'patrname', 'Дата рождения': 'birthdate',
              'Пол': 'sex', 'ОМС': 'SNILS', 'тип документа': "name",
              'серийный номер': "CONCAT_WS(' ',cd.serial, cd.number)"}


class LoginWidget(QWidget):
    """Login widget. displays input 'Database', 'Host', 'User' and 'password' fields.
    On login btn ckick trys to connect the database"""

    login_ok_signal = pyqtSignal()

    def __init__(self, parent=None):
        """Login widget init"""
        QWidget.__init__(self, parent)
        self.line_data_list = {}
        self.setWindowTitle('Login Form')
        form_widget = QWidget(self)

        form_fields = ['Database', 'Host', 'User', 'password']
        field_grid = QGridLayout()
        form_widget.setLayout(field_grid)
        for index, name in enumerate(form_fields):
            field_grid.addWidget(QLabel(name), index, 0)
            if name == 'password':
                l_edit = QLineEdit()
                l_edit.setEchoMode(QLineEdit.Password)
                self.line_data_list[name] = l_edit
                field_grid.addWidget(l_edit, index, 1)
            else:
                l_edit = QLineEdit()
                self.line_data_list[name] = l_edit
                field_grid.addWidget(l_edit, index, 1)
        vert_layout = QVBoxLayout()
        vert_layout.addWidget(form_widget)
        login_btn = QPushButton('Login')
        login_btn.clicked.connect(self.login_cliked)
        vert_layout.addWidget(login_btn)
        self.setLayout(vert_layout)

    def login_cliked(self):
        """on login clicked tries to connect data base"""
        db = QSqlDatabase.addDatabase('QMYSQL');
        db.setHostName(self.line_data_list['Host'].text())
        db.setDatabaseName(self.line_data_list['Database'].text())
        db.setUserName(self.line_data_list['User'].text())
        db.setPassword(self.line_data_list['password'].text())
        if db.open():
            self.login_ok_signal.emit()

    def keyPressEvent(self, qKeyEvent):
        """detect Enter key press"""
        if qKeyEvent.key() == Qt.Key_Enter or Qt.Key_Return:
            self.login_cliked()
        else:
            super(self.__class__, self).keyPressEvent(qKeyEvent)


class SearchWidget(QWidget):
    """Search widget. displays input fields to filter sql query. Equal, LIKE nad REGEXP filter available"""
    search_signal = pyqtSignal(object)

    def __init__(self, parent=None, form_field_names=tuple()):
        """Search widget init"""
        QWidget.__init__(self, parent)
        self.filter_params = {}
        self.setWindowTitle('Search Form')
        search_widget = QWidget(self)
        field_grid_layout = QGridLayout()
        search_widget.setLayout(field_grid_layout)
        for index, name in enumerate(form_field_names):
            field_grid_layout.addWidget(QLabel(name[0].decode('utf-8')), index, 0)
            if name[1] == FieldType.COMBOBOX:
                cb = QComboBox()
                for item in name[2]:
                    cb.addItem(item.decode('utf-8'))
                field_grid_layout.addWidget(cb, index, 2)
                self.filter_params[name[0]] = (name[1], cb)
            elif name[1] == FieldType.TEXT_INPUT:
                name = name[0]
                cb = QComboBox()
                cb.addItem('equals')
                cb.addItem('Regexp')
                cb.addItem('Like')
                field_grid_layout.addWidget(cb, index, 1)
                le = QLineEdit()
                field_grid_layout.addWidget(le, index, 2)
                self.filter_params[name] = (name[0], cb, le)
        form_vert_layout = QVBoxLayout()
        form_vert_layout.addWidget(search_widget)
        login_btn = QPushButton('Search')
        login_btn.clicked.connect(self.search_cliked)
        form_vert_layout.addWidget(login_btn)
        self.setLayout(form_vert_layout)

    def search_cliked(self):
        """on search clicked prepare filter parameters"""
        query_param = {}
        for key in self.filter_params:
            if self.filter_params[key][0] != FieldType.COMBOBOX:
                if self.filter_params[key][2].text().toUtf8() == '':
                    continue
                query_param[key] = str(self.filter_params[key][2].text().toUtf8()), self.filter_params[key][1].currentIndex()
            else:
                if self.filter_params[key][1].currentIndex() == 0:
                    continue
                query_param[key] = self.filter_params[key][1].currentIndex(), 0
        self.search_signal.emit(query_param)

    def keyPressEvent(self, qKeyEvent):
        """detect Enter key press"""
        if qKeyEvent.key() == Qt.Key_Enter or Qt.Key_Return:
            self.search_cliked()
        else:
            super(self.__class__, self).keyPressEvent(qKeyEvent)


class ClientQueryBuilder(QObject):
    """Builds Sql query according filter parameters"""
    send_query_signal = pyqtSignal(object)
    EQUALS, REGEXP, LIKE = 0, 1, 2

    def __init__(self, parent=None, template=''):
        QObject.__init__(self, parent)
        self.template = template

    @pyqtSlot(object)
    def get_query(self, query_dict):
        """prepare sql query according filter parameters"""
        sql_param_template = []
        for param_key in query_dict:
            sql_param_template.append("{0}{1}'{2}'".format(CirilicDict.c_dict[param_key], SearchParamType.typeDict[query_dict[param_key][1]], query_dict[param_key][0]))
        sql_param_template = ' AND '.join(sql_param_template)
        if len(sql_param_template):
            result = '{0}{1}{2}'.format(self.template, ' WHERE ', sql_param_template)
        else:
            result = self.template
        query = QSqlQuery()
        query.prepare(result.decode('utf-8'))
        query.exec_()
        self.send_query_signal.emit(query)


class ApplicationWidget(QWidget):
    template = (r"SELECT CONCAT_WS(' ',lastname, firstname, patrName) as ФИО ,"
                " CONCAT_WS(' ',TIMESTAMPDIFF( year, birthDate, curdate()),'год',birthdate)"
                " as Возраст, IF(sex=1, 'муж', 'жен') AS Пол, SNILS AS ОМС ,"
                " rbd.name as 'тип документа', CONCAT_WS(' ',cd.serial, cd.number) as 'серийный номер'"
                " FROM client as c"
                " JOIN clientdocument as cd on c.id = cd.client_id"
                " JOIN rbdocumenttype as rbd on cd.documentType_id = rbd.id")

    form_fields_names = (('Фамилия', FieldType.TEXT_INPUT), ('Имя', FieldType.TEXT_INPUT),
                         ('Отчество', FieldType.TEXT_INPUT), ('Дата рождения', FieldType.TEXT_INPUT),
                         ('Пол', FieldType.COMBOBOX, ('-', 'Муж', 'Жен')), ('ОМС', FieldType.TEXT_INPUT),
                         ('тип документа', FieldType.TEXT_INPUT),
                         ('серийный номер', FieldType.TEXT_INPUT))

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        qb = LoginWidget(self)
        qb.show()
        qb.login_ok_signal.connect(self.render_search_widget)
        qb.login_ok_signal.connect(qb.close)

    @pyqtSlot(object)
    def set_query(self, query):
        self.q_model.setQuery(query)

    @pyqtSlot()
    def render_search_widget(self, query=QSqlQuery()):
        self.showMaximized()
        self.q_model = QSqlQueryModel()
        self.q_model.setQuery(query)
        sql_table = QTableView()
        sql_table.setModel(self.q_model)
        header = sql_table.horizontalHeader()
        header.setResizeMode(QHeaderView.ResizeToContents)
        search_form = SearchWidget(self, self.form_fields_names)
        search_form.setMaximumSize(400, 600)

        self.q_builder = ClientQueryBuilder(self, self.template)
        search_form.search_signal.connect(self.q_builder.get_query)
        self.q_builder.send_query_signal.connect(self.set_query)
        h_layout = QHBoxLayout()
        h_layout.addWidget(sql_table)
        h_layout.addWidget(search_form)
        self.setLayout(h_layout)


def main():
    app = QApplication(sys.argv)

    mw = ApplicationWidget()
    mw.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
