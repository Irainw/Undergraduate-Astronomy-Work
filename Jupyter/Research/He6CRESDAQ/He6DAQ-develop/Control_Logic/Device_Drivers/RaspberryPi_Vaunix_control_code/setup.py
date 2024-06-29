from distutils.core import setup, Extension

LMS_module = Extension('LMS_module',
                       sources = ['LMS_module.c'],
                       extra_objects = ['LMShid.o'],
                       libraries = ['usb'])


setup(name = 'Vaunix LMS Python 3 support',
      version = '0.1',
      description = 'Python Package for Vaunix LMS synthesizers',
      ext_modules = [LMS_module],

      url='http://www.vaunix.com',
      author='Howard Eglowstein for Vaunix, Inc.',
      author_email='howard@overpricedsoftware.com')
