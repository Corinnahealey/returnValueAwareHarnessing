#Sketching out metadata collection for return values. Merge this with the engine.py code at some point.

import matplotlib as plt
import numpy as np
import multiplier as mx

class VarAssignment:
    def __init__(self, depth, is_conditional, is_loop):
        self.depth = depth
        self.is_conditional = is_conditional
        self.is_loop = is_loop

class Retval:
    def __init__(self, value, depth, token_str):
        self.intValue = value
        self.functionName = "default"
        self.libName = ""
        self.lineNumber = 0
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

    def to_dict(self):
        return {
            "intValue": self.intValue,
            "function_name": self.functionName,
            "lib_name": self.libName,
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
            "is_last": self.is_last
        }

    def __str__(self):
        """User-friendly representation (values only)."""
        return ", ".join(str(v) for v in self.to_dict().values())
    
    def __repr__(self):
        return self.__str__()

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

    def expand_ast(self, node, enums):
        #print("        "*depth + str(type(node)))
        
        if (isinstance(node, mx.ast.CallExpr)):
            self.callcount += 1
            if "err" in node.callee.expression_token.data.lower():
                error_func_called = True
        elif isinstance(node, mx.ast.WhileStmt) or isinstance(node, mx.ast.ForStmt):
            was_already_loop = self.is_loop
            self.is_loop = True
            self.depth += 1

            self.callcount = 0

            self.expand_ast(node.body, enums)

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
                self.expand_ast(child, enums)

            callcount = 0
            self.error_func_called = False
            if not was_already_conditional:
                self.is_conditional = False
            self.depth -= 1
        elif isinstance(node, mx.ast.CompoundStmt) or isinstance(node, mx.ast.LabelStmt) or isinstance(node, mx.ast.SwitchStmt):
            for child in node.children:
                self.expand_ast(child, enums)
            self.callcount = 0
            self.error_func_called = False

        if isinstance(node, mx.ast.ReturnStmt):
            #print(f"        Found return stmt")
            #print(f"        Depth {self.depth}")
            #print(f"        Is conditional {self.is_conditional}")
            #print(f"        Is in loop {self.is_loop}")
            #print(f"        Callexprs in block {self.callcount}")
            #print(f"        Errno function called {self.error_func_called}")
            #print("")
            
            if not node.return_value:
                return
            token_type = node.return_value.expression_token.category

            retval = Retval(node.return_value.expression_token.data, self.depth, node.return_value.expression_token.data)

            if token_type == 9:
                #TODO: assign int literal value
                pass

            if token_type == 11 or token_type == 12 or token_type == 13:
                #print(f"Found var {node.return_value.expression_token.data}")
                retval.intValue = 0
                retval.is_var = True

            if token_type == 14:
                #print("Found func")
                retval.intValue = 0 #TODO: propagate function return value
                retval.is_callexpr = True

            if token_type == 26:
                #print("Found enum")
                if node.return_value.expression_token.data not in enums:
                    print(f"Warning: Enum {node.return_value.expression_token.data} not found in enums")
                retval.intValue = None #TODO: get enum value
                retval.is_conditional = self.is_conditional
                retval.is_enum = True

            retval.is_loop = self.is_loop
            retval.is_conditional = self.is_conditional
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
    for decl in mx.ast.EnumDecl.IN(index):
        count = 0

        for enum in decl.enumerators:
            if enum.name in enums:
                continue

            #print(enum.name)

            if not enum.initializer_expression:
                enums[enum.name] = str(count)
            else:
                if not hasattr(enum.initializer_expression, "sub_expression"):
                    enums[enum.name] = str(count)
                    continue

                subexpr = enum.initializer_expression.sub_expression

                if isinstance(subexpr, mx.ast.DeclRefExpr):
                    enums[enum.name] = subexpr.r_angle_token.data
                elif isinstance(subexpr, mx.ast.UnaryOperator):
                    if not hasattr(subexpr.sub_expression, "sub_expression") or not hasattr(subexpr.sub_expression, "token"):
                        enums[enum.name] = str(count)
                        continue
                    enums[enum.name] = subexpr.operator_token.data + subexpr.sub_expression.token.data
                elif hasattr(subexpr, "token"):
                    enums[enum.name] = subexpr.token.data
                else:
                    continue
            
            #print(enums[enum.name])
            #print(count)
            count += 1
import inspect

def get_public_methods_with_params(obj):
    methods = []
    for name in dir(obj):
        if name.startswith("_"):
            continue  # Skip private or magic methods
        attr = getattr(obj, name)
        if callable(attr):
            try:
                sig = inspect.signature(attr)
                methods.append(f"{name}{sig}")
            except ValueError:
                # In case the signature cannot be retrieved (e.g., built-ins)
                methods.append(f"{name}(?)")
    return methods


def ExtractLib(idx, libName):
    
    funcs = dict()
    enums = dict()

    get_enums(idx, enums)
  
    for func in mx.ast.FunctionDecl.IN(idx):
        if (isinstance(func.return_type, mx.ast.BuiltinType) and func.return_type.builtin_kind == 426):
            continue

        if not func.body:
            continue

        #print(func.name)
        
        function = Function(func.name)
        funcs[func.name] = function

        for child in func.body.children:
            function.expand_ast(child, enums)
            function.get_vars(child)
        
        if (len(function.retlist)):
            function.retlist[-1].is_last = True
        
        for ret in function.retlist:
            ret.functionName = func.name 
            ret.libName = libName

    #print(get_public_methods(idx))
    return funcs 
    

#ExtractLib("../demos/lexbor/lib.db")