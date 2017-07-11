import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf


class MyWindow(Gtk.Window):

    def __init__(self):
        self.window = Gtk.Window(title="Images")
        self.window.set_default_size(400, 400)
        self.window.connect("delete-event", Gtk.main_quit)
        self.window.set_border_width(8)

        self.scale = 1.0

        v_box = Gtk.VBox(spacing=8)
        v_box.set_border_width(8)
        self.window.add(v_box)

        label = Gtk.Label()
        label.set_markup('Open 2 image and make them zoom-able')
        v_box.pack_start(label, False, False, 0)

        bt_switch = Gtk.ToggleButton('Switch image')
        bt_switch.connect("toggled", self.switch_images)
        v_box.pack_start(bt_switch, False, False, 0)

        self.add_zoom_buttons(v_box)
        self.add_images(v_box)

        self.window.show_all()
        self.image2.hide()

    def add_images(self, vbox):
        scrolled_window = Gtk.ScrolledWindow()
        vbox.add(scrolled_window)
        v_box2 = Gtk.VBox(spacing=0)
        v_box2.set_border_width(8)
        scrolled_window.add_with_viewport(v_box2)
        image_path = 'data/drone.png'
        self.image = Gtk.Image.new_from_file(image_path)
        self.pixbuf1 = self.image.get_pixbuf()
        v_box2.pack_start(self.image, False, False, 0)
        image_path2 = 'data/drone2.png'
        self.image2 = Gtk.Image.new_from_file(image_path2)
        self.pixbuf2 = self.image2.get_pixbuf()
        v_box2.pack_start(self.image2, False, False, 0)

    def add_zoom_buttons(self, vbox):
        flow_box = Gtk.FlowBox()
        vbox.pack_start(flow_box, False, False, 0)
        button_zoom_out = Gtk.Button()
        button_zoom_out.set_label('-')
        button_zoom_out.connect('clicked', self.zoom_toggled)
        flow_box.add(button_zoom_out)
        self.label_zoom_level = Gtk.Label()
        self.label_zoom_level.set_markup(str(self.scale))
        flow_box.add(self.label_zoom_level)
        button_zoom_in = Gtk.Button()
        button_zoom_in.set_label('+')
        button_zoom_in.connect('clicked', self.zoom_toggled)
        flow_box.add(button_zoom_in)

    def switch_images(self, button):
        if button.get_active():
            self.image.hide()
            self.image2.show()
        else:
            self.image2.hide()
            self.image.show()

    def zoom_toggled(self, button):
        value = 0.5
        if button.get_label() == '-':
            value = -value
        if value < 0 and self.scale < 1:
            pass
        else:
            self.scale = self.scale + value
            width = self.scale * 320
            pix_buf1 = self.pixbuf1.scale_simple(width,
                                                 width,
                                                 GdkPixbuf.InterpType.BILINEAR)
            pix_buf2 = self.pixbuf2.scale_simple(width,
                                                 width,
                                                 GdkPixbuf.InterpType.BILINEAR)
            self.image.set_from_pixbuf(pix_buf1)
            self.image2.set_from_pixbuf(pix_buf2)
            self.label_zoom_level.set_markup(str(self.scale))


if __name__ == '__main__':
    MyWindow()
    Gtk.main()
