import re
import os
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.tokenize import PunktSentenceTokenizer
import nltk


def create_qadict_from_pdf(list):
    qlist = '(What|Where|When|Why|How|Who|Which)'
    qmatch = re.compile(qlist + '.*\?')
    # amatch = re.compile()
    lastansmatch = re.compile('(.*)\\n.*(Medication Guide|Manufactured|Distributed|Novartis).*', re.DOTALL)
    a = ""
    mydict = {}
    q = None
    for line in list:
        if qmatch.match(line.get_text()):
            if q != None:
                mydict[q] = a
            q = line.get_text()
            a = ""
            print(line.get_text())
        else:
            if q != None:
                a += line.get_text()
    m = lastansmatch.match(a)
    ans = None
    while (m != None):
        ans = m.group(1)
        m = lastansmatch.match(m.group(1))

    if ans:
        mydict[q] = ans
    else:
        mydict[q] = a
    # print(mydict)
    return mydict

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import HTMLConverter
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTFigure, LTChar, LTAnno, LTLine, LTCurve
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfparser import PDFSyntaxError

OUTPUT_FOLDER = 'output'


def download_pdf(url, OUTPUT=OUTPUT_FOLDER):
    if not os.path.exists(OUTPUT):
        os.makedirs(OUTPUT)

    r = requests.get(url)

    drug_name = url.split('/')[-1]
    output_file_name = os.path.join(OUTPUT, drug_name)
    if not os.path.exists(output_file_name):
        with open(output_file_name, 'wb') as f:
            f.write(r.content)
    return output_file_name, drug_name


def parse_layout(layout, mytext, line_list):
    """Function to recursively parse the layout tree."""
    # mytext = []
    line = ""
    for lt_obj in layout:
        # print(lt_obj.__class__.__name__)
        # print(lt_obj.bbox)
        if isinstance(lt_obj, LTTextLine):
            mytext.append(lt_obj)  # .get_text())
            # print(lt_obj.get_text())
            # print(text)
        elif isinstance(lt_obj, LTLine):
            line_list.append(lt_obj)
        elif isinstance(lt_obj, LTCurve):
            bbox = lt_obj.bbox
            if bbox[1] == bbox[3]:
                line_list.append(lt_obj)
        elif isinstance(lt_obj, LTTextBox):  # or isinstance(lt_obj, LTTextLine):
            # print(lt_obj.get_text())
            mytext, line_list = parse_layout(lt_obj, mytext, line_list)  # Recursive

        # elif isinstance(lt_obj, LTAnno):
        # print(line)
        # print(str(lt_obj._text) + 'xx')
        # if lt_obj._text == '\n':
        #    text.append(line)
        # print(str(type(lt_obj)) + " : " + str(lt_obj.get_text()))
        # print(dir(lt_obj))
    # print(mytext)
    return mytext, line_list


def read_pdf_by_line(pdfpath):
    rsrcmgr = PDFResourceManager()
    codec = 'utf-8'
    laparams = LAParams()
    fp = open(pdfpath, 'rb')
    password = ""
    maxpages = 0
    caching = True
    pagenos = set()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    listout = []
    line_list = []

    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password, caching=caching,
                                  check_extractable=True):
        interpreter.process_page(page)
        layout = device.get_result()
        # print(parse_layout(layout))
        listout, lines = parse_layout(layout, listout, line_list)
        # lines = parse_lines(layout)

        # print(listout)
    device.close()

    return listout, lines

from bs4 import BeautifulSoup as bs
import requests
import json
import pdfminer
from pdfminer.pdfparser import PDFSyntaxError
#import nltk..wordnet.wordnet

ROOT_URL = 'https://www.pharma.us.novartis.com/product-list'


def page_soup(url):
    """return a soup object"""
    html = requests.get(url).text
    return bs(html, 'html.parser')


def get_pdf_hrefs():
    pdf_href_list = []  # {page_num: [BULAs URIs]}
    soup = page_soup(ROOT_URL)

    pdf_link_list = soup.findAll('a', text='Medication guide')
    pdf_href_list += [href.get('href') for href in pdf_link_list]
    return pdf_href_list




