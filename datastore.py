from google.appengine.ext import db
from google.appengine.api import memcache
import autoproxy2pac

class RuleList(db.Model):
    name = db.StringProperty(required=True)
    url = db.LinkProperty(required=True)
    date = db.StringProperty()
    raw = db.TextProperty()
    code = db.TextProperty()
    
    def update(self):
        rawOld = self.raw
        self.raw, timestamp = autoproxy2pac.fetchRuleList(self.url)
        if timestamp == self.date: return False
        
        self.code = autoproxy2pac.rule2js(self.raw)
        self.date = timestamp
        memcache.set(self.name, self)
        self.put()
        
        if rawOld:
            ChangeLog(self, rawOld, self.raw).put()
        
        return True
    
    def toDict(self):
        return { 'ruleListUrl'  : self.url,
                 'ruleListDate' : self.date,
                 'ruleListCode' : self.code }
    
    @classmethod
    def getList(cls, name):
        data = memcache.get(name)
        if data is not None: return data
        
        data = cls.gql('WHERE name=:1', name).get()
        memcache.add(name, data)
        return data

class ChangeLog(db.Model):
    ruleList = db.ReferenceProperty(RuleList, required=True)
    date = db.DateTimeProperty(auto_now_add=True)
    add = db.StringListProperty()
    remove = db.StringListProperty()
    
    def __init__(self, ruleList, old, new):
        db.Model.__init__(self, ruleList=ruleList)
        
        from difflib import SequenceMatcher
        toSeq = lambda raw: [l for l in raw.splitlines()[1:] if l and not l.startswith('!')]
        old = toSeq(old)
        new = toSeq(new)
        for tag, i1, i2, j1, j2 in SequenceMatcher(a=old, b=new).get_opcodes():
            if tag != 'equal':
                self.remove.extend(old[i1:i2])
                self.add.extend(new[j1:j2])
