import subprocess
import sys
import os
import shutil
from lxml import etree as ET
from collections import Counter

# Takes in a file name outputs its dimensions
def get_image_dimensions(image_file_name):
    identify = subprocess.run(["identify",'-format','%w:%h',image_file_name],capture_output=True)
    x,y = identify.stdout.split(b":")
    return int(x),int(y)

# Removes all non-digits from a string and then converts it to an int
def int_of_string_noticing_only_digits(s):
    return int(''.join(filter(str.isdigit, s)))

# Assuming that a web page has a tag like
# <META name="viewport" content="width=605ox;, height=783px;"/>
# or similar, this will pull out the width and height
# This should be a required field for Fixed-Format ePubs,
# so we can generally expect this to work.
def get_viewport_dimensions(page_file):
    page_root = ET.parse(page_file).getroot()
    viewport = page_root.find('./{*}head/{*}meta[@name="viewport"]')
    if viewport is not None:
        content_desc = viewport.attrib["content"]
        width_desc, height_desc = content_desc.split(",")
        _, width = width_desc.split("=")
        _, height = height_desc.split("=")
        return int_of_string_noticing_only_digits(width), int_of_string_noticing_only_digits(height)
    else:
        return 0,0
    
directory_temp_string = "_conversiontemp"

base_dir_name = os.getcwd()
name = sys.argv[1]
short_name,_,_ = name.partition(".epub")

# Where the epub will be expanded to
temp_dir_name = name+directory_temp_string+"_epub"
output_dir_name = base_dir_name+"/"+name+directory_temp_string+"_cbz"

dirs_to_delete_at_end = []

# Makes a temporary directory and adds it to the list of temporary
# directories using its full pathname
def make_temp_dir(name,local=True):
    os.mkdir(name)
    if local:
        dirs_to_delete_at_end.append(os.getcwd()+"/"+name)
    else:
        dirs_to_delete_at_end.append(name)

make_temp_dir(temp_dir_name)
        
unzip = subprocess.run(["unzip", name, "-d",temp_dir_name])

os.chdir(temp_dir_name)
# Sanity check the included mimetype.
with open('mimetype', 'r') as mimetype_file:
    mimetype = mimetype_file.read().strip()
if mimetype != "application/epub+zip":
    print("Invalid mime type.  Not epub file.")
    sys.exit(-2)

# Next we follow the container to find the rootfile or possibly rootfiles.
# I have no concept of why there can be more than one "book" in an epub,
# but it appears to be allowed, so I've tried to support it, just in
# case.  This has only been tested with one book per file.
container = ET.parse("META-INF/container.xml")
container_root = container.getroot()
all_rootfiles = container_root.findall("./{*}rootfiles/{*}rootfile")
if len(all_rootfiles) > 1:
    multiple = True
    print("Multiple rootfiles detected")
else:
    multiple = False
for rootfile in all_rootfiles:

    # The rootfile element only tells us where the opf file is.
    # Because paths within HREF attributes in the .opf are all
    # relative rather than absolute, we know that the other stuff
    # will generally be in the same directory or a sub directory
    # as the .opf file.  If this is not true, we don't handle it well.
    # But regardless, we have to extract the directory so we can move into
    # it and then find the other stuff.
    opf = rootfile.attrib["full-path"]
    opf_parts = opf.split("/")
    opf_dir = "/".join(opf_parts[:-1])
    opf_filename = opf_parts[-1]
    os.chdir(opf_dir)

    if multiple:
        rootfile_name = "".join(opf_part[:-1])
        print("Starting rootfile "+rootfile_name)
        rootfile_cbz_dir = output_dir_name + "_" + rootfile_name
        rootfile_cbz_name = short_name + "_" + rootfile_name + ".cbz"
    else:
        rootfile_cbz_dir = output_dir_name
        rootfile_cbz_name = short_name + ".cbz"

    make_temp_dir(rootfile_cbz_dir)
        
    opf_root = ET.parse(opf_filename).getroot()
    # All items
    items = opf_root.findall('./{*}manifest/{*}item')
    # Only those which are images
    images = [item for item in items if item.attrib["media-type"].startswith("image/")]
    # Next we need all the sizes so that we can find the size of background
    # images (assuming that they exist).
    # We need these sizes rather than just the viewport size because we want
    # to export at the highest supported size, which means
    # images at the size of the background image rather than at the size
    # of the viewport.
    imagesizes = [get_image_dimensions(image.attrib["href"]) for image in images]
    # We assume that the mode of the image sizes is the background image
    # page size.
    imgx,imgy = Counter(imagesizes).most_common(1)[0][0]
    print("Image dimensions found to be: "+str(imgx)+"x"+str(imgy))

    # Then we extract the pages by doing spine:itemref:pageref -> item:idfref
    page_file_names = [opf_root.find("./{*}manifest/{*}item[@id='"+page_ref.attrib["idref"]+"']").attrib["href"] for page_ref in opf_root.findall('./{*}spine/{*}itemref')]

    page = 0
    current_dir = os.getcwd()
    for page_file in page_file_names:
        page += 1
        page_num = str(page).zfill(5) # Hopefully, everything is no more than 99,999 pages long
        page_name = "page_"+page_num+".png"
        
        pagex,pagey = get_viewport_dimensions(page_file)
        # Fallback in case this didn't work, shouldn't be needed
        if pagex == 0 and pagey == 0:
            pagex = imgx
            pagey = imgy
        # In case the scale works backwards on some images.
        if pagex >= imgx and pagey >= imgy:
            scale = 1.0
        else:
            scale = max(imgx/pagex,imgy/pagey)
        print("Rendering page "+page_name+" using scale "+str(scale))

        # Google Chrome's headless mode can take a screenshot
        # But it should be noted that using the page size (viewport size)
        # as the scale is not a mistake.  The --force-device-scale-factor
        # argument gets multiplied by the resolution to get the
        # actual resolution of the .png screenshot image it produces.
        # For example, if we set window-size to 600x800, but
        # force-device-scale-factor to 1.5, it will actually output
        # a png file with 900x1200 pixels.
        #
        # We're going to capture output on the next line just so it is not displayed
        subprocess.run(["google-chrome","--headless","--disable-gpu","--screenshot","--force-device-scale-factor="+str(scale),"--window-size="+str(pagex)+","+str(pagey),"file:///"+current_dir+"/"+page_file],capture_output=True)
        os.rename("screenshot.png",rootfile_cbz_dir+"/"+page_name)

    # All done, zip it up to a .cbz file
    subprocess.run(["zip -j "+base_dir_name+"/"+rootfile_cbz_name+" "+rootfile_cbz_dir+"/*"],shell=True)

for dir in dirs_to_delete_at_end:
    print("Cleaning up temp director: "+dir)
    shutil.rmtree(dir)
