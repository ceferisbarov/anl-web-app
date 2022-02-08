import os
import io
import base64
import requests
import numpy as np

from flask import Flask, url_for, redirect, request, render_template, send_from_directory
from bs4 import BeautifulSoup
from PIL import Image
import img2pdf
import ocrmypdf

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        UPLOAD_FOLDER='var'
    )
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route("/", methods=["GET"])
    def home():
        return render_template("home.html")
      
      
    @app.route('/', methods=['POST'])
    def my_form_post():
         url = request.form['book_url'] # TODO: ACCEPTS URL ONLY. SHOULD ALSO ACCEPT BIBID
         bibid = get_bibid(url)
         return redirect(f"/book/{bibid}")
      
    @app.route("/book/<string:bibid>", methods=["GET"])
    def book(bibid):
        entered_url = 'http://web2.anl.az:81/read/page.php?bibid='  + bibid # TODO: reconstruct url properyl
        page_count, book_title = get_url_parameters(entered_url)
        
        page_count = 20 # THIS IS FOR A TEST THIS IS FOR A TEST THIS IS FOR A TEST
        
        book_info = {}
        book_info["bibid"] = bibid
        book_info["title"] = book_title
        book_info["page_count"] = page_count
        book_info["url"] = entered_url
        book_info["page_images"] = [save_images(entered_url + '&pno=' + str(pno+1), pno+1) for pno in range(page_count)]
        
        for number, image in enumerate(book_info["page_images"]):
            imageStream = io.BytesIO(image)
            imageFile = Image.open(imageStream)
            imageFile.save(os.path.join(app.config['UPLOAD_FOLDER'], f"page_{str(number).zfill(6)}.png"), format='PNG')
            
        img_path = []
        for file in os.listdir(app.config['UPLOAD_FOLDER']):
            if file.endswith(".jpg") or file.endswith(".JPG") or file.endswith(".png") or file.endswith(
                ".PNG") or file.endswith(".jpeg") or file.endswith(".JPEG"):
                img_path.append(os.path.join(app.config['UPLOAD_FOLDER'], file))
                
        with open(os.path.join(app.config['UPLOAD_FOLDER'], f"{book_info['title']}.pdf"), "wb") as f:
                f.write(img2pdf.convert(sorted(img_path)))
        
        
        OCR_choice = True # TODO: Make this an option for the user
        if OCR_choice:
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{book_info["title"]}.pdf')
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{book_info["title"]}.pdf')
            ocrmypdf.ocr(pdf_path, save_path, rotate_pages=True,
                         remove_background=True, language="aze", deskew=True, force_ocr=True)  # TODO: Add language options

        else:
            pass

        #return render_template("show.html", img_src=os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('download_file', name=f"{book_info['title']}.pdf"))
        
    @app.route('/show/<name>')
    def download_file(name):
        return send_from_directory(app.config["UPLOAD_FOLDER"], name)
                    
    return app
	    

def get_url_parameters(url):
    """
    @return:
    This function returns tüo parameters we need to iterate through URLs of a single book:
    1. book_title, which is same everywhere throughout the website,
    2. page_count, which will be used to construct a while loop (we need to know when to stop).

    @param url: URL
    @type url: str

    """
    # TODO: Rewrite this function with help of BeautifulSoup4

    page_content = requests.get(url).text
    start_last_page_params = page_content.find('last_page_params')
    start_page_count = page_content.find('pno', start_last_page_params, start_last_page_params + 100)
    start_page_count_ending = page_content.find('";', start_last_page_params, start_last_page_params + 100)
    page_count = int(page_content[start_page_count + 4:start_page_count_ending])
    length = len('<h2 class="book-title font-f-book-reg">')
    start_book_title = page_content.find('<h2 class="book-title font-f-book-reg">')
    start_book_title_ending = page_content.find('</h2>')
    book_title = page_content[start_book_title + length:start_book_title_ending]
    return page_count, book_title

def get_bibid(url):
    start_bibid = url.find('bibid')

    start_vtls = url.find('vtls')
    if start_vtls == -1:
        start_bibid = url.find('bibid')
        start_pno = url.find('&pno')
        bibid = url[start_bibid + 6:start_pno]
    else:
        bibid = url[start_vtls + 4:]
        
    return bibid


def save_images(url, pno):
    r = requests.get(url)

    soup = BeautifulSoup(r.text, 'html.parser')
    images = soup.findAll('img')

    image = download_images(images)
    print(f'Downloaded {pno} pages.')
    return image

# DOWNLOAD ALL IMAGES FROM THAT URL
def download_images(images):
    # checking if images is not zero
    if len(images) != 0:
        for i, image in enumerate(images):
            # first we will search for "data-srcset" in img tag
            try:
                # In image tag ,searching for "data-srcset"
                image_link = image["data-srcset"]

            # then we will search for "data-src" in img 
            # tag and so on..
            except:
                try:
                    # In image tag ,searching for "data-src"
                    image_link = image["data-src"]
                except:
                    try:
                        # In image tag ,searching for "data-fallback-src"
                        image_link = image["data-fallback-src"]
                    except:
                        try:
                            # In image tag ,searching for "src"
                            image_link = image["src"]

                        # if no Source URL found
                        except:
                            print("No source URL found")
                            return 0

            # After getting Image Source URL
            # We will try to get the content of image
            try:
                image = requests.get('http://web2.anl.az:81/read/' + image_link).content
                return image
                
            except Exception as e:
                print(e)
