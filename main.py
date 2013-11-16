
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.graphics import RenderContext
from kivy.properties import StringProperty, ListProperty, ObjectProperty

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

shader_bottom_both = '''
   vec3 rgbcol = hsv2rgb( vec3(atan(resy, resx) / (2.0*3.1416), 1, 1));

   gl_FragColor = vec4( rgbcol.x, rgbcol.y, rgbcol.z, sqrt(resx*resx + resy*resy));
}
'''
shader_bottom_intensity = '''
   gl_FragColor = vec4( 1.0, 1.0, 1.0, sqrt(resx*resx + resy*resy));
}
'''
shader_bottom_phase = '''
   vec3 rgbcol = hsv2rgb( vec3(atan(resy, resx) / (2.0*3.1416), 1, 1));

   gl_FragColor = vec4( rgbcol.x, rgbcol.y, rgbcol.z, 1.0);
}
'''

class ShaderWidget(FloatLayout):

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
            kx, ky = wv
            shader_mid += ('''
            resx += cos({kx}*x / resolution.x + {ky}*y / resolution.y);
            resy += sin({kx}*x / resolution.x + {ky}*y / resolution.y);
            ''').format(kx=kx, ky=ky)
        self.shader_mid = shader_mid

    def replace_shader(self, *args):
        self.fs = header + shader_top + self.shader_mid + self.shader_bottom
        
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

    def update_glsl(self, *largs):
        self.canvas['time'] = Clock.get_boottime()
        self.canvas['resolution'] = list(map(float, self.size))
        # This is needed for the default vertex shader.
        self.canvas['projection_mat'] = Window.render_context['projection_mat']

class AppLayout(BoxLayout):
    wavevector_layout = ObjectProperty()
    

class PlaneWaveApp(App):
    def build(self):
        return AppLayout()

if __name__ == '__main__':
    PlaneWaveApp().run()
