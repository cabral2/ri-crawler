from urllib import robotparser
from urllib.parse import ParseResult, urlparse

from util.threads import synchronized
from time import sleep
from collections import OrderedDict
from .domain import Domain


class Scheduler:
    # tempo (em segundos) entre as requisições
    TIME_LIMIT_BETWEEN_REQUESTS = 20

    def __init__(self, usr_agent: str, page_limit: int, depth_limit: int, arr_urls_seeds: list):
        """
        :param usr_agent: Nome do `User agent`. Usualmente, é o nome do navegador, em nosso caso,  será o nome do coletor (usualmente, terminado em `bot`)
        :param page_limit: Número de páginas a serem coletadas
        :param depth_limit: Profundidade máxima a ser coletada
        :param arr_urls_seeds: ??????

        Demais atributos:
        - `page_count`: Quantidade de página já coletada
        - `dic_url_per_domain`: Fila de URLs por domínio (explicado anteriormente)
        - `set_discovered_urls`: Conjunto de URLs descobertas, ou seja, que foi extraída em algum HTML e já adicionadas na fila - mesmo se já ela foi retirada da fila. A URL armazenada deve ser uma string.
        - `dic_robots_per_domain`: Dicionário armazenando, para cada domínio, o objeto representando as regras obtidas no `robots.txt`
        """
        self.usr_agent = usr_agent
        self.page_limit = page_limit
        self.depth_limit = depth_limit
        self.page_count = 0

        self.dic_url_per_domain = OrderedDict()
        self.set_discovered_urls = set()
        self.dic_robots_per_domain = {}
        for url in arr_urls_seeds:
            self.add_new_page(url, 1)

    @synchronized
    def count_fetched_page(self) -> None:
        """
        Contabiliza o número de paginas já coletadas
        """
        self.page_count += 1

    def has_finished_crawl(self) -> bool:
        """
        :return: True se finalizou a coleta. False caso contrário.
        """
        if self.page_count > self.page_limit:
            return True
        return False

    @synchronized
    def can_add_page(self, obj_url: ParseResult, depth: int) -> bool:
        """
        :return: True caso a profundidade for menor que a maxima e a url não foi descoberta ainda. False caso contrário.
        """

        if depth > self.depth_limit:
            return False
        if self.set_discovered_urls.__contains__(obj_url.geturl()):
            return False
        return True

    @synchronized
    def add_new_page(self, obj_url: ParseResult, depth: int) -> bool:
        """
        Adiciona uma nova página
        :param obj_url: Objeto da classe ParseResult com a URL a ser adicionada
        :param depth: Profundidade na qual foi coletada essa URL
        :return: True caso a página foi adicionada. False caso contrário
        """
        if (not self.can_add_page(obj_url, depth)):
            return False

        domain = Domain(obj_url.netloc, self.TIME_LIMIT_BETWEEN_REQUESTS)

        if not (domain in self.dic_url_per_domain):
            self.dic_url_per_domain[domain] = []
            self.dic_url_per_domain[domain].append((obj_url, depth))
        else:
            self.dic_url_per_domain[domain].append((obj_url, depth))

        self.set_discovered_urls.add(obj_url.geturl())
        self.count_fetched_page()
        return True

    @synchronized
    def get_next_url(self) -> tuple:
        """
        Obtém uma nova URL por meio da fila. Essa URL é removida da fila.
        Logo após, caso o servidor não tenha mais URLs, o mesmo também é removido.
        """
        for domain in self.dic_url_per_domain.keys():
            if domain.is_accessible():
                obj_url, depth = self.dic_url_per_domain[domain].pop(0)
                domain.accessed_now()
                if(self.dic_url_per_domain[domain] == []):
                    del self.dic_url_per_domain[domain]
                return (obj_url, depth)

        sleep(self.TIME_LIMIT_BETWEEN_REQUESTS)
        return None, None

    def can_fetch_page(self, obj_url: ParseResult) -> bool:
        """
        Verifica, por meio do robots.txt se uma determinada URL pode ser coletada
        """
        domain = Domain(obj_url.netloc, self.TIME_LIMIT_BETWEEN_REQUESTS)

        if not (domain in self.dic_robots_per_domain):
            robots_url = url=f'https://{obj_url.netloc}/robots.txt'
            url = obj_url.geturl()
            robots_parser = robotparser.RobotFileParser()
            robots_parser.set_url(robots_url)
            robots_parser.read()
            self.dic_robots_per_domain[domain] = robots_parser.can_fetch('*', url)

        return self.dic_robots_per_domain[domain]
