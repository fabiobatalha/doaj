import esprit
from portality.core import app

remote = esprit.raw.Connection("http://ooz.cottagelabs.com:9200", "doaj")
local = esprit.raw.Connection("http://localhost:9200", "doaj")

esprit.tasks.copy(remote, "journal", local, "journal")
esprit.tasks.copy(remote, "account", local, "account")
esprit.tasks.copy(remote, "article", local, "article")
esprit.tasks.copy(remote, "suggestion", local, "suggestion")
esprit.tasks.copy(remote, "upload", local, "upload")
esprit.tasks.copy(remote, "cache", local, "cache")
esprit.tasks.copy(remote, "toc", local, "toc")
esprit.tasks.copy(remote, "lcc", local, "lcc")
esprit.tasks.copy(remote, "article_history", local, "article_history")
esprit.tasks.copy(remote, "editor_group", local, "editor_group")
esprit.tasks.copy(remote, "news", local, "news")
esprit.tasks.copy(remote, "lock", local, "lock")
esprit.tasks.copy(remote, "bulk_reapplication", local, "bulk_reapplication")
esprit.tasks.copy(remote, "bulk_upload", local, "bulk_upload")
esprit.tasks.copy(remote, "journal_history", local, "journal_history")