def dump_dict_to_json_file(dict_, file_name):
    with open(file_name, 'w') as fp:
        json.dump(dict_, fp, indent=4)


if __name__ == '__main__':

    print('\nscraping medication hrefs ... ')
    # scrape urls of medication list
    pdf_hrefs = get_pdf_hrefs()
    print(pdf_hrefs)
    
    # scrape and extract info of each bula, i.e. name, page link, and download pdf link
    
    # store output to a json file
    output_json_name = "drug_links.json"
    #dump_dict_to_json_file(BULAs, output_json_name)
    drugdict = {}
    for pdf in pdf_hrefs:
        pdfpath, drugname = download_pdf(pdf)
        drugname = drugname.split('_')[0]
        try:
            list, _ = read_pdf_by_line(pdfpath)
            drugdict[drugname] = create_qadict_from_pdf(list)
        except PDFSyntaxError as err:
            print("pdf at: " + pdf + " is invalid")
    print(drugdict)

questions = ['importantinfo', 'whatusedfor', 'howtouse', 'sideeffects', 'ingredients', 'whotakes', 'doctoradvice',
             'storage', 'interactions']
i = iter(drug.values() for drug in drugdict.values())
k = iter(drug.keys() for drug in drugdict.values())
drugs = iter(drug for drug in drugdict.keys())
mytree = {}
mydict = {}


# i = drug.values() for drug in drugdict.values()
# k = drug.keys() for drug in drugdict.values()
def splitanswer(a, mytree, tree, question):
    lasttitle = ''
    setlasttitle = False
    setnextinner = False
    mytree[drug][question] = {}
    tree = tree.add(question)
    m = re.compile("(.*)if you(.*)")

    for answers in re.split('(:)', a):
        if answers == (':'):
            setlasttitle = True
            #setnextinner = False
        asplit = re.split('(\uf0b7)|(\u2022)|( o )|(\\no )|([1-9]\.)', answers)
        answlen = len(asplit)
        if answlen > 1:
            for inner in asplit:
                if inner == None:
                    continue
                elif (inner == '\uf0b7') or (inner == '\u2022') or (inner == ' o ') or (inner == '\no '):
                    setnextinner = True
                    #setlasttitle = False
                    # print('note the following' + inner)
                    continue
                elif setlasttitle:
                    setlasttitle = False
                    if lasttitle != '':
                        try:
                            idx = lasttitle.strip('.').rindex('. ') + 2
                        except ValueError:
                            idx = 0

                        tree = tree.add('title')

                        if m.search(lasttitle,idx):
                            print("\033[31m last title question grouping\033[00m " + m.search(lasttitle[idx:]).group(
                                1))
                            tree.parent.data = m.search(lasttitle,idx).group(1)
                            tree.nodetype = 1
                        tree.data = lasttitle[idx:]
                    # mytree[drug]['info']['inner']
                    # lasttitle.rindex('. ')
                if setnextinner:
                    setnextinner = False
                    if (inner != "") and (inner != '\n'):
                        print('\033[31m inner\033[00m' + inner)
                        try:
                            mytree[drug][question]['inner'].append(inner)
                        except KeyError:
                            mytree[drug][question] = {}
                            mytree[drug][question]['inner'] = [inner]
                        innertree = tree.add('inner')
                        #if m.search(inner):
                            #print("\033[31m inner question grouping\033[00m " + m.search(inner).group(1))
                            #innertree.parent.nodetype = 1
                            #innertree.parent.data = m.search(inner).group(1)
                        innertree.data = inner

                # else:
                # print('inner title ' + inner)
                lasttitle = inner
        else:
            if not setlasttitle:
                print("\033[31m qtitle\033[00m " + answers)
                if m.match(answers):
                    print("\033[31m qtitle question grouping\033[00m " + m.match(answers).group(1))
                    data = m.match(answers).group(1)
                    try:
                        idx = data.strip('.').rindex('. ') + 2
                    except ValueError:
                        idx = 0
                    tree.data = data[idx:]
                    tree = tree.add('qtitle')
                    tree.data = m.match(answers).group(2)
                    tree.nodetype = 1
        # lasttitle = inner


from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import nltk

stopWords = set(stopwords.words('english'))


