import argparse
import csv
import os
from collections import namedtuple
from math import sqrt, pi, atan2, cos, sin
import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject


def cl_arg():
    parser = argparse.ArgumentParser(description='GUI to annotate images.')
    parser.add_argument('-i', '--images',
                        type=str,
                        help='Folder with images (%(type)s).')
    parser.add_argument('-t', '--types',
                        type=str,
                        help='File with point types in csv (%(type)).')
    parser.add_argument('-p', '--points',
                        type=str,
                        help='File of saved points in csv (%(type)).')
    arguments = parser.parse_args()
    return arguments


def main(handler):
    args = cl_arg()
    if args.images:
        if os.path.isdir(args.images):
            handler.open_image_folder(args.images)
        else:
            handler.open_image(args.images)
    if args.types:
        handler.load_point_types(args.types)
    if args.points:
        handler.load_points(args.points)


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
        self.point = namedtuple('point', ('image', 'type',
                                          'x', 'y',
                                          'size', 'angle')
                                + self.color._fields)
        self.summary_values = namedtuple('summary_values', ['amount', 'size',
                                                            'color'])
        # handles to different widgets
        self.main_window = gui_builder.get_object('main_window')
        self.scroll_window = gui_builder.get_object('scroll_window')
        self.v_adjust = self.scroll_window.get_vadjustment()
        self.h_adjust = self.scroll_window.get_hadjustment()
        self.overlay = gui_builder.get_object('overlay')
        self.label_zoom_level = gui_builder.get_object('zoom_label')
        self.save_points_button = gui_builder.get_object('save_points')
        self.open_image_button = gui_builder.get_object('open_image')
        self.load_point_type_button = gui_builder.get_object('load_point_type')
        self.load_points_button = gui_builder.get_object('load_points')
        self.open_dir_button = gui_builder.get_object('open_image_folder')
        self.zoom_in_button = gui_builder.get_object('zoom_in')
        self.zoom_out_button = gui_builder.get_object('zoom_out')
        self.gtk_point_type_list = gui_builder.get_object('point_type_list')
        self.gtk_point_summary_list = gui_builder.get_object('point_summary')
        self.point_type_button = gui_builder.get_object('select_point_type_box')
        self.switch_image_button = gui_builder.get_object('switch_image')
        self.switch_image_button.set_sensitive(False)
        self.progress_bar = gui_builder.get_object('progress_bar')
        self.last_entry_label = gui_builder.get_object('last_entry')
        self.next_image_button = gui_builder.get_object('open_next_image')
        self.next_image_button.set_sensitive(False)
        # setup the status bar
        self.status_bar = gui_builder.get_object('status_bar')
        self.status_msg = self.status_bar.get_context_id('Message')
        self.status_warning = self.status_bar.get_context_id('Warning')
        self.show_missing_image_warning = True
        # ready the draw area
        self.radius = 10
        self.buffers_and_images = {}
        self.init_draw_area(gui_builder)
        self.do_scroll = False
        self.do_drag = False
        self.pressed_x = None
        self.pressed_y = None
        self.draw_temp = None
        self.draw_buf_temp = None
        # ready the point type selection
        self.point_type_color = self.hex_color_to_rgba('#FF0000')
        self.point_type = 'None'
        self.current_image = 'None'
        self.list_of_images = []
        self.image_folder = None
        self.current_point_file = None
        self.gtk_point_type_list.append(['#FF0000', 'None'])
        self.font = 'arial 11'
        self.bold_font = 'arial bold 11'
        self.background_color = '#FFFFFF'
        self.point_summary_dict = {}
        self.point_type_button.set_active(0)
        # init list to store points in
        self.point_list = []
        self.points_saved = True
        # init variables for zooming
        self.scale = 1
        self.old_scale = 1
        self.image_width = 100
        self.image_height = 100

    def summary_init_values(self, color='#FFFFFF'):
        return self.summary_values(0, 0, color)

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
        if self.warning_dialog_response():
            return True
        Gtk.main_quit(*args)

    def warning_dialog_response(self):
        if not self.points_saved:
            warring_dialog = PointsNotSavedDialog(self.main_window)
            response = warring_dialog.run()
            if response == Gtk.ResponseType.OK:
                warring_dialog.destroy()
                return False
            elif response == Gtk.ResponseType.CANCEL:
                warring_dialog.destroy()
                return True

    def hex_color_to_rgba(self, hex_color):
        h = hex_color.lstrip('#')
        rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        rgb.append(1)
        rgba = self.color._make(rgb)
        return rgba

    @staticmethod
    def rgba_color_to_hex(rgba):
        rgb = (int(rgba.r * 255), int(rgba.g * 255), int(rgba.b * 255))
        hex_color = '#%02X%02X%02X' % rgb
        return hex_color

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
        self.progress_bar.set_text(None)
        task = self.zoom_with_progress()
        GObject.idle_add(task.__next__)

    def zoom_with_progress(self):
        progress = 0
        self.progress_bar.set_fraction(0.0)
        yield True
        width = self.image_width * self.scale
        height = self.image_height * self.scale
        for bi in self.buffers_and_images.values():
            try:
                buf_temp = bi.buf.scale_simple(width,
                                               height,
                                               GdkPixbuf.InterpType.BILINEAR)
                bi.image.set_from_pixbuf(buf_temp)
            except AttributeError:
                self.warn_annotated_image()
            progress = progress + 0.25
            self.progress_bar.set_fraction(progress)
            yield True
        self.label_zoom_level.set_markup(str(self.scale))
        self.redraw_points()
        self.progress_bar.set_text('Done!')
        yield False

    def warn_annotated_image(self):
        if self.show_missing_image_warning:
            status_string = 'Computer annotated image not loaded!'
            self.status_bar.push(self.status_warning, status_string)
            self.switch_image_button.set_sensitive(False)
            self.show_missing_image_warning = False

    def point_type_changed(self, button):
        model = button.get_model()
        active = button.get_active()
        if active >= 0:
            code = model[active][0]
            color = self.hex_color_to_rgba(code)
            self.point_type_color = color
            self.point_type = model[active][1]
        self.update_summary()

    def handle_shortcuts(self, event_box, event):
        key_name = Gdk.keyval_name(event.keyval)
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            if key_name == 's':
                self.save_points_shortcut()
            elif key_name == 'o':
                self.file_dialog(self.open_image_button)
            elif key_name == 'n':
                self.open_next_image()
            elif key_name == 'l':
                self.file_dialog(self.load_point_type_button)
            elif key_name == 'p':
                self.file_dialog(self.load_points_button)
            elif key_name == 'q':
                self.delete_window()
            elif key_name == 'd':
                self.file_dialog(self.open_dir_button)
            elif key_name == 'less':
                self.switch_image_shortcut()
            elif key_name == 'comma':
                self.zoom_pressed(self.zoom_out_button)
            elif key_name == 'period':
                self.zoom_pressed(self.zoom_in_button)
        else:
            self.switch_point_type(key_name)

    def save_points_shortcut(self):
        if self.current_point_file is None:
            self.file_dialog(self.save_points_button)
        else:
            self.save_points(self.current_point_file)

    def switch_image_shortcut(self):
        if self.switch_image_button.get_sensitive():
            if self.switch_image_button.get_active():
                self.switch_image_button.set_active(False)
            else:
                self.switch_image_button.set_active(True)

    def switch_point_type(self, key_name):
        try:
            idx = int(key_name) - 1
            if idx in range(len(self.gtk_point_type_list)):
                self.point_type_button.set_active(idx)
        except ValueError:
            pass

    def clean_draw_image(self):
        width = self.image_width * self.scale
        height = self.image_height * self.scale
        draw = self.buffers_and_images.get('draw')
        buf_temp = draw.buf.scale_simple(width,
                                         height,
                                         GdkPixbuf.InterpType.BILINEAR)
        draw.image.set_from_pixbuf(buf_temp)

    def mouse_move(self, event_box, event):
        if self.do_drag:
            self.make_line_marking(event)
        if self.do_scroll:
            self.scroll(event)

    def scroll(self, event):
        scroll_x = self.h_adjust.get_value()
        scroll_y = self.v_adjust.get_value()
        change_x = self.pressed_x - event.x
        change_y = self.pressed_y - event.y
        new_scroll_x = scroll_x + change_x
        self.h_adjust.set_value(new_scroll_x)
        new_scroll_y = scroll_y + change_y
        self.v_adjust.set_value(new_scroll_y)

    def make_point(self, x, y, dist=None, angle=None):
        point = self.point(self.current_image,
                           self.point_type,
                           x,
                           y,
                           dist,
                           angle,
                           self.point_type_color.r,
                           self.point_type_color.g,
                           self.point_type_color.b,
                           self.point_type_color.a)
        return point

    def make_line_marking(self, event):
        point_start = self.make_point(self.pressed_x, self.pressed_y)
        point_stop = self.make_point(event.x, event.y)
        self.draw_line_marking_live(point_start, point_stop)

    def add_remove_point(self, event_box, event):
        if event.button == 1:
            if event.state & Gdk.ModifierType.CONTROL_MASK:
                self.remove_marking(event)
            else:
                self.add_marking(event)
        elif event.button == 3:
            self.remove_marking(event)
        elif event.button == 2:
            self.button_scroll(event)
        else:
            print(event.button)

    def button_scroll(self, event):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            self.do_scroll = True
            self.pressed_x = event.x
            self.pressed_y = event.y
        elif event.type == Gdk.EventType.BUTTON_RELEASE:
            self.do_scroll = False

    def find_closest_point(self, point):
        dist_keep = 1000000
        p_keep = None
        for p in self.point_list:
            dist = sqrt((p.x - point.x) ** 2 + (p.y - point.y) ** 2)
            if dist < dist_keep:
                dist_keep = dist
                p_keep = p
        return dist_keep, p_keep

    def remove_marking(self, event):
        if self.check_if_click(event):
            dist, point = self.find_closest_point(event)
            if dist < self.radius:
                self.points_saved = False
                self.point_list.remove(point)
                self.clean_draw_image()
                self.draw_markings(self.point_list)
                label_text = 'removed: (%i, %i)' % (int(event.x), int(event.y))
                self.last_entry_label.set_text(label_text)
                key = self.current_image + '--' + point.type
                summary = self.point_summary_dict.get(key)
                new_summary = self.summary_values(summary.amount - 1,
                                                  summary.size, summary.color)
                self.point_summary_dict[key] = new_summary
                self.update_summary()

    def check_if_click(self, event, do_drag=False):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            self.do_drag = do_drag
            self.pressed_x = event.x
            self.pressed_y = event.y
            self.draw_temp = self.buffers_and_images.get('draw')
            self.draw_buf_temp = self.draw_temp.image.get_pixbuf()
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            self.do_drag = False
            if self.pressed_x == event.x and self.pressed_y == event.y:
                return True
        return False

    def add_marking(self, event):
        if self.check_if_click(event, do_drag=True):
            self.add_point(event)
        elif event.type == Gdk.EventType.BUTTON_RELEASE:
            self.add_size_mark(event)

    def add_size_mark(self, event):
        self.points_saved = False
        diff_x = event.x - self.pressed_x
        diff_y = event.y - self.pressed_y
        dist = sqrt(diff_x ** 2 + diff_y ** 2)
        angle = atan2(-diff_y, diff_x)
        display_angle = angle / pi * 180
        point = self.make_point(self.pressed_x,
                                self.pressed_y,
                                dist,
                                angle)
        self.point_list.append(point)
        label_text = '%s %i px, %i degrees' % (self.point_type,
                                               int(dist),
                                               int(display_angle))
        self.last_entry_label.set_text(label_text)
        key = self.current_image + '--' + self.point_type
        summary = self.point_summary_dict.get(key)
        new_summary = self.summary_values(summary.amount + 1,
                                          summary.size + dist, summary.color)
        self.point_summary_dict[key] = new_summary
        self.update_summary()

    def add_point(self, event):
        dist, _ = self.find_closest_point(event)
        if dist > 2 * self.radius:
            self.points_saved = False
            point = self.make_point(event.x, event.y)
            self.point_list.append(point)
            self.draw_markings([point])
            label_text = '%s (%i, %i)' % (self.point_type,
                                          int(event.x),
                                          int(event.y))
            self.last_entry_label.set_text(label_text)
            key = self.current_image + '--' + self.point_type
            summary = self.point_summary_dict.get(key)
            new_summary = self.summary_values(summary.amount + 1,
                                              summary.size, summary.color)
            self.point_summary_dict[key] = new_summary
            self.update_summary()

    def update_summary(self):
        self.gtk_point_summary_list.clear()
        old_image = ''
        dict_sort = sorted(self.point_summary_dict.items(), key=lambda x: x[0])
        for key, summary in dict_sort:
            full_image, point_type = key.split('--')
            if full_image == self.current_image:
                image_font = self.bold_font
                if point_type == self.point_type:
                    point_font = self.bold_font
                else:
                    point_font = self.font
            else:
                image_font = self.font
                point_font = self.font
            image = full_image.split('/')[-1]
            if image != old_image:
                self.gtk_point_summary_list.append([image, '', '',
                                                    image_font,
                                                    self.background_color])
                old_image = image
            self.gtk_point_summary_list.append([point_type,
                                                str(summary.amount),
                                                str(int(summary.size)),
                                                point_font,
                                                summary.color])

    def draw_line_marking_live(self, point_start, point_stop):
        width = self.draw_buf_temp.get_width()
        height = self.draw_buf_temp.get_height()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(cr, self.draw_buf_temp, 0, 0)
        cr.paint()
        cr.set_source_rgba(point_start.r,
                           point_start.g,
                           point_start.b,
                           point_start.a)
        x = int(point_start.x)
        y = int(point_start.y)
        cr.arc(x, y, self.radius, 0, 2 * pi)
        cr.fill()
        cr.move_to(x, y)
        x = int(point_stop.x)
        y = int(point_stop.y)
        cr.line_to(x, y)
        cr.set_line_width(3)
        cr.stroke()
        cr.arc(x, y, self.radius / 2, 0, 2 * pi)
        cr.fill()
        surface = cr.get_target()
        draw_buf = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
        self.draw_temp.image.set_from_pixbuf(draw_buf)

    def draw_markings(self, points):
        draw = self.buffers_and_images.get('draw')
        draw_buf = draw.image.get_pixbuf()
        width = draw_buf.get_width()
        height = draw_buf.get_height()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(cr, draw_buf, 0, 0)
        cr.paint()
        for point in points:
            if point.size is None:
                x = int(point.x)
                y = int(point.y)
                cr.set_source_rgba(point.r, point.g, point.b, point.a)
                cr.arc(x, y, self.radius, 0, 2 * pi)
                cr.fill()
            else:
                cr.set_source_rgba(point.r, point.g, point.b, point.a)
                x = int(point.x)
                y = int(point.y)
                cr.arc(x, y, self.radius, 0, 2 * pi)
                cr.fill()
                cr.move_to(x, y)
                x = int(x + point.size * cos(point.angle))
                y = int(y - point.size * sin(point.angle))
                cr.line_to(x, y)
                cr.set_line_width(3)
                cr.stroke()
                cr.arc(x, y, self.radius / 2, 0, 2 * pi)
                cr.fill()
        surface = cr.get_target()
        draw_buf = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
        draw.image.set_from_pixbuf(draw_buf)

    def redraw_points(self, old_scale=True):
        if old_scale:
            scale_factor = self.scale / self.old_scale
        else:
            scale_factor = self.scale
        scaled_points = []
        draw_points = []
        for p in self.point_list:
            x = p.x * scale_factor
            y = p.y * scale_factor
            if p.size is None:
                dist = None
            else:
                dist = p.size * scale_factor
            new_point = self.point(p.image, p.type, x, y, dist, p.angle,
                                   p.r, p.g, p.b, p.a)
            scaled_points.append(new_point)
            if p.image == self.current_image:
                draw_points.append(new_point)
        self.draw_markings(draw_points)
        self.point_list = scaled_points

    def open_next_image(self, button=None):
        if not self.list_of_images:
            self.get_list_of_images()
        try:
            idx = self.list_of_images.index(self.current_image) + 1
        except ValueError:
            idx = 0
        if idx < len(self.list_of_images):
            new_image = self.list_of_images[idx]
            self.open_image(new_image)
        if idx + 1 == len(self.list_of_images):
            self.next_image_button.set_sensitive(False)
        else:
            status_string = 'No more images in folder'
            self.status_bar.push(self.status_msg, status_string)

    def get_list_of_images(self):
        files = list(self.get_files_in_dir())
        self.list_of_images = sorted(files, key=lambda x: x)

    def get_files_in_dir(self):
        for file in os.scandir(self.image_folder):
            if file.path.endswith('JPG'):
                yield file.path

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

    def open_image_folder(self, filename):
        self.image_folder = filename
        self.open_next_image()

    def open_image(self, filename):
        self.current_image = filename
        self.image_folder = os.path.dirname(filename)
        status_string = 'Image and computer annotated image opened.'
        self.status_bar.push(self.status_msg, status_string)
        self.next_image_button.set_sensitive(True)
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
        for pt in self.gtk_point_type_list:
            key = self.current_image + '--' + pt[1]
            if key not in self.point_summary_dict:
                new_dict = {key: self.summary_init_values(pt[0])}
                self.point_summary_dict.update(new_dict)
        self.update_summary()
        self.zoom()

    def load_point_types(self, filename):
        status_string = 'Point types loaded.'
        self.status_bar.push(self.status_msg, status_string)
        self.gtk_point_type_list.clear()
        self.gtk_point_summary_list.clear()
        self.point_summary_dict.clear()
        image = self.current_image.split('/')
        self.gtk_point_summary_list.append([image[-1], '', '', self.font,
                                            self.background_color])
        with open(filename, newline='') as csv_file:
            reader = csv.reader(csv_file, delimiter=',')
            reader.__next__()
            sort_points = sorted(reader, key=lambda x: x[1])
            for point in sort_points:
                self.update_point_types(point)
        self.point_type_button.set_active(0)
        self.point_list = []
        self.points_saved = True
        self.clean_draw_image()

    def update_point_types(self, row):
        self.gtk_point_type_list.append(row)
        key = self.current_image + '--' + row[1]
        self.point_summary_dict.update({key: self.summary_init_values(row[0])})
        self.update_summary()

    def save_points(self, filename):
        self.current_point_file = filename
        status_string = 'points saved'
        self.status_bar.push(self.status_msg, status_string)
        self.points_saved = True
        header = ['image', 'type', 'x', 'y', 'size', 'angle',
                  'red', 'green', 'blue', 'alpha']
        with open(filename, 'w') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(header)
            for p in self.point_list:
                x = p.x / self.scale
                y = p.y / self.scale
                if p.size is None:
                    dist = None
                else:
                    dist = p.size / self.scale
                writer.writerow([p.image, p.type, x, y, dist, p.angle,
                                 p.r, p.g, p.b, p.a])

    def load_points(self, filename):
        status_string = 'Point types loaded.'
        self.status_bar.push(self.status_msg, status_string)
        self.point_list = []
        self.gtk_point_summary_list.clear()
        with open(filename, newline='') as csv_file:
            reader = csv.reader(csv_file, delimiter=',')
            reader.__next__()
            for row in reader:
                image = row[0]
                point_type = row[1]
                x = float(row[2])
                y = float(row[3])
                if row[4] != '':
                    dist = float(row[4])
                    angle = float(row[5])
                else:
                    dist = None
                    angle = None
                r = float(row[6])
                g = float(row[7])
                b = float(row[8])
                a = float(row[9])
                self.point_list.append(self.point(image, point_type, x, y,
                                                  dist, angle, r, g, b, a))
        self.make_summary_dict()
        self.update_summary()
        self.points_saved = True
        self.redraw_points(old_scale=False)

    def make_summary_dict(self):
        self.point_summary_dict.clear()
        for p in self.point_list:
            color = self.rgba_color_to_hex(p)
            key = p.image + '--' + p.type
            if p.size is None:
                size = 0
            else:
                size = p.size
            if key not in self.point_summary_dict:
                values = self.summary_values(1, size, color)
                self.point_summary_dict.update({key: values})
            else:
                values = self.point_summary_dict.get(key)
                new_values = self.summary_values(values.amount + 1,
                                                 values.size + size,
                                                 color)
                self.point_summary_dict.update({key: new_values})
        for pt in self.gtk_point_type_list:
            key = self.current_image + '--' + pt[1]
            if key not in self.point_summary_dict:
                new_dict = {key: self.summary_init_values(pt[0])}
                self.point_summary_dict.update(new_dict)

    def file_dialog(self, button):
        text = 'Choose a file'
        action = Gtk.FileChooserAction.OPEN
        file_button = Gtk.STOCK_OPEN
        if button.get_label() == 'Save points':
            text = 'Save points as'
            action = Gtk.FileChooserAction.SAVE
            file_button = Gtk.STOCK_SAVE
        elif button.get_label() == 'Load points':
            if self.warning_dialog_response():
                return True
            text = 'Choose a file with the points'
        elif button.get_label() == 'Open image':
            text = 'Choose a image to open'
        elif button.get_label() == 'Load point types':
            if self.warning_dialog_response():
                return True
            text = 'Choose a file with the point types'
        elif button.get_label() == 'Open image folder':
            text = 'choose a folder with images'
            action = Gtk.FileChooserAction.SELECT_FOLDER
        response = (Gtk.STOCK_CANCEL,
                    Gtk.ResponseType.CANCEL,
                    file_button,
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
            if self.image_folder is not None:
                dialog.set_current_folder(self.image_folder)
            self.add_text_filters(dialog)
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                self.save_points(dialog.get_filename())
        elif button.get_label() == 'Load points':
            self.add_text_filters(dialog)
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                self.load_points(dialog.get_filename())
        elif button.get_label() == 'Open image folder':
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                self.open_image_folder(dialog.get_filename())
        dialog.destroy()


if __name__ == '__main__':
    builder = Gtk.Builder()
    builder.add_from_file('data/GUI.glade')
    signal_handler = Handler(builder)
    builder.connect_signals(signal_handler)
    window = builder.get_object('main_window')
    window.show_all()
    main(signal_handler)
    Gtk.main()
