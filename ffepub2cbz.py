import subprocess
import sys
import os
from lxml import etree as ET
from collections import Counter

def get_image_dimensions(image_file_name):
    identify = subprocess.run(["identify",'-format','%w:%h',image_file_name],capture_output=True)
    x,y = identify.stdout.split(b":")
    return int(x),int(y)

def int_of_string_noticing_only_digits(s):
    return int(''.join(filter(str.isdigit, s)))

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
temp_dir_name = name+directory_temp_string+"_epub"
output_dir_name = base_dir_name+"/"+name+directory_temp_string+"_cbz"

os.mkdir(temp_dir_name)

unzip = subprocess.run(["unzip", name, "-d",temp_dir_name])

os.chdir(temp_dir_name)
with open('mimetype', 'r') as mimetype_file:
    mimetype = mimetype_file.read().strip()
if mimetype != "application/epub+zip":
    print("Invalid mime type.  Not epub file.")
    sys.exit(-2)

container = ET.parse("META-INF/container.xml")
container_root = container.getroot()
all_rootfiles = container_root.findall("./{*}rootfiles/{*}rootfile")
if len(all_rootfiles) > 1:
    multiple = True
    print("Multiple rootfiles detected")
else:
    multiple = False
for rootfile in all_rootfiles:
    opf = rootfile.attrib["full-path"]
    opf_parts = opf.split("/")
    opf_dir = "/".join(opf_parts[:-1])
    opf_filename = opf_parts[-1]
    os.chdir(opf_dir)

    if multiple:
        rootfile_name = "".join(opf_part[:-1])
        print("Starting rootfile "+rootfile_name)
        rootfile_cbz_dir = output_dir_name + "/" + rootfile_name
        rootfile_cbz_name = short_name + "_" + rootfile_name + ".cbz"
    else:
        rootfile_cbz_dir = output_dir_name
        rootfile_cbz_name = short_name + ".cbz"

    os.mkdir(rootfile_cbz_dir)
        
    opf_root = ET.parse(opf_filename).getroot()
    items = opf_root.findall('./{*}manifest/{*}item')
    images = [item for item in items if item.attrib["media-type"].startswith("image/")]
    imagesizes = [get_image_dimensions(image.attrib["href"]) for image in images]
    imgx,imgy = Counter(imagesizes).most_common(1)[0][0]
    print("Image dimensions found to be: "+str(imgx)+"x"+str(imgy))
    
    page_file_names = [opf_root.find("./{*}manifest/{*}item[@id='"+page_ref.attrib["idref"]+"']").attrib["href"] for page_ref in opf_root.findall('./{*}spine/{*}itemref')]

    page = 0
    current_dir = os.getcwd()
    for page_file in page_file_names:
        page += 1
        page_num = str(page).zfill(5) # Hopefully, everything is no more than 99,999 pages long
        page_name = "page_"+page_num+".png"
        
        pagex,pagey = get_viewport_dimensions(page_file)
        if pagex == 0 and pagey == 0:
            pagex = imgx
            pagey = imgy
        if pagex >= imgx and pagey >= imgy:
            scale = 1.0
        else:
            scale = max(imgx/pagex,imgy/pagey)
        print("Rendering page "+page_name+" using scale "+str(scale))

        # We're going to capture output on the next one just so it is not displayed
        subprocess.run(["google-chrome","--headless","--disable-gpu","--screenshot","--force-device-scale-factor="+str(scale),"--window-size="+str(pagex)+","+str(pagey),"file:///"+current_dir+"/"+page_file],capture_output=True)
        os.rename("screenshot.png",rootfile_cbz_dir+"/"+page_name)

    subprocess.run(["zip -j "+base_dir_name+"/"+rootfile_cbz_name+" "+rootfile_cbz_dir+"/*"],shell=True)
