====
bget
====

`bget` aims to fill a similar role as wget, but for the modern web. Unfortunatly
wget is working on less and less sites as the "dumb" approach of simply
downloading the html and following links rarely works on complicated sites.

`bget` takes a different approach, instead of downloading the html from a page
we remote-control a real web browser using selenium. We then record every http
request the browser makes. This lets simple javascript work, and also lets us do
things like scrape content from encrypted AWS S3 stores.

Instead of saving web pages as html, we save them in the internet archives [warc
format](https://en.wikipedia.org/wiki/Web_ARChive).

`bget` aims to be as flexable as possible, but when trying to do a complicated
archive sometimes you just need to write code. `bget` can be extended with
custom python classes and also works as a python library, so it can grow to fit
your needs.

A short introduction to archiving using WARC files
--------------------------------------------------

`warc` files (web archive) is the internet-archives standard for archiving
websites. Tools like wget will save a website a bunch of files. `warc` files
instead save http(s) requests/responses.

Quickstart
----------

This only runs on linux.

Install with `pip install --user bget`. Start a browser session with `bget
browse`. You probably want to install an ad-blocker like the excelent
`ublock-origin`.

Now run `bget archive example.com`.


Customization
-------------

`bget` is built on top of selenium and is relativly easy to customize.
