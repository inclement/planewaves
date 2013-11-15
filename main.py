'''
Plasma Shader
=============

This shader example have been taken from http://www.iquilezles.org/apps/shadertoy/
with some adapation.

This might become a Kivy widget when experimentation will be done.
'''


from kivy.clock import Clock
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.graphics import RenderContext
from kivy.properties import StringProperty, ListProperty

# This header must be not changed, it contain the minimum information from Kivy.
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
'''

shader_bottom = '''
   vec3 rgbcol = hsv2rgb( vec3(atan(resy, resx) / (2.0*3.1416), 1, 1));

   gl_FragColor = vec4( rgbcol.x, rgbcol.y, rgbcol.z, sqrt(resx*resx + resy*resy));
}
'''

class ShaderWidget(FloatLayout):

    fs = StringProperty(None)
    wavevectors = ListProperty([])
    shader_mid = StringProperty('')

    def on_wavevectors(self, *args):
        shader_mid = ''
        for wv in self.wavevectors:
            kx, ky = wv
            shader_mid += ('''
            resx += cos({kx}*x / resolution.x + {ky}*y / resolution.y);
            resy += sin({kx}*x / resolution.x + {ky}*y / resolution.y);
            ''').format(kx=kx, ky=ky)
        self.shader_mid = shader_mid

    def on_shader_mid(self, *args):
        self.fs = header + shader_top + self.shader_mid + shader_bottom
        print 'self.fs changed'
        print self.shader_mid

    def on_touch_down(self, touch):
        length = min(self.width, self.height)
        dx = touch.x - self.center_x
        dy = touch.y - self.center_y
        self.wavevectors.append((dx / length * 25 * 3.1416, dy / length * 50 * 3.1416))

    def __init__(self, **kwargs):
        # Instead of using Canvas, we will use a RenderContext,
        # and change the default shader used.
        self.canvas = RenderContext()

        # call the constructor of parent
        # if they are any graphics object, they will be added on our new canvas
        super(ShaderWidget, self).__init__(**kwargs)

        # We'll update our glsl variables in a clock
        Clock.schedule_interval(self.update_glsl, 1 / 60.)

    def on_fs(self, instance, value):
        # set the fragment shader to our source code
        shader = self.canvas.shader
        old_value = shader.fs
        shader.fs = value
        if not shader.success:
            shader.fs = old_value
            raise Exception('failed')

        print 'changed shader'
        print self.canvas.shader.fs

    def update_glsl(self, *largs):
        self.canvas['time'] = Clock.get_boottime()
        self.canvas['resolution'] = list(map(float, self.size))
        # This is needed for the default vertex shader.
        self.canvas['projection_mat'] = Window.render_context['projection_mat']


class PlaneWaveApp(App):
    def build(self):
        return ShaderWidget(fs=header+shader_top+shader_bottom)

if __name__ == '__main__':
    PlaneWaveApp().run()
