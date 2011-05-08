import cgi
from uuid import UUID 

from lxml import etree

try:
    import re2 as re
except ImportError:
    import re

class XMLEncoder(object):

    _is_uuid = re.compile(r'^\{?([0-9a-f]{8}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{12})\}?$', re.I)

    def __init__(self, data, doc_el='document', encoding='UTF-8', **params):
        self.data = data
        self.document = etree.Element(doc_el, **params)
        self.encoding = encoding

    
    def to_string(self, indent=True, declaration=True):
        return etree.tostring(self.to_xml(),
                              encoding=self.encoding,
                              xml_declaration=declaration,
                              pretty_print=indent
                              )


    def to_xml(self):
        if self.data:
            self.document = self._update_document(self.document, self.data)
        return self.document


    def from_string(self, string):
        self.document = etree.parse(StringIO(string))
            

    def _update_document(self, node, data):

        if data is None:
            node.text = None

        elif data is True:
            node.set('nodetype', u'boolean')
            node.text = u"true"

        elif data is False:
            node.set('nodetype', u'boolean')
            node.text = u"false"
        
        elif isinstance(data, basestring) and \
             len(data) in (36, 38) and \
             self._is_uuid.match(data):

            try:
                UUID(data)
            except:
                pass
            else:
                node.set('nodetype', u'uuid')
            finally:
                node.text = self._to_unicode(data)

        elif hasattr(data, 'isoformat'):
            try:
                node.text = data.isoformat()
                node.set('nodetype', u'timestamp')
            except TypeError:
                pass

        elif self._is_scalar(data):
            node.text = self._to_unicode(data)

        elif hasattr(data, 'iteritems'):
            #node.set('nodetype',u'map')
            for name, items in data.iteritems():
                if isinstance(name, basestring) and name and str(name[0]) is '?':
                    #  processing instruction 
                    #self._add_processing_instruction(node, items)
                    pass

                elif isinstance(name, basestring) and name and str(name[0]) is '!':
                    # doctype 
                    #self._add_docype(node, items)
                    pass
                
                    
                elif isinstance(name, basestring) and name and not name[0].isalpha():
                    child = etree.SubElement(node, u'node', name=unicode(name))
                    
                elif isinstance(name, basestring) and name:
                    child = etree.SubElement(node, unicode(name))

                else:
                    child = etree.SubElement(node, u"node", name=unicode(name))

                child = self._update_document(child, items)
        
        elif isinstance(data, list):
            node.set('nodetype',u'list')
            for item in data:
                self._update_document(
                    etree.SubElement(node, u'i'),
                    item)
            
        elif isinstance(data, set):
            node.set('nodetype',u'unique-list')
            for item in data:
                self._update_document(
                    etree.SubElement(node, u'i'),
                    item)


        elif hasattr(data, 'send'):
            # generator
            node.set('nodetype',u'generated-list')
            for item in data:
                self._update_document(
                    etree.SubElement(node, u'i'),
                    item)


        elif isinstance(data, tuple):
            node.set('nodetype',u'fixed-list')
            for item in data:
                self._update_document(
                    etree.SubElement(node, u'i'),
                    item)


        elif isinstance(data, object) \
            and hasattr(data, '__slots__'):
            children = ((n, getattr(data, n))
                        for n in data.__slots__
                        if n[0] is not '_' and not hasattr(n, '__call__'))

            sub = etree.SubElement(node,
                                   unicode(data.__class__.__name__),
                                   nodetype="container")

            for item, value in children:
                self._update_document(
                    etree.SubElement(sub, unicode(item)),
                    value)

            
        elif isinstance(data, object):
            children = ((n, v)
                        for n, v in data.__dict__.iteritems()
                        if n[0] is not '_' and not hasattr(n, '__call__'))
                

            sub = etree.SubElement(node,
                                   unicode(data.__class__.__name__),
                                   nodetype="container")

            for item, value in children:
                self._update_document(
                    etree.SubElement(sub, unicode(item)),
                    value)


        else:
            raise Exception('self._update_document: unsupported type "%s"' % type(data))

        return node


    def _is_scalar(self, value):
        return isinstance(value, (basestring, float, int, long))
    

    def _to_unicode(self, string):
        if not string and not self._is_scalar(string):
            return u''

        return unicode(self.escape(string))


    def _add_processing_instruction(self, node, data):

        self.document = etree.ElementTree(self.document)
        
        attrs = []

        if type(data) is dict:
            attrs = self.__dict_to_attrs(dict(
                (name, value)
                for name, value in data.iteritems()
                if name[0].isalpha() and type(value) is not dict
                ))

        #pi = etree.ProcessingInstruction(node[1:])#, ' '.join(attrs))
        pi = etree.ProcessingInstruction(
            'xml-stylesheet',
            'type="text/xml" href="default.xsl"'
            )

    
    def __dict_to_attrs(self, d):
        return ('%s="%s"' % (name, value) for name, value in d.iteritems())


    def escape(self, data):
        if data is None:
            return None

        if isinstance(data, unicode):
            return data

        if isinstance(data, str):
            try:
                data = unicode(data, 'latin1')
            except:
                pass

        return data


    def unicodeToHTMLEntities(self, text):
        """Converts unicode to HTML entities.  For example '&' becomes '&amp;'."""
        return cgi.escape(text).encode('ascii', 'xmlcharrefreplace')

