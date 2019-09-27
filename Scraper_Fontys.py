## Here we import all necessary packages
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib3.util import parse_url
from lxml.html.clean import Cleaner
from write_2_sql import Results
from write_2_sql import FontysStartURL
import urllib3



def urls_sql_2_list(list_sql):
    ## Here we create a python list from the urls which were imported in SequelPro.
    ## This step needs to be adjusted if the script will be repeated with the list of websites from a different source.
    list_starturl = []
    for link in list_sql:
        list_starturl.append(link.start_url)
    return list_starturl


def delete_file_types(url):
    ## Here we delete all the unusefull file types (which cannot be read).
    if url[-4:] in [".png", ".jpg", ".txt", ".pdf", ".doc", "jpeg"]:
        return False


def url_slash_check(url):
    # This function checks whether the link as a slash at the end. Adds a slash if abscent.
    if url[-1] != '/':
        url2check = url + '/'
    else:
        url2check = url
    return url2check

def url_http_check(url):
    # This function checks whether the link contains http or https. Adds http:// if abscent.
    if "http://" in url or "https://" in url:
        http_url = url
    else:
        http_url = "http://%s" % url
    return http_url

def url_reform(url):
    # Here we fix the url when necessary
    # url = url_slash_check(url)
    url = url_http_check(url)
    return url

def redirect_url(content, url):
    ## Here we check if the start URL redirects to a different URL. If so, the redirect URL is now the new start URL.
    redirect_to = content.url
    if redirect_to != '':
       new_link = redirect_to
    else:
        new_link = url
    return new_link

def url_downloader(url):
    ## Here we download the complete webpage of a URL

    try:
        checked_url = url_reform(url)

        content = requests.get(checked_url, timeout=5)
        # Here we scrape the complete webpage.

        is_alive = content.status_code == 200
        # Check if URL is alive (if not, we save this info in the database)
        start_url = redirect_url(content, checked_url)
        # this link is either the redirect link, or the checked link
        # if there is no redirect link.

        redirects = content.history

        return checked_url, content, is_alive, start_url, redirects

    # Here we make sure the script continues running even when errors occur.
    except urllib3.exceptions.HTTPError as e:
        print(e, checked_url)
    except requests.ConnectionError as e:
        print(e, checked_url)
    except Exception as e:
        print(e, checked_url)

def html2text(content):
    ## Uses the requested content as input, returns the cleaned text in one large string
    text = content.text
    if text != '':

        cleaner = Cleaner()
        cleaner.javascript = True  # This is True because we want to activate the javascript filter
        cleaner.style = True
        cleaned_text = cleaner.clean_html(text)
        cleaned_text = BeautifulSoup(cleaned_text, "lxml").text
        cleaned_text = cleaned_text.replace('\n', ' ')
        cleaned_text = cleaned_text.replace('\t', ' ')
        cleaned_text = " ".join(cleaned_text.split())
        cleaned_text = "".join(i for i in cleaned_text if ord(i) < 128)

        return cleaned_text

def html2links(content):
    # Returns a list of all the links from one url. External links included.
    html_doc = BeautifulSoup(content.content, 'lxml')
    list_links = []
    links = html_doc.find_all('a')
    for link in links:
        link_in_file = link.get('href')

        if link_in_file is None:
            continue
        web_url = delete_file_types(link_in_file)
        if web_url == False:
            continue
        else:
            list_links.append(link_in_file)

    return list(set(list_links))

def linkinhtml(link_to_test, start_url):
    # Here we make sure all the found links are working and pastes them to the correct start url.
    try:
        o = urllib3.util.parse_url(link_to_test)
        j = urllib3.util.parse_url(start_url)

        if  o.netloc == j.netloc or o.netloc == None or 'html' in str(o.path):
            newurl = "http://" + j.netloc + o.path

            return newurl

        elif o.scheme is None or len(o.scheme) == 0:
            if link_to_test[0] == '/' and start_url[-1] == '/':
                newurl = start_url + link_to_test[1:]
            elif (start_url[-1] != '/') and (link_to_test[0] != '/'):
                newurl = start_url + '/' + link_to_test
            else:
                newurl = start_url + link_to_test
            return newurl
        else:
            return

    except Exception as e:
        print('error in linkinhtml', e, link_to_test)


