import os
from django.http import HttpResponse
from django.shortcuts import redirect, render
import requests,json
from django.views.decorators.csrf import csrf_exempt
import ast
import astor



@csrf_exempt
def index(request):
    return HttpResponse("Hello Devansh")

@csrf_exempt
def format_code(request):
    if request.method == 'POST':
        code = request.POST.get('code', '')
        # print(code)
        formatted_output = code.replace('\n','\\n').replace('"', "'")
        # print('hello',formatted_output)
        request.session['code'] = code
        request.session['my_variable'] = formatted_output
        return createASTfromAPI(request)

@csrf_exempt
def createASTfromAPI(request):
    my_variable = request.session.get('my_variable')
    # print(f"import ast \ncode = '{my_variable}' \nparsed_ast = ast.parse(code) \nast.dump(parsed_ast)")
    r = requests.post('https://online-code-compiler.p.rapidapi.com/v1/' , 
            headers = {
                'X-RapidAPI-Key' : 'bf3d23b953msh22d99c684dcfdebp1ad975jsn742acbd71271',
                'X-RapidAPI-Host' : 'online-code-compiler.p.rapidapi.com',
                'Content-Type' : 'application/json'
            },
            json = {
                    "language": "python3",
                    "version": "latest",
                    "code": f"import ast \ncode = '''{my_variable}''' \nparsed_ast = ast.parse(code) \nprint(ast.dump(parsed_ast))",
                    "input": None
            },
            )
    parsed_output = json.loads(r.text)
    actual_output = parsed_output["output"]
    request.session['output'] = actual_output

    code_to_parse = request.session.get('code')
    # ast_tree = ast.parse(code_to_parse)
    # ast_dict = ast_to_dict(ast_tree)

    keys_to_extract = ['node_type','arg', 'name', 'id', 'value','args']

    result = process_ast(code_to_parse)
    json_result = json.dumps(result)
    # print("Json ---------- ",json_result)

    return HttpResponse(json_result)


@csrf_exempt
# lower level things like bin operations, or simple code like variables
def extract_value(node):
    if isinstance(node, ast.AST):
        return {key: extract_value(value) for key, value in ast.iter_fields(node)}
    elif isinstance(node, list):
        return [extract_value(item) for item in node]
    elif isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Expr):
        return extract_value(node.value)
    elif isinstance(node, ast.BinOp):    
        left = extract_value(node.left)
        right = extract_value(node.right)
        return {"left": left, "right": right, "op": node.op}
    else:
        return str(node)

@csrf_exempt
def extract_info(node):
    
    info = {}
    
    if isinstance(node, ast.FunctionDef):
        function_name = node.name    
        info["function"] = node.name
        info["args"] = [arg.arg for arg in node.args.args]
        info["body"] = [extract_info(stmt) for stmt in node.body]

    elif isinstance(node, ast.For):
        info["for_loop"] = {
            "variable": node.target.id,
            "iterable": extract_value(node.iter),
            "body": [extract_info(stmt) for stmt in node.body]
        }

    elif isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                info["variable"] = target.id
                info["value"] = extract_value(node.value)
                if hasattr(node.value, 'op'):
                    info["value"]["op"] = extract_operator(node.value.op)


    elif isinstance(node, ast.ClassDef):
        info["class"] = {
            "name": node.name,
        }

    elif isinstance(node, ast.If):
        info["if_statement"] = {}
    
    # Extract condition from the if statement
        if isinstance(node.test, ast.Compare):
            comparators = [extract_value(comp) for comp in node.test.comparators]
            ops = [extract_operator(op) for op in node.test.ops]
            condition = {"left": extract_value(node.test.left), "comparators": comparators, "ops": ops}
        else:
            condition = extract_value(node.test)
        
        info["if_statement"]["condition"] = condition

        # Extract statements inside the if block
        if_statements = []
        for stmt in node.body:
            if_statements.append(astor.to_source(stmt).strip())
        info["if_statement"]["if_statements"] = if_statements

        # Extract statements inside the else block, if present
        else_statements = []
        if node.orelse:
            for stmt in node.orelse:
                else_statements.append(astor.to_source(stmt).strip())
        info["if_statement"]["else_statements"] = else_statements

    return info

def extract_condition(node):
    if isinstance(node, ast.If):
        condition_str = astor.to_source(node.test).strip()
        return condition_str

def extract_operator(node):
    if isinstance(node, ast.Add):
        return "+"
    elif isinstance(node, ast.Sub):
        return "-"
    elif isinstance(node,ast.Mult):
        return "*"
    elif isinstance(node,ast.Div):
        return "/"
    elif isinstance(node, ast.Eq):
        return "Equals"
    elif isinstance(node, ast.NotEq):
        return "NotEquals"
    elif isinstance(node, ast.Lt):
        return "LessThan"
    elif isinstance(node, ast.LtE):
        return "LessThanOrEquals"
    elif isinstance(node, ast.Gt):
        return "GreaterThan"
    elif isinstance(node, ast.GtE):
        return "GreaterThanOrEquals"
    elif isinstance(node, ast.Is):
        return "Is"
    elif isinstance(node, ast.IsNot):
        return "IsNot"
    elif isinstance(node, ast.In):
        return "In"
    elif isinstance(node, ast.NotIn):
        return "NotIn"
    # Add more cases for other operators as needed
    else:
        return str(node)


    
def process_ast(source_code):
    tree = ast.parse(source_code)
    res = [extract_info(node) for node in ast.walk(tree) if isinstance(node, (ast.Assign, ast.FunctionDef, ast.For, ast.If, ast.ClassDef))]
    return res 


