import requests
import os
import time

from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse
from pathlib import Path


class WebDownloader():

    def __init__(self, url, destino, filename=None, timeout=10, retries=3, backoff_factor=0.3):
        self.url = url
        self.destino = destino
        self.filename = filename
        self.timeout = timeout
        self.retries = retries
        self.backoff_factor = backoff_factor
        self.session = self._criar_sessao()
        self.response = None
        self.tamanho_total = None
        self.chunksize = None

    def _escolher_chunksize(self):
        if self.tamanho_total is None:
            return 8192
        if self.tamanho_total < 1 * 1024 * 1024:
            return 1024
        elif self.tamanho_total < 100 * 1024 * 1024:
            return 8192
        elif self.tamanho_total < 1024 * 1024 * 1024:
            return 65536
        else:
            return 262144

    def _obter_nome_arquivo(self):
        parsed_url = urlparse(self.url)
        filename = os.path.basename(parsed_url.path)
        return filename

    def _criar_sessao(self):
        session = requests.Session()
        retry = Retry(
            total=self.retries,
            read=self.retries,
            connect=self.retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def _obter_response(self):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
            }
            self.response = self.session.get(self.url, headers=headers, stream=True, timeout=self.timeout)
            self.response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Erro ao baixar o arquivo: {e}")

        content_length = self.response.headers.get('Content-Length')
        self.tamanho_total = int(content_length) if content_length else None
        self.chunksize = self._escolher_chunksize()

    def download(self):
        print(f"Iniciando download de: {self.url}")
        self._obter_response()

        if self.tamanho_total:
            print(f"Tamanho total: {self.tamanho_total / (1024 * 1024):.2f} MB")
        else:
            print("Tamanho total desconhecido (Content-Length ausente)")

        print(f"Chunksize definido: {self.chunksize} bytes")

        path_destino = Path(self.destino)
        if self.filename is None:
            filename = self._obter_nome_arquivo()
            self.filename = filename

        path_destino.mkdir(parents=True, exist_ok=True)

        file_path = path_destino / self.filename

        inicio = time.time()

        progress_bar = tqdm(
            total=self.tamanho_total,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            desc='Baixando',
            disable=not self.tamanho_total
        )

        with open(file_path, 'wb') as f:
            for chunk in self.response.iter_content(chunk_size=self.chunksize):
                if chunk:
                    f.write(chunk)
                    progress_bar.update(len(chunk))

        fim = time.time()
        minutos, segundos = divmod(fim - inicio, 60)
        print(f"Download concluído em {int(minutos)}m {int(segundos)}s")