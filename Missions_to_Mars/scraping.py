from bs4 import BeautifulSoup
import json
# from selenium import webdriver
# from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import pymongo
import datetime

# executable_path = {'executable_path': ChromeDriverManager().install()}

class Scrape:
    def __init__(self, browser):
        #self.chrome = executable_path
        #self.browser = Browser('chrome', **executable_path, headless=False)
        #self.browser.driver.set_window_size(1920,1080)
        self.browser = browser
    
    def get(self, http):
        self.browser.visit(http)
        time.sleep(5)
        self.soup = BeautifulSoup(self.browser.html, "lxml")

    def retrieveFirstText(self, tags_list):
        # soup = self.soup.find(tags_list[0])
        # for x in range(1, len(tags_list)):
        #     soup = soup.find(tags_list[x])
        soup = None
        if "class" in tags_list[0]:
            soup = self.soup.find(tags_list[0]["tag"], class_=tags_list[0]["class"])
        else:
            soup = self.soup.find(tags_list[0]["tag"])
        for i in range(1, len(tags_list)):
            if "class" in tags_list[i]:
                soup = soup.find(tags_list[i]["tag"], class_=tags_list[i]["class"])
            else:
                soup = soup.find(tags_list[i]["tag"])
                
        return soup.text

    def retrieveFirstAttr(self, tags_list, attr):
        soup = None
        if "class" in tags_list[0]:
            soup = self.soup.find(tags_list[0]["tag"], class_=tags_list[0]["class"])
        else:
            soup = self.soup.find(tags_list[0]["tag"])
        for i in range(1, len(tags_list)):
            if "class" in tags_list[i]:
                soup = soup.find(tags_list[i]["tag"], class_=tags_list[i]["class"])
            else:
                soup = soup.find(tags_list[i]["tag"])        
        return soup[attr]

    def retrieveFirstSoup(self, tags_list):
        soup = None
        if "class" in tags_list[0]:
            soup = self.soup.find(tags_list[0]["tag"], class_=tags_list[0]["class"])
        else:
            soup = self.soup.find(tags_list[0]["tag"])
        for i in range(1, len(tags_list)):
            if "class" in tags_list[i]:
                soup = soup.find(tags_list[i]["tag"], class_=tags_list[i]["class"])
            else:
                soup = soup.find(tags_list[i]["tag"])
        return soup

def http_join(root, sub):
    return root.rstrip("/") + "/" + sub.lstrip("/")

def scrape(browser):
    scraping = Scrape(browser)

    #######################################
    # https://mars.nasa.gov/news/
    #######################################
    weblink = "https://mars.nasa.gov/news/"
    scraping.get(weblink)

    # get news title
    tags = [{"tag":"article"}, {"tag":"ul"}, {"tag":"li"}, {"tag":"div", "class":"content_title"}]
    news_title = scraping.retrieveFirstText(tags)

    # get news date
    tags[3]["class"] = "list_date"
    news_date = scraping.retrieveFirstText(tags)

    # get news briefing
    tags[3]["class"] = "article_teaser_body"
    news_brief = scraping.retrieveFirstText(tags)

    #######################################
    # https://data-class-jpl-space.s3.amazonaws.com/JPL_Space/index.html
    #######################################
    weblink = "https://data-class-jpl-space.s3.amazonaws.com/JPL_Space/index.html"
    scraping.get(weblink)
    feature_img = scraping.retrieveFirstAttr([{"tag":"div", "class":"header"}, {"tag":"img", "class":"headerimage"}], "src")
    feature_img = weblink[0:weblink.rfind("/")] + "/" + feature_img

    #######################################
    # https://space-facts.com/mars/
    #######################################
    weblink = "https://space-facts.com/mars/"
    df = pd.read_html(weblink)
    df_fact = df[0]
    df_fact.columns=["Fact","Value"]
    df_fact["Fact"] = df_fact["Fact"].str.strip(":")
    # df_fact.set_index("Fact", inplace=True)
    facts_dict = {}
    for index, row in df_fact.iterrows():
        facts_dict[row["Fact"]] = row["Value"]
    facts_table = df_fact.to_html(index=False)

    #######################################
    # https://astrogeology.usgs.gov/search/results?q=hemisphere+enhanced&k1=target&v1=Mars
    #######################################
    webroot = "https://astrogeology.usgs.gov/"
    weblink = "https://astrogeology.usgs.gov/search/results?q=hemisphere+enhanced&k1=target&v1=Mars"
    scraping.get(weblink)
    tags = [{"tag":"div", "class":"full-content"}, {"tag":"div", "class":"results"}]
    soup = scraping.retrieveFirstSoup(tags)
    all_links = soup.find_all("a", class_="itemLink")
    # 2 <a> elements for a same link, one for img and one for text
    # filter out all the img ones
    all_links = [ x for x in all_links if x.find("img") is None]
    imgs = []
    for x in all_links:
        title = x.find("h3").text
        sub_link = http_join(webroot, x["href"])
        scraping.get(sub_link)
        tags = [{"tag":"div", "class":"downloads"}]
        sub_soup = scraping.retrieveFirstSoup(tags)
        # find <a> tag with text is "Original"
        thumb = sub_soup.find("a", string="Sample")
        img = sub_soup.find("a", string="Original")
        imgs.append({"title" : title, "thumb" : thumb["href"], "img_url" : img["href"]})
        # wait 5 sec before redirecting to the next link
        time.sleep(5)

    today = datetime.datetime.today()
    mars_dict = {
        "scrape_time" : datetime.datetime(today.year, today.month, today.day),
        "news_title" : news_title,
        "news_date" : news_date,
        "news_briefing" : news_brief,
        "feature_img" : feature_img,
        "facts" : facts_dict,
        "facts_table" : facts_table,
        "hemisphere_img" : imgs
    }

    savetodb(mars_dict)
#    print(mars_dict)
    return mars_dict

def savetodb(mars_dict):
    conn = 'mongodb://localhost:27017'
    client = pymongo.MongoClient(conn)
    db = client.mars_db
    db.scrape.update_one({"scrape_time": mars_dict["scrape_time"]}, {"$set" : mars_dict}, upsert=True)
    client.close()

def getlatestdict():
    conn = 'mongodb://localhost:27017'
    client = pymongo.MongoClient(conn)
    db = client.mars_db
    scrape_col = db.scrape.find_one({"$query" :{}, "$orderby" : { "scrape_time" : -1 }})
    client.close()
    return scrape_col