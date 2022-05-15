from typing import Optional

from bs4 import BeautifulSoup
from threading import Thread
import requests
from urllib.parse import urlparse, urljoin, ParseResult
import re

from crawler.scheduler import Scheduler


class PageFetcher(Thread):
    def __init__(self, obj_scheduler: Scheduler):
        super().__init__()
        self.obj_scheduler = obj_scheduler

    def request_url(self, obj_url: ParseResult) -> Optional[bytes] or None:
        """
        :param obj_url: Instância da classe ParseResult com a URL a ser requisitada.
        :return: Conteúdo em binário da URL passada como parâmetro, ou None se o conteúdo não for HTML
        """
        user_agent = 'Savinho/0.1'
        response = None
        response = requests.get(obj_url.geturl(), headers={ 'User-Agent':  user_agent })

        if not response.headers['Content-type'].__contains__('text/html'):
            return None
        return response.content

    def discover_links(self, obj_url: ParseResult, depth: int, bin_str_content: bytes):
        """
        Retorna os links do conteúdo bin_str_content da página já requisitada obj_url
        """
        soup = BeautifulSoup(bin_str_content, features='lxml')

        for link in soup.select('body a'):
            url = ''
            try:
                url = link.attrs['href']
            except:
                continue

            obj_new_url = urlparse(url)

            if obj_new_url.hostname is None:
                obj_new_url = urlparse(f'{obj_url.scheme}://{obj_url.hostname}{"" if obj_new_url.path.startswith("/") else "/"}{obj_new_url.path}')
        
            if obj_url.netloc == obj_new_url.netloc:
                new_depth = depth + 1
            else:
                new_depth = 0

            yield obj_new_url, new_depth

    def crawl_new_url(self):
        """
        Coleta uma nova URL, obtendo-a do escalonador
        """
        url, depth = self.obj_scheduler.get_next_url()

        if url is None:
            return

        content = None
        try:
            content = self.request_url(url)
        except:
            print('Erro ao requisitar URL')

        if content is not None:
            for current_url, current_depth in self.discover_links(url, depth, content):
                if current_url is not None:
                    self.obj_scheduler.count_fetched_page()
                    self.obj_scheduler.add_new_page(current_url, current_depth)
                    


        # - Caso a URL seja um HTML válido, imprima esta URL e extraia os seus links

    def run(self):
        """
        Executa coleta enquanto houver páginas a serem coletadas
        """
        while not self.obj_scheduler.has_finished_crawl():
            self.crawl_new_url()
