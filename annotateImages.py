import argparse
import csv
import os
from collections import namedtuple
from math import sqrt, pi, atan2
import platform
import cairo
import gi
import numpy as np
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GdkPixbuf, GObject


def cl_arg():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.MetavarTypeHelpFormatter,
        description='GUI to annotate images.')
    parser.add_argument('-i', '--images',
                        type=str,
                        help='Folder with images (%(type)s).')
    parser.add_argument('-t', '--types',
                        type=str,
                        help='File with point types in csv (%(type)s).')
    parser.add_argument('-p', '--points',
                        type=str,
                        help='File of saved points in csv (%(type)s).')
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


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='org.annotate.images',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None
        self.handler = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.make_action('preferences', self.on_preferences)
        self.make_action('open_image_folder', self.on_open_image_folder)
        self.make_action('open_image', self.on_open_image)
        self.make_action('open_markings', self.on_open_markings)
        self.make_action('open_markings_types', self.on_open_marking_types)
        self.make_action('save_markings', self.on_save_markings)
        self.make_action('save_as_markings', self.on_save_as_markings)
        self.make_action('quit', self.on_quit)
        self.make_action('previous_image', self.on_previous_image)
        self.make_action('next_image', self.on_next_image)
        self.make_action('switch_image', self.on_switch_image)
        self.make_action('switch_to_boundingbox', self.on_switch_bounding_box)
        self.make_action('zoom_out', self.on_zoom_out)
        self.make_action('zoom_in', self.on_zoom_in)
        self.make_action('zoom_normal', self.on_zoom_normal)
        self.make_action('about', self.on_about)

    def do_activate(self):
        menu_builder = Gtk.Builder()
        menu_builder.add_from_file('data/menu.glade')
        menu_bar = menu_builder.get_object('menu_bar')
        self.set_menubar(menu_bar)
        win_builder = Gtk.Builder()
        win_builder.add_from_file('data/GUI.glade')
        self.handler = Handler(win_builder)
        win_builder.connect_signals(self.handler)
        self.window = win_builder.get_object('main_window')
        self.window.set_title('Image Annotating')
        self.window.set_application(self)
        self.window.show_all()
        main(self.handler)

    def make_action(self, name, func):
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', func)
        self.add_action(action)

    def on_about(self, action, param):
        about_dialog = AboutDialog(self.window)
        response = about_dialog.run()
        if response:
            about_dialog.destroy()

    def on_quit(self, action, param):
        self.quit()

    def on_open_image_folder(self, action, param):
        self.handler.file_dialog(self.handler.open_dir_button)

    def on_open_image(self, action, param):
        self.handler.file_dialog(self.handler.open_image_button)

    def on_open_markings(self, action, param):
        self.handler.file_dialog(self.handler.load_points_button)

    def on_open_marking_types(self, action, param):
        self.handler.file_dialog(self.handler.load_point_type_button)

    def on_save_markings(self, action, param):
        self.handler.save_points_shortcut()

    def on_save_as_markings(self, action, param):
        self.handler.file_dialog(self.handler.save_points_button)

    def on_previous_image(self, action, param):
        self.handler.open_next_image(self.handler.previous_image_button)

    def on_next_image(self, action, param):
        self.handler.open_next_image(self.handler.next_image_button)

    def on_switch_image(self, action, param):
        self.handler.switch_things_shortcut(self.handler.switch_image_button)

    def on_switch_bounding_box(self, action, param):
        self.handler.switch_things_shortcut(self.handler.switch_box_button)

    def on_zoom_out(self, action, param):
        self.handler.zoom_pressed(self.handler.zoom_out_button)

    def on_zoom_in(self, action, param):
        self.handler.zoom_pressed(self.handler.zoom_in_button)

    def on_zoom_normal(self, action, param):
        self.handler.zoom_pressed(self.handler.zoom_normal)

    def on_preferences(self, action, pram):
        preferences_dialog = PreferencesDialog(self.window)
        response = preferences_dialog.run()
        if response:
            preferences_dialog.destroy()


