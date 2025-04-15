# realtime_editor.py
from mkdocs.plugins import BasePlugin
from mkdocs.config import config_options

class RealtimeEditor(BasePlugin):
    config_scheme = (
        ('editor_route', config_options.Type(str, default='/editor')),
    )

    def on_config(self, config):
        # Inyectamos el JavaScript y CSS personalizados
        extra_js = config.get('extra_javascript', [])
        extra_js.append('js/realtime_editor.js')
        config['extra_javascript'] = extra_js

        extra_css = config.get('extra_css', [])
        extra_css.append('css/realtime_editor.css')
        config['extra_css'] = extra_css

        return config

    def on_post_page(self, output_content, page, config):
        # Inyectamos un botón para abrir el editor (antes del cierre del body)
        editor_button = '''
        <button id="open-editor" style="position: fixed; bottom: 20px; right: 20px; z-index:999;">
            Editar esta página
        </button>
        '''
        if '</body>' in output_content:
            output_content = output_content.replace('</body>', editor_button + '</body>')
        return output_content
