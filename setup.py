from setuptools import setup, find_packages

with open("README.md", 'r', encoding="utf-8") as file:
    long_description = file.read()

setup(name='PythonBotnet',
      version='0.1',
      description='Simple C&C python botnet using websockets',
      license="MIT",
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/HappyStoic/PythonBotnet',
      package_dir={'': 'src'},
      packages=find_packages(where='src'),
      install_requires=[
         'click==7.0',
         'ptable==0.9.2',
         'websockets==9.1',
      ],
      author='Martin Řepa',
      author_email='repa.martin@hotmail.com',
      python_requires='>3.7.*',
)
