This post describes a very simple way to create a simple website with a custom domain name and free hosting with github pages.

## Steps
These steps wcan be completed on any web browser without using command line tools.

1. Buy a domain name.  In this example we'll use namecheap.com
2. Set up a new github public repo
3. Add a file named `index.md` to the repo root path.  The file can contain any text like `hello world`
4. Edit the repo settings and enable github pages, enter the custom domain name, and require https
5. Go back to the domain name in namecheap.com and configure the advanced dns settings.  [link to namecheap article](https://www.namecheap.com/support/knowledgebase/article.aspx/9645/2208/how-do-i-link-my-domain-to-github-pages/) 
6. Use any browser to try reaching the website.  Try it with both http:// and https://, and with and without a `www` prefix in the domain name.  if there are errors wait 10 minutes and try again.
7. Edit the `index.md` file to make some changes and see them show up on the website.  It can take a few minutes for the changes to appear because Github pages use a [content delivery network](https://en.m.wikipedia.org/wiki/Content_delivery_network) (CDN) that caches the page.

## Conclusions
It took about an hour to complete these steps from a mobile device browser and create a functioning website.  I did most of this experiment while stuck in traffic as a car passenger.  I did it to scratch a personal itch and see if it could be done in a low tech way.

This current article was also written from a phone browser using the github broswer-based text editor.  It did the job though the ergonomics are not the best.  I simply don't have access to a laptop right now.

Markdown is superior to html for browser-based editing.  It takes way fewer keystrokes to do the same thing.

I am happy with the results.  From here, the next steps I'll probably do are:
- Check out the GitHub repo to my laptop for easier editing
- Look into [using jekyll for nicer formatting](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/about-github-pages-and-jekyll)
