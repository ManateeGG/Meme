from io import BytesIO

from PIL import Image
from flask import send_file

from utils import http
from utils.endpoint import Endpoint, setup


@setup
class Gay(Endpoint):
    params = ['avatar0']

    def generate(self, avatars, text, usernames):
        img1 = http.get_image(avatars[0])
        img2 = Image.open(self.assets.get('assets/gay/gay.bmp')).convert('RGBA').resize(img1.size)
        img2.putalpha(128)
        img1.paste(img2, (0, 0), img2)
        img1 = img1.convert('RGB')

        b = BytesIO()
        img1.save(b, format='jpeg')
        b.seek(0)
        return send_file(b, mimetype='image/jpeg')
