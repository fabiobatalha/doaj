"""
Home for all article upload and ingest processing code

Main point of entry is the ingest_file function, which will do the validation, and if 
a crosswalk is available pass the DOM to be xwalked

"""

from lxml import etree
from portality import models
from portality.core import app
from datetime import datetime

class XWalk(object):
    def add_journal_info(self, article):
        """
        this function takes an article and makes sure that it is populated
        with all the relevant info from its owning parent object
        """
        bibjson = article.bibjson()
        
        # first, get the ISSNs associated with the record
        pissns = bibjson.get_identifiers(bibjson.P_ISSN)
        eissns = bibjson.get_identifiers(bibjson.E_ISSN)
        allissns = list(set(pissns + eissns))
        
        # find a matching journal record from the index
        journal = None
        for issn in allissns:
            journals = models.Journal.find_by_issn(issn)
            if len(journals) > 0:
                # there should only ever be one, so take the first one
                journal = journals[0]
                break
        
        # we were unable to find a journal
        if journal is None:
            return False
        
        # FIXME: use the journal model API
        # if we get to here, we have a journal record we want to pull data from
        jbib = journal.bibjson()
        
        for s in jbib.subjects():
            bibjson.add_subject(s.get("scheme"), s.get("term"), code=s.get("code"))
        
        if jbib.title is not None:
            bibjson.journal_title = jbib.title
        
        if jbib.get_license() is not None:
            lic = jbib.get_license()
            bibjson.set_journal_license(lic.get("title"), lic.get("type"), lic.get("url"), lic.get("version"), lic.get("open_access"))
        
        if jbib.language is not None:
            bibjson.journal_language = jbib.language
        
        if jbib.country is not None:
            bibjson.journal_country = jbib.country
        
        article.set_in_doaj(journal.get("in_doaj", False))
        return True
    
    def is_legitimate_owner(self, article, owner):
        b = article.bibjson()
        issns = b.get_identifiers(b.P_ISSN)
        issns += b.get_identifiers(b.E_ISSN)
        owners = []
        for issn in issns:
            journals = models.Journal.find_by_issn(issn) # FIXME: could make this query more efficient
            if len(journals) == 0:
                # if we can't find a matching journal, this article is a dud
                return False
            owners += [j.owner for j in journals if j.owner is not None]
        owners = list(set(owners))
        
        if len(owners) == 0:
            # no owner means we can't confirm
            return False
        if len(owners) > 1:
            # multiple owners means ownership of this article is confused
            return False
        
        return owners[0] == owner

class FormXWalk(XWalk):
    format_name = "form"
    
    def crosswalk_form(self, form, add_journal_info=True):
        article = models.Article()
        bibjson = article.bibjson()
        
        # title
        bibjson.title = form.title.data
        
        # doi
        doi = form.doi.data
        if doi is not None and doi != "":
            bibjson.add_identifier(bibjson.DOI, doi)
        
        # authors
        for subfield in form.authors:
            author = subfield.form.name.data
            aff = subfield.form.affiliation.data
            if author is not None and author != "":
                bibjson.add_author(author, affiliation=aff)
                
        # abstract
        abstract = form.abstract.data
        if abstract is not None and abstract != "":
            bibjson.abstract = abstract
        
        # keywords
        keywords = form.keywords.data
        if keywords is not None and keywords != "":
            ks = [k.strip() for k in keywords.split(",")]
            bibjson.set_keywords(ks)
            
        # fulltext
        ft = form.fulltext.data
        if ft is not None and ft != "":
            bibjson.add_url(ft, "fulltext")
        
        # publication year/month
        py = form.publication_year.data
        pm = form.publication_month.data
        if pm is not None:
            bibjson.month = pm
        if py is not None:
            bibjson.year = py
            
        # pissn
        pissn = form.pissn.data
        if pissn is not None and pissn != "":
            bibjson.add_identifier(bibjson.P_ISSN, pissn)
        
        # eissn
        eissn = form.eissn.data
        if eissn is not None and eissn != "":
            bibjson.add_identifier(bibjson.E_ISSN, eissn)
        
        # volume
        volume = form.volume.data
        if volume is not None and volume != "":
            bibjson.volume = volume
        
        # number
        number = form.number.data
        if number is not None and number != "":
            bibjson.number = number
        
        # start date
        start = form.start.data
        if start is not None and start != "":
            bibjson.start_page = start
        
        # end date
        end = form.end.data
        if end is not None and end != "":
            bibjson.end_page = end
        
        # add the journal info if requested
        if add_journal_info:
            self.add_journal_info(article)
        
        return article

