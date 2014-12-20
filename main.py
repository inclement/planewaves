# Copyright (c) 2013 Alexander Taylor

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from kivy.clock import Clock
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.graphics import RenderContext, Fbo, Rectangle, Color
from kivy.properties import (StringProperty, ListProperty, ObjectProperty,
                             NumericProperty, ReferenceListProperty,
                             BooleanProperty)
from kivy.metrics import sp
from kivy.utils import platform
from shaderwidget import ShaderWidget
import toast
import os

__version__ = '0.5'


if platform == 'android':
    from jnius import autoclass
    Environment = autoclass('android.os.Environment')
    pictures_dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES)
    pictures_path = pictures_dir.getPath()
    pictures_dir.mkdirs()



# This header must be not changed, it contains the minimum information
# from Kivy.
header = '''
#ifdef GL_ES
precision highp float;
#endif

/* Outputs from the vertex shader */
varying vec4 frag_color;
varying vec2 tex_coord0;

/* uniform texture samplers */
uniform sampler2D texture0;
'''

shader_uniforms = '''
uniform vec2 resolution;
uniform float time;
uniform float time_rate;
'''

shader_top = '''
vec3 hsv2rgb(vec3 c)
{
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main(void)
{
   float x = gl_FragCoord.x;
   float y = gl_FragCoord.y;

   float resx = 0.0;
   float resy = 0.0;
   float max_intensity = 1.0;
'''

shader_bottom_both = '''
   float intensity = sqrt(resx*resx + resy*resy) / max_intensity;
   vec3 rgbcol = hsv2rgb( vec3(atan(resy, resx) / (2.0*3.1416), 1, 1));

   gl_FragColor = vec4( rgbcol.x*intensity, rgbcol.y*intensity, rgbcol.z*intensity, 1.0);
}
'''
shader_bottom_intensity = '''
   float intensity = sqrt(resx*resx + resy*resy) / max_intensity;
   gl_FragColor = vec4( 1.0*intensity, 1.0*intensity, 1.0*intensity, 1.0);
}
'''
shader_bottom_phase = '''
   vec3 rgbcol = hsv2rgb( vec3(atan(resy, resx) / (2.0*3.1416), 1, 1));

   gl_FragColor = vec4( rgbcol.x, rgbcol.y, rgbcol.z, 1.0);
}
'''


class PlaneWaveShader(ShaderWidget):
    fs = StringProperty(None)
    wavevectors = ListProperty([])
    shader_uniforms = StringProperty('')
    shader_mid = StringProperty('')
    shader_bottom = StringProperty(shader_bottom_both)
    mode = StringProperty('both')
    time_rate = NumericProperty(3.)
    time_active = BooleanProperty(False)

    def __init__(self, *args, **kwargs):
        super(PlaneWaveShader, self).__init__(*args, **kwargs)
        self.on_time_rate()

    def on_time_active(self, *args):
        self.on_wavevectors()

    def on_time_rate(self, *args):
        self.canvas['time_rate'] = self.time_rate

    def on_mode(self, *args):
        if self.mode == 'both':
            self.shader_bottom = shader_bottom_both
        elif self.mode == 'intensity':
            self.shader_bottom = shader_bottom_intensity
        elif self.mode == 'phase':
            self.shader_bottom = shader_bottom_phase

    def on_wavevectors(self, *args):
        shader_mid = ''
        shader_uniforms = ''
        i = 0
        for wv in self.wavevectors:
            wv.number = i
            current_uniform = 'k{}'.format(i)
            shader_uniforms += ('''
            uniform vec2 {};
            ''').format(current_uniform)
            if self.time_active:
                shader_mid += ('''
                resx += cos({cu}.x*x / resolution.x + {cu}.y*y / resolution.y + time*6.2831/time_rate);
                resy += sin({cu}.x*x / resolution.x + {cu}.y*y / resolution.y + time*6.2831/time_rate);
                ''').format(cu=current_uniform)
            else:
                shader_mid += ('''
                resx += cos({cu}.x*x / resolution.x + {cu}.y*y / resolution.y);
                resy += sin({cu}.x*x / resolution.x + {cu}.y*y / resolution.y);
                ''').format(cu=current_uniform)
                
            i += 1
        shader_mid += ('''
        max_intensity = {};
        ''').format(max(1.0, float(len(self.wavevectors))))
        self.shader_uniforms = shader_uniforms
        self.shader_mid = shader_mid
        self.replace_shader()
        self.update_glsl()

    def update_glsl(self, *args):
        super(PlaneWaveShader, self).update_glsl(*args)
        for wv in self.wavevectors:
            number = wv.number
            current_uniform = 'k{}'.format(number)
            self.canvas[current_uniform] = [float(wv.kx), float(wv.ky)]

    def replace_shader(self, *args):
        self.fs = header + shader_uniforms + self.shader_uniforms + shader_top + self.shader_mid + self.shader_bottom


