#! /usr/bin/env python3
from functools import reduce
import os
import re
import sys

try:
    import shutil
    from terminaltables import AsciiTable
    import texttable
except:
    err = """
    You haven't installed the required dependencies.
    """
    import sys, traceback
    traceback.print_exc()
    print(err)
    sys.exit(0)

try:
    from lib.Colour import Colour
    from lib.Constants import Const
    from lib.files import verify_file, verify_folder
    from lib.hash_dir import get_hash
    from lib.Soup import Soup
    from lib.srbjson import srbjson
    from lib.utils import utils
except:
    from Colour import Colour
    from Constants import Const
    from files import verify_file, verify_folder
    from hash_dir import get_hash
    from Soup import Soup
    from srbjson import srbjson
    from utils import utils


class Problem:
    def __init__(self,p_name,c_name,c_type='contest',p_title="",subm=-1):
        # trivially cached
        self.c_name = str(c_name)
        self.c_type = c_type
        self.p_name = p_name

        # fetchable variables
        self.hash = ""
        self.is_good = False
        self.mult_soln = False
        self.num_test = 0
        self.p_title = p_title
        self.subm = subm        # cant be fetched from prob page, needs to be done by contest
        self.time_limit = ""

        # fetchable long variables
        self.h_desc = ""
        self.i_desc = ""
        self.o_desc = ""
        self.p_desc = ""

        # file cached
        self.inputs = []
        self.outputs = []
        self.soup = None        # TODO in future

        # non cached
        self.link = "https://codeforces.com/"+self.c_type+"/"+self.c_name+"/problem/"+self.p_name
        self.dir = Const.cache_dir + '/'+self.c_type+'/' + self.c_name + "/prob/" + self.p_name

        srbjson.dump_data({
                "c_name":self.c_name,
                "c_type":self.c_type,
                "p_name":self.p_name
            },
            self.dir + "/config",
            srbjson.prob_template)

        self._load_problem()


    def _load_problem(self):
        data = srbjson.extract_data(self.dir+'/config',srbjson.prob_template)

        self.hash = data['hash']
        self.is_good = data['is_good']
        self.mult_soln = data['mult_soln']
        self.num_test = data['num_test']
        self.p_title = data['p_title']
        self.subm = data['subm']
        self.time_limit = data['time_limit']

        self.h_desc = data['h_desc']
        self.i_desc = data['i_desc']
        self.o_desc = data['o_desc']
        self.p_desc = data['p_desc']

        verify_folder(self.dir + '/io')
        now_hash = get_hash(self.dir +'/io')
        if(self.hash != now_hash):
            print(Colour.YELLOW+'Warning prob '+self.p_name+' has been modified'+Colour.END)
            self.hash = now_hash
            srbjson.dump_data({"hash":self.hash}, self.dir + "/config",srbjson.prob_template)

        io = os.listdir(self.dir+'/io')
        if(len(io) != 2* self.num_test):
            if(len(io)!=0):
                print(Colour.RED+self.p_name + ' testcases corrupt' + str(io) + Colour.END)
            self.is_good = False
            srbjson.dump_data({"is_good":self.is_good}, self.dir + "/config",srbjson.prob_template)


    def pull_problem(self,force=False):
        self.fetch_problem(force)
        self.dump_problem()

    def dump_problem(self):
        '''
        dump data, including io
        '''
        for i, inp in enumerate(self.inputs):
            filename = os.path.join(self.dir, 'io', 'Input' + str(i+1))
            verify_file(filename)
            with open(filename, 'w') as handler:
                handler.write(inp)

        for i, out in enumerate(self.outputs):
            filename = os.path.join(self.dir, 'io', 'Output' + str(i+1))
            verify_file(filename)
            with open(filename, 'w') as handler:
                handler.write(out)

        self.hash = get_hash(self.dir +'/io')

        srbjson.dump_data({
                "hash":self.hash,
                "is_good":self.is_good,
                "mult_soln":self.mult_soln,
                "num_test":self.num_test,
                "p_title":self.p_title,
                'subm':self.subm,
                'time_limit':self.time_limit,

                "h_desc":self.h_desc,
                "i_desc":self.i_desc,
                "o_desc":self.o_desc,
                "p_desc":self.p_desc
            },
            self.dir + "/config",
            srbjson.prob_template)


    def fetch_problem(self,force=False):
        '''
        method to fetch a given problem
        we could load it contest within contest using load_from_soup()
        this method is to fetch io for individual problem
        '''
        if(force):
            shutil.rmtree(self.dir)
            self._load_problem()

        if(self.is_good):
            return

        if(self.soup is None):
            self.soup = Soup.get_soup(self.link)

        if(self.soup is None):
            print(Colour.RED+'failed to fetch problem'+Colour.END)
            return

        self.load_from_soup(self.soup)


    def load_from_soup(self,soup):
        '''
        is_good
        mult_soln
        num_test
        p_title
        time_limit

        h_desc
        i_desc
        o_desc
        p_desc

        inputs
        outputs
        soup    # not yet cached
        '''

        self.soup = soup
        self.p_title = soup.findAll('div',{'class':'title'})[0].get_text().strip()
        self.time_limit = soup.findAll('div',{'class':'time-limit'})[0].get_text().strip()
        prob_statement = soup.findAll('div', {'class': 'problem-statement'})[0]

        prob_divs = prob_statement.findAll('div',recursive=False)

        self.p_desc = ""
        p_desc = prob_divs[1].findAll('p')
        for p in p_desc:
            self.p_desc += p.get_text().strip() + '\n\n'

        self.i_desc = ""
        i_desc = prob_statement.findAll('div',{'class':'input-specification'})[0].findAll('p')
        for p in i_desc:
            self.i_desc += p.get_text().strip() + '\n\n'

        self.o_desc = ""
        o_desc = prob_statement.findAll('div',{'class':'output-specification'})[0].findAll('p')
        for p in o_desc:
            self.o_desc += p.get_text().strip() + '\n\n'

        # there are some problems with no description
        self.h_desc = ""
        h_desc_divs = prob_statement.findAll('div',{'class':'note'})
        if(len(h_desc_divs) > 0):
            h_desc = h_desc_divs[0].findAll('p')
            for p in h_desc:
                self.h_desc += p.get_text().strip() + '\n\n'

        self.mult_soln = False
        for word in Const.mult_soln_words:
            if word in self.o_desc:
                self.mult_soln = True
                break

        self.inputs, self.outputs = Problem.get_test_cases(self.soup,self.p_name)
        if(len(self.inputs) > 0 and len(self.outputs) > 0):
            if(len(self.inputs) == len(self.outputs)):
                self.is_good = True
                self.num_test = len(self.inputs)
            else:
                self.is_good = False
                print(Colour.RED+'num of inputs unequal to num of outputs in problem'+Colour.END)


    def display_problem(self):
        if(not self.is_good):
            table_data = [[Colour.FULLRED+Colour.BOLD+'WARNING:'+Colour.END+Colour.RED+' Problem incomplete'+Colour.END]]
            print(AsciiTable(table_data).table)

        table_data = [[Colour.PURPLE+self.p_title+Colour.END],[self.time_limit]]
        print(AsciiTable(table_data).table)

        table_data = [[Colour.CYAN+'Description'+Colour.END],[utils.shrink(self.p_desc,80,[32])]]
        print(AsciiTable(table_data).table)
        table_data = [[Colour.CYAN+'Input'+Colour.END],[utils.shrink(self.i_desc,80,[32])]]
        print(AsciiTable(table_data).table)
        table_data = [[Colour.CYAN+'Output'+Colour.END],[utils.shrink(self.o_desc,80,[32])]]
        print(AsciiTable(table_data).table)

        table_data = [[Colour.CYAN+'Examples'+Colour.END]]
        print(AsciiTable(table_data).table)

        printer = [['#','input','output']]
        for i in range(len(self.inputs)):
            inp = self.inputs[i]
            out = self.outputs[i]
            printer.append([i+1,inp,out])

        tt = texttable.Texttable()
        tt.add_rows(printer)
        print(tt.draw())

        table_data = [[Colour.CYAN+'Hint'+Colour.END],[utils.shrink(self.h_desc,80,[32])]]
        print(AsciiTable(table_data).table)


    @staticmethod
    def get_test_cases(soup,p_name=''):
        """
        Method to parse the html and get test cases
        from a codeforces problem
        return formatted_inputs , formatted_outputs, mult_son

        """
        inputs = soup.findAll('div', {'class': 'input'})
        outputs = soup.findAll('div', {'class': 'output'})

        if len(inputs) == 0 or len(outputs) == 0:
            print(Colour.RED+'Unable to fetch test cases in prob '+p_name + Colour.END)
            return [],[],False

        repls = ('<br>', '\n'), ('<br/>', '\n'), ('</br>', '')

        formatted_inputs, formatted_outputs = [], []
        for inp in inputs:
            pre = inp.find('pre').decode_contents()
            pre = reduce(lambda a, kv: a.replace(*kv), repls, pre)
            pre = re.sub('<[^<]+?>', '', pre)
            formatted_inputs += [pre]
        for out in outputs:
            pre = out.find('pre').decode_contents()
            pre = reduce(lambda a, kv: a.replace(*kv), repls, pre)
            pre = re.sub('<[^<]+?>', '', pre)
            formatted_outputs += [pre]

        return formatted_inputs, formatted_outputs

if __name__ == "__main__":
    p_name = 'B'
    c_name = 1025
    if(len(sys.argv) >= 2): c_name = sys.argv[1]
    if(len(sys.argv) >= 3): p_name = sys.argv[2]

    prob = Problem(p_name,c_name)
    prob.pull_problem(force=False)
    prob.display_problem()
    print(Colour.CYAN+prob.link+Colour.END)
    print(prob.mult_soln)
