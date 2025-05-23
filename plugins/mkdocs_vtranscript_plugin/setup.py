from setuptools import setup, find_packages

setup(
    name='mkdocs-vtranscript-plugin',
    version='0.1',
    packages=find_packages(),
    entry_points={
        'mkdocs.plugins': [
            'mkdocs-vtranscript = mkdocs_vtranscript.plugin:VTranscript'
        ]
    },
)