class PreferencesDialog(Gtk.Dialog):
    def __init__(self, parent):
        header = 'Preferences'
        response = (Gtk.STOCK_OK, Gtk.ResponseType.OK)
        Gtk.Dialog.__init__(self, header, parent, 0, response)
        self.set_default_size(150, 100)
        label = Gtk.Label('Coming soon')
        label2 = Gtk.Label('')
        box = self.get_content_area()
        box.add(label)
        box.add(label2)
        self.show_all()
        # drawing size
        # ending of annotated files
        # working dir


class AboutDialog(Gtk.Dialog):
    def __init__(self, parent):
        header = 'About'
        response = (Gtk.STOCK_OK, Gtk.ResponseType.OK)
        Gtk.Dialog.__init__(self, header, parent, 0, response)
        self.set_default_size(150, 100)
        label = Gtk.Label('Image annotation program')
        label2 = Gtk.Label('Used to make markings on images.')
        box = self.get_content_area()
        box.add(label)
        box.add(label2)
        self.show_all()


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


class OverridePointImageDialog(Gtk.Dialog):
    def __init__(self, parent):
        header = 'Point - Image mismatch'
        response = (Gtk.STOCK_NO,
                    Gtk.ResponseType.NO,
                    Gtk.STOCK_YES,
                    Gtk.ResponseType.YES)
        Gtk.Dialog.__init__(self, header,  parent, 0, response)
        self.set_default_size(150, 100)
        label = Gtk.Label('The points loaded do not match the current image.')
        label2 = Gtk.Label('Do you want to show the point anyway?')
        box = self.get_content_area()
        box.add(label)
        box.add(label2)
        self.show_all()


