"""Cython build file"""
from distutils.core import setup
from distutils.extension import Extension
from os import getcwd, path, walk

from Cython.Build import cythonize

cythonExt = []
for root, dirs, files in walk(getcwd()):
    for file in files:
        if file.endswith('.pyx') and '.pyenv' not in root:	# im sorry
            filePath = path.relpath(path.join(root, file))
            cythonExt.append(Extension(filePath.replace('/', '.')[:-4], [filePath]))

setup(
    name = 'lets pyx modules',
    ext_modules = cythonize(cythonExt, nthreads = 4),
)
