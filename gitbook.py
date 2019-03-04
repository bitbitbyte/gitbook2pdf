import html
import requests
from lxml import etree
from weasyprint import HTML, CSS
from urllib.parse import urljoin
import asyncio
import aiohttp
from bs4 import BeautifulSoup


async def request(url, headers, timeout=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=timeout) as resp:
            return await resp.text()


class Gitbook2PDF():
    def __init__(self, base_url, fname=None):
        self.fname = fname
        self.base_url = base_url
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36'
        }
        self.content_list = []

    def run(self):
        content_urls = self.collect_toc(self.base_url)
        self.content_list = [None for _ in range(len(content_urls))]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.crawl_main_content(content_urls))
        loop.close()
        all_html = "".join(self.content_list)
        csstext = self.get_all_css()
        self.write_pdf(self.fname, all_html, csstext)

    async def crawl_main_content(self, content_urls):
        tasks = []
        for index, url in enumerate(content_urls):
            tasks.append(
                self.gettext(index, url)
            )
        await asyncio.gather(*tasks)
        print("crawl : all done!")

    async def gettext(self, index, url):
        '''
        return path's html
        '''

        print("crawling : ", url)
        try:
            metatext = await request(url, self.headers, timeout=10)
        except Exception as e:
            print("retrying : ", url)
            metatext = await request(url, self.headers)

        tree = etree.HTML(metatext)
        context = tree.xpath('//section[@class="normal markdown-section"]')[0]

        if context.find('footer'):
            context.remove(context.find('footer'))
        text = etree.tostring(context).decode()
        text = html.unescape(text)
        print("done : ", url)

        self.content_list[index] = text

    def write_pdf(self, fname, html_text, css_text):
        tmphtml = HTML(string=html_text)
        tmpcss = CSS(string=css_text)
        tmphtml.write_pdf(fname, stylesheets=[tmpcss])

    def get_all_css(self):
        with open('gitbook.css', 'r') as f:
            return f.read()

    def collect_toc(self, start_url):
        text = requests.get(start_url, headers=self.headers).text
        soup = BeautifulSoup(text, 'html.parser')

        if not self.fname:
            # 如果不提供输出文件名的话，抓取html标题为文件名
            self.fname = soup.find('title').text

        lis = soup.find('ul', class_='summary').find_all('li')

        content_urls = []

        for li in lis:
            element_class = li.attrs.get('class')
            if not element_class:
                continue
            if "chapter" in element_class:
                data_path = li.attrs.get('data-path')
                content_urls.append(
                    urljoin(start_url, data_path)
                )
        return content_urls


if __name__ == '__main__':
    Gitbook2PDF("https://hit-alibaba.github.io/interview/").run()
