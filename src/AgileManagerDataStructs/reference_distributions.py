class Reference_Distribution:
    def __init__(self, id, atts):
        self._id = id
        self._attributes = atts

    def set_id(self, id):
        self._id = id

    def set_attributes(self, atts):
        if not len(atts) == len(self._attributes):
            print("attribute length mismatch")
        i = 0
        for att in atts:
            self._attributes[i] = att
            i += 1
    
    def get_id(self):
        return self._id

    def get_attributes(self):
        return self._attributes
