# Creating a static website with a custom domain and free hosting
This post describes a simple way to create a basic website with a custom domain name and free hosting with github pages.

## Steps
These steps can be completed on any web browser.  Command line tools are not required.

1. Buy a domain name.  In this example I used [namecheap.com](namecheap.com).
2. Set up a new github public repository (repo)
3. Add a file named `index.md` to the repo root path.  The file can contain any text like `hello world`
4. Edit the repo settings enter the custom domain name.  Then go to the `pages` tab and enable github pages.
5. Go back to the domain name in [namecheap.com](namecheap.com) and configure the advanced dns settings.  See [this namecheap article](https://www.namecheap.com/support/knowledgebase/article.aspx/9645/2208/how-do-i-link-my-domain-to-github-pages/) for details.
6. Use any browser to try reaching the new website.  Try it with both `http://` and `https://`, and with and without a `www` prefix in the domain name.  If there are errors wait 10 minutes and try again.  DNS changes take some time to propagate.
7. Edit the `index.md` file to make some changes and see them show up on the website.  It can take a few minutes for the changes to appear because Github pages use a [content delivery network](https://en.m.wikipedia.org/wiki/Content_delivery_network) (CDN) that caches the page.

## Conclusions
1. It took about an hour to complete these steps from a mobile device browser and create a functioning website.  I did most of this experiment while stuck in traffic as a car passenger.  I did it to scratch a personal itch and see if it could be done in a low tech way.  From a computer with an actual keyboard it could be done a lot more efficiently.  A lot of the time was spent choosing a domain name.
2. This current article was also written from a phone browser using the github broswer-based text editor.  It did the job though the ergonomics are not the best on my mobile device.  I simply don't have access to a laptop right now.
3. Markdown is superior to html for browser-based editing.  It takes way fewer keystrokes to do the same thing.

I am happy with the results.  From here, the next steps I may take are:
- Check out the GitHub repo to my laptop for easier writing from a text editor
- Look into [using jekyll for nicer formatting](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/about-github-pages-and-jekyll)

For now I'll focus on writing and consider this "good enough" for that purpose.