class DOAJXWalk(XWalk):
    format_name = "doaj"
    schema_path = app.config.get("SCHEMAS", {}).get("doaj")
    
    def __init__(self):
        # load the schema into memory for more efficient usage in repeat calls to the crosswalk
        if self.schema_path is None:
            raise IngestException("Unable to validate for DOAJXWalk, as schema path is not set in config")
        
        try:
            schema_file = open(self.schema_path)
            schema_doc = etree.parse(schema_file)
            self.schema = etree.XMLSchema(schema_doc)
        except:
            raise IngestException("There was an error attempting to load schema from " + self.schema_path)
    
    def validate(self, doc):
        valid = self.schema.validate(doc)
        return valid
    
    def crosswalk_file(self, handle, add_journal_info=True, article_callback=None, limit_to_owner=None, fail_callback=None):
        doc = etree.parse(handle)
        return self.crosswalk_doc(doc, add_journal_info=add_journal_info, article_callback=article_callback, 
                                    limit_to_owner=limit_to_owner, fail_callback=fail_callback)
    
    def crosswalk_doc(self, doc, add_journal_info=True, article_callback=None, limit_to_owner=None, fail_callback=None):
        success = 0
        fail = 0
        
        root = doc.getroot()
        for record in root:
            article = self.crosswalk_article(record, add_journal_info=add_journal_info)
            if limit_to_owner is not None:
                legit = self.is_legitimate_owner(article, limit_to_owner)
                if not legit:
                    fail += 1
                    if fail_callback:
                        fail_callback(article)
                    continue
            if article_callback is not None:
                article_callback(article)
            success += 1
        return success, fail
    
    def crosswalk_article(self, record, add_journal_info=True):
        """
        Example record:
        <record>
          <language>eng</language>
          <publisher>Co-Action Publishing</publisher>
          <journalTitle>Tellus A</journalTitle>
          <issn>0280-6495</issn>
          <eissn>1600-0870</eissn>
          <publicationDate>2014-02-05</publicationDate>
          <volume>66</volume>
          <issue>0</issue>
          <startPage>1</startPage>
          <endPage>18</endPage>
          <doi>10.3402/tellusa.v66.21390</doi>
          <publisherRecordId>21390</publisherRecordId>
          <documentType>Original</documentType>
          <title language="eng">LakeMIP Kivu...</title>
          <authors>
             <author>
                <name>WIM Thiery</name>
                <email>wim.thiery@ees.kuleuven.be</email>
                <affiliationId>1</affiliationId>
            </author>
         </authors>
          <affiliationsList>
             <affiliationName affiliationId="1">
		            Department of Earth and Environmental Sciences...</affiliationName>
         </affiliationsList>
          
          <abstract language="eng">The African great...</abstract>
          <fullTextUrl format="pdf">http://www.tellusa.net/index.php/tellusa/article/download/21390/pdf_1</fullTextUrl>
          <keywords language="eng">
             <keyword>lake modelling</keyword>
         </keywords>
        </record>
        """
        article = models.Article()
        bibjson = article.bibjson()
        
        # language
        lang = _element(record, "language")
        if lang is not None:
            bibjson.journal_language = lang
        
        # publisher
        pub = _element(record, "publisher")
        if pub is not None:
            bibjson.publisher = pub
        
        # journal title
        jt = _element(record, "journalTitle")
        if jt is not None:
            bibjson.journal_title = jt
        
        # p-issn
        pissn = _element(record, "issn")
        if pissn is not None:
            bibjson.add_identifier(bibjson.P_ISSN, pissn.upper())
        
        # e-issn
        eissn = _element(record, "eissn")
        if eissn is not None:
            bibjson.add_identifier(bibjson.E_ISSN, eissn.upper())
        
        # publication date
        pd = _element(record, "publicationDate")
        if pd is not None:
            y, m = _year_month(pd)
            if y is not None:
                bibjson.year = y
            if m is not None:
                bibjson.month = m
        
        # volume
        vol = _element(record, "volume")
        if vol is not None:
            bibjson.volume = vol
        
        # issue
        iss = _element(record, "issue")
        if iss is not None:
            bibjson.number = iss
        
        # start page
        sp = _element(record, "startPage")
        if sp is not None:
            bibjson.start_page = sp
        
        # end page
        ep = _element(record, "endPage")
        if ep is not None:
            bibjson.end_page = ep
        
        # doi
        doi = _element(record, "doi")
        if doi is not None:
            bibjson.add_identifier(bibjson.DOI, doi)
        
        # publisher record id
        pri = _element(record, "publisherRecordId")
        if pri is not None:
            article.set_publisher_record_id(pri)
        
        # document type
        dt = _element(record, "documentType")
        if dt is not None:
            # FIXME: outstanding question as to what to do with this
            pass
        
        # title
        title = _element(record, "title")
        if title is not None:
            bibjson.title = title
        
        # authors
        ## first we need to extract the affiliations
        affiliations = {}
        affel = record.find("affiliationsList")
        if affel is not None:
            for ael in affel:
                affid = ael.get("affiliationId")
                aff = ael.text
                affiliations[affid] = aff
        ## now crosswalk each author and dereference their affiliation from the table
        authorsel = record.find("authors")
        if authorsel is not None:
            for ael in authorsel:
                name = _element(ael, "name")
                email = _element(ael, "email")
                affid = _element(ael, "affiliationId")
                aff = affiliations.get(affid)
                bibjson.add_author(name, email=email, affiliation=aff)
        
        # abstract
        abstract = _element(record, "abstract")
        if abstract is not None:
            bibjson.abstract = abstract
        
        # fulltext
        ftel = record.find("fullTextUrl")
        if ftel is not None and ftel.text is not None and ftel.text != "":
            ct = ftel.get("format")
            url = ftel.text
            bibjson.add_url(url, "fulltext", ct)
        
        # keywords
        keyel = record.find("keywords")
        if keyel is not None:
            for kel in keyel:
                if kel.text != "":
                    bibjson.add_keyword(kel.text)
        
        # add the journal info if requested
        if add_journal_info:
            self.add_journal_info(article)
            
        return article

