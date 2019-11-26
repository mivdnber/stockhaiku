from io import BytesIO
from typing import Tuple, Any, Dict, Optional, Iterable, Sequence
from abc import ABCMeta, abstractmethod, abstractproperty
from itertools import permutations
import tempfile

from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, clips_array, vfx, AudioFileClip, CompositeVideoClip, TextClip
import requests
import gtts

from stockhaiku.database import Haiku

configurations = [
    "vv",
    "hh",
    "vh",
    "hv",
]

ImageSpec = Dict[Any, Tuple[int, int]]
ImageBounds = Tuple[Any, float, float, float, float]

class Node(metaclass=ABCMeta):
    
    @abstractproperty
    def width(self) -> float:
        ...
    
    @abstractproperty
    def height(self) -> float:
        ...
    
    @abstractmethod
    def walk_images(self, offset_x: float, offset_y: float, scale: float) -> Iterable[ImageBounds]:
        ...

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height
    
    def is_image(self, image: Any) -> bool:
        return False


class Leaf(Node):
    
    def __init__(self, image: Any, width: float, height: float):
        self._image = image
        self._width = float(width)
        self._height = float(height)

    @property
    def width(self) -> float:
        return self._width
    
    @property
    def height(self) -> float:
        return self._height
    
    def __repr__(self) -> str:
        return f'<Leaf:{self._image} {self.width}x{self.height} -> {self.aspect_ratio}>'

    def is_image(self, image: Any) -> bool:
        return self._image == image
    
    def walk_images(self, offset_x: float, offset_y: float, scale: float) -> Iterable[ImageBounds]:
        yield self._image, offset_x, offset_y, self._width * scale, self._height * scale


class Interior(Node):

    def __init__(self, left: Node, right: Node, op: str):
        self._left = left
        self._right = right
        self._op = op

    @property
    def width(self) -> float:
        if self._op == 'h':
            return self._left.width
        else:
            return self._left.width +  self._left.height * self._right.aspect_ratio
    
    @property
    def height(self) -> float:
        if self._op == 'v':
            return self._left.height
        else:
            return self._left.height + self._left.width / self._right.aspect_ratio
    
    @property
    def right_scale(self) -> float:
        if self._op == 'h':
            return self._left.width / self._right.width
        else:
            return self._left.height / self._right.height

    def __repr__(self) -> str:
        return f'<Interior {self.width}x{self.height} {self._op} {self._left!r} {self._right!r}>'

    def walk_images(
        self,
        offset_x: float = 0,
        offset_y: float = 0,
        scale: float = 1.0,
    ) -> Iterable[ImageBounds]:
        left = next(self._left.walk_images(offset_x, offset_y, scale))
        yield left
        (left_image, left_x, left_y, left_width, left_height) = left
        x = offset_x if self._op == 'h' else left_x + left_width
        y = offset_y if self._op == 'v' else left_y + left_height
        yield from self._right.walk_images(x, y, scale * self.right_scale)
    
    def calculate_error(self, desired_aspect_ratio: float = 1.5) -> float:
        aspect_ratio_weight = 5
        surface_weight = 2
        aspect_ratio_error = (desired_aspect_ratio - self.aspect_ratio) ** 2
        return aspect_ratio_error


def generate_collage_tree(image_specs: Sequence[ImageSpec], ops: str) -> Interior:
    nodes = [
        Leaf(image, w, h)
        for image, w, h in reversed(image_specs)
    ]
    ops_iter = iter(ops)
    while len(nodes) > 1:
        right = nodes.pop()
        left = nodes.pop()
        op = next(ops_iter)
        nodes.append(Interior(left, right, op))
    return nodes[0]


def find_best_tree(image_specs: Tuple[Any, int, int]) -> Interior:
    best_tree = None
    least_error = None
    for ops in ['vv', 'vh', 'hv', 'hh']:
        for image_specs_permutation in permutations(image_specs):
            tree = generate_collage_tree(image_specs_permutation, ops)
            error = tree.calculate_error(1)
            if best_tree is None or least_error > error:
                best_tree = tree
                least_error = error
    return best_tree
    

def render_collage(tree: Interior) -> Image.Image:
    initial_collage: Image.Image = Image.new('RGB', (int(tree.width), int(tree.height)))
    for image, x, y, width, height in tree.walk_images():
        resized_image = image.copy().resize((int(width), int(height)), Image.LANCZOS)
        box = (int(x), int(y), int(x) + int(width), int(y) + int(height))
        initial_collage.paste(resized_image, box=box)
    return initial_collage


def render_image(haiku: Haiku) -> Tuple[Image.Image, BytesIO]:
    images = [
        Image.open(BytesIO(requests.get(verse.raw_json['urls']['regular']).content))
        for verse in haiku
    ]
    image_specs = [(image, *image.size) for image in images]
    font = ImageFont.truetype("fonts/Rokkitt-Medium.ttf", 24)
    collage_tree = find_best_tree(image_specs)
    out_image = render_collage(collage_tree)
    draw = ImageDraw.Draw(out_image)
    haiku = '\n'.join(v.alt_description for v in haiku)
    draw.multiline_text((10, 10), haiku, font=font)
    out_image.save('out.png')
    image_as_bytesio = BytesIO()
    out_image.save(image_as_bytesio, format='PNG')
    image_as_bytesio.seek(0)
    return out_image, image_as_bytesio


PAUSE_BETWEEN_VERSES = 1.5


def render_video(haiku: Haiku, filename='movie.mp4'):
    audio_clips = []
    total_duration = 0
    for verse in haiku:
        tts_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        tts = gtts.gTTS(verse.alt_description, 'en')
        tts.write_to_fp(tts_file)
        tts_file.close()
        audio_clip = AudioFileClip(tts_file.name)
        clip_duration = audio_clip.duration + PAUSE_BETWEEN_VERSES
        total_duration += clip_duration
        audio_clips.append(audio_clip)
    clip_specs = []
    verse_clips = []
    duration_up_to_now = 0
    for i, (verse, audio_clip) in enumerate(zip(haiku, audio_clips)):
        clip = (ImageClip(verse.url)
            .set_duration(total_duration - duration_up_to_now)
            .set_audio(audio_clip)
            .fx(vfx.fadein, 3)
            .fx(vfx.freeze, 0, duration_up_to_now)
        )
        verse_clip = (
            TextClip(
                txt=verse.alt_description,
                color='white',
                fontsize=24,
                bg_color='black',
                font='fonts/Rokkitt-Medium.ttf',
            )
            .set_duration(total_duration - duration_up_to_now)
            .crossfadein(3)
            .fx(vfx.freeze, 0, duration_up_to_now)
            .set_position((20, 20 + 30 * i))
        )
        verse_clips.append(verse_clip)
        duration_up_to_now += audio_clip.duration + PAUSE_BETWEEN_VERSES
        clip_specs.append((clip, clip.w, clip.h))
    collage_tree = find_best_tree(clip_specs)
    collage_clips = []
    collage_scale = min(1200 / collage_tree.width, 900 / collage_tree.height)
    for clip, x, y, width, height in collage_tree.walk_images(scale=collage_scale):
        print(x, y, width, height)
        collage_clips.append(clip.resize(width=width, height=height).set_position((x, y)))
    composition = CompositeVideoClip(
        collage_clips + verse_clips,
        size=(int(collage_scale*collage_tree.width), int(collage_scale * collage_tree.height))
    )

    composition.write_videofile(filename, fps=24)