class Tree:
    """A tree implementation using python's autovivification feature."""

    def __init__(self, name='default'):
        self.name = name
        self.node = []
        self.otherInfo = None
        self.parent = None
        self.data = ""
        self.lastsibling = 0
        self.nodetype = 0

    def draw(self):
        out = self.name + '\n'
        for child in range(0, len(self.node)):
            print(self.node[child].name)
            out += '/' + ' '.join(['' for i in range(0, len(self.node[child].name) + 1)])
        out += '\n'
        for child in range(0, len(self.node)):
            out += self.node[child].__repr__()
        return out

    def nex(self, child):
        "Gets a node by number"
        return self.node[child]

    def incrementlastsibling(self):
        if len(self.node) > self.lastsibling + 1:
            self.lastsibling += 1
            return True
        else:
            return False

    def getnextsibling(self):
        if len(self.parent.node) > self.parent.lastsibling:
            tree = self.parent.nex(self.parent.lastsibling)
            self.parent.incrementlastsibling()
            return tree
        else:
            return self

    def getnextuncle(self):
        if len(self.uptree().uptree().node) > self.uptree().uptree().lastsibling:
            return self.uptree().getnextsibling()
            # return parent.nex(self.uptree().lastsibling)
        else:
            return self.parent

    def uptree(self):
        if self.parent != None:
            return self.parent
        else:
            raise ValueError(self.name + " has no parent node")

    def goto(self, name):
        "Gets the node by name"
        for child in range(0, len(self.node)):
            if (self.node[child].name == name):
                return self.node[child]
        else:
            try:
                if self.name != 'root':
                    tree = self.uptree()
                    return tree.goto(name)
                else:
                    raise ValueError(name + " node not found")
            except ValueError:
                print(name + ' not found')
                raise ValueError(self.name + " has no parent node")

    def info(self):
        for child in range(0, len(self.node)):
            print("\033[31m " + self.node[child].name + ": \033[00m " + self.node[child].data + "\t")
            self.node[child].info()

    def moresiblingsexist(self):
        if self.parent.lastsibling  < len(self.parent.node):
            return True
        else:
            return False

    def nextdata(self):
        out = ''
        if self.nodetype == 0:

            # for child in range(0, len(self.node)):
            # if self.node[child].data != '' and self.node[child].data != '\n':
            # if self.data != '' and self.data != '\n':
            # out = self.data
            if len(self.node) > 0 and self.node[self.lastsibling].data != '' and self.node[
                self.lastsibling].data != '\n':
                # out += str(self.node[child].nextdata())
                out += str(self.node[self.lastsibling].data)
                #if out != '':
                tree = self.node[self.lastsibling]
                self.incrementlastsibling()
                #if self.incrementlastsibling():
                #    out += "\nWould you like more detail?"
                #else:
                #    out += "\nThat's all the details. Is there anything else?"
                return tree, out
            else:
                try:
                    tree = self.nex(0)
                    return tree.nextdata()
                except IndexError:
                    if self.data == '' or self.data == '\n':
                        return self, "\nI have no further information. What else can I help you with?"
                    else:
                        return self, self.data
        else:
            # get next child

            if str(self.node[self.lastsibling].data) != '':
                out = '\nDo you ' + str(self.node[self.lastsibling].data.strip('\n')) + '?'

            else:
                return self.nextdata()
            self.incrementlastsibling()
            return self, out

    def add(self, name):
        node1 = Tree(name)
        self.node.append(node1)
        node1.parent = self
        return node1

    # def traverse(self):

    def __missing__(self, key):
        value = self[key] = type(self)()
        return value