class IngestException(Exception):
    pass

###############################################################################
## some convenient utilities
###############################################################################

def _year_month(date):
    try:
        stamp = datetime.strptime(date, "%Y-%m-%d")
        return stamp.year, stamp.month
    except:
        pass
    try:
        stamp = datetime.strptime(date, "%Y-%m")
        return stamp.year, stamp.month
    except:
        pass
    try:
        stamp = datetime.strptime(date, "%Y")
        return stamp.year, None
    except:
        pass
    return None, None
    

def _element(xml, field):
    el = xml.find(field)
    if el is not None and el.text is not None and el.text != "":
        return el.text
    return None
    
################################################################################
## main entry point to this module
################################################################################

xwalk_map = {DOAJXWalk.format_name : DOAJXWalk}


def article_save_callback(article):
    article.save()
    
def ingest_file(handle, format_name=None, owner=None):
    try:
        doc = etree.parse(handle)
    except:
        raise IngestException("Unable to parse XML file")
    
    xwalk = None
    valid = False
    if format_name is not None:
        klazz = xwalk_map.get(format_name)
        if klazz is not None:
            xwalk = klazz()
            valid = xwalk.validate(doc)
    
    if not valid: # which can happen if there was no format name or if the format name was wrong
        # look for an alternative
        for name, x in xwalk_map.iteritems():
            if format_name is not None and format_name != name:
                # we may have already tried validating with this one already
                continue
            inst = x()
            valid = inst.validate(doc)
            if valid:
                xwalk = inst
                break
    
    # did we manage to detect a crosswalk?
    if xwalk is None:
        raise IngestException("Unable to validate document with any available ingesters")
    
    # do the crosswalk
    try:
        success, fail = xwalk.crosswalk_doc(doc, article_callback=article_save_callback, limit_to_owner=owner)
        return success, fail
    except:
        raise IngestException("Error occurred ingesting the records in the document")

def check_schema(handle, format_name=None):
    try:
        doc = etree.parse(handle)
    except:
        raise IngestException("Unable to parse XML file")
        
    actual_format = format_name
    valid = False
    if format_name is not None:
        klazz = xwalk_map.get(format_name)
        if klazz is not None:
            xwalk = klazz()
            valid = xwalk.validate(doc)
    
    if not valid: # which can happen if there was no format name or if the format name was wrong
        # look for an alternative
        for name, x in xwalk_map.iteritems():
            if format_name is not None and format_name != name:
                # we may have already tried validating with this one already
                continue
            inst = x()
            valid = inst.validate(doc)
            if valid:
                actual_format = name
                break
    
    if not valid:
        return False
    
    return actual_format







