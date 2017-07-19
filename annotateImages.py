import cairo
import gi
from collections import namedtuple
import csv
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf


class Handler:
    def __init__(self, gui_builder):
        # named tuples used.
        self.buf_and_image = namedtuple('buf_and_image', ['buf', 'image'])
        self.color = namedtuple('color', ['r', 'g', 'b', 'a'])
        self.point = namedtuple('point', ('x', 'y', 'type') +
                                self.color._fields)
        # handles to different widgets
        self.main_window = gui_builder.get_object('main_window')
        self.overlay = gui_builder.get_object('overlay')
        self.label_zoom_level = gui_builder.get_object('zoom_level')
        self.gtk_point_type_list = gui_builder.get_object('point_type_list')
        self.points_type_button = gui_builder.get_object('point_types')
        # ready the draw area
        self.buffers_and_images = {}
        self.init_draw_area(gui_builder)
        # ready the point type selection
        self.point_type_color = self.hex_color_to_rgba('#FF0000')
        self.point_type = 'None'
        self.gtk_point_type_list.append(['#FF0000', 'None'])
        self.points_type_button.set_active(0)
        # init list to store points in
        self.point_list = []
        # init variables for zooming
        self.scale = 1
        self.old_scale = 1
        self.image_width = 100
        self.image_height = 100
        # open the image dialog to choose first image
        self.open_image_dialog()

    def init_draw_area(self, gui_builder):
        images = ['background_image',
                  'original_image',
                  'bw_image',
                  'draw_image']
        for im in images:
            image = gui_builder.get_object(im)
            buf = image.get_pixbuf()
            bi = self.buf_and_image(buf, image)
            self.buffers_and_images[im.rstrip('_image')] = bi

    @staticmethod
    def delete_window(*args):
        Gtk.main_quit(*args)

    def hex_color_to_rgba(self, hex_color):
        h = hex_color.lstrip('#')
        rgb = [int(h[i:i + 2], 16)/255 for i in (0, 2, 4)]
        rgb.append(1)
        rgba = self.color._make(rgb)
        return rgba

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
        self.old_scale = self.scale
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
        for bi in self.buffers_and_images.values():
            buf_temp = bi.buf.scale_simple(width,
                                           height,
                                           GdkPixbuf.InterpType.BILINEAR)
            bi.image.set_from_pixbuf(buf_temp)
        self.label_zoom_level.set_markup(str(self.scale))
        self.redraw_points()

    def point_type_changed(self, button):
        model = button.get_model()
        active = button.get_active()
        if active >= 0:
            code = model[active][0]
            color = self.hex_color_to_rgba(code)
            self.point_type_color = color
            self.point_type = model[active][1]
        else:
            print('No point type selected')

    def add_point(self, event_box, event):
        if event.button == 1:
            point = self.point(event.x,
                               event.y,
                               self.point_type,
                               self.point_type_color.r,
                               self.point_type_color.g,
                               self.point_type_color.b,
                               self.point_type_color.a)
            self.point_list.append(point)
            self.draw_rectangle(point)
        else:
            print(event.button)

    def draw_rectangle(self, point):
        radius = 20
        x = int(point.x - radius / 2)
        y = int(point.y - radius / 2)
        draw = self.buffers_and_images.get('draw')
        draw_buf = draw.image.get_pixbuf()
        width = draw_buf.get_width()
        height = draw_buf.get_height()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(cr, draw_buf, 0, 0)
        cr.paint()
        cr.set_source_rgba(point.r,
                           point.g,
                           point.b,
                           point.a)
        cr.rectangle(x, y, radius, radius)
        cr.fill()
        surface = cr.get_target()
        draw_buf = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
        draw.image.set_from_pixbuf(draw_buf)

    def redraw_points(self):
        scale_factor = self.scale / self.old_scale
        scaled_points = []
        for p in self.point_list:
            x = p.x * scale_factor
            y = p.y * scale_factor
            new_point = self.point(x, y, p.type, p.r, p.g, p.b, p.a)
            scaled_points.append(new_point)
            self.draw_rectangle(new_point)
        self.point_list = scaled_points

    @staticmethod
    def add_image_filters(dialog):
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

    @staticmethod
    def add_text_filters(dialog):
        filter_csv = Gtk.FileFilter()
        filter_csv.set_name("csv")
        filter_csv.add_mime_type("text/csv")
        dialog.add_filter(filter_csv)

        filter_plain = Gtk.FileFilter()
        filter_plain.set_name("Plain text")
        filter_plain.add_mime_type("text/plain")
        dialog.add_filter(filter_plain)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

    def open_image(self, filename):
        original = self.buffers_and_images.get('original')
        original.image.set_from_file(filename)
        new_original_buf = original.image.get_pixbuf()
        new_original = self.buf_and_image(new_original_buf,
                                          original.image)
        self.buffers_and_images['original'] = new_original
        bw = self.buffers_and_images.get('bw')
        bw_filename = filename[0:-4] + '_annotated.png'
        bw.image.set_from_file(bw_filename)
        new_bw_buf = bw.image.get_pixbuf()
        new_bw = self.buf_and_image(new_bw_buf, bw.image)
        self.buffers_and_images['bw'] = new_bw
        self.scale = 1
        self.image_width = new_original.buf.get_width()
        self.image_height = new_original.buf.get_height()
        self.zoom()

    def open_image_dialog(self, open_button=None):
        dialog = Gtk.FileChooserDialog("Please choose a image",
                                       self.main_window,
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        self.add_image_filters(dialog)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("File selected: " + dialog.get_filename())
            self.open_image(dialog.get_filename())
        elif response == Gtk.ResponseType.CANCEL:
            pass
        dialog.destroy()

    def save_points(self, filename):
        header = ['x', 'y', 'type', 'red', 'green', 'blue', 'alpha']
        with open(filename, 'w') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(header)
            for p in self.point_list:
                x = p.x / self.scale
                y = p.y / self.scale
                writer.writerow([x, y, p.type, p.r, p.g, p.b, p.a])

    def save_points_dialog(self, save_button):
        dialog = Gtk.FileChooserDialog("Save annotated points",
                                       self.main_window,
                                       Gtk.FileChooserAction.SAVE,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        dialog.set_do_overwrite_confirmation(True)
        self.add_text_filters(dialog)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("File selected: " + dialog.get_filename())
            self.save_points(dialog.get_filename())
        elif response == Gtk.ResponseType.CANCEL:
            pass
        dialog.destroy()

    def load_point_types(self, filename):
        self.gtk_point_type_list.clear()
        with open(filename, newline='') as csv_file:
            reader = csv.reader(csv_file, delimiter=',')
            for row in reader:
                self.gtk_point_type_list.append(row)
        self.points_type_button.set_active(0)

    def load_point_types_dialog(self, button):
        dialog = Gtk.FileChooserDialog("Please choose a file",
                                       self.main_window,
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN,
                                        Gtk.ResponseType.OK))
        self.add_text_filters(dialog)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("File selected: " + dialog.get_filename())
            self.load_point_types(dialog.get_filename())
        elif response == Gtk.ResponseType.CANCEL:
            pass
        dialog.destroy()


if __name__ == '__main__':
    builder = Gtk.Builder()
    builder.add_from_file("GUI.glade")
    signal_handler = Handler(builder)
    builder.connect_signals(signal_handler)
    window = builder.get_object("main_window")
    window.show_all()
    Gtk.main()
