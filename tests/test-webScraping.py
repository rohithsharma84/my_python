"""
Use Beautiful Soup for web scraping
Pre-req: python -m pip install bs4

"""
import os
import bs4 # Beautiful Soup 4
from urllib.request import urlopen as newUreq
from bs4 import BeautifulSoup as soup

url = 'https://www.amazon.com/dp/B0BFC7WQ6R?ref_=nav_em__ods_ha_echo_bak_0_2_4_5&th=1'
Uclient = newUreq(url)
html_page = Uclient.read()
Uclient.close()
html_soup = soup(html_page, "html.parser")

# print the title of the page
print(html_soup.h1)

# pause for user to continue
input("\n\nPress Enter to continue...")

# Print all the contents of the page
print(html_soup.findAll)