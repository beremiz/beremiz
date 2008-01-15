#!/usr/bin/env python
# -*- coding: utf-8 -*-

# La première ligne doit commencer par #! et contenir python.
# Elle sera adaptée au système de destination automatiquement

""" This is a part of Beremiz project.

    Post installation script for win32 system
    
    This script creat a shortcut for Beremiz.py in the desktop and the
    start menu, and remove them at the uninstallation
    
"""

import os
import sys

# Ce script sera aussi lancé lors de la désinstallation.
# Pour n'exécuter du code que lors de l'installation :
if sys.argv[1] == '-install':
    # On récupère le dossier où mes fichiers seront installés (dossier où python est aussi installé sous windows)
    python_path = sys.prefix
    # On récupère le chemin de pythonw.exe (l'exécutable python qui n'affiche pas de console).
    # Si vous voulez une console, remplacez pythonw.exe par python.exe
    pyw_path = os.path.abspath(os.path.join(python_path, 'pythonw.exe'))
    # On récupère le dossier coincoin
    Beremiz_dir = os.path.abspath(os.path.join(python_path, 'LOLITech', 'Beremiz'))
    
    # On récupère les chemins de coincoin.py, et de coincoin.ico
    # (Ben oui, l'icone est au format ico, oubliez le svg, ici on en est encore à la préhistoire.
    # Heureusement que the GIMP sait faire la conversion !)
    ico_path = os.path.join(Beremiz_dir, 'Beremiz.ico')
    script_path = os.path.join(Beremiz_dir, 'Beremiz.py')
    
    # Création des raccourcis
    # Pour chaque raccourci, on essaye de le faire pour tous les utilisateurs (Windows NT/2000/XP),
    # sinon on le fait pour l'utilisateur courant (Windows 95/98/ME)
    
    # Raccourcis du bureau
    # On essaye de trouver un bureau
    try:
        desktop_path = get_special_folder_path("CSIDL_COMMON_DESKTOPDIRECTORY")
    except OSError:
        desktop_path = get_special_folder_path("CSIDL_DESKTOPDIRECTORY")
    
    # On créé le raccourcis
    create_shortcut(pyw_path, # programme à lancer
                    "Can Node Editor", # Description
                    os.path.join(desktop_path, 'Beremiz.lnk'),  # fichier du raccourcis (gardez le .lnk)
                    script_path, # Argument (script python)
                    Beremiz_dir, # Dossier courant
                    ico_path # Fichier de l'icone
                    )
    # On va cafter au programme de désinstallation qu'on a fait un fichier, pour qu'il soit supprimé
    # lors de la désinstallation
    file_created(os.path.join(desktop_path, 'Beremiz.lnk'))
    
    # Raccourcis dans le menu démarrer (idem qu'avant)
    try:
        start_path = get_special_folder_path("CSIDL_COMMON_PROGRAMS")
    except OSError:
        start_path = get_special_folder_path("CSIDL_PROGRAMS")
    
    

    # Création du dossier dans le menu programme
    programs_path = os.path.join(start_path, "Beremiz project")
    try :
        os.mkdir(programs_path)

    except OSError:

        pass
    directory_created(programs_path)
    
    create_shortcut(pyw_path, # Cible
                    "Can Node Editor", #Description
                    os.path.join(programs_path, 'Beremiz.lnk'),  # Fichier
                    script_path, # Argument
                    Beremiz_dir, # Dossier de travail
                    ico_path # Icone
                    )
    file_created(os.path.join(programs_path, 'Beremiz.lnk'))
    
    # End (youpi-message)
    # Ce message sera affiché (très) furtivement dans l'installateur.
    # Vous pouvez vous en servir comme moyen de communication secret, c'est très in.
    sys.stdout.write("Shortcuts created.")
    # Fin du bidule
    sys.exit()