def scrape_level_0(list_starturls):
    # This function scrapes level 0 (start URL) and extracts the level 1 urls.
    # It also writes the results from the start URLs to the database.
    dict_errors = {}
    scrape_data = {}
    for item in list_starturls:

        try:
            checked_url, content, is_alive,  start_url, redirects = url_downloader(item)

            links = html2links(content)

            list_links_in_html = []
            for link_to_test in links:

                tested_link = urljoin(start_url,link_to_test)
                if tested_link is not None:
                    list_links_in_html.append(tested_link)

            text = html2text(content)
            scrape_data[item] = {
                'original_url': item,
                'start_url': start_url,
                'text': text,
                'sub_url' : None,
                'links': list_links_in_html,
                'is_alive': is_alive,
                'level': 0
                }
            Results.create(**scrape_data[item]) # This writes a new line to SQLPro database (in dict form)
        except Exception as e:
            dict_errors['error'] = e
            dict_errors['original_link'] = item
            print(e, item)
            continue

    return scrape_data, list_starturls, dict_errors



def scrape_level_12(list_starturl, scrape_data):
    # This function scrapes all the level 1 and level 2 URLs, and writes all the output to the database.
    suburl_dict = {}
    num = 1
    for item in scrape_data:

        ## Here we extract the dictionary for each start URL, level 0.
        start_url_dict = scrape_data[item]

        # These are the level 1 urls from the start URL which we want to explore and store.
        level1_urls =  list(set(start_url_dict['links']))
        if start_url_dict['is_alive'] == 1 and len(level1_urls) > 0:
            start_url = start_url_dict['start_url']

            level2_urls = [] # This is the list of level 2 URLs
            for url_lvl1 in level1_urls:

                if url_lvl1 != start_url or url_lvl1 != start_url + str('/'):
                    try:
                        checked_url, content, is_alive, redirect_url, redirects = url_downloader(url_lvl1)
                        links_lvl2 = html2links(content)

                        for link_to_test in links_lvl2:
                            level2_urls.append(urljoin(link_to_test, start_url))

                        text = html2text(content)
                        suburl_dict[url_lvl1] = {
                            'original_url': item,
                            'sub_url': url_lvl1,
                            'start_url': start_url_dict['start_url'],
                            'text': text,
                            'is_alive': is_alive,
                            'level': 1 }

                    except Exception as e:
                        print(e, url_lvl1)

            if len(level2_urls) > 0 : # Here we check if there are any level 2 URLs.
                                      # If not, we continue with the next start URL
                remaining_level2_urls = list(set(level2_urls) - set(level1_urls))

                for url_lvl2 in remaining_level2_urls:
                    if url_lvl2 != None:

                        try:
                            checked_url_lvl2, content_lvl2, is_alive_lvl2, start_url_lvl2, redirects_lvl2 = url_downloader(url_lvl2)
                            text_lvl2 = html2text(content_lvl2)
                            suburl_dict[url_lvl2] = {
                                'original_url': item,
                                'sub_url': url_lvl2,
                                'start_url': start_url_dict['start_url'],
                                'text': text_lvl2,
                                'is_alive': is_alive_lvl2,
                                'level': 2
                            }

                        except Exception as e:
                            print(e, url_lvl2)

        # Here we loop through the 'sub_url' dictionary. Per start URL we make a connection with the database
        # and write the data.
        for row in suburl_dict:
            Results.create(**suburl_dict[row])
        print("websites scraped", num)
        num += 1

    return suburl_dict




# ##########
# ## Main ##
# ##########

def main():
    list_sql = FontysStartURL.select()  ## make connection with SQLPro database and select alle data.
    list_starturl = urls_sql_2_list(list_sql) ## create a list of the start URLs.
    scrape_data, list_starturl, dict_errors = scrape_level_0(list_starturl) ## scrape level 0 webpages.
    suburl_dict = scrape_level_12(list_starturl, scrape_data) ## scrape level 1 and 2 webpages.

if __name__ == "__main__":
    main()