class AppLayout(BoxLayout):
    wavevector_layout = ObjectProperty()


class WavevectorMaker(Widget):
    shader_widget = ObjectProperty()
    markers = ListProperty([])
    axes = BooleanProperty(False)

    def on_touch_down(self, touch):
        if (not any([marker.collide_point(*touch.pos) for
                     marker in self.markers]) and
            self.collide_point(*touch.pos)):         
            marker = WvMarker(pos=(touch.pos[0]-sp(20), touch.pos[1]-sp(20)),
                              touch=touch)
            self.add_widget(marker)
            marker.recalculate_k()
            self.markers.append(marker)

            length = min(self.width, self.height)
            dx = touch.x - self.center_x
            dy = touch.y - self.center_y
            self.shader_widget.wavevectors.append(marker)
        else:
            super(WavevectorMaker, self).on_touch_down(touch)

    def reset(self, *args):
        for marker in self.markers:
            self.remove_widget(marker)
        self.markers = []
        self.shader_widget.wavevectors = []

    def toggle_axes(self):
        if self.axes:
            self.axes = False
        else:
            self.axes = True


class WvMarker(Widget):
    colour = ListProperty([0.8, 0.2, 0.2])
    touch = ObjectProperty(None, allownone=True)
    kx = NumericProperty(0.0)
    ky = NumericProperty(0.0)
    k = ReferenceListProperty(kx, ky)
    number = NumericProperty(0)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.touch = touch
            self.colour = [0.2, 0.8, 0.2]
            return True
        return False

    def on_touch_move(self, touch):
        if touch is self.touch:
            self.center = touch.pos
            self.recalculate_k()

    def on_touch_up(self, touch):
        if touch is self.touch:
            self.colour = [0.8, 0.2, 0.2]

    def recalculate_k(self, *args):
        dx = self.center_x - self.parent.center_x
        dy = self.center_y - self.parent.center_y
        length = min(self.parent.width, self.parent.height)
        self.kx = dx / length * 30 * 3.1416
        self.ky = dy / length * 30 * 3.1416

class SaveDialog(Popup):
    shader_size = ListProperty()
    shader_ratio = NumericProperty()
    image_x = NumericProperty()
    image_y = NumericProperty()

class TimeSlider(Popup):
    time_rate = NumericProperty(3.)

class PlaneWaveApp(App):
    fbo = ObjectProperty(None, allownone=True)

    def build(self):
        Clock.schedule_interval(self.update_shader_time, 0)
        self.time_slider = None
        return AppLayout()

    def update_shader_time(self, dt):
        self.root.shader_widget.canvas['time'] = Clock.get_boottime()

    def on_pause(self, *args):
        return True

    def raise_time_slider(self, *args):
        if self.time_slider is None:
            self.time_slider = TimeSlider()
            self.time_slider.ids.slider.value = self.root.shader_widget.time_rate
            self.time_slider.bind(
                time_rate=self.root.shader_widget.setter('time_rate'),
                time_active=self.root.shader_widget.setter('time_active'))
        self.time_slider.open()

    def save_image(self, size=None):
        '''Save an image of the superposition texture.'''
        if size is None:
            size = self.root.shader_widget.size

        toast.toast('Saving...')
        
        fs = self.root.shader_widget.fs

        with self.root.canvas:
            self.fbo = Fbo(size=size)

        with self.fbo:
            Color(1, 1, 1, 1)
            Rectangle(size=(10000, 10000))

        self.fbo.shader.fs = fs

        self.fbo['time'] = 0.0
        self.fbo['time_rate'] = 1.0
        self.fbo['resolution'] = map(float, self.fbo.size)

        shader = self.root.shader_widget
        for wv in shader.wavevectors:
            number = wv.number
            current_uniform = 'k{}'.format(number)
            self.fbo[current_uniform] = [float(wv.kx), float(wv.ky)]

        Clock.schedule_once(self.finish_save, 0)

    def finish_save(self, *args):
        # if platform == 'android':
        #     if not os.path.exists('{}/planewaves'.format(pictures_path)):
        #         os.mkdir('{}/planewaves'.format(pictures_path))

        filen = self.get_save_filen()
        print('Save filen is', filen)
            
        self.fbo.texture.save(filen)
        toast.toast('Saved as {}'.format(filen))
        self.root.canvas.remove(self.fbo)
        self.fbo = None

    def get_save_filen(self):
        i = 0

        if platform == 'android':
            while os.path.exists('{}/planewaves{}.png'.format(pictures_path, i)):
                i += 1
            return '{}/planewaves{}.png'.format(pictures_path, i)
        else:
            while os.path.exists('planewaves{}.png'.format(i)):
                i += 1
            return 'planewaves{}.png'.format(i)
        

if __name__ == '__main__':
    PlaneWaveApp().run()
