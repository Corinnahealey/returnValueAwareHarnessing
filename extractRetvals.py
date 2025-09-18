#Sketching out metadata collection for return values. Merge this with the engine.py code at some point.

import matplotlib as plt
import numpy as np
import multiplier as mx
import os

class VarAssignment:
    def __init__(self, depth, is_conditional, is_loop):
        self.depth = depth
        self.is_conditional = is_conditional
        self.is_loop = is_loop

class Retval:
    def __init__(self, value, depth, token_str):

    #    if isinstance(value, (int, float)) and not isinstance(value, bool):
       # self.intValue = value
     #   else:
        self.intValue = None

        self.functionName = "default"
        self.libName = ""
        self.lineNumber = 0
        self.fileName = ""
        self.depth = depth
        self.token_str = token_str
        self.in_loop = False
        self.in_conditional = False
        self.is_var = False
        self.is_callexpr = False
        self.is_enum = False
        self.error_func_called = False
        self.callexprs_in_block = 0
        self.is_last = False
        self.error_handling = "Needs Manual Analysis"

    def to_dict(self):
        return {
            "int_value": self.intValue,
            "function_name": self.functionName,
            "lib_name": self.libName,
            "file_name" : self.fileName,
            "line_number": self.lineNumber,
            "depth": self.depth,
            "token_str": self.token_str,
            "in_loop": self.in_loop,
            "in_conditional": self.in_conditional,
            "is_var": self.is_var,
            "is_callexpr": self.is_callexpr,
            "is_enum": self.is_enum,
            "error_func_called": self.error_func_called,
            "callexprs_in_block": self.callexprs_in_block,
            "is_last": self.is_last,
            "error_handling" : self.error_handling
        }

    def __str__(self):
        """User-friendly representation (values only)."""
        return ", ".join(str(v) for v in self.to_dict().values())

    def __repr__(self):
        return self.__str__()


    @classmethod
    def get_formatted_keys(cls):
        dummy = cls(0, 0, "")  # make a throwaway object
        keys = dummy.to_dict().keys()
        return ", ".join(k.replace("_", " ") for k in keys)

class Function:
    def __init__(self, name):
        self.name = name
        self.retlist = []
        self.vars = []

        self.callcount = 0
        self.error_func_called = False
        self.is_conditional = False
        self.is_loop = False
        self.depth = 0

    def expand_ast(self, node, enums, idx, enum_values_map):
       
        import multiplier
        dir(multiplier)
        
        if (isinstance(node, mx.ast.CallExpr)):
            self.callcount += 1
            if "err" in node.callee.expression_token.data.lower():
                error_func_called = True
        elif isinstance(node, mx.ast.WhileStmt) or isinstance(node, mx.ast.ForStmt):
            was_already_loop = self.is_loop
            self.is_loop = True
            self.depth += 1

            self.callcount = 0

            self.expand_ast(node.body, enums, idx, enum_values_map)

            self.callcount = 0
            self.error_func_called = False
            if not was_already_loop:
                self.is_loop = False
            self.depth -= 1
        elif isinstance(node, mx.ast.IfStmt) or isinstance(node, mx.ast.CaseStmt) or isinstance(node, mx.ast.CXXTryStmt) or isinstance(node, mx.ast.CXXCatchStmt):
            was_already_conditional = self.is_conditional
            self.is_conditional = True
            self.depth += 1

            self.callcount = 0

            for child in node.children:
                self.expand_ast(child, enums, idx, enum_values_map)

            callcount = 0
            self.error_func_called = False
            if not was_already_conditional:
                self.is_conditional = False
            self.depth -= 1
        elif isinstance(node, mx.ast.CompoundStmt) or isinstance(node, mx.ast.LabelStmt) or isinstance(node, mx.ast.SwitchStmt):
            for child in node.children:
                self.expand_ast(child, enums, idx, enum_values_map)
            self.callcount = 0
            self.error_func_called = False

        if isinstance(node, mx.ast.ReturnStmt):

            if not node.return_value:
                return

            token_type = node.return_value.expression_token.category
            
            saw_return = False
            collected_data = []

            for t in node.tokens:
                if saw_return:
                    collected_data.append(t.data)
                elif t.data == "return":
                    saw_return = True
            
            joined_data = ''.join(collected_data)

            # NULL is expanded to ((void*)0)
            if joined_data ==  " ((void*)0)":
                joined_data = "NULL"
                 

            joined_data = joined_data.replace('"', '""')
            joined_data = f'"{joined_data}"'

            retval = Retval(node.return_value.expression_token.data, self.depth, joined_data)
            if joined_data == "NULL":
                retval.intValue = 0 
            
            fileID = None

            for f in idx.files:
                result = f.containing(node)
                if result:
                    fileID = result.id
                    break
            file_path = None

            for path, fid in idx.file_paths.items():
                if fid == fileID:
                    file_path = path
                    break
            retval.fileName = file_path
            token = node.return_value.expression_token
            loc = token.location(multiplier.frontend.FileLocationCache())
            #print(dir(token))

            if len(loc) >= 1:
                retval.lineNumber = loc[0]
              #  if token.category == 8:
                   # print (retval.lineNumber)
                if retval.lineNumber == 89:
                    if retval.lineNumber == 89:

                        line_numbers = []

                        for t in node.tokens:
                            try:
                                loc = t.location(multiplier.frontend.FileLocationCache())
                                if loc and len(loc) > 0:
                                    line_numbers.append(loc[0])
                            except Exception as e:
                                print(f"Error getting location for token {t}: {e}")

                        # Filter out 89 because for some reason, returning null results in the line number being always set to 89..?
                        non_89_lines = [ln for ln in line_numbers if ln != 89]

                        if non_89_lines:
                            retval.lineNumber = max(non_89_lines)
                        elif line_numbers:
                            retval.lineNumber = max(line_numbers)  # They're all 89
                        else:
                            retval.lineNumber = 89  # Nothing available

                
            if token_type == 9:
               retval.intValue = node.return_value.expression_token.data
                #TODO: assign int literal value
                #pass

            if token_type == 11 or token_type == 12 or token_type == 13:
                #print(f"Found var {node.return_value.expression_token.data}")
                #retval.intValue = 0
                retval.is_var = True

            if token_type == 14:
                #print("Found func")
                #retval.intValue = 0 #TODO: propagate function return value
                retval.is_callexpr = True

            if token_type == 26:
               # print(enum_values_map)
                #print("Found enum")
                #if node.return_value.expression_token.data not in enums:
                    #print(f"Warning: Enum {node.return_value.expression_token.data} not found in enums")
                key = retval.token_str.strip().strip('"').strip("'").replace(" ", "")
                retval.intValue = enum_values_map.get(key)
                #print(key + " " + str(retval.intValue))
                retval.is_conditional = self.is_conditional
                retval.is_enum = True

            retval.in_loop = self.is_loop
            retval.in_conditional = self.is_conditional
            retval.callexprs_in_block = self.callcount
            retval.error_func_called = self.error_func_called
            self.retlist.append(retval)

            return

    #Assumption: The first assignment to a var is the success value
    def get_vars(self, node):
        if isinstance(node, mx.ast.DeclStmt):
            for decl in node.declarations:
                if isinstance(decl, mx.ast.VarDecl):
                    if isinstance(decl.initializer, mx.ast.IntegerLiteral):
                        #print(f"    {decl.name} assigned {decl.initializer.token.data}")
                        continue
                    if isinstance(decl.initializer, mx.ast.ImplicitCastExpr):
                        continue
                        #print(f"    {decl.name} assigned {decl.initializer.expression_token.data}")
                    if isinstance(decl.initializer, mx.ast.BinaryOperator) and decl.initializer.operator_token.data == "=":
                        #print(f"    {decl.name} assigned {decl.initializer.rhs.expression_token.data}")
                        continue

        if isinstance(node, mx.ast.CompoundStmt):
            for child in node.children:
                self.get_vars(child)
        if isinstance(node, mx.ast.WhileStmt) or isinstance(node, mx.ast.ForStmt):
            was_already_loop = self.is_loop
            self.is_loop = True
            self.depth += 1

            self.get_vars(node.body)

            if not was_already_loop:
                self.is_loop = False
            self.depth -= 1
        if isinstance(node, mx.ast.IfStmt):
            was_already_conditional = self.is_conditional
            self.is_conditional = True
            self.depth += 1

            for child in node.children:
                self.get_vars(child)

            if not was_already_conditional:
                self.is_conditional = False
            self.depth -= 1