class Handler:
    def __init__(self, gui_builder):
        self.dir_delimiter = '/'
        if platform.system().startswith('Win'):
            self.dir_delimiter = '\\'
        # named tuples used.
        self.buf_and_image = namedtuple('buf_and_image', ['buf', 'image'])
        self.color = namedtuple('color', ['r', 'g', 'b', 'a'])
        self.point = namedtuple('point', ('image', 'type',
                                          'x', 'y', 'x2', 'y2', 'box')
                                + self.color._fields)
        self.summary_values = namedtuple('summary_values', ['amount', 'size',
                                                            'color'])
        # handles to different widgets
        self.main_window = gui_builder.get_object('main_window')
        self.scroll_window = gui_builder.get_object('scroll_window')
        self.v_adjust = self.scroll_window.get_vadjustment()
        self.h_adjust = self.scroll_window.get_hadjustment()
        self.v_adjust_value = 0
        self.h_adjust_value = 0
        self.layout = gui_builder.get_object('layout')
        self.draw_image = gui_builder.get_object('draw_image')
        self.draw_image_and_buf = self. buf_and_image(
            self.draw_image.get_pixbuf(),
            self.draw_image)
        self.save_points_button = gui_builder.get_object('save_points')
        self.open_image_button = gui_builder.get_object('open_image')
        self.load_point_type_button = gui_builder.get_object('load_point_type')
        self.load_points_button = gui_builder.get_object('load_points')
        self.open_dir_button = gui_builder.get_object('open_image_folder')
        self.zoom_in_button = gui_builder.get_object('zoom_in')
        self.zoom_out_button = gui_builder.get_object('zoom_out')
        self.zoom_normal = gui_builder.get_object('zoom_too_normal')
        self.zoom_slider = gui_builder.get_object('zoom_scale')
        self.gtk_point_type_list = gui_builder.get_object('point_type_list')
        self.gtk_point_summary_list = gui_builder.get_object('point_summary')
        self.point_type_button = gui_builder.get_object('select_point_type_box')
        self.switch_image_button = gui_builder.get_object('switch_image')
        self.switch_image_button.set_sensitive(False)
        self.switch_box_button = gui_builder.get_object('draw_boxes')
        self.progress_bar = gui_builder.get_object('progress_bar')
        self.last_entry_label = gui_builder.get_object('last_entry')
        self.next_image_button = gui_builder.get_object('open_next_image')
        self.next_image_button.set_sensitive(False)
        self.previous_image_button = gui_builder.get_object(
            'open_previous_image')
        self.previous_image_button.set_sensitive(False)
        # setup the status bar
        self.status_bar = gui_builder.get_object('status_bar')
        self.status_msg = self.status_bar.get_context_id('Message')
        self.status_warning = self.status_bar.get_context_id('Warning')
        self.show_missing_image_warning = True
        # ready the draw area
        self.scroll_speed = 78
        self.radius = 10
        self.buffers_and_images = {}
        self.init_draw_area(gui_builder)
        self.window_height = 0
        self.window_width = 0
        self.do_scroll = False
        self.do_drag = False
        self.pressed_on_point = False
        self.pressed_on_point_head = False
        self.pressed_on_point_tail = False
        self.point_clicked = None
        self.pressed_x = None
        self.pressed_y = None
        self.draw_temp = None
        self.draw_buf_temp = None
        self.do_draw_bounding_boxes = False
        # ready the point type selection
        self.point_type_color = self.hex_color_to_rgba('#FF0000')
        self.point_type = None
        self.current_image = 'None'
        self.list_of_images = []
        self.tree_image_index = {}
        self.image_folder = None
        self.current_point_file = None
        self.font = 'arial 11'
        self.bold_font = 'arial bold 11'
        self.background_color = '#FFFFFF'
        self.point_summary_dict = {}
        self.point_type_button.set_active(0)
        # init list to store points in
        self.point_list = []
        self.points_saved = True
        self.override_point_image_match = False
        # init variables for zooming
        self.slider_pressed = False
        self.zoom_percent = 100
        self.image_width = 100
        self.image_height = 100
        self.do_run_idle_tasks = True
        task = self.do_draw_markings_when_idle()
        GObject.idle_add(task.__next__)
        task2 = self.do_move_draw_image_if_scrolled()
        GObject.idle_add(task2.__next__)

    def do_move_draw_image_if_scrolled(self):
        while self.do_run_idle_tasks:
            if self.v_adjust.get_value() != self.v_adjust_value or self.h_adjust.get_value != self.h_adjust_value:
                self.v_adjust_value = self.v_adjust.get_value()
                self.h_adjust_value = self.h_adjust.get_value()
                self.move_draw_image()
                self.draw_markings()
            yield True
        yield False

    def set_cursor(self, cursor_type=None):
        cursor = Gdk.Cursor(Gdk.CursorType.ARROW)
        if cursor_type == 'cross':
            cursor = Gdk.Cursor(Gdk.CursorType.CROSSHAIR)
        self.layout.get_bin_window().set_cursor(cursor)

    def do_draw_markings_when_idle(self):
        while self.do_run_idle_tasks:
            if not self.do_drag and not self.do_scroll and \
                    not self.slider_pressed:
                self.draw_markings()
            yield True
        yield False

    def summary_init_values(self, color='#FFFFFF'):
        return self.summary_values(0, 0, color)

    def init_draw_area(self, gui_builder):
        images = ['original_image',
                  'bw_image']
        for im in images:
            image = gui_builder.get_object(im)
            buf = image.get_pixbuf()
            bi = self.buf_and_image(buf, image)
            self.buffers_and_images[im.rstrip('_image')] = bi

    def delete_window(self, *args):
        if self.warning_dialog_response():
            return True
        self.do_run_idle_tasks = False
        self.main_window.destroy()

    def warning_dialog_response(self):
        if not self.points_saved:
            warning_dialog = PointsNotSavedDialog(self.main_window)
            response = warning_dialog.run()
            if response == Gtk.ResponseType.OK:
                warning_dialog.destroy()
                return False
            elif response == Gtk.ResponseType.CANCEL:
                warning_dialog.destroy()
                return True

    def warning_point_image_mismatch(self):
        warning_dialog = OverridePointImageDialog(self.main_window)
        response = warning_dialog.run()
        if response == Gtk.ResponseType.YES:
            warning_dialog.destroy()
            return True
        elif response == Gtk.ResponseType.NO:
            warning_dialog.destroy()
            return False

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
            original.image.hide()
            bw.image.show()
        else:
            original.image.show()
            bw.image.hide()

    def switch_to_bounding_box(self, button):
        if button.get_active():
            self.do_draw_bounding_boxes = True
            self.set_cursor('cross')
        else:
            self.do_draw_bounding_boxes = False
            self.set_cursor()

    def zoom_slide(self, slider, scroll, value):
        self.zoom_percent = round(value)
        if abs(slider.get_value() - value) >= 10:
            self.check_zoom_range()
            self.zoom()

    def check_zoom_range(self):
        if self.zoom_percent > 250:
            self.zoom_percent = 250
        elif self.zoom_percent < 10:
            self.zoom_percent = 10

    def zoom_slide_pressed(self, scale, event):
        self.slider_pressed = True

    def zoom_slide_release(self, scale, event):
        self.slider_pressed = False
        self.check_zoom_range()
        self.zoom()

    def mouse_wheel(self, event_box, event):
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            self.zoom_mouse_wheel(event)
        else:
            self.do_scroll_step(event)
            self.move_draw_image()
            self.draw_markings()
        return True

    def do_scroll_step(self, event):
        y_updated = self.v_adjust.get_value()
        y_updated = y_updated + event.delta_y * self.scroll_speed
        self.v_adjust.set_value(y_updated)

    def scale_to_zoom(self, *numbers, divide=False, offset=None):
        if divide:
            factor = 100 / self.zoom_percent
        else:
            factor = self.zoom_percent / 100
        if offset is None:
            offset = (0,) * len(numbers)
        if len(numbers) == 1:
            return numbers[0] * factor - offset[0]
        args_out = []
        for n, o in zip(numbers, offset):
            if n is None:
                args_out.append(None)
            else:
                args_out.append(n * factor - o)
        return args_out

    def zoom_mouse_wheel(self, event):
        x, y = self.scale_to_zoom(event.x, event.y)
        if event.delta_y == 1:
            self.zoom_percent = self.zoom_percent - 10
        elif event.delta_y == -1:
            self.zoom_percent = self.zoom_percent + 10
        self.check_zoom_range()
        self.zoom()
        delta_x = self.scale_to_zoom(event.x) - x
        delta_y = self.scale_to_zoom(event.y) - y
        delta_x = self.scale_to_zoom(delta_x, divide=True)
        delta_y = self.scale_to_zoom(delta_y, divide=True)
        self.scroll(delta_x, delta_y, delta=True)
        self.move_draw_image()

    def zoom_pressed(self, button):
        if button.get_label() == 'Zoom too normal':
            self.zoom_percent = 100
        elif button.get_label() == 'Zoom in':
            self.zoom_percent = self.zoom_percent + 10
        elif button.get_label() == 'Zoom out':
            self.zoom_percent = self.zoom_percent - 10
        self.check_zoom_range()
        self.zoom()

    def zoom(self):
        self.zoom_slider.set_value(self.zoom_percent)
        self.progress_bar.set_text(None)
        task = self.zoom_with_progress()
        GObject.idle_add(task.__next__)

    def zoom_with_progress(self):
        progress = 0
        self.progress_bar.set_fraction(0.0)
        yield True
        width, height = self.scale_to_zoom(self.image_width, self.image_height)
        self.layout.set_size(width, height)
        for bi in self.buffers_and_images.values():
            try:
                self.scale_image(bi, height, width)
            except AttributeError:
                self.warn_annotated_image()
            progress = progress + 0.50
            self.progress_bar.set_fraction(progress)
            yield True
        self.draw_markings()
        self.progress_bar.set_text('Done!')
        yield False

    @staticmethod
    def scale_image(buf_image, height, width):
        buf_new = buf_image.buf.scale_simple(width,
                                             height,
                                             GdkPixbuf.InterpType.BILINEAR)
        buf_image.image.set_from_pixbuf(buf_new)
        return buf_new

    def resize(self, widget, event):
        if event.width != self.window_width \
                or event.height != self.window_height:
            self.resize_draw_image()
            self.draw_markings()
            self.window_height = event.height
            self.window_width = event.width

    def resize_draw_image(self):
        width = self.h_adjust.get_page_size()
        height = self.v_adjust.get_page_size()
        draw = self.draw_image_and_buf
        buf_new = self.scale_image(draw, height, width)
        self.draw_image_and_buf = self.buf_and_image(buf_new, draw.image)

    def move_draw_image(self):
        x = self.h_adjust.get_value()
        y = self.v_adjust.get_value()
        self.layout.move(self.draw_image, x, y)

    def scroll(self, x, y, *, delta=False):
        scroll_x = self.h_adjust.get_value()
        scroll_y = self.v_adjust.get_value()
        if delta:
            change_x = x
            change_y = y
        else:
            change_x = self.pressed_x - x
            change_y = self.pressed_y - y
        new_scroll_x = scroll_x + change_x
        self.h_adjust.set_value(new_scroll_x)
        new_scroll_y = scroll_y + change_y
        self.v_adjust.set_value(new_scroll_y)

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
        self.switch_point_type(key_name)

    def save_points_shortcut(self):
        if self.current_point_file is None:
            self.file_dialog(self.save_points_button)
        else:
            self.save_points(self.current_point_file)

    @staticmethod
    def switch_things_shortcut(button):
        if button.get_sensitive():
            if button.get_active():
                button.set_active(False)
            else:
                button.set_active(True)

    def switch_point_type(self, key_name):
        try:
            idx = int(key_name) - 1
            if idx in range(len(self.gtk_point_type_list)):
                self.point_type_button.set_active(idx)
        except ValueError:
            pass

    def mouse_move(self, event_box, event):
        if self.do_drag:
            self.make_line_marking(event)
        elif self.do_scroll:
            self.scroll(event.x, event.y)
        elif self.pressed_on_point:
            self.point_clicked = self.move_marking_live(event)

    def make_point(self, x, y, x2=None, y2=None, box=False):
        args = (self.current_image, self.point_type, x, y, x2, y2, box)
        point = self.point(*args, *self.point_type_color)
        return point

    def make_line_marking(self, event):
        args = (self.pressed_x, self.pressed_y, event.x, event.y)
        point = self.make_point(*args)
        self.draw_live(point)

    def add_remove_point(self, event_box, event):
        if event.button == 1:
            if event.state & Gdk.ModifierType.CONTROL_MASK:
                self.remove_marking(event)
            else:
                self.pressed_on_point = self.find_closest_point(event)
                if not self.pressed_on_point or self.do_drag:
                    self.add_marking(event)
        elif event.button == 2:
            self.button_scroll(event)
        elif event.button == 3:
            self.remove_marking(event)
        self.draw_markings()

    def button_scroll(self, event):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            self.do_scroll = True
            self.pressed_x = event.x
            self.pressed_y = event.y
        elif event.type == Gdk.EventType.BUTTON_RELEASE:
            self.do_scroll = False
            self.move_draw_image()

    def find_closest_point(self, point):
        scaled_p = self.scale_to_zoom(point.x, point.y, divide=True)
        dist_keep = np.inf
        p_keep = None
        for p in self.point_list:
            if p.image == self.current_image:
                dist_head = self.get_dist(p, scaled_p)
                dist_tail = self.get_dist(p, scaled_p, head=False)
                dist = min(dist_head, dist_tail)
                if dist < dist_keep:
                    dist_keep = dist
                    p_keep = p
                    if dist == dist_head:
                        self.pressed_on_point_head = True
                        self.pressed_on_point_tail = False
                    else:
                        self.pressed_on_point_tail = True
                        self.pressed_on_point_head = False
        dist_keep = self.scale_to_zoom(dist_keep)
        smaller_then_radius = dist_keep < self.radius
        if smaller_then_radius:
            self.point_clicked = p_keep
        return smaller_then_radius

    @staticmethod
    def get_dist(marking, point=None, head=True):
        x1 = marking[2]
        y1 = marking[3]
        if point is None:
            x2 = marking[4]
            y2 = marking[5]
            if x2 is None:
                return 0
        else:
            x2 = point[0]
            y2 = point[1]
            if not head:
                x1 = marking[4]
                y1 = marking[5]
                if x1 is None:
                    return np.inf
        return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    @staticmethod
    def get_angle(marking):
        if marking.x2 is None:
            return 0
        else:
            angle = atan2(-(marking.y2 - marking.y),
                          (marking.x2 - marking.x)) / pi * 180
            return angle

    def check_if_clicked_on_marking(self, event):
        if self.point_type is not None:
            if self.check_if_click(event):
                if self.find_closest_point(event):
                    return True
        else:
            status_string = 'No point types loaded!'
            self.status_bar.push(self.status_msg, status_string)
        return False

    def remove_marking(self, event):
        if self.check_if_clicked_on_marking(event):
            self.points_saved = False
            self.point_list.remove(self.point_clicked)
            label_text = 'removed: (%i, %i)' % (int(event.x), int(event.y))
            self.update_label(label_text)
            self.make_new_summary(self.point_clicked, add=False)
            self.update_summary()

    def update_label(self, text):
        self.last_entry_label.set_text(text)

    def make_new_summary(self, point, *, add):
        if add:
            sign = 1
        else:
            sign = -1
        key = self.current_image + '--' + point.type
        summary = self.point_summary_dict.get(key)
        size = self.get_dist(point)
        new_summary = self.summary_values(summary.amount + sign*1,
                                          summary.size + sign*size,
                                          summary.color)
        self.point_summary_dict[key] = new_summary

    def check_if_click(self, event, do_drag=False):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            self.do_drag = do_drag
            self.pressed_x = event.x
            self.pressed_y = event.y
            self.draw_temp = self.draw_image_and_buf
            self.draw_buf_temp = self.draw_temp.image.get_pixbuf()
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            self.do_drag = False
            sensitivity = 5
            if abs(self.pressed_x - event.x) < sensitivity and \
               abs(self.pressed_y - event.y) < sensitivity:
                return True
        return False

    def add_marking(self, event):
        if self.point_type is not None:
            if self.check_if_click(event, do_drag=True):
                self.add_point(event)
            elif event.type == Gdk.EventType.BUTTON_RELEASE:
                self.add_size_mark(event)
        else:
            status_string = 'No point types loaded!'
            self.status_bar.push(self.status_msg, status_string)

    def add_size_mark(self, event):
        self.points_saved = False
        args = self.scale_to_zoom(self.pressed_x,
                                  self.pressed_y,
                                  event.x,
                                  event.y,
                                  divide=True)
        box = self.do_draw_bounding_boxes
        point = self.make_point(*args, box)
        self.point_list.append(point)
        label_text = '%s %i px, %i degrees' % (self.point_type,
                                               int(self.get_dist(point)),
                                               int(self.get_angle(point)))
        self.update_label(label_text)
        self.make_new_summary(point, add=True)
        self.update_summary()

    def add_point(self, event):
        self.points_saved = False
        args = self.scale_to_zoom(event.x, event.y, divide=True)
        point = self.make_point(*args)
        self.point_list.append(point)
        label_text = '%s (%i, %i)' % (self.point_type,
                                      int(point.x),
                                      int(point.y))
        self.update_label(label_text)
        self.make_new_summary(point, add=True)
        self.update_summary()

    def move_marking_live(self, event):
        point = self.point_clicked
        new_coord = self.scale_to_zoom(event.x, event.y, divide=True)
        if self.pressed_on_point_head:
            new_point = point._replace(x=new_coord[0], y=new_coord[1])
        else:
            new_point = point._replace(x2=new_coord[0], y2=new_coord[1])
        self.point_list.remove(point)
        self.point_list.append(new_point)
        self.change_size_in_summary(point, new_point)
        self.update_summary()
        return new_point

    def change_size_in_summary(self, point_old, point_new):
        size_old = self.get_dist(point_old)
        size_new = self.get_dist(point_new)
        key = self.current_image + '--' + point_old.type
        summary = self.point_summary_dict.get(key)
        new_summary = self.summary_values(summary.amount,
                                          summary.size + size_new - size_old,
                                          summary.color)
        self.point_summary_dict[key] = new_summary

    def update_summary(self):
        self.gtk_point_summary_list.clear()
        old_image = ''
        idx = 0
        self.tree_image_index = {}
        dict_sort = sorted(self.point_summary_dict.items(), key=lambda x: x[0])
        for key, summary in dict_sort:
            full_image, point_type = key.split('--')
            image_font, point_font = self.get_font(full_image, point_type)
            image = full_image.split(self.dir_delimiter)[-1]
            if image != old_image:
                self.gtk_point_summary_list.append([image, '', '',
                                                    image_font,
                                                    self.background_color])
                old_image = image
                self.tree_image_index.update({idx: full_image})
                idx = idx + 1
            self.gtk_point_summary_list.append([point_type,
                                                str(summary.amount),
                                                str(int(summary.size)),
                                                point_font,
                                                summary.color])
            idx = idx + 1

    def get_font(self, image, point_type):
        if image == self.current_image:
            image_font = self.bold_font
            if point_type == self.point_type:
                point_font = self.bold_font
            else:
                point_font = self.font
        else:
            image_font = self.font
            point_font = self.font
        return image_font, point_font

    def draw_live(self, point):
        width = self.draw_buf_temp.get_width()
        height = self.draw_buf_temp.get_height()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(cr, self.draw_buf_temp, 0, 0)
        cr.paint()
        cr.set_source_rgba(point.r, point.g, point.b, point.a)
        args = self.shift_coordinates(point)
        self.draw_circle(cr, args[0], args[1])
        if self.do_draw_bounding_boxes:
            self.draw_box(cr, *args)
        else:
            self.draw_line(cr, *args)
        surface = cr.get_target()
        draw_buf = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
        self.draw_temp.image.set_from_pixbuf(draw_buf)

    def shift_coordinates(self, point):
        offset = (self.h_adjust.get_value(), self.v_adjust.get_value())
        args = (point.x - offset[0], point.y - offset[1],
                point.x2 - offset[0], point.y2 - offset[1])
        return args

    def get_draw_coordinate(self, p):
        offset = (self.h_adjust.get_value(), self.v_adjust.get_value(),
                  self.h_adjust.get_value(), self.v_adjust.get_value())
        args = self.scale_to_zoom(p.x, p.y, p.x2, p.y2, offset=offset)
        return args

    def draw_markings(self):
        draw = self.draw_image_and_buf
        draw_buf = draw.buf
        width = draw_buf.get_width()
        height = draw_buf.get_height()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(cr, draw_buf, 0, 0)
        cr.paint()
        for point in self.point_list:
            if point.image == self.current_image or \
                    self.override_point_image_match:
                args = self.get_draw_coordinate(point)
                cr.set_source_rgba(point.r, point.g, point.b, point.a)
                self.draw_circle(cr, args[0], args[1])
                if point.box:
                    self.draw_box(cr, *args)
                elif args[3] is not None:
                    self.draw_line(cr, *args)
        surface = cr.get_target()
        draw_buf = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
        draw.image.set_from_pixbuf(draw_buf)

    def draw_circle(self, cr, x, y):
        cr.arc(x, y, self.radius, 0, 2 * pi)
        cr.fill()

    def draw_line(self, cr, x, y, x2, y2):
        cr.move_to(x, y)
        cr.line_to(x2, y2)
        cr.set_line_width(3)
        cr.stroke()
        cr.arc(x2, y2, self.radius / 2, 0, 2 * pi)
        cr.fill()

    def draw_box(self, cr, x, y, x2, y2):
        cr.move_to(x, y)
        cr.line_to(x, y2)
        cr.line_to(x2, y2)
        cr.line_to(x2, y)
        cr.line_to(x, y)
        cr.set_line_width(3)
        cr.stroke()
        cr.arc(x2, y2, self.radius / 2, 0, 2 * pi)
        cr.fill()

    def open_image_from_tree(self, tree, path, col):
        idx = Gtk.TreePath.get_indices(path)[0]
        if idx in self.tree_image_index:
            self.open_image(self.tree_image_index.get(idx))

    def open_next_image(self, button):
        shift = 1
        if button.get_label() == 'Open previous image':
            shift = -1
        if not self.list_of_images:
            self.get_list_of_images()
        try:
            idx = self.list_of_images.index(self.current_image) + shift
        except ValueError:
            idx = 0
        if 0 <= idx < len(self.list_of_images):
            new_image = self.list_of_images[idx]
            self.open_image(new_image)
        if idx + 1 == len(self.list_of_images):
            self.next_image_button.set_sensitive(False)
        elif idx == 0:
            self.previous_image_button.set_sensitive(False)
        elif idx + 1 > len(self.list_of_images) or idx < 0:
            status_string = 'No more images in folder'
            self.status_bar.push(self.status_msg, status_string)

    def get_list_of_images(self):
        files = list(self.get_files_in_dir())
        self.list_of_images = sorted(files, key=lambda x: x)

    def get_files_in_dir(self):
        for file in os.listdir(self.image_folder):
            if file.endswith('JPG'):
                yield os.path.join(self.image_folder, file)
            elif file.endswith('_annotated.png'):
                pass
            elif file.endswith('png'):
                yield os.path.join(self.image_folder, file)

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
        self.open_next_image(self.next_image_button)

    def open_image(self, filename):
        self.current_image = filename
        self.image_folder = os.path.dirname(filename)
        status_string = 'Image and computer annotated image opened.'
        self.status_bar.push(self.status_msg, status_string)
        self.next_image_button.set_sensitive(True)
        self.previous_image_button.set_sensitive(True)
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
        self.zoom_percent = 100
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
        image = self.current_image.split(self.dir_delimiter)
        self.gtk_point_summary_list.append([image[-1], '', '', self.font,
                                            self.background_color])
        with open(filename, newline='') as csv_file:
            reader = csv.reader(csv_file, delimiter=',')
            reader.__next__()
            sort_points = sorted(reader, key=lambda x: x[1])
            for point in sort_points:
                self.update_point_types(point)
        self.point_type_button.set_active(0)
        self.draw_markings()

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
        header = ['image', 'type', 'x1', 'y1', 'x2', 'y2', 'box'
                  'red', 'green', 'blue', 'alpha']
        with open(filename, 'w') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(header)
            for p in self.point_list:
                writer.writerow(p)

    def load_points(self, filename):
        self.current_point_file = filename
        status_string = 'Point loaded.'
        self.status_bar.push(self.status_msg, status_string)
        self.point_list = []
        self.gtk_point_summary_list.clear()
        with open(filename, newline='') as csv_file:
            reader = csv.reader(csv_file, delimiter=',')
            reader.__next__()
            image_point_match = self.points_parser(reader)
        if not image_point_match:
            if self.warning_point_image_mismatch():
                self.override_point_image_match = True
        self.make_summary_dict()
        self.update_summary()
        self.points_saved = True
        self.draw_markings()

    @staticmethod
    def point_parser(row):
        args = []
        for data in row:
            try:
                args.append(float(data))
            except ValueError:
                if data == 'True':
                    args.append(True)
                elif data == 'False':
                    args.append(False)
                elif not data:
                    args.append(None)
                else:
                    args.append(data)
        return args

    def points_parser(self, reader):
        image_point_match = False
        for row in reader:
            if not row:
                pass
            else:
                args = self.point_parser(row)
                if args[0] == self.current_image:
                    image_point_match = True
                self.point_list.append(self.point(*args))
        return image_point_match

    def make_summary_dict(self):
        self.point_summary_dict.clear()
        for p in self.point_list:
            color = self.rgba_color_to_hex(p)
            key = p.image + '--' + p.type
            size = self.get_dist(p)
            if key not in self.point_summary_dict:
                values = self.summary_values(1, size, color)
            else:
                values = self.point_summary_dict.get(key)
                values = self.summary_values(values.amount + 1,
                                             values.size + size,
                                             color)
            self.point_summary_dict.update({key: values})
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
            dialog.set_current_name('untitled.csv')
            if self.current_point_file is None:
                if self.image_folder is not None:
                    dialog.set_current_folder(self.image_folder)
            else:
                dialog.set_filename(self.current_point_file)
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
    app = App()
    app.run()
