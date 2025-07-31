FROM jekyll/jekyll:4.2.2

# Set working directory
WORKDIR /srv/jekyll

# Copy Gemfile and install dependencies first (for better caching)
COPY Gemfile* ./
RUN bundle install

# Expose port 4000
EXPOSE 4000

# Default command to serve the site
CMD ["bundle", "exec", "jekyll", "serve", "--host", "0.0.0.0", "--livereload", "--force_polling"]