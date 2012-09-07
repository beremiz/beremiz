
from editors.TextViewer import TextViewer

class IECCodeViewer(TextViewer):
    
    def __del__(self):
        TextViewer.__del__(self)
        if getattr(self, "_OnClose"):
            self._OnClose(self)