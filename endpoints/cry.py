from io import BytesIO

from PIL import Image, ImageDraw
from flask import send_file

from utils.endpoint import Endpoint, setup
from utils.textutils import wrap


@setup
class Cry(Endpoint):
    params = ['text']

    def generate(self, avatars, text, usernames):
        base = Image.open(self.assets.get('assets/cry/cry.bmp'))
        font = self.assets.get_font('assets/fonts/tahoma.ttf', size=20)
        canv = ImageDraw.Draw(base)

        text = wrap(font, text, 180)
        canv.text((382, 80), text, font=font, fill='Black')

        b = BytesIO()
        base.save(b, format='jpeg')
        b.seek(0)
        return send_file(b, mimetype='image/jpeg')
