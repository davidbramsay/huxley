import glob
import os

#convert all epubs to pdfs with the same name

#for xelatex need 'sudo tlmgr install lm-math'
#'fc-list' for list of possible fonts

def get_epubs(path='./pdfs/'):
    files = glob.glob(path + '*.epub')
    return files

def convert_epub_pdf(filepath, newpath='./pdfs/epub_pdfs/', margin='.5in', fontsize=20, font='Helvetica'):
    newpath = newpath + filepath.split('/')[-1]
    newpath = newpath[:-4] + 'pdf'
    print 'converting/saving ' + newpath
    os.system('pandoc "' + filepath + '" -o "' + newpath + '" --pdf-engine=xelatex -V documentclass=scrartcl -V mainfont="' + font + '" -V fontsize="' + str(fontsize) + 'pt" -V geometry:margin=' + margin)

epubs = get_epubs()

for e in epubs:
    print e + ' ...'
    convert_epub_pdf(e)
