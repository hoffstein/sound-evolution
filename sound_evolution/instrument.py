"""A single csound instrument."""

import os
import abc
import simplejson as json
import random
from collections import deque
import csound_adapter

from genetics import Individual

class Instrument(object):
    """A class representing the genome tree."""

    __CONST_PROB = 0.7
    __MAX_CHILDREN = 4
    __OPCODES_FILE = "opcodes_new.json"

    def __init__(self, instrument_tree=None):
        """ Create a new Instrument from a json string or from a tree of python objects """
        if type(instrument_tree) is str:
            self.instrument_tree = json.loads(instrument_tree)
        else:
            self.instrument_tree = instrument_tree

    def to_instr(self):
        """Generate csound ocr code."""
        n = 0
        (code, data, n) = self.__class__.__to_instr(self.instrument_tree, n, "a")
        return code + "out\ta%d" % (n-1)

    @staticmethod
    def __to_instr(node, n, out_type):

        csound_code = ""
        data = []
        for i, child in enumerate(node["children"]):
            intype = child["code"]["outtype"]
            (code, d, n) = Instrument.__to_instr(child, n, intype)
            csound_code += code
            data += (d,)
        (c, d, n) = Instrument.__render(node, data, n, out_type)
        return (csound_code + c, d, n)

    @staticmethod
    def __render(node, data, n, out_type):
        """render the code for a node"""
        
        if out_type == "x":
            out_type = random.choice(["a", "k"])
            
        code = ""
        var = "%s%d" % (out_type, n)
        if node["code"]["type"] == "code":
            code = "%s\t%s\t%s" % (var, node["code"]["symbol"], ", ".join(data))
        elif node["code"]["type"] == "math":
            code = "%s\t=\t%s" % (var, node["code"]["symbol"].join(data))
        elif node["code"]["type"] == "const":
            val = str(node["code"]["value"])
            return ("", val, n)
        return (code +"\n", var, n+1)

    def to_json(self):
        """Serialize instrument to JSON."""
        return json.dumps(self.instrument_tree)

    #     def mutate(self):
    #         """Mutate an instrument."""
    #         traverses = 4
    # a = self.instrument_tree['children']
    # for i in range(traverses):
    #     n = len(a)
    #     cc = random.randint(0,n-1)    #no. to pick a child out
    #     if i < traverses:
    #         if a[cc]['children'] == []: 
    #       a[cc] = Instrument.random({"const_prob": 0.7, "max_children": 4}).instrument_tree
    #       break
    #         else:
    #       a = a[cc]['children']
    #     else:
    #   a[cc] = Instrument.random({"const_prob": 0.7, "max_children": 4}).instrument_tree #something random


    @classmethod
    def random(cls, **keywords):
        """create a random instrument"""

        const_prob = keywords.get("const_prob") or cls.__CONST_PROB
        max_children = keywords.get("max_children") or cls.__MAX_CHILDREN
        opcodes_file = keywords.get("opcodes_file") or cls.__OPCODES_FILE
        root_type = keywords.get("root_type")

        def get_only_type(the_type, opcodes):
            """get only opcodes the have output of the_type"""
            if the_type == "x":
                types = ["a", "k", "x"]
            else:
                types = [the_type]
            return [op for op in opcodes if op["outtype"] in types]
            
        def get_only_not_type(the_type, opcodes):
            """get only opcodes that don't have a certain type"""
            return [op for op in opcodes if op["outtype"] != the_type]

        # get list of available opcodes from json file_
        opcodes = json.loads(file(os.path.join(os.path.dirname(__file__), opcodes_file)).read())

        # select random root element (with a output)
        if root_type and root_type == "t":
            # TODO this 1 here has to be changed to a randint when we have more 
            # than 1 table in the score
            root = Instrument.__make_node(Instrument.__make_const_code("t", 1))
            inst = Instrument(root)
            return inst
        elif root_type:
            filtered = get_only_type(root_type, opcodes)
        else:
            filtered = get_only_not_type("k", opcodes)
        root = Instrument.__make_node(random.choice(filtered))
        todo = deque([root])

        # TODO this number has to be replaced by the max value of the opcode with
        # which it is used
        max_rand_const = 100

        while todo:
            tmp_tree = todo.popleft()
            
            # if it is a math operator
            if tmp_tree["code"]["type"] == "math":

                n_children = random.randint(2, max_children)
                for i in range(n_children):
                    if random.random() > const_prob:
                        filtered = get_only_type(tmp_tree["code"]["intype"], opcodes)
                        random_node = Instrument.__make_node(random.choice(filtered))
                        todo.append(random_node)
                    else:
                        const_code = Instrument.__make_const_code("x", random.random() * max_rand_const)
                        random_node = Instrument.__make_node(const_code)

                    tmp_tree["children"].append(random_node)

            # if it is an opcode
            else:
                for param in tmp_tree["code"]["params"]:
                    
                    # if param type is t alwys plug in a constant
                    if param["type"] == "t":
                        if param["max"] == param["min"]:
                            random_const = param["max"]
                        else:
                            random_const = random.randrange(param["min"], param["max"], 1)
                        const_code = Instrument.__make_const_code("t", random_const)
                        random_node = Instrument.__make_node(const_code)

                    # if it is below constant probability also plug in constant
                    elif random.random() < const_prob:
                        # choose random constant according to input range and type
                        random_const = (random.random() * (param["max"]-param["min"])) + param["min"]
                        const_code = Instrument.__make_const_code("x", random_const)
                        random_node = Instrument.__make_node(const_code)

                    # when above the constant probability plug in another opcode
                    else:
                        filtered = get_only_type(param["type"], opcodes)
                        randop = random.choice(filtered)
                        random_node = Instrument.__make_node(randop)
                        todo.append(random_node)

                    tmp_tree["children"].append(random_node)

        inst = Instrument(root)
        return inst
        
        
    def mutate(self):
        """Mutate an instrument."""
        flat = Instrument.traverse(self.instrument_tree)
        winner = random.randint(0,len(flat)-1)
        random_tree = Instrument.random(root_type=flat[winner]["code"]["outtype"]).instrument_tree
        flat[winner]["code"] = random_tree["code"]
        flat[winner]["children"] = random_tree["children"]

    def ficken(self, individual=None):
        """Cross a tree-instrument with another one."""
        flatself = traverse()
        flatother = other.traverse()
        candidates = []
        while (candidates == []):
            winner = random.randint(0,len(flatself)-1)
            crosstype = flatself[winner]["code"]["type"]
            for item in flatother:
                if item["code"]["type"] == crosstype:
                    candidates.append(item)
        winner2 = random.randint(0,len(candidates)-1)
        temp = flatself[winner]
        flatself[winner] = candidates[winner2]
        candidates[winner2] = temp
        return

    @staticmethod
    def traverse(node):
        flat = []    
        for child in node["children"]:
            if child["code"]["type"] == "const":
                flat.append(child)
            else:
                flat.extend(Instrument.traverse(child))
        flat.append(node)
        return flat        
        
    def fitness(self):
        """Score of the instrument."""
        return


    @staticmethod
    def __make_node(code):
        """Make a node with no children."""
        return { "code": code, "children": []}

    @staticmethod
    def __make_const_code(outtype, val):
        """make a new constant"""
        return {"name": "const", "type": "const", "outtype": outtype, "value": str(val)}



Individual.register(Instrument)


if __name__ == '__main__':
    comp = open("../tests/fixtures/render_error.json").read()
    i = Instrument(comp)
    # i = Instrument.random(const_prob=0.6, max_children=4,
    #     opcodes_file="opcodes_new.json")
    
    # csd = csound_adapter.CSD()
    # csd.orchestra(i)
    # csd.score('i 1 0 2')
    # csd.play()
    # print i.to_json()
    print i.to_instr()