import argparse
import json
from pathlib import Path
from os import path, makedirs
import shutil

parser = argparse.ArgumentParser(description='Converts Keep notes exported using Google\' \'Takeout\' exporter to Obsidian markdown files.')
parser.add_argument('--source-path', dest='source_path', required=False, default='.', help='The path of the keep archive to convert. Default is current directory.')
parser.add_argument('--target-path', dest='target_path', required=False, default='.', help='The path to create the converted folder in. Default is current directory.')
parser.add_argument('--folder-name', dest='folder_name', required=True, help='What to name the created folder of converted notes. --target-path specifies the location of this folder."')
parser.add_argument('--convert-trashed', dest='convert_trashed', default=False, action='store_true', help='Convert trashed notes.')
parser.add_argument('--convert-archived', dest='convert_archived', default=False, action='store_true', help='Convert archived notes.')
parser.add_argument('--no-color-tags', dest='no_color_tags', default=False, action='store_true', help='Don\'t convert note colors into tags (the default).')
parser.add_argument('--super-tag', dest='super_tag', default='', help='A \'super\' tag to use for nested tags.')
parser.add_argument('--overwrite', dest='overwrite', default=False, action='store_true', help='Overwrite already converted files. Defaults to false.')
args = parser.parse_args()

SUPER_TAG = '#' + args.super_tag + '/' if args.super_tag else ''
EXPORT_FOLDER_PATH = path.join(args.target_path, args.folder_name)
IMAGE_PATH = path.join(EXPORT_FOLDER_PATH, 'images')


def error(message):
    print(message)
    exit(1)


def printLinebreak(): print('----------------------------------')


def convertNote(json) -> str:
    result = ''
    tags = []

    def handleTaskList(taskList):
        nonlocal result # Why does python have such stupid scoping rules???
        for task in taskList:
            status = 'X' if task['isChecked'] else ' '
            text = task['text']
            result += f'- [{status}] {text}\n'
        result += ('\n')

    def handleAttachments(attachments):
        nonlocal result # Why does python have such stupid scoping rules???
        for attachment in attachments:
            source_path = path.join(args.source_path, attachment['filePath'])
            target_path = path.join(IMAGE_PATH, attachment['filePath'])
            relativePath = 'images/' + attachment['filePath']

            if not path.exists(source_path):
                print(f'WARNING: Could not find referenced attachment: {source_path}. Skipping...')
                continue
            shutil.copy(source_path, target_path)
            result += f'![[{relativePath}]]\n'
    
    def handleLabels(labels):
        nonlocal tags # Why does python have such stupid scoping rules???
        for label in labels:
            tags.append(SUPER_TAG + label['name'])

    if 'textContent' in json and (text := json['textContent']):
        result += (text + '\n\n')
    if 'listContent' in json:
        handleTaskList(json['listContent'])
    if not args.no_color_tags and (color := json['color']) != 'DEFAULT':
        tags.append(SUPER_TAG + color)
    if 'attachments' in json:
        handleAttachments(json['attachments'])
    if 'labels' in json:
        handleLabels(json['labels'])

    result += ' '.join(tags)

    return result


if not path.exists(args.source_path):
    error(f'--source-path {args.source_path} does not exist. Quitting...')
if not path.exists(IMAGE_PATH):
    makedirs(IMAGE_PATH)

noteFiles = [x for x in Path(args.source_path).iterdir() if x.is_file() and (x.suffix == '.json')]

printLinebreak()
print(f'Found {len(noteFiles)} .json files in source directory {args.source_path}')
printLinebreak()

convert_count = 0

for noteFile in noteFiles:

    convertedNotePath = path.join(EXPORT_FOLDER_PATH, noteFile.name.replace('.json', '.md'))
    if not args.overwrite and path.exists(convertedNotePath):
        continue

    with open(noteFile.name) as f:
        try:
            noteJson = json.loads(f.read())
        except:
            print(f'ERROR: Could not deserialise file {noteFile.name} as json. Skipping...')
            continue

    if not args.convert_trashed and noteJson['isTrashed']:
        continue
    if not args.convert_archived and noteJson['isArchived']:
        continue

    convert_count+=1
    noteContent = convertNote(noteJson)

    with open(convertedNotePath, 'w') as f:
        f.write(noteContent)

printLinebreak()
print(f'Converted {convert_count} notes!')
