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
from kivy.core.window import Window
from kivy.graphics import RenderContext
from kivy.properties import (StringProperty, ListProperty, ObjectProperty,
                             NumericProperty, ReferenceListProperty,
                             BooleanProperty)
from kivy.metrics import sp
from shaderwidget import ShaderWidget

__version__ = '0.1'

# This header must be not changed, it contain the minimum information
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

# Plasma shader
shader_top = '''
uniform vec2 resolution;
uniform float time;

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
   vec3 rgbcol = hsv2rgb( vec3(atan(resy, resx) / (2.0*3.1416), 1, 1));

   gl_FragColor = vec4( rgbcol.x, rgbcol.y, rgbcol.z, sqrt(resx*resx + resy*resy) / max_intensity);
}
'''
shader_bottom_intensity = '''
   gl_FragColor = vec4( 1.0, 1.0, 1.0, sqrt(resx*resx + resy*resy) / max_intensity);
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
    shader_mid = StringProperty('')
    shader_bottom = StringProperty(shader_bottom_both)
    mode = StringProperty('both')

    def on_mode(self, *args):
        if self.mode == 'both':
            self.shader_bottom = shader_bottom_both
        elif self.mode == 'intensity':
            self.shader_bottom = shader_bottom_intensity
        elif self.mode == 'phase':
            self.shader_bottom = shader_bottom_phase

    def on_wavevectors(self, *args):
        shader_mid = ''
        for wv in self.wavevectors:
            kx, ky = wv.k
            shader_mid += ('''
            resx += cos({kx}*x / resolution.x + {ky}*y / resolution.y);
            resy += sin({kx}*x / resolution.x + {ky}*y / resolution.y);
            ''').format(kx=kx, ky=ky)
        shader_mid += ('''
        max_intensity = {};
        ''').format(max(1.0, float(len(self.wavevectors))))
        self.shader_mid = shader_mid

    def replace_shader(self, *args):
        self.fs = header + shader_top + self.shader_mid + self.shader_bottom
        
class AppLayout(BoxLayout):
    wavevector_layout = ObjectProperty()
    
class WavevectorMaker(Widget):
    shader_widget = ObjectProperty()
    markers = ListProperty([])
    axes = BooleanProperty(True)
    def on_touch_down(self, touch):
        if not any([marker.collide_point(*touch.pos) for marker in self.markers]):
            marker = WvMarker(pos=(touch.pos[0]-sp(20), touch.pos[1]-sp(20)))
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
        dx = self.x - self.parent.center_x
        dy = self.y - self.parent.center_y
        length = min(self.parent.width, self.parent.height)
        self.kx = dx / length * 30 * 3.1416
        self.ky = dy / length * 30 * 3.1416
        print 'parent.shader_widget is', self.parent.shader_widget
        self.parent.shader_widget.on_wavevectors()

class PlaneWaveApp(App):
    def build(self):
        return AppLayout()
    def on_pause(self, *args):
        return True

if __name__ == '__main__':
    PlaneWaveApp().run()
