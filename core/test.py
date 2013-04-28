import gtk

window = gtk.Window()

liststore = gtk.ListStore(gtk.gdk.Pixbuf)
for f in ["1.jpg", "2.jpg", "3.jpg"]:
    i = gtk.gdk.pixbuf_new_from_file(f)
    liststore.append([i])

treeview = gtk.TreeView(liststore)
cell = gtk.CellRendererPixbuf()
column = gtk.TreeViewColumn("Pixbuf", cell)
column.add_attribute(cell, "pixbuf", 0)
treeview.append_column(column)

window.connect("destroy", lambda w: gtk.main_quit())

window.add(treeview)
window.show_all()

gtk.main()
