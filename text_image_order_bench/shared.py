from utils import read_and_encode_image
import os 

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

class Animal:
    def __init__(self, id):
        self.id = id
        self.label = id.capitalize()
        self.image_url = None
        # Encode the image in the constructor
        self.encode_image()
    
    def encode_image(self):
        """Encode the image for this animal"""
        image_path = os.path.join(ROOT_DIR, "images", f"{self.id}.png")
        encoded_image = read_and_encode_image(image_path)
        self.image_url = f"data:image/png;base64,{encoded_image}"
        

# Global animals list
ANIMALS = [
    Animal("cat"),
    Animal("dog"),
    Animal("cow"),
    Animal("pig")
]

ANIMALS_DICT = {animal.id: animal for animal in ANIMALS}