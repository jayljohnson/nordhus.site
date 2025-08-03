FROM jekyll/jekyll:4.3

# Set working directory
WORKDIR /srv/jekyll

# Copy Gemfile and install dependencies first (for better caching)
COPY Gemfile* ./
RUN bundle install

# Create cache directories with proper permissions
RUN mkdir -p .jekyll-cache _site && \
    chown -R jekyll:jekyll .jekyll-cache _site

# Expose ports
EXPOSE 4000 35729

# Default command to serve the site with optimizations
CMD ["bundle", "exec", "jekyll", "serve", \
     "--config", "_config.yml,_config_dev.yml", \
     "--host", "0.0.0.0", \
     "--livereload", \
     "--livereload-port", "35729", \
     "--force_polling", \
     "--incremental", \
     "--watch"]