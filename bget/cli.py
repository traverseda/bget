#!/usr/bin/env python3
import click
import click_config_file
import urllib
import queue
import asyncio
import time
import subprocess
import random
import socket
import xdg
import xdg.BaseDirectory.xdg_data_home as XDG_DATA_HOME
from pathlib import Path
import shutil

import selenium
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

if not (XDG_DATA_HOME/"bget").exists():
    (XDG_DATA_HOME/"bget").mkdir()
    (XDG_DATA_HOME/"bget"/"firefoxProfile").mkdir()
    (XDG_DATA_HOME/"bget"/"warcprox").mkdir()

XDG_RUNTIME_DIR = xdg.BaseDirectory.get_runtime_dir(strict=False)

portRange=set(range(32768,32768+100))

#Fixes add-ons not loading issue
#Per https://github.com/mozilla/geckodriver/issues/1517#issuecomment-514276587
def retoggleAllTheAddons(driver):
    print("Manually initializing all extentsions")
    driver.get("about:addons")
    driver.find_element_by_id("category-extension").click()
    driver.execute_script("""
        let hb = document.getElementById("html-view-browser");
        let al = hb.contentWindow.window.document.getElementsByTagName("addon-list")[0];
        let cards = al.getElementsByTagName("addon-card");
        for(let card of cards){
            card.addon.disable();
            card.addon.enable();
        }
    """)

class Archiver:

    def __init__(self):
        self.port=None
        self.warcProxy=None
        self.driver=None
        self.profile=None
        self.crawl_delay=0
        self.crawl_delay_random=0
        self.queue = queue.Queue()
        self.filters=[]

    def __del__(self):
        if self.port:
            portRange.add(self.port)
        if self.warcProxy:
            self.warcProxy.terminate()
        if self.driver:
            self.driver.quit()

    def setup_proxy(self,warcName=None,blackoutPeriod=604800):
        if not self.warcProxy:
            if not self.port:
                self.port = random.sample(portRange,1)[0]
                portRange.remove(self.port)
            self.warcProxy = subprocess.Popen(["warcprox",
                                          "--warc-filename",warcName+"-{timestamp17}-{serialno}-{randomtoken}",
                                          "-j", "dedupe_"+warcName+".sqlite",
                                          "-p", str(self.port),
                                          #"-q", #Not so much logging
                                          "--blackout-period", str(blackoutPeriod),
                                          ],cwd=str(XDG_DATA_HOME/"bget"/"warcprox"),
                                        )
        return self.warcProxy

    def setup_driver(self):
        if not self.driver:
            profile = (XDG_DATA_HOME/"bget"/"firefoxProfile").resolve()
            profile = webdriver.FirefoxProfile(str(profile))
            #Disable browser disk cache. Memory cache still works, so
            #in effect this just wipes the cache each session.
            profile.set_preference("browser.cache.disk.enable","false")
            #Fully download any media files, don't wait for the player to
            #catch up.
            profile.set_preference("media.cache_readahead_limit","999999")
            profile.set_preference("media.cache_resume_threshold","999999")
            #Clean up firefox's native calls
            profile.set_preference("browser.search.geoip.url","")
            profile.set_preference("browser.aboutHomeSnippets.updateUrl","")
            profile.set_preference("browser.startup.homepage_override.mstone","ignore")
            profile.set_preference("extensions.getAddons.cache.enabled","false")
            self.profile=profile
            if self.port:
                profile.set_preference("network.proxy.type", 1)
                profile.set_preference("network.proxy.http", "localhost")
                profile.set_preference("network.proxy.http_port", self.port)
                profile.set_preference("network.proxy.ssl", "localhost")
                profile.set_preference("network.proxy.ssl_port", self.port)
            driver = webdriver.Firefox(firefox_profile=profile)
            retoggleAllTheAddons(driver)
            self.driver=driver
        return self.driver

    def process(self,item):
        """Add a url to be processed.
        """
        for i in self.filters:
            item = i(item)
            if not item: return False
        self.queue.put(item)
        return True

    def no_querystring(self):
        def no_querystring(url):
            return url.split('?')[0]
        self.filters.append(no_querystring)
        return self

    def no_parent(self,url):
        """This filter will prevent bget from processing
        above a certain point in a url.
        """
        def noparent(item):
            f"""Makes sure items start with {url}
            """
            if not item.startswith(url):
                return False
            return item
        self.filters.append(noparent)
        return self

    def remove_fragment(self):
        """This filter removes urls from fragments.
        """
        def remove_fragment(item):
            item = urllib.parse.urldefrag(item)[0]
            return item
        self.filters.append(remove_fragment)
        return self

    def session_dedupe(self):
        """Dedupes urls, so we don't visit the same
        url more than once during a session. More complicated
        dedupes could do things like call out to a memento api.

        Dedupe should be last in your filter chain.
        """
        dedupe=set()
        def session_dedupe(item):
            if item in dedupe:
                return False
            dedupe.add(item)
            return item
        self.filters.append(session_dedupe)
        return self

    async def loop_async(self, run_forever=False):
        """Runs through all the items in the queue
        """
        driver = self.setup_driver()
        while run_forever or not self.queue.empty():
            item = self.queue.get()
            driver.get(item)
            driver.implicitly_wait(0)
            delay = random.uniform(0,self.crawl_delay_random)+self.crawl_delay
            await asyncio.sleep(delay)
            self.on_page_load(driver)

            elems = driver.find_elements_by_xpath("//a[@href]")
            for elem in elems:
                try:
                    e = str(elem.get_attribute("href"))
                except selenium.common.exceptions.StaleElementReferenceException:
                    print(f"element {e} on page {item} has dissapeared!")
                self.process(e)
            #Load all videos
            driver.execute_script("""var elements = document.getElementsByTagName('video');
                                     for (let item of elements) {
                                         item.setAttribute("preload","auto");
                                     }
                                  """)
            #Load all audio
            driver.execute_script("""var elements = document.getElementsByTagName('audio');
                                     for (let item of elements) {
                                         item.setAttribute("preload","auto");
                                     }
                                  """)

    def loop(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.loop_async())

    def on_page_load(self,page):
        """This is where you'd define custom user actions.
        """
        pass

