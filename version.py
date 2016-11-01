import subprocess, os

def GetAppRevision():
    rev = None
    app_dir=os.path.dirname(os.path.realpath(__file__))    
    try:
        pipe = subprocess.Popen(
            ["hg", "id", "-i"],
            stdout = subprocess.PIPE,
            cwd = app_dir
        )
        rev = pipe.communicate()[0]
        if pipe.returncode != 0:
            rev = None
    except:
        pass
    
    # if this is not mercurial repository
    # try to read revision from file
    if rev is None:
        try:
            f = open(os.path.join(app_dir,"revision"))
            rev = f.readline()
        except:
            pass
    return rev

app_version =  "1.2"
rev = GetAppRevision()
if rev is not None:
    app_version = app_version + "-" + rev.rstrip()
    
        

