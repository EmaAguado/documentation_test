from setuptools import setup, find_packages

setup(
    name='mkdocs-realtime-editor-plugin',
    version='0.1',
    packages=find_packages(),
    entry_points={
        'mkdocs.plugins': [
            'mkdocs-realtime-editor = mkdocs_realtime_editor.plugin:RealtimeEditor'
        ]
    },
)
