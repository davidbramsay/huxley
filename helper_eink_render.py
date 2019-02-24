from PIL import Image, ImageFilter
import glob
import fitz

WIDTH = 384
HEIGHT = 640

#load_doc(filename) creates a fitz doc
#total_pages(doc) returns the number of pages in the doc
#get_page(doc, page_num) returns a bw PIL file of 384x640 of the page
#make_page(img) turns a random size RGB image into a bw PIL file of 384x640

def load_doc(file):
    return fitz.open(file)


def total_pages(doc):
    return doc.pageCount


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

    return binarize_img(final_img)


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

    return binarize_img(final_img)


def binarize_img(img):
    #we have 6 params, thats 64 combos
    img_raw = img

    for i in range(8):
        for v in [ 100, 128, 150, 175, 200 ]:
            img = img_raw

            if i & 0b1:
                img = img.filter(ImageFilter.SHARPEN)
            if i & 0b10:
                img = img.filter(ImageFilter.SMOOTH)

            img = img.point(lambda x: 0 if x<v else 255, '1')

            if i & 0b100:
                img = img.filter(ImageFilter.SHARPEN)

            img.convert('1').save('temp/' + str(i) + '-' + str(v) + '.bmp')
    #return img.convert('1')


    #NONE
    #SHARPEN
    #SHARPEN/SMOOTH

    # ALL 3 ABOVE + SHARPEN AFTER