#Re-implemented get_enums() here because I think it would be useful to get the real integer value placed in Retval

def get_enums(index, enums):
    enum_values_map = {}
    unresolved_aliases = []
    for decl in mx.ast.EnumDecl.IN(index):
        count = 0

        for enum in decl.enumerators:
            if enum.name in enums:
                continue

            if not enum.initializer_expression:
                enums[enum.name] = str(count)
            else:
                try:
                    enum_values_map[enum.name] = str(int(enum.tokens[-1].data.strip(), 0))
                    if(enum.name == "LXB_STATUS_ERROR_OBJECT_IS_NULL"):
                        print("FOUND")
                except Exception as e:
                    unresolved_aliases.append((enum.name, enum.tokens[-1].data.strip()))
   

            count += 1
    for name, alias in unresolved_aliases:
        resolved_value = enum_values_map.get(alias)

        if resolved_value is not None:
            enum_values_map[name] = resolved_value
        else:
            print(f"Could not resolve alias: {name} -> {alias}")

    return enum_values_map
import inspect

def get_public_methods_with_params(obj):
    methods = []
    for name in dir(obj):
        if name.startswith("_"):
            continue  
        attr = getattr(obj, name)
        if callable(attr):
            try:
                sig = inspect.signature(attr)
                methods.append(f"{name}{sig}")
            except ValueError:
                methods.append(f"{name}(?)")
    return methods


def ExtractLib(idx, libName, headers):

    funcs = dict()
    enums = dict()

    enums_value_map = get_enums(idx, enums)

    for func in mx.ast.FunctionDecl.IN(idx):
        if (isinstance(func.return_type, mx.ast.BuiltinType) and func.return_type.builtin_kind == 426):
            continue

        if not func.body:
            continue

        function = Function(func.name)
        funcs[func.name] = function

        for child in func.body.children:
            function.expand_ast(child, enums, idx, (enums_value_map | enums))
            function.get_vars(child)

        if (len(function.retlist)):
            function.retlist[-1].is_last = True

        for ret in function.retlist:
            ret.functionName = func.name
            ret.libName =  os.path.basename(os.path.dirname(libName))

    return funcs



