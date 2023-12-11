# Long pipeline
# coding: utf-8
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import smtplib
from bs4 import BeautifulSoup
import os

def wbprocurements_pubsub(criteria1, criteria2):
    # Extract table from main page
    url = 'https://www.worldbank.org/en/about/corporate-procurement/business-opportunities/administrative-procurement'
    html = requests.get(url).content
    df_list = pd.read_html(html)
    df = df_list[-1]

    # Transform table and join url links
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    trigger = 0

    links = []
    for tr in table.findAll("tr"):
        trs = tr.findAll("td")
        for each in trs:
            try:
                link = each.find('a')['href']
                links.append(link)
            except:
                pass

    df['Link'] = links
    df['Link'] =str('https://www.worldbank.org')+df['Link']

    # Scan each url
    df['scan'] = 'Not treated'

    for index, row in df.iterrows():
        print(df.loc[index, 'Link'])
        url = df.loc[index, 'Link']

        html = requests.get(url).content

        soup = BeautifulSoup(html, features="html.parser")

        # kill all script and style elements
        for script in soup(["script", "style"]):
            script.extract()    # rip it out

        # get text
        text = soup.get_text()
        text = text[text.find('SOLICITATION NUMBER'):].replace('\n','').replace('\xa0','')

        key_words = ['earth observation', 'Earth Observation', 'remote sensing', 'Remote sensing', ' EO ', ' GIS ', 'geospatial', 'Geospatial', 'geographic information', 'Geographic information', 'imagery', 'Imagery','geotechnical', 'Geotechnical', 'satellite', 'Satellite']

        if any(word in text for word in key_words):
            df.loc[index, 'scan'] = 'detected'      
            print("query found")
            trigger = 1
        elif '403 ERROR' in text:
            df.loc[index, 'scan'] = 'error'     
            print("error")
        else:
            print('no match')
        
    df = df[(df['scan']=='detected')]
    df = df[['Solicitation Title', 'Issue Date', 'Closing Date', 'Link']]
    df = df.rename(columns={'Solicitation Title' : 'Procurement Title', 'Issue Date' : 'Published Date', 'Closing Date' : 'Submission Date'})
    df = df.reset_index(drop=True)


    # Notification function #
    msg = MIMEMultipart()
    msg['Subject'] = "WB Corporate Procurements screening"
    sender = 'alex.chunet@gmail.com'
    recipients = ['alex.chunet@gmail.com','achunet@worldbank.org','alex.chunet@esa.int','carlotta@cariboudigital.net', 'nicki@cariboudigital.net', 'christoph.aubrecht@esa.int']
    emaillist = [elem.strip().split(',') for elem in recipients]

    def send_email(sbjt, msg):
        toaddrs = 'alex.chunet@gmail.com'

        # The actual mail sent
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.starttls()
        server.login(os.environ['email_p'],os.environ['pass_p'])
        server.sendmail(sender, emaillist, msg)
        server.quit()

    # Format email
    html = """\
    <html>
    <head></head>
    <body>
        <p1>Keywords used: ['earth observation', 'Earth Observation', 'remote sensing', 'Remote sensing', ' EO ', ' GIS ', 'geospatial', 'Geospatial', 'geographic information', 'Geographic information', 'imagery', 'Imagery','geotechnical', 'Geotechnical', 'satellite', 'Satellite']</p1>
        {0}
    </body>
    </html>
    """.format(df.to_html())

    part1 = MIMEText(html, 'html')
    msg.attach(part1)

    # Send 
    if trigger == 1:
        send_email('Query found', msg.as_string())
    else:
        send_email('No query found', msg.as_string())

    print("SUCCESS!")
