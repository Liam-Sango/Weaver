import requests
import uuid
#Arweave gateways
GATEWAYS = ["https://arweave.net", "https://ar-io.net"]

class MockArweave:

    #INIT
    def __init__(self):
        self.store = {}
    
    def upload_image(self, image_path):
        #Opens the image we wish to "upload"
        with open(image_path, 'rb') as file:
            image_data = file.read()

            #Stores our "uploaded" image in self.store
            txid = uuid.uuid4().hex
            self.store[txid] = image_data

            #Returns our TXID
            return txid
    
    def download_image(self, txid):
        #Returns the stored bytes from self.store
        if txid in self.store:
            stored_bytes = self.store[txid]
            return stored_bytes
        else:
            #Raises error if TXID is not present.
            raise KeyError ("TXID is not present in self.store")
        



    
    

