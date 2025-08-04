FROM jekyll/jekyll:latest

# Install additional tools for development workflow
USER root
RUN apk add --no-cache \
    python3 \
    py3-pip

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Add venv to PATH
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /srv/jekyll

# Copy Gemfile and install dependencies first (for better caching)
COPY Gemfile* ./
RUN bundle install

# Switch back to jekyll user after installations
USER jekyll

# Create cache directories with proper permissions
RUN mkdir -p .jekyll-cache _site

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