class Pharmabot:
    drug = ''
    drugtries = 0
    qtype = 0
    question = None
    previousqn = None
    answer = ''
    strike1 = False
    tree = Tree()

    def __init__(self, drugdict, drug='', qtype=0):
        self.drugdict = drugdict
        self.drug = drug
        self.drugtries = 0
        self.qtype = qtype

    def __repr__(self):
        return ', '.join(
            ['drug:', self.drug, 'drugtries:', str(self.drugtries), 'question:', str(self.question), 'answer:',
             self.answer])

    def getapptext(self, usertext):
        words = word_tokenize(usertext)
        drugexists, drug = self.checkdrug(self.drugdict, words)
        qn = self.parsequestion(usertext)

        if qn != None:
            self.previousqn = self.question
            self.question = qn
        print(self.question)
        if (not drugexists) and (self.drug == ''):
            self.drugtries += 1
        elif drugexists:
            self.drug = drug
            self.tree = self.drugdict[drug]
            self.drugtries = 0
        self.answer = self.replyqn()
        return '\033[31m' + str(self.answer) + '\033[00m\n'

    def replyqn(self):
        #print('q: ' + str(self.question))
        if (self.drug != '') and (self.question != None) and (self.question != ''):
            if (self.question != 'no') or (self.tree.parent.nodetype == 1):
                self.strike1 = False
            if (self.question == 'no') and (self.tree.parent.nodetype == 1):
                self.question = self.previousqn
                try:
                    self.tree = self.tree.getnextsibling()
                    out = self.tree.data
                    # out += self.tree.nextdata()
                    tree, moreout = self.tree.nextdata()
                    self.tree = tree
                    if moreout != '':
                        out = moreout
                    return out
                except:
                    self.tree.nodetype == 0
                    return "Do you have any other questions?"
            elif (self.question == 'yes') and (self.tree.parent.nodetype == 1):
                self.question = self.previousqn
                self.tree = self.tree.uptree()
                out = self.tree.data
                # out += self.tree.nextdata()
                if out == '' or out == '\n':
                    tree, moreout = self.tree.nextdata()
                    self.tree = tree
                    out = moreout

                else:
                    out += "\nIs there anything else?"
                return out
            elif (self.question == 'yes') and (self.tree.parent.nodetype == 0):
                self.question = self.previousqn
                try:
                    # self.tree = self.tree.getnextuncle()
                    self.tree = self.tree.getnextsibling()
                    out = self.tree.data
                    # out += self.tree.nextdata()
                    tree, moreout = self.tree.nextdata()
                    self.tree = tree
                    if out != moreout:
                        out += moreout

                    if self.tree.moresiblingsexist():
                        out += "\nWould you like more detail?"
                    else:
                        out += "\nI have no further information. What else can I help you with?"

                    return out
                except:
                    self.tree.nodetype == 0
                    return "Do you have any other questions?"

            elif (self.question == 'no') and (self.tree.parent.nodetype == 0):
                self.question = self.previousqn
                if self.strike1:
                    return "Nice talking with you. Bye"
                self.strike1 = True
                return "Ok, is there anything else I can help with?"
            else:
                try:
                    self.tree = self.tree.goto(self.question)
                    out = self.tree.data
                    # out += self.tree.nextdata()
                    tree, moreout = self.tree.nextdata()
                    self.tree = tree
                    if tree.nodetype != 1:
                        out += moreout
                    else:
                        out = moreout
                    if self.tree.moresiblingsexist():
                        if tree.nodetype != 1:
                        out += "\nWould you like more detail?"
                        #else:
                           # out = "\nDo you " + out + " ?"
                    else:
                        out += "\nThat's all the details. Is there anything else?"

                    return out
                except ValueError:
                    return "I don't have information on " + self.question + "\n Is there something else I can help with?"

        elif self.drugtries > 1:
            nodrugreply = 'You can ask about one of these: ' + ', '.join(drugdict.keys())
        elif self.question == None:
            return 'What would you like to know about ' + self.drug + '?'

        else:
            nodrugreply = 'Please enter the drugname'
        return nodrugreply

    # TO DO: replace this function with NLP
    def parsequestion(self, usertext):
        words = word_tokenize(usertext)
        if ('no' in words) and (len(words) < 4):
            return 'no'
        elif ('yes' in words) and (len(words) < 4):
            return 'yes'
        elif ('how' in words) and ('use' in words):
            return questions[2]
        elif ('who' in words) and (('use' in words) or ('take' in words)):
            return questions[5]

        elif ('what' in words) and ('use' in words):
            return questions[1]

        elif ('effects' in words) and ('side' in words):
            return questions[3]
        elif 'ingredients' in words:
            return questions[4]
        elif 'storage' in words:
            return questions[7]
        elif ('doctor' in words) or (('healthcare' in words) and ('practitioner' in words)):
            return questions[6]
        elif 'information' in words:
            return questions[0]

        else:
            return None

    def checkdrug(self, drugdict, words):
        drugs = iter(drug for drug in drugdict.keys())

        while (True):
            try:
                drug = next(drugs)
                if drug in words:
                    print(drug)
                    return (True, drug)
            except StopIteration:
                break
        return False, None

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import nltk

