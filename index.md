---
layout: default
title: Jay Johnson - Software Professional & Writer
description: Personal website and blog of Jay Johnson, featuring posts on technology, home projects, career development, and personal experiences.
---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Person",
  "name": "Jay Johnson",
  "url": "{{ site.url }}",
  "sameAs": [
    "https://www.linkedin.com/in/jayljohnson/"
  ],
  "jobTitle": "Software Professional",
  "description": "Personal blog featuring posts on technology, projects, and personal experiences",
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "{{ site.url }}"
  }
}
</script>

Software professional and writer sharing insights on technology, home projects, and personal experiences.

*Views expressed here are my own.*

## Contact
[LinkedIn](https://www.linkedin.com/in/jayljohnson/)

## Blog Posts
{% for post in site.posts %}
[{{ post.date | date: "%Y-%m-%d" }}: {{ post.title }}]({{ post.url }})

{% endfor %}
