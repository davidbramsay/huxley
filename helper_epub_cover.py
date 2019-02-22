#!/usr/bin/python

#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Author: Mariano Simone (http://marianosimone.com)
# Version: 1.0
# Name: epub-thumbnailer
# Description: An implementation of a cover thumbnailer for epub files
# Installation: see README


#Edited by dramsay

import os
import re
from io import BytesIO
import sys
from xml.dom import minidom
from StringIO import StringIO
import urllib
import zipfile
from PIL import Image


img_ext_regex = re.compile(r'^.*\.(jpg|jpeg|png)$', flags=re.IGNORECASE)
cover_regex = re.compile(r'.*cover.*\.(jpg|jpeg|png)', flags=re.IGNORECASE)


def get_cover_from_manifest(epub):

    # open the main container
    container = epub.open("META-INF/container.xml")
    container_root = minidom.parseString(container.read())

    # locate the rootfile
    elem = container_root.getElementsByTagName("rootfile")[0]
    rootfile_path = elem.getAttribute("full-path")

    # open the rootfile
    rootfile = epub.open(rootfile_path)
    rootfile_root = minidom.parseString(rootfile.read())

    # find possible cover in meta
    cover_id = None
    for meta in rootfile_root.getElementsByTagName("meta"):
        if meta.getAttribute("name") == "cover":
            cover_id = meta.getAttribute("content")
            break

    # find the manifest element
    manifest = rootfile_root.getElementsByTagName("manifest")[0]
    for item in manifest.getElementsByTagName("item"):
        item_id = item.getAttribute("id")
        item_properties = item.getAttribute("properties")
        item_href = item.getAttribute("href")
        item_href_is_image = img_ext_regex.match(item_href.lower())
        item_id_might_be_cover = item_id == cover_id or ('cover' in item_id and item_href_is_image)
        item_properties_might_be_cover = item_properties == cover_id or ('cover' in item_properties and item_href_is_image)
        if item_id_might_be_cover or item_properties_might_be_cover:
            return os.path.join(os.path.dirname(rootfile_path), item_href)

    return None


def get_cover_by_filename(epub):
    no_matching_images = []
    for fileinfo in epub.filelist:
        if cover_regex.match(fileinfo.filename):
            return fileinfo.filename
        if img_ext_regex.match(fileinfo.filename):
            no_matching_images.append(fileinfo)
    return _choose_best_image(no_matching_images)


def _choose_best_image(images):
    if images:
        return max(images, key=lambda f: f.file_size)
    return None


def extract_cover(epub, cover_path):
    if cover_path:
        cover = epub.open(cover_path)
        image = Image.open(BytesIO(cover.read()))
        if image.mode == "CMYK": image = image.convert("RGB")
        return image

    return None


def get_cover_image(epub_file):
    # An epub is just a zip
    file_url = urllib.urlopen(epub_file)
    epub = zipfile.ZipFile(StringIO(file_url.read()), "r")

    extraction_strategies = [get_cover_from_manifest, get_cover_by_filename]

    for strategy in extraction_strategies:
        try:
            cover_path = strategy(epub)
            image = extract_cover(epub, cover_path)
            if image is not None:
                return image
        except Exception as ex:
            print("Error getting cover using %s: " % strategy.__name__, ex)

    return None
