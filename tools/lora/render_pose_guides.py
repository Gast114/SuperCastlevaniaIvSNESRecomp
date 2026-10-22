"""Draw editable COCO18 body guides on black for a local ControlNet trial.

No AI detection/generation: points are explicit, approximate 2D annotations.
The conventional OpenPose body topology/colors are used as a control format.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

EDGES = [(1,2),(1,5),(2,3),(3,4),(5,6),(6,7),(1,8),(8,9),(9,10),
         (1,11),(11,12),(12,13),(1,0),(0,14),(14,16),(0,15),(15,17)]
COLORS = [(255,0,0),(255,85,0),(255,170,0),(255,255,0),(170,255,0),
          (85,255,0),(0,255,0),(0,255,85),(0,255,170),(0,255,255),
          (0,170,255),(0,85,255),(0,0,255),(85,0,255),(170,0,255),
          (255,0,255),(255,0,170),(255,0,85)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recipe', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.recipe.read_text(encoding='utf-8'))
    if args.out.exists():
        raise FileExistsError('Use a new guide folder')
    args.out.mkdir(parents=True)
    for pose in data['poses']:
        points = pose['points']
        if len(points) != 18:
            raise ValueError('COCO18 requires eighteen point slots')
        image = Image.new('RGB', tuple(data['canvas']), 'black')
        draw = ImageDraw.Draw(image)
        for i, (start, end) in enumerate(EDGES):
            if points[start] and points[end]:
                color = tuple(round(v * .6) for v in COLORS[i])
                draw.line([tuple(points[start]), tuple(points[end])], fill=color, width=8)
        for i, point in enumerate(points):
            if point:
                x, y = point
                draw.ellipse((x-4,y-4,x+4,y+4), fill=COLORS[i])
        image.save(args.out / (pose['name'] + '.png'))
    (args.out / 'poses.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    print(args.out.resolve())


if __name__ == '__main__':
    main()
