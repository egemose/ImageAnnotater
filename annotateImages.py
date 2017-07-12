import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf


class Handler:
    def __init__(self, gui_builder):
        self.overlay = gui_builder.get_object('overlay')
        self.background_image = gui_builder.get_object('background_image')
        self.original_image = gui_builder.get_object('original_image')
        self.bw_image = gui_builder.get_object('bw_image')
        self.draw_image = gui_builder.get_object('drawing_image')
        self.label_zoom_level = gui_builder.get_object('zoom_level')
        self.background_buf = self.background_image.get_pixbuf()
        self.original_buf = self.original_image.get_pixbuf()
        self.bw_buf = self.bw_image.get_pixbuf()
        self.draw_buf = self.draw_image.get_pixbuf()

        self.scale = 1

    @staticmethod
    def delete_window(*args):
        Gtk.main_quit(*args)

    def switch_images(self, button):
        if button.get_active():
            self.overlay.reorder_overlay(self.original_image, 0)
            self.overlay.reorder_overlay(self.bw_image, 1)
        else:
            self.overlay.reorder_overlay(self.original_image, 1)
            self.overlay.reorder_overlay(self.bw_image, 0)

    def zoom(self, button):
        value = 0.5
        if button.get_label() == '-':
            value = -value
        if value < 0 and self.scale < 1:
            pass
        else:
            self.scale = self.scale + value
            width = self.scale * 320
            background_buf = self.background_buf.scale_simple(width,
                                                              width,
                                                              GdkPixbuf.InterpType.BILINEAR)
            original_buf = self.original_buf.scale_simple(width,
                                                          width,
                                                          GdkPixbuf.InterpType.BILINEAR)
            bw_buf = self.bw_buf.scale_simple(width,
                                              width,
                                              GdkPixbuf.InterpType.BILINEAR)
            draw_buf = self.draw_buf.scale_simple(width,
                                                  width,
                                                  GdkPixbuf.InterpType.BILINEAR)
            self.background_image.set_from_pixbuf(background_buf)
            self.original_image.set_from_pixbuf(original_buf)
            self.bw_image.set_from_pixbuf(bw_buf)
            self.draw_image.set_from_pixbuf(draw_buf)
            self.label_zoom_level.set_markup(str(self.scale))

    def draw_circle(self, event_box, event):
        print('event at: (%f, %f)' % (event.x, event.y))
        draw_buf = self.draw_image.get_pixbuf()
        width = draw_buf.get_width()
        print(width)
        height = draw_buf.get_height()
        print(height)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(cr, draw_buf, 0, 0)
        cr.paint()
        cr.set_source_rgba(0, 0, 0, 0.5)
        cr.rectangle(int(event.x)-5, int(event.y)-5, 10, 10)
        cr.fill()
        surface = cr.get_target()
        self.draw_buf = Gdk.pixbuf_get_from_surface(surface, 0, 0, width,
                                                    height)
        self.draw_image.set_from_pixbuf(self.draw_buf)


if __name__ == '__main__':
    builder = Gtk.Builder()
    builder.add_from_file("test4.glade")
    signal_handler = Handler(builder)
    builder.connect_signals(signal_handler)
    window = builder.get_object("main_window")
    window.show_all()
    Gtk.main()
