from distutils.core import setup
from distutils.extension import Extension
from os import getcwd, path, walk

from Cython.Build import cythonize

extensions = []
for root, dirs, files in walk(getcwd()):
    for file in files:
        if file.endswith(".pyx"):
            file_path = path.relpath(path.join(root, file))
            extensions.append(Extension(file_path.replace("/", ".")[:-4], [file_path]))

setup(
    name="catch-the-pp",
    ext_modules=cythonize(extensions, nthreads=4),
)
