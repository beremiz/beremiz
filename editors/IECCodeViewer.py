
from editors.TextViewer import TextViewer
from plcopen.plcopen import TestTextElement

class IECCodeViewer(TextViewer):
    
    def __del__(self):
        TextViewer.__del__(self)
        if getattr(self, "_OnClose"):
            self._OnClose(self)
            
    def Search(self, criteria):
        return [((self.TagName, "body", 0),) + result for result in TestTextElement(self.Editor.GetText(), criteria)]