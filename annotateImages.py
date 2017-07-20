import csv
from collections import namedtuple
from math import sqrt, pi
import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject


class PointsNotSavedDialog(Gtk.Dialog):

    def __init__(self, parent):
        header = 'Points not saved!'
        response = (Gtk.STOCK_CANCEL,
                    Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_OK,
                    Gtk.ResponseType.OK)
        Gtk.Dialog.__init__(self, header, parent, 0, response)
        self.set_default_size(150, 100)
        label = Gtk.Label('The current points have not been saved.')
        label2 = Gtk.Label('Use Cancel to return and then save.')
        label3 = Gtk.Label('Use OK to discard and continue.')
        box = self.get_content_area()
        box.add(label)
        box.add(label2)
        box.add(label3)
        self.show_all()


class Handler:
    def __init__(self, gui_builder):
        # named tuples used.
        self.buf_and_image = namedtuple('buf_and_image', ['buf', 'image'])
        self.color = namedtuple('color', ['r', 'g', 'b', 'a'])
        self.point = namedtuple('point', ('x', 'y', 'type')+self.color._fields)
        # handles to different widgets
        self.main_window = gui_builder.get_object('main_window')
        self.overlay = gui_builder.get_object('overlay')
        self.label_zoom_level = gui_builder.get_object('zoom_label')
        self.gtk_point_type_list = gui_builder.get_object('point_type_list')
        self.point_type_button = gui_builder.get_object('select_point_type_box')
        self.switch_image_button = gui_builder.get_object('switch_image')
        self.progress_bar = gui_builder.get_object('progress_bar')
        # setup the status bar
        self.status_bar = gui_builder.get_object('status_bar')
        self.status_msg = self.status_bar.get_context_id('Message')
        self.status_warning = self.status_bar.get_context_id('Warning')
        self.show_missing_image_warning = True
        # ready the draw area
        self.radius = 10
        self.buffers_and_images = {}
        self.init_draw_area(gui_builder)
        # ready the point type selection
        self.point_type_color = self.hex_color_to_rgba('#FF0000')
        self.point_type = 'None'
        self.gtk_point_type_list.append(['#FF0000', 'None'])
        self.point_type_button.set_active(0)
        # init list to store points in
        self.point_list = []
        self.points_saved = True
        # init variables for zooming
        self.scale = 1
        self.old_scale = 1
        self.image_width = 100
        self.image_height = 100

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

    def delete_window(self, *args):
        if not self.points_saved:
            warring_dialog = PointsNotSavedDialog(self.main_window)
            response = warring_dialog.run()
            if response == Gtk.ResponseType.OK:
                warring_dialog.destroy()
            elif response == Gtk.ResponseType.CANCEL:
                warring_dialog.destroy()
                return True
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
        self.progress_bar.set_fraction(0.0)
        self.old_scale = self.scale
        value = 0.5
        if button.get_label() == 'Zoom too normal':
            self.scale = 1
            self.zoom()
            return
        elif button.get_label() == 'Zoom out':
            value = -value
        if value < 0 and self.scale < 1:
            pass
        else:
            self.scale = self.scale + value
            self.zoom()

    def zoom(self):
        task = self.zoom_with_progress()
        GObject.idle_add(task.__next__)

    def zoom_with_progress(self):
        progress = 0
        width = self.image_width * self.scale
        height = self.image_height * self.scale
        for bi in self.buffers_and_images.values():
            try:
                buf_temp = bi.buf.scale_simple(width,
                                               height,
                                               GdkPixbuf.InterpType.BILINEAR)
                bi.image.set_from_pixbuf(buf_temp)
            except AttributeError:
                if self.show_missing_image_warning:
                    status_string = 'Computer annotated image not loaded!'
                    self.status_bar.push(self.status_warning, status_string)
                    self.switch_image_button.set_sensitive(False)
                    self.show_missing_image_warning = False
            progress = progress + 0.25
            self.progress_bar.set_fraction(progress)
            yield True
        self.label_zoom_level.set_markup(str(self.scale))
        self.redraw_points()
        yield False

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

    def clean_draw_image(self):
        width = self.image_width * self.scale
        height = self.image_height * self.scale
        draw = self.buffers_and_images.get('draw')
        buf_temp = draw.buf.scale_simple(width,
                                         height,
                                         GdkPixbuf.InterpType.BILINEAR)
        draw.image.set_from_pixbuf(buf_temp)

    def find_closest_point(self, point):
        dist_keep = 1000000
        p_keep = None
        for p in self.point_list:
            dist = sqrt((p.x-point.x)**2+(p.y-point.y)**2)
            if dist < dist_keep:
                dist_keep = dist
                p_keep = p
        return dist_keep, p_keep

    def add_remove_point(self, event_box, event):
        if event.button == 1:
            dist, _ = self.find_closest_point(event)
            if dist > 2*self.radius:
                self.points_saved = False
                point = self.point(event.x,
                                   event.y,
                                   self.point_type,
                                   self.point_type_color.r,
                                   self.point_type_color.g,
                                   self.point_type_color.b,
                                   self.point_type_color.a)
                self.point_list.append(point)
                self.draw_circles([point])
        elif event.button == 3:
            dist, point = self.find_closest_point(event)
            if dist < self.radius:
                self.points_saved = False
                self.point_list.remove(point)
                self.clean_draw_image()
                self.draw_circles(self.point_list)
        else:
            print(event.button)

    def draw_circles(self, points):
        draw = self.buffers_and_images.get('draw')
        draw_buf = draw.image.get_pixbuf()
        width = draw_buf.get_width()
        height = draw_buf.get_height()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(cr, draw_buf, 0, 0)
        cr.paint()
        for point in points:
            x = int(point.x)
            y = int(point.y)
            cr.set_source_rgba(point.r,
                               point.g,
                               point.b,
                               point.a)
            cr.arc(x, y, self.radius, 0, 2*pi)
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
        self.draw_circles(scaled_points)
        self.point_list = scaled_points

    @staticmethod
    def add_image_filters(dialog):
        filter_jpg = Gtk.FileFilter()
        filter_jpg.set_name('JPG images')
        filter_jpg.add_mime_type('image/jpeg')
        dialog.add_filter(filter_jpg)

        filter_png = Gtk.FileFilter()
        filter_png.set_name('Png images')
        filter_png.add_mime_type('image/png')
        dialog.add_filter(filter_png)

        filter_any = Gtk.FileFilter()
        filter_any.set_name('Any files')
        filter_any.add_pattern('*')
        dialog.add_filter(filter_any)

    @staticmethod
    def add_text_filters(dialog):
        filter_csv = Gtk.FileFilter()
        filter_csv.set_name('csv')
        filter_csv.add_mime_type('text/csv')
        dialog.add_filter(filter_csv)

        filter_plain = Gtk.FileFilter()
        filter_plain.set_name('Plain text')
        filter_plain.add_mime_type('text/plain')
        dialog.add_filter(filter_plain)

        filter_any = Gtk.FileFilter()
        filter_any.set_name('Any files')
        filter_any.add_pattern('*')
        dialog.add_filter(filter_any)

    def open_image(self, filename):
        status_string = 'Image and computer annotated image opened.'
        self.status_bar.push(self.status_msg, status_string)
        self.switch_image_button.set_sensitive(True)
        self.show_missing_image_warning = True
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
        self.point_list = []
        self.points_saved = True
        self.zoom()

    def load_point_types(self, filename):
        status_string = 'Point types loaded.'
        self.status_bar.push(self.status_msg, status_string)
        self.gtk_point_type_list.clear()
        with open(filename, newline='') as csv_file:
            reader = csv.reader(csv_file, delimiter=',')
            reader.__next__()
            for row in reader:
                self.gtk_point_type_list.append(row)
        self.point_type_button.set_active(0)
        self.point_list = []
        self.points_saved = True
        self.clean_draw_image()
        self.draw_circles(self.point_list)

    def save_points(self, filename):
        status_string = 'points saved'
        self.status_bar.push(self.status_msg, status_string)
        self.points_saved = True
        header = ['x', 'y', 'type', 'red', 'green', 'blue', 'alpha']
        with open(filename, 'w') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(header)
            for p in self.point_list:
                x = p.x / self.scale
                y = p.y / self.scale
                writer.writerow([x, y, p.type, p.r, p.g, p.b, p.a])

    def file_dialog(self, button):
        text = 'Choose a file'
        if button.get_label() == 'Save points':
            text = 'Save points as'
            action = Gtk.FileChooserAction.SAVE
            response = (Gtk.STOCK_CANCEL,
                        Gtk.ResponseType.CANCEL,
                        Gtk.STOCK_SAVE,
                        Gtk.ResponseType.OK)
        else:
            if not self.points_saved:
                warring_dialog = PointsNotSavedDialog(self.main_window)
                response = warring_dialog.run()
                if response == Gtk.ResponseType.OK:
                    warring_dialog.destroy()
                elif response == Gtk.ResponseType.CANCEL:
                    warring_dialog.destroy()
                    return True
            if button.get_label() == 'Open Image':
                text = 'Choose a image to open'
            elif button.get_label() == 'Load point types':
                text = 'Choose a file with the point types'
            action = Gtk.FileChooserAction.OPEN
            response = (Gtk.STOCK_CANCEL,
                        Gtk.ResponseType.CANCEL,
                        Gtk.STOCK_OPEN,
                        Gtk.ResponseType.OK)
        dialog = Gtk.FileChooserDialog(text,
                                       self.main_window,
                                       action,
                                       response)
        if button.get_label() == 'Open image':
            self.add_image_filters(dialog)
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                self.open_image(dialog.get_filename())
        elif button.get_label() == 'Load point types':
            self.add_text_filters(dialog)
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                self.load_point_types(dialog.get_filename())
        elif button.get_label() == 'Save points':
            dialog.set_do_overwrite_confirmation(True)
            self.add_text_filters(dialog)
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                self.save_points(dialog.get_filename())
        dialog.destroy()


if __name__ == '__main__':
    builder = Gtk.Builder()
    builder.add_from_file('data/GUI.glade')
    signal_handler = Handler(builder)
    builder.connect_signals(signal_handler)
    window = builder.get_object('main_window')
    window.show_all()
    Gtk.main()
