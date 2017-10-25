from distutils.core import setup
import os

#def read(fname):
#    """Utility function to get README.rst into long_description.
#
#    ``long_description`` is what ends up on the PyPI front page.
#    """
#    return open(os.path.join(os.path.dirname(__file__), fname)).read()

long_description = ''

try:
    import subprocess
    import pandoc
    process = subprocess.Popen(
        ['which pandoc'],
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True
    )
    pandoc_path = process.communicate()[0]
    pandoc_path = pandoc_path.strip('\n')
    pandoc.core.PANDOC_PATH = pandoc_path
    doc = pandoc.Document()
    doc.markdown = open('README.md').read()
    long_description = doc.rst

except:
    pass

setup(
  name = 'ipdata',
  packages = ['ipdata'], # this must be the same as the name above
  version = '1.2',
  description = 'Python Client for Ipdata.co - a Free Ip Geolocation API',
  author = 'Jonathan Kosgei',
  author_email = 'jonathan@ipdata.co',
  url = 'https://github.com/ipdata/python', # use the URL to the github repo
  download_url = 'https://github.com/ipdata/python/archive/1.2.tar.gz', # I'll explain this in a second
  keywords = ['geolocation', 'ip geolocation', 'ip locate'], # arbitrary keywords
  long_description=long_description,
  classifiers = [],
)