# FixedFormatEpubToCBZConverter

This tool transforms Comic Books provided as "fixed format" .epub files into
.cbz files (with .png images inside) instead.

I built this after buying an Abrams Arts bundle on HumbleBundle which
said that files would be available as .epuf, .pdf, and .cbz.
In practice, only Parable of the Sower (which had previously been part of
another bundle, and thus I already owned) was available in these three
formats.
All other comic books were available only as epubs.

This didn't worry me at first, as most comic book epubs just have an
image for each page.
But it turned out that when I used my default converter (a shell script
which unzipped the .epub, extracted the images, and then zipped it back
up as a .cbz), I got pages without any text.
All of the lettering was done via fonts.
When I opened these in epub reading programs, the text was present, but
not properly placed.
Only the iPad seemed to be able to read them properly.

So, if you have .epub files like that, this will probably work for you.

## How it Works
One goal for this is simply to convert, but the other is to convert in
the best resolution reasonably possible.
We assume that most pages have an image which serves as their background
and a defined "viewport" in the HTML.
In the comics I applied this to, the viewport on the HTML was smaller than
the resolution of the background image.

To maximize resolution, we scale the page to match the image resolution
rather than the viewport size.
So, the basic overall algorithm looks like:
1) Locate the images from the content directory of the epub
2) Assume that the most common image size is the background image size
(and that it is uniform throughout the book)
3) Extract the viewport size from the HTML
4) Have Google Chrome headless mode generate a screenshot of each page(scaled up by image size divided by viewport size)
5) Zip the screenshots together to make a cbz

Note that this does not preserve page numbers

## Shortcomings

This will not work properly for:
1) Regular epubs (will likely generate the start of each chapter, at most)
2) Fixed-format epubs which are all text or where there are no background
images
3) Fixed-format epubs where some other image size appears more frequently than
the background image size
4) Fixed-format epubs where the pages do not define a viewport measured in pixels

Some of these short-comings may be remedied in the future by adding
command-line overrides.

## Dependencies

Python Lxml libraries
Google Chrome
