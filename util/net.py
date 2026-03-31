import urllib.request
from os import remove
from os.path import exists

def Download(log, url, dest):
    downloaded = 0
    percent = None

    def ReportDownloadProgress(count, blockSize, totalSize):
        nonlocal downloaded, percent
        prev_percent = percent
        downloaded += blockSize
        percent = downloaded * 100 // totalSize
        if percent != prev_percent:
            if percent % 10 == 0:
                log.write(f"{percent}%")
            else:
                log.write(".")

    log.write(f"Downloading {url} to {dest}\n")
    try:
        urllib.request.FancyURLopener().retrieve(url, dest, ReportDownloadProgress)
        log.write(f" OK\n")
        percent = 100
    except:
        log.write(f" FAILED\n")
        return False
    finally:
        if exists(dest) and percent != 100:
            # remove incmplete download
            remove(dest)
            
    return True

