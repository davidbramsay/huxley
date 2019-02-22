from PIL import Image
import glob
import fitz

WIDTH = 384
HEIGHT = 640

#load_doc(filename) creates a fitz doc
#get_page(doc, page_num) returns a bw PIL file of 384x640 of the page
#make_page(img) turns a random size RGB image into a bw PIL file of 384x640

def load_doc(file):
    return fitz.open(file)


def get_page(doc, page_num):

    #load with PyMuPDF
    page = doc.loadPage(page_num)
    pix = page.getPixmap(alpha=False)

    #create a b/w image of the right renger size
    final_img = Image.new('L', (WIDTH, HEIGHT), color=255)
    resize_ratio = min(float(WIDTH)/pix.width, float(HEIGHT)/pix.height)
    new_size = [int(pix.width*resize_ratio), int(pix.height*resize_ratio)]

    #convert to a b/w PIL image
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert('L')

    #resize
    print 'new size= ' + str(new_size)
    img = img.resize(new_size, Image.LANCZOS)

    #put in background image
    final_img.paste(img, ( (WIDTH-new_size[0])/2, (HEIGHT-new_size[1])/2))

    return final_img


def make_page(img):

    #create a b/w image of the right renger size
    final_img = Image.new('L', (WIDTH, HEIGHT), color=255)
    resize_ratio = min(float(WIDTH)/img.size[0], float(HEIGHT)/img.size[1])
    new_size = [int(img.size[0]*resize_ratio), int(img.size[1]*resize_ratio)]

    #convert to a b/w PIL image
    img = img.convert('L')

    #resize
    print 'new size= ' + str(new_size)
    img = img.resize(new_size, Image.LANCZOS)

    #put in background image
    final_img.paste(img, ( (WIDTH-new_size[0])/2, (HEIGHT-new_size[1])/2))

    return final_img

