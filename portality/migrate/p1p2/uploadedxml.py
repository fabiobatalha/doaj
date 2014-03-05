import os, csv
from lxml import etree
from portality import article, models
from datetime import datetime

start = datetime.now()

xml_dir = "/home/richard/tmp/doaj/uploads/doaj-xml"
#xml_dir = "/home/richard/tmp/doaj/uploads/testfail"
corrections_csv = "/home/richard/Dropbox/Documents/DOAJ/corrections.csv"

# start by reading in the publisher id corrections 
corrections = {}
reader = csv.reader(open(corrections_csv))
first = True
for row in reader:
    if first:
        first = False
        continue
    id = row[0]
    publisher = row[4]
    corrections[id] = publisher

txt_files = [f for f in os.listdir(xml_dir) if f.endswith(".txt")]

out_dir = "/home/richard/tmp/doaj/uploads/output"
success_file = os.path.join(out_dir, "success.csv")
malformed_file = os.path.join(out_dir, "malformed.csv")
invalid_file = os.path.join(out_dir, "invalid.csv")
orphan_file = os.path.join(out_dir, "orphan.csv")
duplicate_file = os.path.join(out_dir, "duplicate.csv")
failed_articles = os.path.join(out_dir, "failed_articles.csv")

success_writer = csv.writer(open(success_file, "wb"))
malformed_writer = csv.writer(open(malformed_file, "wb"))
invalid_writer = csv.writer(open(invalid_file, "wb"))
orphan_writer = csv.writer(open(orphan_file, "wb"))
duplicate_writer = csv.writer(open(duplicate_file, "wb"))
failed_articles_writer = csv.writer(open(failed_articles, "wb"))

success_writer.writerow(["DOAJ Filename", "Publisher", "Original Filename", "Date Uploaded"])
malformed_writer.writerow(["DOAJ Filename", "Publisher", "Original Filename", "Date Uploaded", "Contact Email"])
invalid_writer.writerow(["DOAJ Filename", "Publisher", "Original Filename", "Date Uploaded", "Contact Email"])
orphan_writer.writerow(["DOAJ Filename", "Publisher", "Original Filename", "Date Uploaded"])
duplicate_writer.writerow(["Old ID", "Publisher", "Original Filename", "Date Uploaded"])
failed_articles_writer.writerow(["File ID", "Publisher", "Original Filename", "Date Uploaded", "Article Title"])

xwalk = article.DOAJXWalk()

total = len(txt_files)
orphaned = 0
duplicate = 0
failed = 0
valid = 0
invalid = 0
processed = 0
attempted = 0
articles_in = 0
articles_failed = 0

print "importing", total, "files"

def article_callback(article):
    global articles_in
    articles_in += 1
    article.save()
    print "saved article", article.id

def fail_closure(id, publisher, filename, uploaded):
    def fail_callback(article):
        global articles_failed
        articles_failed += 1
        title = article.bibjson().title
        if title is not None:
            title = title.encode("ascii", errors="ignore")
        print "illegitimate owner", title
        failed_articles_writer.writerow([id, publisher, filename, uploaded, title])
    return fail_callback

# read in all the txt files to a datastructure that we can then work with
imports = {}
for t in txt_files:
    processed += 1
    
    txt_file = os.path.join(xml_dir, t)
    txt = open(txt_file)
    
    id = t.split(".")[0]
    publisher = txt.readline().strip()
    filename = txt.readline().strip()
    lm = os.path.getmtime(txt_file)
    uploaded = datetime.fromtimestamp(lm).strftime("%Y-%m-%d %H:%M:%S")
    
    # at this point we apply a correction in the event that we have a 
    # correction for this id
    if id in corrections:
        print t, "correcting publisher", publisher, "-", corrections[id]
        publisher = corrections[id]
    
    acc = models.Account.pull(publisher)
    if acc is None:
        print t, "No such publisher -", publisher
        orphaned += 1
        orphan_writer.writerow([id, publisher, filename, uploaded])
        continue
    
    if publisher in imports:
        if filename in imports[publisher]:
            preup = imports[publisher][filename].keys()[0]
            duplicate += 1
            if lm > preup:
                rid = imports[publisher][filename][preup]
                ruploaded = datetime.fromtimestamp(preup).strftime("%Y-%m-%d %H:%M:%S")
                #print id, publisher, filename, "seen before, so ignoring", rid
                duplicate_writer.writerow([rid, publisher, filename, ruploaded])
                imports[publisher][filename] = {lm : id}
            else:
                duplicate_writer.writerow([id, publisher, filename, uploaded])
                
        else:
            #print "remembering", publisher, filename, lm, id
            imports[publisher][filename] = {lm : id}
    else:
        #print "remembering", publisher, filename, lm, id
        imports[publisher] = { filename : {lm : id} }

# so what we should have by here is an object listing publishers and then unique filenames
# per publisher, which represent the most recent file of that name, then the last mod date
# then the id of the file to be imported

# how many unique publisher names and filenames are there
for publisher, files in imports.iteritems():
    for filename in files:
        attempted += 1

print "orphaned", orphaned, "duplicate", duplicate
print "attempting import of", attempted, "from", total

for publisher, files in imports.iteritems():
    for filename, details in files.iteritems():
        for lm, id in details.iteritems():
            f = id + ".xml"
            xml_file = os.path.join(xml_dir, f)
            
            # now try and parse the file
            doc = None
            try:
                doc = etree.parse(open(xml_file))
            except:
                failed += 1
                print f, "Malformed XML"
                malformed_writer.writerow([f, publisher, filename, uploaded, acc.email])
                continue
            
            # now try and validate the file
            validates = xwalk.validate(doc)
            print f, ("Valid" if validates else "Invalid")
            
            if validates: 
                valid += 1
                success_writer.writerow([f, publisher, filename, uploaded])
            
            if not validates: 
                invalid += 1
                invalid_writer.writerow([f, publisher, filename, uploaded, acc.email])
            
            if validates:
                xwalk.crosswalk_doc(doc, article_callback=article_callback, limit_to_owner=publisher, fail_callback=fail_closure(f, publisher, filename, uploaded))

end = datetime.now()

print "Total", total, "attempted", attempted, "valid", valid, "invalid", invalid, "failed", failed, "duplicate", duplicate, "orphaned", orphaned
print "Created Articles", articles_in, "Failed Articles", articles_failed
print start, end