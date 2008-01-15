import os,sys,glob
from distutils.core import setup


install_dir=os.path.join("LOLITech","beremiz")

data_files=[]
os.getcwd()
os.chdir(os.getcwd())

def generate(base_dir):
    listfile=[]
    if base_dir == "":
        directory = "."
    else:
        directory = base_dir
    data_files.append((os.path.join(install_dir, base_dir), listfile))

    for element in os.listdir(directory):
        element_path=os.path.join(base_dir, element)
        if os.path.isdir(element_path):
            generate(element_path)
        elif os.path.isfile(element_path):
            listfile.append(element_path)

generate("")


setup(name='Beremiz',
      version='0.1',
      description='Open Source framework for automation',
      author='Edouard Tisserant, Laurent Bessard',
      author_email='edouard.tisserant@lolitech.fr,laurent.bessard@lolitech.fr,gregory.trelat@lolitech.fr',
      url='http://www.beremiz.org',
      license='GPL',
      windows=["Beremiz.py"],
      scripts=['beremiz_postinst.py'],
      data_files=data_files, # Add files to install
)