#def getdict(mytree, mydict):
    # from nltk.tokenize import PunktSentenceTokenizer
stopWords = set(stopwords.words('english'))
#from scipy import spatial

# mytree = {}
# try:
for drug in drugs:
    # try:
    mytree[drug] = {}
    tree = mydict[drug] = Tree('root')
    tree.data = drug
    # except NameError:
    #    mytree = {}
    qlist = ['What', 'Where', 'When', 'Why', 'How', 'Who', 'Which']

    for q, a in zip(next(k), next(i)):
        # a = next(i)
        #words = word_tokenize(q)
        #qtype = qlist.index(words[0])
        # print(nltk.pos_tag(nltk.word_tokenize(a)))
        setlasttitle = False
        tokenlist = nltk.pos_tag(nltk.word_tokenize(q))
        qtype = qlist.index(tokenlist[0][0])

        for pairing in tokenlist:
            if pairing[0] not in stopWords:
                #pairing = (nltk.pos_tag(nltk.word_tokenize(w))[0])

                # (lambda x:
                try:

                    if (pairing[1] == 'VB') & (pairing[0] in ['use', 'take']) & (qtype == 4):
                        splitanswer(a, mytree, tree, questions[2])
                        print(questions[2], q)
                        break
                    elif (pairing[1] == 'VB') & (pairing[0] in ['use', 'take']) & (qtype == 5):
                        splitanswer(a, mytree, tree, questions[5])
                        print(questions[5], q)
                        break

                    elif (pairing[1] == 'VB') & (pairing[0] in ['use', 'take']) & (qtype == 0):
                        splitanswer(a, mytree, tree, questions[1])
                        print(questions[1], q)
                        break
                    elif (pairing[1] == 'NN') & (pairing[0] in ['information']) & (qtype == 0):
                        splitanswer(a, mytree, tree, questions[0])
                        print(questions[0], q)

                        break
                        # print(repr(a))
                    elif (pairing[1] == 'NN') & (pairing[0] in ['doctor', 'healthcare', 'practitioner']) & (qtype == 0):
                        splitanswer(a, mytree, tree, questions[6])
                        print(questions[6], q)
                        break
                    elif (pairing[1] == 'NNS') & (pairing[0] in ['ingredients', 'constituents']):
                        splitanswer(a, mytree, tree, questions[4])
                        print(questions[4], q)
                        print(a)
                        break
                    elif (pairing[1] == 'NNS') & (pairing[0] in ['effects', 'side-effects']):
                        splitanswer(a, mytree, tree, questions[3])
                        print(questions[3], q)
                        print(a)
                        break
                    elif ((pairing[1] == 'NN') & (pairing[0] in ['storage'])& (qtype == 0))|((pairing[1] == 'VB') & (pairing[0] in ['store']) & (qtype == 4)):
                        splitanswer(a, mytree, tree, questions[7])
                        print(questions[7], q)
                        print(a)
                        break
                    elif ((pairing[1] == 'NNS') & (pairing[0] in ['interactions'])) | ((pairing[1] == 'VB') & (pairing[0] in ['avoid'])) & (qtype == 0):
                        splitanswer(a, mytree, tree, questions[8])
                        print(questions[8], q)
                        print(a)
                        break

                    # else:
                    # print(w + ' dd' + pairing[1])
                except KeyError:
                    print(w + " not in dict")
                    # v2 if p2(x) else
                    # v3)
print('done')
#return mydict
# except StopIteration:
# pass
import time
mybot = Pharmabot(mydict)
apptext = '\033[31m Hi\033[00m\n'
usertext = ''
delay = 0
def slowprint(astring):
    for letter in astring:
        print(letter,end='')
        time.sleep(delay)
    return ''
while usertext.lower() != 'bye':

    usertext = input(slowprint(apptext))
    apptext = mybot.getapptext(usertext)

