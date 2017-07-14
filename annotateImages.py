import cairo
import gi
from collections import namedtuple
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf


class Handler:
    def __init__(self, gui_builder):
        self.buf_and_image = namedtuple('buf_and_image', ['buf', 'image'])
        self.main_window = gui_builder.get_object('main_window')
        self.overlay = gui_builder.get_object('overlay')
        self.label_zoom_level = gui_builder.get_object('zoom_level')
        background_image = gui_builder.get_object('background_image')
        original_image = gui_builder.get_object('original_image')
        bw_image = gui_builder.get_object('bw_image')
        draw_image = gui_builder.get_object('drawing_image')
        background_buf = background_image.get_pixbuf()
        original_buf = original_image.get_pixbuf()
        bw_buf = bw_image.get_pixbuf()
        draw_buf = draw_image.get_pixbuf()
        background = self.buf_and_image(background_buf, background_image)
        original = self.buf_and_image(original_buf, original_image)
        bw = self.buf_and_image(bw_buf, bw_image)
        draw = self.buf_and_image(draw_buf, draw_image)
        self.buffers_and_images = {'background': background,
                                   'original': original,
                                   'bw': bw,
                                   'draw': draw}
        self.scale = 1
        self.image_width = 320
        self.image_height = 320

    @staticmethod
    def delete_window(*args):
        Gtk.main_quit(*args)

    def switch_images(self, button):
        original = self.buffers_and_images.get('original')
        bw = self.buffers_and_images.get('bw')
        if button.get_active():
            self.overlay.reorder_overlay(original.image, 0)
            self.overlay.reorder_overlay(bw.image, 1)
        else:
            self.overlay.reorder_overlay(original.image, 1)
            self.overlay.reorder_overlay(bw.image, 0)

    def zoom_pressed(self, button):
        value = 0.5
        if button.get_label() == '-':
            value = -value
        if value < 0 and self.scale < 1:
            pass
        else:
            self.scale = self.scale + value
            self.zoom()

    def zoom(self):
        width = self.image_width * self.scale
        height = self.image_height * self.scale
        for buf_and_image in self.buffers_and_images.values():
            buf_temp = buf_and_image.buf.scale_simple(width,
                                                      height,
                                                      GdkPixbuf.InterpType.BILINEAR)
            buf_and_image.image.set_from_pixbuf(buf_temp)
        self.label_zoom_level.set_markup(str(self.scale))

    def draw_circle(self, event_box, event):
        print('event at: (%f, %f)' % (event.x, event.y))
        draw = self.buffers_and_images.get('draw')
        draw_buf = draw.image.get_pixbuf()
        width = draw_buf.get_width()
        height = draw_buf.get_height()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(cr, draw_buf, 0, 0)
        cr.paint()
        cr.set_source_rgba(1, 0, 0, 1)
        cr.rectangle(int(event.x)-5, int(event.y)-5, 10, 10)
        cr.fill()
        surface = cr.get_target()
        draw_buf = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
        new_draw = self.buf_and_image(draw_buf, draw.image)
        self.buffers_and_images['draw'] = new_draw
        draw.image.set_from_pixbuf(draw_buf)

    @staticmethod
    def add_filters(dialog):
        filter_jpg = Gtk.FileFilter()
        filter_jpg.set_name("JPG images")
        filter_jpg.add_mime_type("image/jpeg")
        dialog.add_filter(filter_jpg)

        filter_png = Gtk.FileFilter()
        filter_png.set_name("Png images")
        filter_png.add_mime_type("image/png")
        dialog.add_filter(filter_png)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

    def open_image(self, filename):
        original = self.buffers_and_images.get('original')
        original.image.set_from_file(filename)
        new_buf = original.image.get_pixbuf()
        new_original = self.buf_and_image(new_buf,
                                          original.image)
        self.buffers_and_images['original'] = new_original
        self.scale = 1
        self.image_width = new_original.buf.get_width()
        self.image_height = new_original.buf.get_height()
        self.zoom()

    def open_image_dialog(self, open_button):
        dialog = Gtk.FileChooserDialog("Please choose a image",
                                       self.main_window,
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        self.add_filters(dialog)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("Open clicked")
            print("File selected: " + dialog.get_filename())
            self.open_image(dialog.get_filename())
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")
        dialog.destroy()


if __name__ == '__main__':
    builder = Gtk.Builder()
    builder.add_from_file("GUI.glade")
    signal_handler = Handler(builder)
    builder.connect_signals(signal_handler)
    window = builder.get_object("main_window")
    window.show_all()
    Gtk.main()
