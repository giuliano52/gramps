#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2001-2004  Donald N. Allingham
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

# $Id$

#-------------------------------------------------------------------------
#
# GTK/Gnome modules
#
#-------------------------------------------------------------------------
import gobject
import gtk
import gtk.gdk

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
import RelLib
import EditSource
import Utils
import DisplayModels

from QuestionDialog import QuestionDialog

column_names = [
    _('Title'),
    _('ID'),
    _('Author'),
    _('Abbreviation'),
    _('Publication Information'),
    ]

#-------------------------------------------------------------------------
#
# internationalization
#
#-------------------------------------------------------------------------
from gettext import gettext as _

#-------------------------------------------------------------------------
#
# SouceView
#
#-------------------------------------------------------------------------
class SourceView:
    def __init__(self,parent,db,glade,update):
        self.parent = parent
        self.glade = glade
        self.db = db
        self.update = update
        self.list = glade.get_widget("source_list")
        self.selection = self.list.get_selection()
        colno = 0

        self.renderer = gtk.CellRendererText()

        self.model = DisplayModels.SourceModel(self.db)
        self.list.set_model(self.model)
        self.topWindow = self.glade.get_widget("gramps")

        self.columns = []
        self.build_columns()

    def load_sources(self,id=None):
        pass

    def on_click(self,column):
        self.click_col = column

    def build_columns(self):
        for column in self.columns:
            self.list.remove_column(column)
            
        column = gtk.TreeViewColumn(_('Title'), self.renderer,text=0)
        column.set_resizable(gtk.TRUE)        
        #column.set_clickable(gtk.TRUE)
        column.set_min_width(225)
        #column.set_sort_column_id(0)
        self.list.append_column(column)
        self.columns = [column]

        index = 1
        for pair in self.parent.db.get_source_column_order():
            if not pair[0]:
                continue
            name = column_names[pair[1]]
            column = gtk.TreeViewColumn(name, self.renderer, text=pair[1])
            column.set_resizable(gtk.TRUE)
            column.set_clickable(gtk.TRUE)
            column.set_min_width(75)
            column.set_sort_column_id(0)
            self.columns.append(column)
            self.list.append_column(column)
            index += 1

    def change_db(self,db):
        self.build_columns()
        self.build_tree()

    def goto(self,id):
        iter = self.map[id]
        self.list.get_selection().select_iter(iter)
        itpath = self.model.get_path (iter)
        col = self.list.get_column (0)
        self.list.scroll_to_cell (itpath, col, gtk.TRUE, 0.5, 0)

    def build_tree(self):
        self.list.set_model(None)
        self.model = DisplayModels.SourceModel(self.parent.db)

        self.list.set_model(self.model)

        self.selection = self.list.get_selection()
        #self.selection.connect('changed',self.row_changed)
        #self.list.connect('row_activated', self.alpha_event)
        #self.model.connect('button-press-event',self.on_plist_button_press)        

    def button_press(self,obj,event):
        if event.type == gtk.gdk._2BUTTON_PRESS and event.button == 1:
            store,iter = self.selection.get_selected()
            id = store.get_value(iter,1)
            source = self.db.get_source(id)
            EditSource.EditSource(source,self.db,self.parent,self.topWindow,self.update_display)
            return 1
        elif event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            self.build_context_menu(event)
            return 1
        return 0

    def key_press(self,obj,event):
    	if event.keyval == gtk.gdk.keyval_from_name("Return") \
    	    	    	    	    	and not event.state:
    	    self.on_edit_clicked(obj)
    	    return 1
    	return 0

    def build_context_menu(self,event):
        """Builds the menu with editing operations on the source's list"""
        
        store,iter = self.selection.get_selected()
        if iter:
            sel_sensitivity = 1
        else:
            sel_sensitivity = 0
        entries = [
            (gtk.STOCK_ADD, self.on_add_clicked,1),
            (gtk.STOCK_REMOVE, self.on_delete_clicked,sel_sensitivity),
            (_("Edit"), self.on_edit_clicked,sel_sensitivity),
        ]

        menu = gtk.Menu()
        menu.set_title(_('Source Menu'))
        for stock_id,callback,sensitivity in entries:
            item = gtk.ImageMenuItem(stock_id)
            if callback:
                item.connect("activate",callback)
            item.set_sensitive(sensitivity)
            item.show()
            menu.append(item)
        menu.popup(None,None,None,event.button,event.time)

    def on_add_clicked(self,obj):
        EditSource.EditSource(RelLib.Source(),self.db,self.parent,self.topWindow,self.new_after_edit)

    def on_delete_clicked(self,obj):
        
        store,iter = self.selection.get_selected()
        if not iter:
            return
        
        id = store.get_value(iter,1)
        source = self.db.get_source(id)

        if self.is_used(source):
            ans = EditSource.DelSrcQuery(source,self.db,self.update)

            QuestionDialog(_('Delete %s?') % source.get_title(),
                           _('This source is currently being used. Deleting it '
                             'will remove it from the database and from all '
                             'records that reference it.'),
                           _('_Delete Source'),
                           ans.query_response,self.topWindow)
        else:
            self.db.remove_source_id(source.get_id())
            self.update(0)

    def is_used(self,source):
        for key in self.db.get_place_id_keys():
            p = self.db.get_place_id(key)
            for sref in p.get_source_references():
                if sref.get_base_id() == source.get_id():
                    return 1
        for key in self.db.get_person_keys():
            p = self.db.get_person(key)
            for v_id in p.get_event_list() + [p.get_birth_id(), p.get_death_id()]:
                v = self.db.find_event_from_id(v_id)
                if v:
                    for sref in v.get_source_references():
                        if sref.get_base_id() == source.get_id():
                            return 1
            for v in p.get_attribute_list():
                for sref in v.get_source_references():
                    if sref.get_base_id() == source.get_id():
                        return 1
            for v in p.get_alternate_names() + [p.get_primary_name()]:
                for sref in v.get_source_references():
                    if sref.get_base_id() == source.get_id():
                        return 1
            for v in p.get_address_list():
                for sref in v.get_source_references():
                    if sref.get_base_id() == source.get_id():
                        return 1
        for p_id in self.db.get_object_keys():
            p = self.db.find_object_from_id(p_id)
            for sref in p.get_source_references():
                if sref.get_base_id() == source.get_id():
                    return 1
        for p_id in self.db.get_family_keys():
            p = self.db.find_family_from_id(p_id)
            for v_id in p.get_event_list():
                v = self.db.find_event_from_id(v_id)
                if v:
                    for sref in v.get_source_references():
                        if sref.get_base_id() == source.get_id():
                            return 1
            for v in p.get_attribute_list():
                for sref in v.get_source_references():
                    if sref.get_base_id() == source.get_id():
                        return 1
        return 0

    def on_edit_clicked(self,obj):
        list_store, iter = self.selection.get_selected()
        if iter:
            id = list_store.get_value(iter,1)
            source = self.db.get_source(id)
            EditSource.EditSource(source, self.db, self.parent, self.topWindow, self.update_display)

    def new_after_edit(self,source):
        self.db.add_source(source)
        self.update(0)

    def update_display(self,place):
        self.db.build_source_display(place.get_id())
        self.update(0)
