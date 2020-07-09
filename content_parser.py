import threading
import random
import time
import json
import abc
import os
import re
from numpy import base_repr

import requests


class Parser():
    def __init__(self, host, slug_len, folder_name):
        self.host = host
        self.slug_len = slug_len
        self.folder_name = folder_name
        self.session = requests.Session()
        self.session.headers.update(
            {'authority': 'prnt.sc',
            'sec-fetch-dest': 'image',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Mobile Safari/537.36',
            'dnt': '1',
            'accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'no-cors',
            'referer': 'https://prnt.sc/',
            'accept-language': 'ru,en;q=0.9,la;q=0.8'})

    def generate_url(self, lowercase=True, uppercase=True, numbers=True):
        letters_lower = 'abcdefghijklmnopqrstuvwxyz'
        letters_upper = letters_lower.upper()
        numbers = '0123456789'
        VALID_CHARS = ''
        VALID_CHARS += letters_lower if lowercase else ''
        VALID_CHARS += letters_upper if uppercase else ''
        VALID_CHARS += numbers if numbers else ''
        return self.host + ''.join([random.choice(VALID_CHARS) for _ in range(self.slug_len)])

    def save_content(self, parsed_content):
        path = f'./{self.folder_name}/{parsed_content.file_type}'
        if os.path.isdir(self.folder_name) == False:
            os.mkdir(self.folder_name)
        if os.path.isdir(path) == False:
            os.mkdir(path)
        
        with open(f'{path}/{parsed_content.name}', 'wb') as output_file:
            output_file.write(parsed_content.content)
    
    @abc.abstractmethod
    def start(self):
        pass

    def __repr__(self):
        return '<Parser>'
    
    __str__ = __repr__

    class ParsedContent():
        def __init__(self, content, name):
            self.content = content
            self.name = name.replace('/', '-')
            try:
                self.file_type = re.compile('\.\w*\Z').findall(name)[0][1:].lower()
            except IndexError:
                self.file_type = 'NoneType'
    

class PrntscParser(Parser):
    def __init__(self, folder_name='prntsc'):
        super().__init__('https://prnt.sc/', 6, folder_name)

    def extract_image_url(self, text):
        matches = re.compile('https://[\w./]*\" cro').findall(text)
        if len(matches) == 1:
            return matches[0][:-5]
        else:
            return None

    def extract_image_name(self, url):
        return re.compile('\w*\.\w*\Z').findall(url)[0]

    def generate_url(self, freshets_shortcode):
        for decimal_counter in range(int(freshets_shortcode, 36), 0, -1):
            yield self.host + base_repr(decimal_counter, 36).lower()

    def download_content(self, url):
        response = self.session.get(url)
        response.raise_for_status()
        img_url = self.extract_image_url(response.text)
        if img_url != None:
            img_response = self.session.get(img_url)
            response.raise_for_status()
            img_name = self.extract_image_name(img_url)
            return self.ParsedContent(img_response.content, img_name)
        else:
            return None

    def start(self):
        #start url (from new to old uploads)
        freshets_shortcode = 'ta78nv'
        for url in self.generate_url(freshets_shortcode):
            content = self.download_content(url)
            if content != None:
                self.save_content(content)

    def __repr__(self):
        return '<prnt.sc parser>'

    __str__ = __repr__


class CloudAppParser(Parser):
    def __init__(self, folder_name='myclly'):
        super().__init__('https://my.cl.ly/v2/items/', 4, folder_name)
    
    def download_content(self, url):
        try:
            response = self.session.get(url)
            item_info = json.loads(response.text)
            content_url = item_info['item']['source_url']
            content = self.session.get(content_url).content
            return self.ParsedContent(content, item_info['item']['name'])
        except Exception:
            return None

    def start(self):
        while True:
            content = self.download_content(self.generate_url())
            if content != None:
                self.save_content(content)

    def __repr__(self):
        return '<CloudApp parser>'

    __str__ = __repr__


def start_parsing():
    parsers = [CloudAppParser(), PrntscParser()]
    for parser in parsers:
        th = threading.Thread(target=parser.start, daemon=False)
        th.start()
        print(f'{parser} started ({th.name})')
    print('Parsers are working...')
    
start_parsing()