@click.group()
def cli():
    pass

@cli.command(help="Start an interactive browser session.")
@click.argument('url', default="")
@click.option("--archive",help="Archive this session",is_flag=True)
@click.option("--archive-name",help="Archive this session with a custom name")
@click.option("--force-selenium",help="Force session to run through selenium",is_flag=True)
@click_config_file.configuration_option()
def browse(url,force_selenium,archive,archive_name):
    archiver=Archiver()
    if archive or archive_name:
        warcName = archive_name or "interactive"
        proxy = archiver.setup_proxy(warcName)

    if force_selenium:
        d = archiver.setup_driver()
        d.get(url or "about:home")
        while True:
            time.sleep(1)
    else:
        if archive or archive_name:
            raise NotImplementedError("ToDo: We currently don't support archiving without selenium")
        profile = (XDG_DATA_HOME/"bget"/"firefoxProfile").resolve()
        subprocess.call(["firefox","--no-remote","--profile",profile])

@cli.command(help="Automatically archive a website.")
@click.option("--headless",default=False, is_flag=True,
              help="Don't show the browser window")
@click.option("--wait-for-input",default=False, is_flag=True,
              help="Waits for the user to press enter before starting scrape")
@click.argument('url')
@click.option("--archive-name",help="Archive this session with a custom name")
@click_config_file.configuration_option()
def archive(url,headless,archive_name,wait_for_input):
    archiver=Archiver()
    warcName=urllib.parse.urlsplit(url).netloc
    archiver.setup_proxy(archive_name or warcName)
    archiver.setup_driver()
    #Set up session
    archiver.no_querystring()
    archiver.remove_fragment().no_parent(url).session_dedupe()
    if wait_for_input:
        input("Press enter when you're ready to start scraping")
    archiver.process(url)
    archiver.loop()

@cli.command(help="Serve your captured warc files")
def serve():
    pass

if __name__ == '__main__':
    try:
        cli()
    except (KeyboardInterrupt,SystemExit):
        pass
