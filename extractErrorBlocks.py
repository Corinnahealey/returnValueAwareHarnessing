#Sketching out metadata collection for return values. Merge this with the engine.py code at some point.

import matplotlib as plt
import numpy as np
import multiplier as mx

class Retval:
    def __init__(self, value, token_str):
        self.intValue = value
        self.token_str = token_str

class Function:
    def __init__(self, name):
        self.name = name
        self.retlist = []
        self.vars = []
        self.is_error_block = False

    #Extract probable error handling retvals (See Ares paper)
    #Heuristic 1: Logs indicating error messages
    #Heuristic 2: Labels indicating error messages (goto err) - DONE
    #Heuristic 3: Functions indicating error (exit())
    #Heuristic 4: Enum names indicating error - DONE
    #Heuristic 5: Propagated status and value of return statements (this only evaluates to a "maybe error" block)
    def extractBlocks(self, node, enums):
        if (isinstance(node, mx.ast.CallExpr)):
            funcname = node.callee.expression_token.data

            if "err" in funcname.lower():
                self.is_error_block = True
            if "printf" in funcname.lower(): #H1
                args = node.arguments

                for arg in args:
                    if isinstance(arg, mx.ast.StringLiteral):
                        failureKeywords = ["too many", "out of memory", "unable", "cannot", "fail"] #TODO: expand this
                        
                        if any(x in arg.string.lower() for x in failureKeywords):
                            self.is_error_block = True
            #TODO: Figure out how to iterate through the arguments
        elif isinstance(node, mx.ast.WhileStmt) or isinstance(node, mx.ast.ForStmt):
            was_already_error = self.is_error_block
    
            self.extractBlocks(node.body, enums)

            if not was_already_error:
                self.is_error_block = False
        elif isinstance(node, mx.ast.IfStmt) or isinstance(node, mx.ast.CaseStmt) or isinstance(node, mx.ast.CXXTryStmt) or isinstance(node, mx.ast.CXXCatchStmt):
            was_already_error = self.is_error_block
            
            for child in node.children:
                self.extractBlocks(child, enums)

            if not was_already_error:
                self.is_error_block = False
        elif isinstance(node, mx.ast.CompoundStmt) or isinstance(node, mx.ast.SwitchStmt):
            was_already_error = self.is_error_block

            for child in node.children:
                self.extractBlocks(child, enums)

            if not was_already_error:
                self.is_error_block = False
        elif isinstance(node, mx.ast.LabelStmt): #H2
            if "err" in node.name.lower():
                self.is_error_block = True
            for child in node.children:
                self.extractBlocks(child, enums)

        if isinstance(node, mx.ast.ReturnStmt):
            if not node.return_value:
                return
            token_type = node.return_value.expression_token.category

            retval = Retval(node.return_value.expression_token.data, node.return_value.expression_token.data)

            #Extract return value
            if token_type == 9:
                #TODO: assign int literal value
                pass
            if token_type == 11 or token_type == 12 or token_type == 13:
                retval.intValue = 0
            if token_type == 14:
                retval.intValue = 0 #TODO: propagate function return value
            if token_type == 26: #H4
                failureKeywords = ["UNSUCCESS", "INVALID", "ERR", "NOTOK", "FAIL", "NULL", "DISALLOWED", "NOMEM",
                                   "CORRUPT", "MISUSE"]

                if any(x in node.return_value.expression_token.data.upper() for x in failureKeywords):
                    self.is_error_block = True

                if node.return_value.expression_token.data not in enums:
                    print(f"Warning: Enum {node.return_value.expression_token.data} not found in enums")
                retval.intValue = None #TODO: get enum value

            if self.is_error_block:
                self.retlist.append(retval)

            return
    
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

def ExtractLib(index):
    idx = mx.Index.in_memory_cache(mx.Index.from_database(index))

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
            function.extractBlocks(child, enums)
            function.get_vars(child)
        
        if (len(function.retlist)):
            function.retlist[-1].is_last = True
        
    return funcs

#ExtractLib("../demos/lexbor/lib.db")
