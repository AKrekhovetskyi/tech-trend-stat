# Scrapy settings for techtrendscrape project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from datetime import timedelta
from os import environ, getenv
from pathlib import Path

BOT_NAME = "techtrendscrape"

SPIDER_MODULES = ["techtrendscrape.spiders"]
NEWSPIDER_MODULE = "techtrendscrape.spiders"

IS_TEST = environ["IS_TEST"].lower() in {"1", "true", "yes", "on"}

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = "techtrendscrape (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
# CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
# CONCURRENT_REQUESTS_PER_DOMAIN = 16
# CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
# }

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    "techtrendscrape.middlewares.TechtrendscrapeSpiderMiddleware": 543,
# }

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
# DOWNLOADER_MIDDLEWARES = {
#    "techtrendscrape.middlewares.TechtrendscrapeDownloaderMiddleware": 543,
# }

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    "techtrendscrape.pipelines.MongoPipeline": 1,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
AUTOTHROTTLE_START_DELAY = 2
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 5
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = timedelta(hours=3).seconds
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = []
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

MONGODB_HOST = getenv("MONGODB_HOST") or None
MONGODB_PORT = int(port) if (port := getenv("MONGODB_PORT")) else None
MONGODB_USERNAME = getenv("MONGODB_USERNAME") or None
MONGODB_PASSWORD = getenv("MONGODB_PASSWORD") or None
MONGODB_CLUSTER_HOST = getenv("MONGODB_CLUSTER_HOST") or None

if not MONGODB_HOST and not MONGODB_PORT and not MONGODB_USERNAME and not MONGODB_PASSWORD and not MONGODB_CLUSTER_HOST:
    ITEM_PIPELINES = {"techtrendscrape.pipelines.CSVPipeline": 1}

PATH_TO_FILE_WITH_PROXIES = getenv("PATH_TO_FILE_WITH_PROXIES")
PROXY_LIST = Path(PATH_TO_FILE_WITH_PROXIES).read_text().split() if PATH_TO_FILE_WITH_PROXIES else None
